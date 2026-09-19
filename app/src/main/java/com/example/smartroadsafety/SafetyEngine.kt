package com.example.smartroadsafety

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.SharedPreferences
import android.content.pm.PackageManager
import android.location.Location
import android.os.Build
import android.os.Looper
import android.telephony.SmsManager
import android.telephony.SubscriptionManager
import android.util.Log
import androidx.core.content.ContextCompat
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import fi.iki.elonen.NanoHTTPD
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.Inet4Address
import java.net.NetworkInterface
import java.net.URL
import java.text.SimpleDateFormat
import java.util.Collections
import java.util.Date
import java.util.Locale
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledExecutorService
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

object SafetyEngine {

    private const val TAG = "SafetyEngine"
    private const val SERVER_PORT = 8080
    private const val SMS_SENT_ACTION = "com.example.smartroadsafety.SMS_SENT"
    private const val SMS_DELIVERED_ACTION = "com.example.smartroadsafety.SMS_DELIVERED"
    const val DEFAULT_EMERGENCY_PHONE = "+919726222922"
    const val DEFAULT_TUNNEL_NAME = "technexa-safety-2026"
    const val PREFS_NAME = "road_safety_prefs"
    const val KEY_TUNNEL_NAME = "saved_tunnel_name"
    const val KEY_RELATIVE_PHONE = "saved_relative_phone"

    @Volatile var currentLat: Double? = null
    @Volatile var currentLng: Double? = null

    private var appContext: Context? = null
    private var isEngineStarted = false

    private lateinit var fusedLocationClient: FusedLocationProviderClient
    private var locationCallback: LocationCallback? = null
    private val isTrackingGps = AtomicBoolean(false)
    private val isPushingGps = AtomicBoolean(false)
    private var scheduledGpsExecutor: ScheduledExecutorService? = null
    private val gpsExecutor = Executors.newSingleThreadExecutor()

    private val handledAlertIds = Collections.synchronizedSet(HashSet<String>())
    private val emergencyPollExecutor = Executors.newSingleThreadExecutor()
    private val isPollingAlerts = AtomicBoolean(false)
    private var lastFullAlertsCheckTs = 0L

    private var server: InternalSmsServer? = null
    private var deviceIp: String = "127.0.0.1"
    private var sentSmsCount = 0

    fun start(context: Context) {
        val app = context.applicationContext
        appContext = app

        synchronized(this) {
            if (isEngineStarted) {
                // Ensure server is up
                if (server == null) {
                    startInternalServer()
                }
                if (!isTrackingGps.get()) {
                    startLocationTracking(app)
                }
                return
            }
            isEngineStarted = true
        }

        Log.i(TAG, "🚀 Initializing Smart Road Safety Background Engine...")

        registerSmsReceivers(app)
        startInternalServer()
        startAutoSendTimer()
        startLocationTracking(app)
    }

    fun getEmergencyTargetPhone(): String {
        val prefs = appContext?.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val saved = prefs?.getString(KEY_RELATIVE_PHONE, DEFAULT_EMERGENCY_PHONE)?.trim()
        return if (saved.isNullOrBlank() || saved.contains("91234") || saved.contains("1234567890") || saved.contains("56789")) {
            DEFAULT_EMERGENCY_PHONE
        } else {
            saved
        }
    }

    fun setEmergencyTargetPhone(phone: String) {
        val cleaned = phone.trim()
        val finalPhone = if (cleaned.length == 10 && !cleaned.startsWith("+")) "+91$cleaned" else cleaned
        appContext?.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            ?.edit()
            ?.putString(KEY_RELATIVE_PHONE, finalPhone)
            ?.apply()
        Log.i(TAG, "☎️ Updated emergency target phone: $finalPhone")
    }

    fun getActiveTunnelName(): String {
        val prefs = appContext?.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val saved = prefs?.getString(KEY_TUNNEL_NAME, DEFAULT_TUNNEL_NAME)
        return if (saved.isNullOrBlank() || saved.contains("curvy-frog") || saved.contains("purple-chicken") || saved.contains("loose-baths") || saved.contains("cold-spiders") || saved.contains("light-jellyfish") || saved.contains("hungry-eels") || saved.contains("neat-doodles") || saved.contains("curvy-hound")) {
            DEFAULT_TUNNEL_NAME
        } else {
            saved
        }
    }

    fun setTunnelName(tunnel: String) {
        val clean = tunnel.trim()
        appContext?.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            ?.edit()
            ?.putString(KEY_TUNNEL_NAME, clean)
            ?.apply()
        Log.i(TAG, "🌐 Updated localtunnel target: $clean")
    }

    // ========================================================
    // URL RESOLUTION
    // ========================================================

    fun resolveBaseUrl(): String {
        val input = getActiveTunnelName()
        val cleanInput = input.removePrefix("https://").removePrefix("http://").trimEnd('/')
        return if (cleanInput.contains(".loca.lt")) {
            val host = cleanInput.substringBefore('/')
            "https://$host"
        } else if (cleanInput.contains(":") || cleanInput.contains(".")) {
            if (input.startsWith("http://") || input.startsWith("https://")) {
                val scheme = if (input.startsWith("http://")) "http://" else "https://"
                scheme + cleanInput.substringBefore('/')
            } else {
                "https://$cleanInput"
            }
        } else {
            "https://$cleanInput.loca.lt"
        }
    }

    private fun resolveEndpointUrl(): String {
        val base = resolveBaseUrl()
        return "$base/api/gps"
    }

    fun formatMapsUrl(lat: Double, lng: Double): String {
        return "https://www.google.com/maps/search/?api=1&query=$lat,$lng"
    }

    private fun currentTimeString(): String {
        return SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(Date())
    }

    // ========================================================
    // HTTP CLIENT HELPERS
    // ========================================================

    private fun httpGet(urlStr: String): Pair<Int, String> {
        var conn: HttpURLConnection? = null
        return try {
            val url = URL(urlStr)
            conn = url.openConnection() as HttpURLConnection
            conn.requestMethod = "GET"
            conn.setRequestProperty("Bypass-Tunnel-Reminder", "true")
            conn.setRequestProperty("User-Agent", "RoadSafetyGateway/1.0")
            conn.connectTimeout = 7000
            conn.readTimeout = 7000
            val code = conn.responseCode
            val body = if (code in 200..299) {
                conn.inputStream.bufferedReader().use { it.readText() }
            } else {
                conn.errorStream?.bufferedReader()?.use { it.readText() } ?: ""
            }
            Pair(code, body)
        } catch (e: Exception) {
            Pair(-1, e.message ?: "")
        } finally {
            conn?.disconnect()
        }
    }

    private fun httpPost(urlStr: String, jsonBody: String): Pair<Int, String> {
        var conn: HttpURLConnection? = null
        return try {
            val url = URL(urlStr)
            conn = url.openConnection() as HttpURLConnection
            conn.requestMethod = "POST"
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8")
            conn.setRequestProperty("Bypass-Tunnel-Reminder", "true")
            conn.setRequestProperty("User-Agent", "RoadSafetyGateway/1.0")
            conn.connectTimeout = 7000
            conn.readTimeout = 7000
            conn.doOutput = true
            val bytes = jsonBody.toByteArray(Charsets.UTF_8)
            conn.setFixedLengthStreamingMode(bytes.size)
            conn.outputStream.use { it.write(bytes) }
            val code = conn.responseCode
            val body = if (code in 200..299) {
                conn.inputStream.bufferedReader().use { it.readText() }
            } else {
                conn.errorStream?.bufferedReader()?.use { it.readText() } ?: ""
            }
            Pair(code, body)
        } catch (e: Exception) {
            Pair(-1, e.message ?: "")
        } finally {
            conn?.disconnect()
        }
    }

    // ========================================================
    // CLOUD EMERGENCY POLLING
    // ========================================================

    private fun checkEmergencyAlerts(baseUrl: String) {
        if (!isPollingAlerts.compareAndSet(false, true)) {
            return
        }

        emergencyPollExecutor.execute {
            try {
                // 1. Fast check: /api/emergency/latest_pending
                val pendingUrl = "$baseUrl/api/emergency/latest_pending"
                val (pendingCode, pendingBody) = httpGet(pendingUrl)
                if (pendingCode in 200..299 && pendingBody.isNotEmpty()) {
                    val json = JSONObject(pendingBody)
                    if (json.optBoolean("has_pending", false) && json.has("alert") && !json.isNull("alert")) {
                        handleEmergencyAlert(json.getJSONObject("alert"), baseUrl)
                    }
                }

                // 2. Periodic check (every 5s): /api/emergency/alerts
                val now = System.currentTimeMillis()
                if (now - lastFullAlertsCheckTs > 5000L) {
                    lastFullAlertsCheckTs = now
                    val alertsUrl = "$baseUrl/api/emergency/alerts"
                    val (alertsCode, alertsBody) = httpGet(alertsUrl)
                    if (alertsCode in 200..299 && alertsBody.isNotEmpty()) {
                        val alertsArr = try {
                            JSONObject(alertsBody).optJSONArray("alerts") ?: JSONArray(alertsBody)
                        } catch (_: Exception) {
                            JSONArray(alertsBody)
                        }
                        val nowSec = now / 1000.0
                        for (i in 0 until alertsArr.length()) {
                            val alert = alertsArr.optJSONObject(i) ?: continue
                            val alertId = alert.optString("alert_id", "")
                            val alertTs = alert.optDouble("timestamp", nowSec)
                            if (alertId.isNotEmpty() && (nowSec - alertTs) < 180.0) {
                                if (!handledAlertIds.contains(alertId)) {
                                    handleEmergencyAlert(alert, baseUrl)
                                }
                            }
                        }
                    }
                }
            } catch (e: Exception) {
                Log.w(TAG, "Emergency polling note: ${e.message}")
            } finally {
                isPollingAlerts.set(false)
            }
        }
    }

    private fun handleEmergencyAlert(alert: JSONObject, baseUrl: String) {
        val alertId = alert.optString("alert_id", "")
        if (alertId.isEmpty() || handledAlertIds.contains(alertId)) {
            return
        }
        handledAlertIds.add(alertId)

        val date = alert.optString("date", "")
        val time = alert.optString("time", currentTimeString())
        val dateTime = if (date.isNotEmpty()) "$date $time" else time
        val hospital = alert.optString("hospital_name", alert.optString("hospital", "Civil Hospital Mehsana"))

        val lat = if (alert.has("latitude") && !alert.isNull("latitude")) alert.optDouble("latitude")
                  else if (alert.has("lat") && !alert.isNull("lat")) alert.optDouble("lat")
                  else (currentLat ?: 23.0338)
        val lng = if (alert.has("longitude") && !alert.isNull("longitude")) alert.optDouble("longitude")
                  else if (alert.has("lon") && !alert.isNull("lon")) alert.optDouble("lon")
                  else if (alert.has("lng") && !alert.isNull("lng")) alert.optDouble("lng")
                  else (currentLng ?: 72.5850)
        val mapsUrl = formatMapsUrl(lat, lng)

        val emergencyMessage = "Accident happened on $dateTime, emergency message sent to $hospital. Location: $mapsUrl"
        val targetPhone = getEmergencyTargetPhone()

        Log.i(TAG, "🚨 CRASH DETECTED ON CLOUD: ID $alertId | Dispatching SMS to $targetPhone")
        sendSms(targetPhone, emergencyMessage)

        // Acknowledge back to cloud backend
        try {
            httpPost("$baseUrl/api/emergency/acknowledge/$alertId", "{}")
            httpPost("$baseUrl/api/emergency/alerts/$alertId/acknowledge", "{}")
        } catch (_: Exception) {}
    }

    // ========================================================
    // LOCATION TRACKING & 1 HZ GPS TELEMETRY
    // ========================================================

    @SuppressLint("MissingPermission")
    private fun startLocationTracking(context: Context) {
        val fineGranted = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
        val coarseGranted = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED

        if (!fineGranted && !coarseGranted) {
            Log.w(TAG, "⚠️ Location permissions not granted yet for SafetyEngine.")
            return
        }

        try {
            fusedLocationClient = LocationServices.getFusedLocationProviderClient(context)
            fusedLocationClient.lastLocation.addOnSuccessListener { loc: Location? ->
                if (loc != null) {
                    currentLat = loc.latitude
                    currentLng = loc.longitude
                    pushGpsValues(loc.latitude, loc.longitude)
                }
            }

            val locationRequest = LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, 1000L)
                .setMinUpdateIntervalMillis(500L)
                .setMinUpdateDistanceMeters(0.0f)
                .build()

            locationCallback = object : LocationCallback() {
                override fun onLocationResult(result: LocationResult) {
                    val loc = result.lastLocation ?: return
                    currentLat = loc.latitude
                    currentLng = loc.longitude
                }
            }

            fusedLocationClient.requestLocationUpdates(
                locationRequest,
                locationCallback!!,
                Looper.getMainLooper()
            )
            isTrackingGps.set(true)
            Log.i(TAG, "🛰️ GPS live tracking active (1000ms continuous).")

            startAutoSendTimer()
        } catch (e: Exception) {
            Log.e(TAG, "Location tracking error: ${e.message}")
        }
    }

    private fun startAutoSendTimer() {
        stopAutoSendTimer()
        val scheduler = Executors.newSingleThreadScheduledExecutor()
        scheduledGpsExecutor = scheduler
        scheduler.scheduleAtFixedRate({
            try {
                val lat = currentLat
                val lng = currentLng
                if (lat != null && lng != null) {
                    pushGpsValues(lat, lng)
                }

                val baseUrl = resolveBaseUrl()
                checkEmergencyAlerts(baseUrl)
            } catch (t: Throwable) {
                Log.w(TAG, "Heartbeat note: ${t.message}")
            }
        }, 500L, 1000L, TimeUnit.MILLISECONDS)
        Log.i(TAG, "⏱️ Auto-send active: Streaming GPS & checking crash alerts every 1s")
    }

    private fun stopAutoSendTimer() {
        try {
            scheduledGpsExecutor?.shutdownNow()
            scheduledGpsExecutor = null
        } catch (_: Exception) {}
    }

    private fun pushGpsValues(lat: Double, lng: Double) {
        if (!isPushingGps.compareAndSet(false, true)) {
            return
        }

        val targetUrl = resolveEndpointUrl()

        gpsExecutor.execute {
            var conn: HttpURLConnection? = null
            try {
                val payload = JSONObject().apply {
                    put("latitude", lat)
                    put("longitude", lng)
                    put("lat", lat)
                    put("lon", lng)
                }

                val url = URL(targetUrl)
                conn = url.openConnection() as HttpURLConnection
                conn.requestMethod = "POST"
                conn.setRequestProperty("Content-Type", "application/json; charset=utf-8")
                conn.setRequestProperty("Bypass-Tunnel-Reminder", "true")
                conn.setRequestProperty("User-Agent", "RoadSafetyGateway/1.0")
                conn.connectTimeout = 7000
                conn.readTimeout = 7000
                conn.doOutput = true

                val bytes = payload.toString().toByteArray(Charsets.UTF_8)
                conn.setFixedLengthStreamingMode(bytes.size)
                conn.outputStream.use { it.write(bytes) }

                val responseCode = conn.responseCode
                if (responseCode in 200..299) {
                    // Success
                } else {
                    Log.w(TAG, "GPS stream note: HTTP $responseCode from $targetUrl")
                }
            } catch (e: Exception) {
                Log.w(TAG, "GPS stream error: ${e.message}")
            } finally {
                conn?.disconnect()
                isPushingGps.set(false)
            }
        }
    }

    // ========================================================
    // EMBEDDED NANOHTTPD SERVER (PORT 8080)
    // ========================================================

    private fun startInternalServer() {
        if (server != null) return

        deviceIp = getDeviceIpAddress()
        try {
            val s = InternalSmsServer(SERVER_PORT)
            s.start(NanoHTTPD.SOCKET_READ_TIMEOUT, false)
            server = s
            Log.i(TAG, "✅ SMS Gateway Server running on 0.0.0.0:$SERVER_PORT")
        } catch (e: Exception) {
            server = null
            Log.e(TAG, "🔴 Failed to start SMS gateway server: ${e.message}")
        }
    }

    private fun getDeviceIpAddress(): String {
        try {
            val interfaces = Collections.list(NetworkInterface.getNetworkInterfaces())
            for (networkInterface in interfaces) {
                if (networkInterface.isLoopback || !networkInterface.isUp) continue
                val addresses = Collections.list(networkInterface.inetAddresses)
                for (address in addresses) {
                    if (!address.isLoopbackAddress && address is Inet4Address) {
                        val ip = address.hostAddress ?: ""
                        if (ip.isNotEmpty() && !ip.startsWith("127.")) {
                            return ip
                        }
                    }
                }
            }
        } catch (_: Exception) {}
        return "127.0.0.1"
    }

    private class InternalSmsServer(port: Int) : NanoHTTPD("0.0.0.0", port) {
        override fun serve(session: IHTTPSession): Response {
            val uri = session.uri
            val method = session.method

            if (method == Method.GET && (uri == "/" || uri == "/status" || uri == "/config")) {
                val statusJson = JSONObject().apply {
                    put("status", "online")
                    put("service", "Road Safety SMS Gateway")
                    put("port", SERVER_PORT)
                    put("endpoint", "/send-sms")
                    put("emergencyTarget", getEmergencyTargetPhone())
                    put("tunnel", getActiveTunnelName())
                    put("tunnelUrl", resolveBaseUrl())
                    put("latitude", currentLat)
                    put("longitude", currentLng)
                }
                return newFixedLengthResponse(Response.Status.OK, "application/json", statusJson.toString())
            }

            if (method == Method.POST && (uri == "/config" || uri == "/tunnel")) {
                return try {
                    val files = HashMap<String, String>()
                    session.parseBody(files)
                    val body = files["postData"] ?: ""
                    val json = JSONObject(body)
                    if (json.has("tunnel")) {
                        setTunnelName(json.getString("tunnel"))
                    } else if (json.has("endpoint")) {
                        setTunnelName(json.getString("endpoint"))
                    }
                    if (json.has("phone")) {
                        setEmergencyTargetPhone(json.getString("phone"))
                    }
                    val resp = JSONObject().apply {
                        put("success", true)
                        put("tunnel", getActiveTunnelName())
                        put("tunnelUrl", resolveBaseUrl())
                        put("emergencyTarget", getEmergencyTargetPhone())
                    }
                    newFixedLengthResponse(Response.Status.OK, "application/json", resp.toString())
                } catch (e: Exception) {
                    val err = JSONObject().put("success", false).put("error", e.message ?: "Server error")
                    newFixedLengthResponse(Response.Status.BAD_REQUEST, "application/json", err.toString())
                }
            }

            if (method == Method.POST && uri == "/send-sms") {
                return try {
                    val files = HashMap<String, String>()
                    session.parseBody(files)
                    val body = files["postData"] ?: ""

                    if (body.isBlank()) {
                        val err = JSONObject().put("success", false).put("error", "Empty body")
                        return newFixedLengthResponse(Response.Status.BAD_REQUEST, "application/json", err.toString())
                    }

                    val json = JSONObject(body)
                    val rawPhone = json.optString("phone", "").trim()
                    var rawMessage = json.optString("message", "").trim()

                    val passedLat = if (json.has("latitude")) json.optDouble("latitude")
                                    else if (json.has("lat")) json.optDouble("lat") else null
                    val passedLng = if (json.has("longitude")) json.optDouble("longitude")
                                    else if (json.has("lng")) json.optDouble("lng")
                                    else if (json.has("lon")) json.optDouble("lon") else null

                    val finalLat = passedLat ?: currentLat
                    val finalLng = passedLng ?: currentLng
                    val mapsUrl = if (finalLat != null && finalLng != null) formatMapsUrl(finalLat, finalLng) else null

                    val hospital = json.optString("hospital", "").trim()
                    val dateTime = json.optString("date_time", json.optString("dateTime", currentTimeString())).trim()

                    val finalMessage: String = if (hospital.isNotEmpty()) {
                        if (mapsUrl != null) {
                            "Accident happened on $dateTime, emergency message sent to $hospital. Location: $mapsUrl"
                        } else {
                            "Accident happened on $dateTime, emergency message sent to $hospital."
                        }
                    } else if (rawMessage.isNotEmpty()) {
                        var cleaned = rawMessage.replace(Regex("at [^,]+ on ", RegexOption.IGNORE_CASE), "on ")
                        if (mapsUrl != null) {
                            if (!cleaned.contains("google.com/maps/search/?api=1")) {
                                cleaned = cleaned.replace(Regex("(Map|Location):\\s*https?://\\S+", RegexOption.IGNORE_CASE), "").trim()
                                "$cleaned Location: $mapsUrl"
                            } else cleaned
                        } else cleaned
                    } else if (mapsUrl != null) {
                        "Accident happened on $dateTime. Location: $mapsUrl"
                    } else {
                        val err = JSONObject().put("success", false).put("error", "Missing message or location")
                        return newFixedLengthResponse(Response.Status.BAD_REQUEST, "application/json", err.toString())
                    }

                    val digits = rawPhone.filter { it.isDigit() }
                    val phone = if (digits.contains("9876543210") || digits.isEmpty()) {
                        getEmergencyTargetPhone()
                    } else if (digits.length == 10 && !rawPhone.startsWith("+")) {
                        "+91$digits"
                    } else {
                        rawPhone
                    }

                    Log.i(TAG, "📩 Received inbound SMS request from ${session.remoteIpAddress} -> Target: $phone")
                    sendSms(phone, finalMessage)

                    val resp = JSONObject().apply {
                        put("success", true)
                        put("message", "SMS accepted by Android gateway")
                        put("phone", phone)
                        put("sms_body", finalMessage)
                        put("timestamp", currentTimeString())
                    }
                    newFixedLengthResponse(Response.Status.OK, "application/json", resp.toString())
                } catch (e: Exception) {
                    val err = JSONObject().put("success", false).put("error", e.message ?: "Server error")
                    newFixedLengthResponse(Response.Status.INTERNAL_ERROR, "application/json", err.toString())
                }
            }

            return newFixedLengthResponse(Response.Status.NOT_FOUND, "text/plain", "Not Found")
        }
    }

    // ========================================================
    // GSM SMS DISPATCH
    // ========================================================

    fun sendSms(phoneNumber: String, message: String) {
        val ctx = appContext ?: return
        if (ContextCompat.checkSelfPermission(ctx, Manifest.permission.SEND_SMS) != PackageManager.PERMISSION_GRANTED) {
            Log.e(TAG, "❌ SEND_SMS permission missing. Cannot dispatch.")
            return
        }

        val digits = phoneNumber.filter { it.isDigit() }
        val targetPhone = if (digits.contains("91234") || digits.contains("1234567890") || digits.isEmpty()) {
            getEmergencyTargetPhone()
        } else if (digits.length == 10 && !phoneNumber.startsWith("+")) {
            "+91$digits"
        } else {
            phoneNumber
        }

        try {
            val managers = getAllSmsManagers(ctx)
            val flags = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_MUTABLE
            } else {
                PendingIntent.FLAG_UPDATE_CURRENT
            }

            for ((simName, smsManager) in managers) {
                try {
                    val parts = smsManager.divideMessage(message)
                    Log.i(TAG, "🚀 Dispatching SMS via $simName to $targetPhone (${parts.size} part(s)): \"$message\"")

                    if (parts.size > 1) {
                        val sentIntents = ArrayList<PendingIntent>()
                        val deliveredIntents = ArrayList<PendingIntent>()
                        val baseCode = 1000 + Math.abs(simName.hashCode() % 1000)
                        for (i in parts.indices) {
                            sentIntents.add(PendingIntent.getBroadcast(
                                ctx, baseCode + i,
                                Intent(SMS_SENT_ACTION).apply {
                                    setPackage(ctx.packageName)
                                    putExtra("sim_name", simName)
                                    putExtra("part", i)
                                },
                                flags
                            ))
                            deliveredIntents.add(PendingIntent.getBroadcast(
                                ctx, baseCode + 100 + i,
                                Intent(SMS_DELIVERED_ACTION).apply {
                                    setPackage(ctx.packageName)
                                    putExtra("sim_name", simName)
                                    putExtra("part", i)
                                },
                                flags
                            ))
                        }
                        smsManager.sendMultipartTextMessage(targetPhone, null, parts, sentIntents, deliveredIntents)
                    } else {
                        val baseCode = 1000 + Math.abs(simName.hashCode() % 1000)
                        val sentIntent = PendingIntent.getBroadcast(
                            ctx, baseCode,
                            Intent(SMS_SENT_ACTION).apply {
                                setPackage(ctx.packageName)
                                putExtra("sim_name", simName)
                            },
                            flags
                        )
                        val deliveredIntent = PendingIntent.getBroadcast(
                            ctx, baseCode + 100,
                            Intent(SMS_DELIVERED_ACTION).apply {
                                setPackage(ctx.packageName)
                                putExtra("sim_name", simName)
                            },
                            flags
                        )
                        smsManager.sendTextMessage(targetPhone, null, message, sentIntent, deliveredIntent)
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "❌ SMS Transmission Exception on $simName: ${e.message}")
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "❌ SMS Transmission Exception: ${e.message}")
        }
    }

    private fun getAllSmsManagers(ctx: Context): List<Pair<String, SmsManager>> {
        val list = mutableListOf<Pair<String, SmsManager>>()
        try {
            if (ContextCompat.checkSelfPermission(ctx, Manifest.permission.READ_PHONE_STATE) == PackageManager.PERMISSION_GRANTED) {
                val subManager = ctx.getSystemService(SubscriptionManager::class.java)
                val activeSubs = subManager?.activeSubscriptionInfoList
                if (!activeSubs.isNullOrEmpty()) {
                    for (sim in activeSubs) {
                        val name = sim.carrierName?.toString()?.ifBlank { sim.displayName?.toString() } ?: "SIM ${sim.simSlotIndex + 1}"
                        val label = "SIM ${sim.simSlotIndex + 1} ($name, SubId: ${sim.subscriptionId})"
                        val sm = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                            ctx.getSystemService(SmsManager::class.java).createForSubscriptionId(sim.subscriptionId)
                        } else {
                            @Suppress("DEPRECATION")
                            SmsManager.getSmsManagerForSubscriptionId(sim.subscriptionId)
                        }
                        list.add(Pair(label, sm))
                    }
                }
            }
        } catch (e: Exception) {
            Log.w(TAG, "Multi-SIM query note: ${e.message}")
        }

        if (list.isEmpty()) {
            try {
                val defaultSubId = SmsManager.getDefaultSmsSubscriptionId()
                if (defaultSubId != -1 && defaultSubId != SubscriptionManager.INVALID_SUBSCRIPTION_ID) {
                    val sm = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                        ctx.getSystemService(SmsManager::class.java).createForSubscriptionId(defaultSubId)
                    } else {
                        @Suppress("DEPRECATION")
                        SmsManager.getSmsManagerForSubscriptionId(defaultSubId)
                    }
                    list.add(Pair("DefaultSub ($defaultSubId)", sm))
                }
            } catch (_: Exception) {}

            if (list.isEmpty()) {
                @Suppress("DEPRECATION")
                list.add(Pair("DefaultSmsManager", SmsManager.getDefault()))
            }
        }
        return list
    }

    private fun registerSmsReceivers(ctx: Context) {
        val sentReceiver = object : BroadcastReceiver() {
            override fun onReceive(c: Context?, intent: Intent?) {
                val simName = intent?.getStringExtra("sim_name") ?: "Carrier"
                val errorCode = intent?.getIntExtra("errorCode", -1) ?: -1
                when (resultCode) {
                    Activity.RESULT_OK -> {
                        sentSmsCount++
                        Log.i(TAG, "✅ CARRIER CONFIRMED ($simName): SMS successfully dispatched to cellular network! (Total: $sentSmsCount)")
                    }
                    else -> Log.w(TAG, "❌ Carrier Error Code: $resultCode on $simName (Modem error code: $errorCode)")
                }
            }
        }

        val deliveredReceiver = object : BroadcastReceiver() {
            override fun onReceive(c: Context?, intent: Intent?) {
                val simName = intent?.getStringExtra("sim_name") ?: "Carrier"
                when (resultCode) {
                    Activity.RESULT_OK -> Log.i(TAG, "📬 CARRIER CONFIRMED ($simName): SMS delivered to recipient handset!")
                    else -> Log.w(TAG, "⚠️ Delivery receipt on $simName: $resultCode")
                }
            }
        }

        val sentFilter = IntentFilter(SMS_SENT_ACTION)
        val deliveredFilter = IntentFilter(SMS_DELIVERED_ACTION)

        val controlReceiver = object : BroadcastReceiver() {
            override fun onReceive(c: Context?, intent: Intent?) {
                when (intent?.action) {
                    "com.example.smartroadsafety.SET_TUNNEL" -> {
                        val tunnel = intent.getStringExtra("tunnel")
                        if (!tunnel.isNullOrBlank()) {
                            setTunnelName(tunnel)
                        }
                    }
                    "com.example.smartroadsafety.SEND_TEST_SMS" -> {
                        val phone = intent.getStringExtra("phone") ?: getEmergencyTargetPhone()
                        val hospital = intent.getStringExtra("hospital") ?: "Civil Hospital Mehsana"
                        val lat = currentLat ?: 23.0338
                        val lng = currentLng ?: 72.5850
                        val msg = "Accident happened on ${currentTimeString()}, emergency message sent to $hospital. Location: ${formatMapsUrl(lat, lng)}"
                        sendSms(phone, msg)
                    }
                }
            }
        }

        val controlFilter = IntentFilter().apply {
            addAction("com.example.smartroadsafety.SET_TUNNEL")
            addAction("com.example.smartroadsafety.SEND_TEST_SMS")
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            ctx.registerReceiver(sentReceiver, sentFilter, Context.RECEIVER_EXPORTED)
            ctx.registerReceiver(deliveredReceiver, deliveredFilter, Context.RECEIVER_EXPORTED)
            ctx.registerReceiver(controlReceiver, controlFilter, Context.RECEIVER_EXPORTED)
        } else {
            ContextCompat.registerReceiver(ctx, sentReceiver, sentFilter, Context.RECEIVER_EXPORTED)
            ContextCompat.registerReceiver(ctx, deliveredReceiver, deliveredFilter, Context.RECEIVER_EXPORTED)
            ContextCompat.registerReceiver(ctx, controlReceiver, controlFilter, Context.RECEIVER_EXPORTED)
        }
    }
}
