package com.biopolymer.screening.ui.components

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.biopolymer.screening.ui.theme.*

@Composable
fun MetricChip(
    value: Float,
    label: String,
    modifier: Modifier = Modifier
) {
    val color = when {
        value >= 0.8f -> ScoreExcellent
        value >= 0.6f -> ScoreGood
        value >= 0.4f -> ScoreFair
        else -> ScorePoor
    }

    Surface(
        shape = MaterialTheme.shapes.small,
        color = color.copy(alpha = 0.1f),
        contentColor = color,
        modifier = modifier
    ) {
        Text(
            text = "${(value * 100).toInt()}% $label",
            style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
        )
    }
}
