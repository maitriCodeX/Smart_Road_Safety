package com.example.smartroadsafety

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import com.example.smartroadsafety.data.DataRepository
import com.example.smartroadsafety.model.BlackspotZone
import com.example.smartroadsafety.model.HeatmapOverview
import kotlinx.coroutines.launch

class HeatmapFragment : Fragment() {

    private lateinit var tvHeatmapIncidentCount: TextView
    private lateinit var tvBlackspotName: TextView
    private lateinit var tvSpeedLimitGeofence: TextView
    private lateinit var tvBlackspotStats: TextView
    private lateinit var spotIskcon: View
    private lateinit var spotVaishno: View
    private lateinit var spotChhatral: View
    private lateinit var spotSanand: View

    private var activeBlackspots: List<BlackspotZone> = emptyList()

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
        val initialOverview = DataRepository.getHeatmapOverview()
        renderHeatmap(initialOverview)

        viewLifecycleOwner.lifecycleScope.launch {
            val overview = DataRepository.fetchHeatmapOverviewOnline()
            renderHeatmap(overview)
        }
    }

    private fun renderHeatmap(overview: HeatmapOverview) {
        if (!isAdded || context == null) return
        activeBlackspots = overview.blackspots
        tvHeatmapIncidentCount.text = "${overview.totalIncidents} Gaussian Mesh Incidents • Gujarat Region"

        val defaultZone = overview.blackspots.firstOrNull()
        if (defaultZone != null) {
            updateSelectedZone(defaultZone)
        }
    }

    private fun setupListeners() {
        spotIskcon.setOnClickListener {
            val zone = activeBlackspots.find { it.id.contains("01") || it.name.contains("Iskcon", true) }
                ?: activeBlackspots.getOrNull(0)
            zone?.let { updateSelectedZone(it) }
        }

        spotVaishno.setOnClickListener {
            val zone = activeBlackspots.find { it.id.contains("02") || it.name.contains("Vaishno", true) }
                ?: activeBlackspots.getOrNull(1)
            zone?.let { updateSelectedZone(it) }
        }

        spotChhatral.setOnClickListener {
            val zone = activeBlackspots.find { it.id.contains("03") || it.name.contains("Chhatral", true) }
                ?: activeBlackspots.getOrNull(2)
            zone?.let { updateSelectedZone(it) }
        }

        spotSanand.setOnClickListener {
            val zone = activeBlackspots.find { it.id.contains("04") || it.name.contains("Sanand", true) }
                ?: activeBlackspots.getOrNull(3)
            zone?.let { updateSelectedZone(it) }
        }
    }

    private fun updateSelectedZone(zone: BlackspotZone) {
        tvBlackspotName.text = "Active Zone: ${zone.name}"
        tvSpeedLimitGeofence.text = "Limit: ${zone.speedLimitKmh} km/h"
        tvBlackspotStats.text = "Historical Crashes: ${zone.historicalCrashes} • Fatalities: ${zone.fatalities} • Danger Radius: ${zone.radiusM.toInt()}m"
    }
}
