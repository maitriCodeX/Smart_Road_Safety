package com.example.smartroadsafety

import android.os.Bundle
import android.widget.EditText
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.AppCompatButton
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.fragment.app.Fragment

class MainActivity : AppCompatActivity() {

    private lateinit var etActiveTunnel: EditText
    private lateinit var btnApplyTunnel: AppCompatButton

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

    private var currentTabPosition = 0

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

        SafetyEngine.start(this)

        // "The first icon is for ride(by default this will be open once logged in)."
        if (savedInstanceState == null) {
            selectTab(0)
        }
    }

    private fun initViews() {
        etActiveTunnel = findViewById(R.id.etActiveTunnel)
        btnApplyTunnel = findViewById(R.id.btnApplyTunnel)

        etActiveTunnel.setText(SafetyEngine.getActiveTunnelName())
        btnApplyTunnel.setOnClickListener {
            val input = etActiveTunnel.text.toString().trim()
            if (input.isNotBlank()) {
                SafetyEngine.setTunnelName(input)
                Toast.makeText(this, "Connected: ${SafetyEngine.resolveBaseUrl()}", Toast.LENGTH_SHORT).show()
                selectTab(currentTabPosition)
            }
        }

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
        currentTabPosition = position
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
                RideFragment()
            }
            1 -> {
                ivNavHazards.setColorFilter(selectedColor)
                tvNavHazards.setTextColor(selectedColor)
                HazardsFragment()
            }
            2 -> {
                ivNavScore.setColorFilter(selectedColor)
                tvNavScore.setTextColor(selectedColor)
                DriverScoreFragment()
            }
            3 -> {
                ivNavHeatmap.setColorFilter(selectedColor)
                tvNavHeatmap.setTextColor(selectedColor)
                HeatmapFragment()
            }
            4 -> {
                ivNavProfile.setColorFilter(selectedColor)
                tvNavProfile.setTextColor(selectedColor)
                ProfileFragment()
            }
            else -> RideFragment()
        }

        supportFragmentManager.beginTransaction()
            .replace(R.id.fragmentContainer, targetFragment)
            .commit()
    }
}