package com.example.smartroadsafety

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.EditorInfo
import android.widget.EditText
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.widget.AppCompatButton
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import com.example.smartroadsafety.data.DataRepository
import com.example.smartroadsafety.model.NavigationAlert
import kotlinx.coroutines.launch

class RideFragment : Fragment() {

    private lateinit var btnStartRide: AppCompatButton
    private lateinit var layoutDestinationContainer: LinearLayout
    private lateinit var etDestination: EditText
    private lateinit var btnSubmitDestination: ImageButton
    private lateinit var layoutAlertsContainer: LinearLayout
    private lateinit var llAlertCardsList: LinearLayout
    private lateinit var tvActiveRouteTitle: TextView
    private lateinit var tvRouteEta: TextView

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        val view = inflater.inflate(R.layout.fragment_ride, container, false)
        initViews(view)
        setupListeners()
        return view
    }

    private fun initViews(view: View) {
        btnStartRide = view.findViewById(R.id.btnStartRide)
        layoutDestinationContainer = view.findViewById(R.id.layoutDestinationContainer)
        etDestination = view.findViewById(R.id.etDestination)
        btnSubmitDestination = view.findViewById(R.id.btnSubmitDestination)
        layoutAlertsContainer = view.findViewById(R.id.layoutAlertsContainer)
        llAlertCardsList = view.findViewById(R.id.llAlertCardsList)
        tvActiveRouteTitle = view.findViewById(R.id.tvActiveRouteTitle)
        tvRouteEta = view.findViewById(R.id.tvRouteEta)
    }

    private fun setupListeners() {
        // "On clicking a text white text field will be visible to enter destination below it."
        btnStartRide.setOnClickListener {
            layoutDestinationContainer.visibility = View.VISIBLE
            etDestination.requestFocus()
            Toast.makeText(requireContext(), "Please enter your destination", Toast.LENGTH_SHORT).show()
        }

        btnSubmitDestination.setOnClickListener {
            handleDestinationSubmitted()
        }

        etDestination.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_DONE || actionId == EditorInfo.IME_ACTION_GO) {
                handleDestinationSubmitted()
                true
            } else {
                false
            }
        }
    }

    private fun handleDestinationSubmitted() {
        val dest = etDestination.text.toString().trim()
        val destinationText = if (dest.isEmpty()) "Mehsana Highway Bypass" else dest
        etDestination.setText(destinationText)

        // Show navigation and alert instruction cards immediately
        layoutAlertsContainer.visibility = View.VISIBLE
        tvActiveRouteTitle.text = "Navigation to $destinationText"
        tvRouteEta.text = "Calculating ETA & hazards..."

        val cachedAlerts = DataRepository.getAlertsForDestination(destinationText)
        populateAlertCards(cachedAlerts)

        val lat = SafetyEngine.currentLat ?: 23.5269
        val lon = SafetyEngine.currentLng ?: 72.4587

        viewLifecycleOwner.lifecycleScope.launch {
            val session = DataRepository.startRideOnline(destinationText, lat, lon)
            tvActiveRouteTitle.text = "Navigation to ${session.destination}"
            tvRouteEta.text = "${session.distanceKm} km • ${session.estimatedMins} min"
            populateAlertCards(session.alerts)
            Toast.makeText(requireContext(), "Navigation active! ${session.alerts.size} hazard alerts loaded.", Toast.LENGTH_SHORT).show()
        }
    }

    private fun populateAlertCards(alerts: List<NavigationAlert>) {
        llAlertCardsList.removeAllViews()
        val inflater = LayoutInflater.from(requireContext())

        alerts.forEach { alert ->
            val cardView = inflater.inflate(R.layout.item_alert_card, llAlertCardsList, false)
            val tvTitle = cardView.findViewById<TextView>(R.id.tvAlertTitle)
            val tvInstruction = cardView.findViewById<TextView>(R.id.tvAlertInstruction)
            val tvDistance = cardView.findViewById<TextView>(R.id.tvAlertDistance)
            val ivIcon = cardView.findViewById<ImageView>(R.id.ivAlertIcon)

            tvTitle.text = alert.title
            tvInstruction.text = alert.instruction
            tvDistance.text = "${alert.distanceAheadMeters}m ahead"

            when (alert.severity) {
                "HIGH" -> ivIcon.setColorFilter(requireContext().getColor(R.color.hazard_btn_bg))
                "MEDIUM" -> ivIcon.setColorFilter(requireContext().getColor(R.color.btn_start_ride_bg))
                else -> ivIcon.setColorFilter(requireContext().getColor(R.color.nav_bar_bg))
            }

            llAlertCardsList.addView(cardView)
        }
    }
}
