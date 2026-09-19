package com.example.smartroadsafety

import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.IBinder

/**
 * These components satisfy Android OS requirements to qualify as a Default SMS App,
 * allowing full background SMS sending privileges without carrier code 32 errors.
 */

class SmsDummyReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context?, intent: Intent?) {
        // No-op for emergency gateway
    }
}

class MmsDummyReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context?, intent: Intent?) {
        // No-op for emergency gateway
    }
}

class HeadlessSmsSendService : Service() {
    override fun onBind(intent: Intent?): IBinder? = null
}
