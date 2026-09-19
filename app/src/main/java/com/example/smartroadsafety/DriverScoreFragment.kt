package com.example.smartroadsafety

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.TextView
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import com.example.smartroadsafety.data.DataRepository
import com.example.smartroadsafety.model.DriverScoreSummary
import kotlinx.coroutines.launch

class DriverScoreFragment : Fragment() {

    private lateinit var tvOverallScoreNumber: TextView
    private lateinit var tvDriverTier: TextView
    private lateinit var tvInsuranceBonus: TextView
    private lateinit var tvScoreTrend: TextView
    private lateinit var tvPillarSmoothness: TextView
    private lateinit var tvPillarCornering: TextView
    private lateinit var tvPillarSpeed: TextView
    private lateinit var tvPillarVigilance: TextView
    private lateinit var llFineTicketsContainer: LinearLayout

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        val view = inflater.inflate(R.layout.fragment_driver_score, container, false)
        initViews(view)
        loadScoreData()
        return view
    }

    private fun initViews(view: View) {
        tvOverallScoreNumber = view.findViewById(R.id.tvOverallScoreNumber)
        tvDriverTier = view.findViewById(R.id.tvDriverTier)
        tvInsuranceBonus = view.findViewById(R.id.tvInsuranceBonus)
        tvScoreTrend = view.findViewById(R.id.tvScoreTrend)
        tvPillarSmoothness = view.findViewById(R.id.tvPillarSmoothness)
        tvPillarCornering = view.findViewById(R.id.tvPillarCornering)
        tvPillarSpeed = view.findViewById(R.id.tvPillarSpeed)
        tvPillarVigilance = view.findViewById(R.id.tvPillarVigilance)
        llFineTicketsContainer = view.findViewById(R.id.llFineTicketsContainer)
    }

    private fun loadScoreData() {
        renderScoreSummary(DataRepository.getDriverScoreSummary())

        viewLifecycleOwner.lifecycleScope.launch {
            val summary = DataRepository.fetchDriverScoreOnline()
            renderScoreSummary(summary)
        }
    }

    private fun renderScoreSummary(summary: DriverScoreSummary) {
        if (!isAdded || context == null) return

        // Populate top rounded rectangle score
        tvOverallScoreNumber.text = summary.overallScore.toString()
        tvDriverTier.text = "${summary.actuarialTier} Tier"
        tvInsuranceBonus.text = "${summary.insuranceDiscountPct}% Insurance Discount"
        tvScoreTrend.text = "Actuarial Status: ${summary.trend}"

        tvPillarSmoothness.text = "${summary.pillars.smoothnessPct}% (Smooth Braking)"
        tvPillarCornering.text = "${summary.pillars.corneringPct}% (Centrifugal Safe)"
        tvPillarSpeed.text = "${summary.pillars.speedCompliancePct}% (Speed Compliant)"
        tvPillarVigilance.text = "${summary.pillars.vigilancePct}% (High Vigilance)"

        // "Below that fine ticket info will be listed in card form with each card having reason for fine ticket, date, amount (bg- 9D0208, text-white)."
        llFineTicketsContainer.removeAllViews()
        val inflater = LayoutInflater.from(requireContext())

        summary.fineTickets.forEach { ticket ->
            val cardView = inflater.inflate(R.layout.item_fine_ticket_card, llFineTicketsContainer, false)
            val tvReason = cardView.findViewById<TextView>(R.id.tvTicketReason)
            val tvDate = cardView.findViewById<TextView>(R.id.tvTicketDate)
            val tvAmount = cardView.findViewById<TextView>(R.id.tvTicketAmount)
            val tvLocation = cardView.findViewById<TextView>(R.id.tvTicketLocation)
            val tvStatus = cardView.findViewById<TextView>(R.id.tvTicketStatus)

            tvReason.text = "Reason: ${ticket.reason}"
            tvDate.text = "Date: ${ticket.date}"
            tvAmount.text = ticket.amount
            tvLocation.text = ticket.location
            tvStatus.text = ticket.status

            llFineTicketsContainer.addView(cardView)
        }
    }
}
