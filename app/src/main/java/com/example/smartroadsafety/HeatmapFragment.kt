package com.example.smartroadsafety

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.fragment.app.Fragment
import com.example.smartroadsafety.data.DataRepository
import com.example.smartroadsafety.model.BlackspotZone

class HeatmapFragment : Fragment() {

    private lateinit var tvHeatmapIncidentCount: TextView
    private lateinit var tvBlackspotName: TextView
    private lateinit var tvSpeedLimitGeofence: TextView
    private lateinit var tvBlackspotStats: TextView
    private lateinit var spotIskcon: View
    private lateinit var spotVaishno: View
    private lateinit var spotChhatral: View
    private lateinit var spotSanand: View

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        val view = inflater.inflate(R.layout.fragment_heatmap, container, false)
        initViews(view)
        loadHeatmapData()
        setupListeners()
        return view
    }

    private fun initViews(view: View) {
        tvHeatmapIncidentCount = view.findViewById(R.id.tvHeatmapIncidentCount)
        tvBlackspotName = view.findViewById(R.id.tvBlackspotName)
        tvSpeedLimitGeofence = view.findViewById(R.id.tvSpeedLimitGeofence)
        tvBlackspotStats = view.findViewById(R.id.tvBlackspotStats)

        spotIskcon = view.findViewById(R.id.spotIskcon)
        spotVaishno = view.findViewById(R.id.spotVaishno)
        spotChhatral = view.findViewById(R.id.spotChhatral)
        spotSanand = view.findViewById(R.id.spotSanand)
    }

    private fun loadHeatmapData() {
        val overview = DataRepository.getHeatmapOverview()
        tvHeatmapIncidentCount.text = "${overview.totalIncidents} Gaussian Mesh Incidents • Gujarat Region"

        val defaultZone = overview.blackspots.firstOrNull()
        if (defaultZone != null) {
            updateSelectedZone(defaultZone)
        }
    }

    private fun setupListeners() {
        val blackspots = DataRepository.getHeatmapOverview().blackspots

        spotIskcon.setOnClickListener {
            blackspots.find { zone -> zone.id == "BS-01" }?.let { updateSelectedZone(it) }
        }

        spotVaishno.setOnClickListener {
            blackspots.find { zone -> zone.id == "BS-02" }?.let { updateSelectedZone(it) }
        }

        spotChhatral.setOnClickListener {
            blackspots.find { zone -> zone.id == "BS-03" }?.let { updateSelectedZone(it) }
        }

        spotSanand.setOnClickListener {
            blackspots.find { zone -> zone.id == "BS-04" }?.let { updateSelectedZone(it) }
        }
    }

    private fun updateSelectedZone(zone: BlackspotZone) {
        tvBlackspotName.text = "Active Zone: ${zone.name}"
        tvSpeedLimitGeofence.text = "Limit: ${zone.speedLimitKmh} km/h"
        tvBlackspotStats.text = "Historical Crashes: ${zone.historicalCrashes} • Fatalities: ${zone.fatalities} • Danger Radius: ${zone.radiusM.toInt()}m"
    }
}
