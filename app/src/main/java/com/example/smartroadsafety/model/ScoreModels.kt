package com.example.smartroadsafety.model

data class FineTicket(
    val ticketId: String,
    val reason: String,
    val date: String,
    val amount: String,
    val status: String = "UNPAID",
    val location: String = ""
)

data class TelematicsPillars(
    val smoothnessPct: Int,
    val corneringPct: Int,
    val speedCompliancePct: Int,
    val vigilancePct: Int
)

data class DriverScoreSummary(
    val overallScore: Int,
    val actuarialTier: String,
    val insuranceDiscountPct: Int,
    val trend: String,
    val pillars: TelematicsPillars,
    val fineTickets: List<FineTicket>
)
