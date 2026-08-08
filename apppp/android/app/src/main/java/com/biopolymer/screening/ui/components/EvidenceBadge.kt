package com.biopolymer.screening.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.biopolymer.screening.ui.theme.ConfidenceHigh
import com.biopolymer.screening.ui.theme.ConfidenceLow
import com.biopolymer.screening.ui.theme.ConfidenceMed

@Composable
fun EvidenceBadge(
    evidenceLevel: String,
    modifier: Modifier = Modifier
) {
    val isHigh = evidenceLevel.lowercase() == "high"
    val isMed = evidenceLevel.lowercase() == "med"

    val color = when {
        isHigh -> ConfidenceHigh
        isMed -> ConfidenceMed
        else -> ConfidenceLow
    }

    Surface(
        shape = MaterialTheme.shapes.small,
        color = if (isHigh) color.copy(alpha = 0.1f) else Color.Transparent,
        border = if (!isHigh) BorderStroke(1.dp, color.copy(alpha = 0.5f)) else null,
        contentColor = color,
        modifier = modifier
    ) {
        Text(
            text = "Evidence: ${evidenceLevel.replaceFirstChar { it.uppercase() }}",
            style = MaterialTheme.typography.labelSmall,
            fontWeight = FontWeight.SemiBold,
            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
        )
    }
}
