package com.biopolymer.screening.ui.components

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.biopolymer.screening.ui.theme.*
import kotlin.math.roundToInt

@Composable
fun MetricChip(
    value: Float,
    label: String,
    modifier: Modifier = Modifier
) {
    val boundedValue = value.coerceIn(0f, 100f)
    val pct = boundedValue.roundToInt()

    val color = when {
        boundedValue >= 80f -> ScoreExcellent
        boundedValue >= 70f -> ScoreGood
        boundedValue >= 50f -> ScoreFair
        else -> ScorePoor
    }

    Surface(
        shape = MaterialTheme.shapes.small,
        color = color.copy(alpha = 0.1f),
        contentColor = color,
        modifier = modifier
    ) {
        Text(
            text = "$pct% $label",
            style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
        )
    }
}
