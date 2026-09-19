package com.example.smartroadsafety

import android.os.Bundle
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.fragment.app.Fragment

class MainActivity : AppCompatActivity() {

    private lateinit var navItemRide: LinearLayout
    private lateinit var navItemHazards: LinearLayout
    private lateinit var navItemScore: LinearLayout
    private lateinit var navItemHeatmap: LinearLayout
    private lateinit var navItemProfile: LinearLayout

    private lateinit var ivNavRide: ImageView
    private lateinit var ivNavHazards: ImageView
    private lateinit var ivNavScore: ImageView
    private lateinit var ivNavHeatmap: ImageView
    private lateinit var ivNavProfile: ImageView

    private lateinit var tvNavRide: TextView
    private lateinit var tvNavHazards: TextView
    private lateinit var tvNavScore: TextView
    private lateinit var tvNavHeatmap: TextView
    private lateinit var tvNavProfile: TextView

    private val rideFragment = RideFragment()
    private val hazardsFragment = HazardsFragment()
    private val driverScoreFragment = DriverScoreFragment()
    private val heatmapFragment = HeatmapFragment()
    private val profileFragment = ProfileFragment()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_main)

        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.mainRoot)) { v, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(0, systemBars.top, 0, 0)
            insets
        }

        initViews()
        setupBottomNav()

        // "The first icon is for ride(by default this will be open once logged in)."
        if (savedInstanceState == null) {
            selectTab(0)
        }
    }

    private fun initViews() {
        navItemRide = findViewById(R.id.navItemRide)
        navItemHazards = findViewById(R.id.navItemHazards)
        navItemScore = findViewById(R.id.navItemScore)
        navItemHeatmap = findViewById(R.id.navItemHeatmap)
        navItemProfile = findViewById(R.id.navItemProfile)

        ivNavRide = findViewById(R.id.ivNavRide)
        ivNavHazards = findViewById(R.id.ivNavHazards)
        ivNavScore = findViewById(R.id.ivNavScore)
        ivNavHeatmap = findViewById(R.id.ivNavHeatmap)
        ivNavProfile = findViewById(R.id.ivNavProfile)

        tvNavRide = findViewById(R.id.tvNavRide)
        tvNavHazards = findViewById(R.id.tvNavHazards)
        tvNavScore = findViewById(R.id.tvNavScore)
        tvNavHeatmap = findViewById(R.id.tvNavHeatmap)
        tvNavProfile = findViewById(R.id.tvNavProfile)
    }

    private fun setupBottomNav() {
        navItemRide.setOnClickListener { selectTab(0) }
        navItemHazards.setOnClickListener { selectTab(1) }
        navItemScore.setOnClickListener { selectTab(2) }
        navItemHeatmap.setOnClickListener { selectTab(3) }
        navItemProfile.setOnClickListener { selectTab(4) }
    }

    private fun selectTab(position: Int) {
        val selectedColor = getColor(R.color.nav_selected_tint)
        val unselectedColor = getColor(R.color.nav_unselected_tint)

        // Reset all
        ivNavRide.setColorFilter(unselectedColor)
        tvNavRide.setTextColor(unselectedColor)

        ivNavHazards.setColorFilter(unselectedColor)
        tvNavHazards.setTextColor(unselectedColor)

        ivNavScore.setColorFilter(unselectedColor)
        tvNavScore.setTextColor(unselectedColor)

        ivNavHeatmap.setColorFilter(unselectedColor)
        tvNavHeatmap.setTextColor(unselectedColor)

        ivNavProfile.setColorFilter(unselectedColor)
        tvNavProfile.setTextColor(unselectedColor)

        val targetFragment: Fragment = when (position) {
            0 -> {
                ivNavRide.setColorFilter(selectedColor)
                tvNavRide.setTextColor(selectedColor)
                rideFragment
            }
            1 -> {
                ivNavHazards.setColorFilter(selectedColor)
                tvNavHazards.setTextColor(selectedColor)
                hazardsFragment
            }
            2 -> {
                ivNavScore.setColorFilter(selectedColor)
                tvNavScore.setTextColor(selectedColor)
                driverScoreFragment
            }
            3 -> {
                ivNavHeatmap.setColorFilter(selectedColor)
                tvNavHeatmap.setTextColor(selectedColor)
                heatmapFragment
            }
            4 -> {
                ivNavProfile.setColorFilter(selectedColor)
                tvNavProfile.setTextColor(selectedColor)
                profileFragment
            }
            else -> rideFragment
        }

        supportFragmentManager.beginTransaction()
            .replace(R.id.fragmentContainer, targetFragment)
            .commit()
    }
}