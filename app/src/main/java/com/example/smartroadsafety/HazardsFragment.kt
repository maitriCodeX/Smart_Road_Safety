package com.example.smartroadsafety

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.widget.AppCompatButton
import androidx.fragment.app.Fragment
import com.example.smartroadsafety.data.DataRepository
import com.example.smartroadsafety.model.RouteHazard
import com.example.smartroadsafety.model.TravelRoute

class HazardsFragment : Fragment() {

    private lateinit var layoutRoutesList: LinearLayout
    private lateinit var llRoutesContainer: LinearLayout
    private lateinit var layoutHazardsDetail: LinearLayout
    private lateinit var btnBackToRoutes: ImageButton
    private lateinit var tvDetailRouteTitle: TextView
    private lateinit var tvDetailRouteSubtitle: TextView
    private lateinit var llRouteHazardsContainer: LinearLayout

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        val view = inflater.inflate(R.layout.fragment_hazards, container, false)
        initViews(view)
        loadRoutes()
        setupListeners()
        return view
    }

    private fun initViews(view: View) {
        layoutRoutesList = view.findViewById(R.id.layoutRoutesList)
        llRoutesContainer = view.findViewById(R.id.llRoutesContainer)
        layoutHazardsDetail = view.findViewById(R.id.layoutHazardsDetail)
        btnBackToRoutes = view.findViewById(R.id.btnBackToRoutes)
        tvDetailRouteTitle = view.findViewById(R.id.tvDetailRouteTitle)
        tvDetailRouteSubtitle = view.findViewById(R.id.tvDetailRouteSubtitle)
        llRouteHazardsContainer = view.findViewById(R.id.llRouteHazardsContainer)
    }

    private fun setupListeners() {
        btnBackToRoutes.setOnClickListener {
            layoutHazardsDetail.visibility = View.GONE
            layoutRoutesList.visibility = View.VISIBLE
        }
    }

    private fun loadRoutes() {
        llRoutesContainer.removeAllViews()
        val routes = DataRepository.getFrequentlyTraveledRoutes()
        val inflater = LayoutInflater.from(requireContext())

        routes.forEach { route ->
            val cardView = inflater.inflate(R.layout.item_route_card, llRoutesContainer, false)
            val tvRouteTitle = cardView.findViewById<TextView>(R.id.tvRouteTitle)
            val tvRouteSubInfo = cardView.findViewById<TextView>(R.id.tvRouteSubInfo)
            val tvTripCount = cardView.findViewById<TextView>(R.id.tvTripCount)
            val btnViewHazards = cardView.findViewById<AppCompatButton>(R.id.btnViewHazards)

            tvRouteTitle.text = "Route info: ${route.title.lowercase()}"
            tvRouteSubInfo.text = "${route.origin} → ${route.destination} • ${route.totalDistanceKm} km • ${route.hazardsCount} hazards detected"
            tvTripCount.text = "${route.tripCount} trips"

            // "On clicking the button it redirects to a page that shows individual hazards that are there on that route in card format"
            btnViewHazards.setOnClickListener {
                showRouteHazards(route)
            }

            llRoutesContainer.addView(cardView)
        }
    }

    private fun showRouteHazards(route: TravelRoute) {
        layoutRoutesList.visibility = View.GONE
        layoutHazardsDetail.visibility = View.VISIBLE

        tvDetailRouteTitle.text = route.title
        tvDetailRouteSubtitle.text = "${route.hazards.size} hazards recorded on this route"

        llRouteHazardsContainer.removeAllViews()
        val inflater = LayoutInflater.from(requireContext())

        val hazards = DataRepository.getHazardsForRoute(route.routeId)
        hazards.forEach { hazard ->
            val cardView = inflater.inflate(R.layout.item_hazard_card, llRouteHazardsContainer, false)
            val tvHazardTitle = cardView.findViewById<TextView>(R.id.tvHazardTitle)
            val tvNearbyLocation = cardView.findViewById<TextView>(R.id.tvNearbyLocation)
            val tvHazardDescription = cardView.findViewById<TextView>(R.id.tvHazardDescription)
            val tvHazardSeverityBadge = cardView.findViewById<TextView>(R.id.tvHazardSeverityBadge)
            val ivHazardIcon = cardView.findViewById<ImageView>(R.id.ivHazardIcon)

            tvHazardTitle.text = hazard.title
            tvNearbyLocation.text = hazard.nearbyLocation
            tvHazardDescription.text = hazard.description
            tvHazardSeverityBadge.text = hazard.severity

            when (hazard.hazardType) {
                "POTHOLE" -> ivHazardIcon.setImageResource(R.drawable.ic_warning_triangle)
                "ACCIDENT_BLACKSPOT" -> ivHazardIcon.setImageResource(R.drawable.ic_nav_hazards)
                else -> ivHazardIcon.setImageResource(R.drawable.ic_location)
            }

            llRouteHazardsContainer.addView(cardView)
        }
    }
}
