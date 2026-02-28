package com.hayatinritmi.app.presentation.screens

import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.hayatinritmi.app.domain.model.ArrhythmiaClass
import com.hayatinritmi.app.domain.model.ConnectionState
import com.hayatinritmi.app.presentation.components.GlassCard
import com.hayatinritmi.app.presentation.components.MetricCard
import com.hayatinritmi.app.presentation.components.StatusBadge
import com.hayatinritmi.app.presentation.theme.*
import com.hayatinritmi.app.presentation.viewmodel.EcgViewModel
import com.hayatinritmi.app.presentation.accessibility.accessibleBpm
import com.hayatinritmi.app.presentation.accessibility.accessibleAlert

@Composable
fun ProModeScreen(navController: NavHostController, viewModel: EcgViewModel) {
    val bpm by viewModel.bpm.collectAsState()
    val hrv by viewModel.hrv.collectAsState()
    val graphPoints by viewModel.graphPoints.collectAsState()
    val connectionState by viewModel.connectionState.collectAsState()
    val aiPrediction by viewModel.aiPrediction.collectAsState()
    val alertLevel by viewModel.alertLevel.collectAsState()
    val signalQuality by viewModel.signalQuality.collectAsState()

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(RichBlack)
    ) {
        // 1. ARKA PLAN ISIKLARI
        Box(
            modifier = Modifier
                .align(Alignment.TopStart)
                .offset(x = (-100).dp, y = 50.dp)
                .size(400.dp)
                .background(NeonBlue.copy(alpha = 0.15f), CircleShape)
                .blur(100.dp)
        )
        Box(
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .offset(x = 100.dp, y = 100.dp)
                .size(300.dp)
                .background(NeonRed.copy(alpha = 0.1f), CircleShape)
                .blur(90.dp)
        )

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 24.dp)
        ) {
            Spacer(modifier = Modifier.height(40.dp))

            // 2. HEADER
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            text = "Canli Monitor",
                            style = MaterialTheme.typography.headlineSmall,
                            color = TextPrimary
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        BlinkingDot()
                        Spacer(modifier = Modifier.width(8.dp))
                        // Connection status dot
                        ConnectionStatusDot(connectionState)
                    }
                    Text(
                        text = when (connectionState) {
                            ConnectionState.CONNECTED -> "SENSOR AKTIF"
                            ConnectionState.CONNECTING -> "BAGLANIYOR..."
                            ConnectionState.SCANNING -> "TARANIYOR..."
                            ConnectionState.DISCONNECTED -> "SENSOR BAGLI DEGIL"
                        },
                        style = MaterialTheme.typography.labelSmall,
                        color = TextTertiary,
                        letterSpacing = 2.sp
                    )
                }

                // Mod Degistirici
                Box(
                    modifier = Modifier
                        .background(GlassMedium, RoundedCornerShape(50))
                        .padding(4.dp)
                        .clickable { navController.popBackStack() }
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            text = "Sakin",
                            style = MaterialTheme.typography.labelSmall,
                            color = TextSecondary,
                            modifier = Modifier.padding(horizontal = 12.dp)
                        )
                        Box(
                            modifier = Modifier
                                .background(NeonRed, RoundedCornerShape(50))
                                .padding(horizontal = 12.dp, vertical = 6.dp)
                        ) {
                            Text(
                                text = "PRO",
                                style = MaterialTheme.typography.labelSmall,
                                color = TextWhite
                            )
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(30.dp))

            // 3. BUYUK BPM GOSTERGESI
            Row(
                verticalAlignment = Alignment.Bottom,
                modifier = Modifier.accessibleBpm(bpm)
            ) {
                Text(
                    text = if (bpm > 0) bpm.toString() else "--",
                    style = MaterialTheme.typography.displayLarge.copy(
                        fontSize = 80.sp,
                        letterSpacing = (-4).sp
                    ),
                    color = TextPrimary
                )
                Text(
                    text = "BPM",
                    style = MaterialTheme.typography.titleMedium,
                    color = TextTertiary,
                    modifier = Modifier.padding(bottom = 16.dp, start = 8.dp)
                )
            }

            // 4. CANLI EKG GRAFIGI
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(200.dp)
                    .background(GlassWhite, RoundedCornerShape(16.dp))
                    .border(1.dp, BorderSubtle, RoundedCornerShape(16.dp))
                    .clip(RoundedCornerShape(16.dp))
            ) {
                RealTimeEcgGraph(graphPoints)
                ScanlineAnimation()
            }

            Spacer(modifier = Modifier.height(24.dp))

            // 5. AI ANALIZ KARTI
            GlassCard(
                modifier = Modifier.accessibleAlert(alertLevel.name)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.AutoAwesome, contentDescription = null, tint = NeonBlue, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "KLINIK AI ANALIZI",
                            style = MaterialTheme.typography.labelMedium,
                            color = TextPrimary
                        )
                    }
                    StatusBadge(
                        text = if (connectionState == ConnectionState.CONNECTED) "CANLI TARAMA" else "BEKLEMEDE",
                        color = if (connectionState == ConnectionState.CONNECTED) NeonBlue else TextTertiary
                    )
                }

                Spacer(modifier = Modifier.height(16.dp))

                val labelColor = when {
                    aiPrediction.label.isCritical -> AlarmRed
                    aiPrediction.label == ArrhythmiaClass.NORMAL -> Emerald500
                    aiPrediction.label == ArrhythmiaClass.UNKNOWN -> TextSecondary
                    else -> AmberWarning
                }
                val confText = if (aiPrediction.confidence > 0f)
                    "${(aiPrediction.confidence * 100).toInt()}%" else "—"
                AnalysisRow("AI Tanı:", aiPrediction.label.displayName, labelColor)
                Spacer(modifier = Modifier.height(8.dp))
                AnalysisRow("Güven Skoru:", confText, TextPrimary)
                Spacer(modifier = Modifier.height(8.dp))
                val sdnnText = if (hrv.sdnn > 0f) String.format("%.1f ms", hrv.sdnn) else "-- ms"
                AnalysisRow("SDNN:", sdnnText, Emerald500)
                Spacer(modifier = Modifier.height(8.dp))
                val qualityColor = when {
                    signalQuality.score == 0 -> TextSecondary
                    signalQuality.isAcceptable -> Emerald500
                    else -> AmberWarning
                }
                val qualityText = if (signalQuality.score > 0)
                    "${if (signalQuality.isAcceptable) "İyi" else "Zayıf"} (${signalQuality.score}/100)" else "—"
                AnalysisRow("Sinyal Kalitesi:", qualityText, qualityColor)
            }

            Spacer(modifier = Modifier.height(16.dp))

            // 6. ALT KARTLAR
            Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                MetricCard(
                    modifier = Modifier.weight(1f),
                    title = "HRV (RMSSD)",
                    value = if (hrv.rmssd > 0f) String.format("%.0f", hrv.rmssd) else "--",
                    unit = "ms",
                    icon = Icons.Default.GraphicEq,
                    color = NeonBlue
                )
                MetricCard(
                    modifier = Modifier.weight(1f),
                    title = "SpO2",
                    value = "98",
                    unit = "%",
                    icon = Icons.Default.WaterDrop,
                    color = CyanAccent
                )
            }
        }
    }
}

@Composable
fun ConnectionStatusDot(connectionState: ConnectionState) {
    val color = when (connectionState) {
        ConnectionState.CONNECTED -> Color(0xFF10B981)
        ConnectionState.CONNECTING, ConnectionState.SCANNING -> Color(0xFFFBBF24)
        ConnectionState.DISCONNECTED -> Color(0xFFEF4444)
    }
    Box(
        modifier = Modifier
            .size(8.dp)
            .background(color, CircleShape)
    )
}

@Composable
fun RealTimeEcgGraph(graphPoints: List<Float>) {
    Canvas(modifier = Modifier.fillMaxSize()) {
        val width = size.width
        val height = size.height
        val midY = height / 2

        // Background
        drawRect(color = Color.Black.copy(alpha = 0.5f))

        // EKG Grid: minor lines every 0.04s, major lines every 0.2s
        // At 250Hz, 4 seconds = 1000 samples displayed across width
        // Minor grid: 0.04s = 10 samples -> width / 100 subdivisions
        // Major grid: 0.2s = 50 samples -> width / 20 subdivisions
        val minorStepX = width / 100f
        val majorStepX = width / 20f

        // Minor vertical grid lines
        for (i in 0..(width / minorStepX).toInt()) {
            drawLine(
                color = Color.White.copy(alpha = 0.03f),
                start = Offset(i * minorStepX, 0f),
                end = Offset(i * minorStepX, height)
            )
        }
        // Major vertical grid lines
        for (i in 0..(width / majorStepX).toInt()) {
            drawLine(
                color = Color.White.copy(alpha = 0.08f),
                start = Offset(i * majorStepX, 0f),
                end = Offset(i * majorStepX, height),
                strokeWidth = 1.5f
            )
        }

        // Horizontal grid lines
        val hGridStep = height / 8f
        for (i in 0..8) {
            val alpha = if (i == 4) 0.1f else 0.04f
            val sw = if (i == 4) 1.5f else 1f
            drawLine(
                color = Color.White.copy(alpha = alpha),
                start = Offset(0f, i * hGridStep),
                end = Offset(width, i * hGridStep),
                strokeWidth = sw
            )
        }

        if (graphPoints.isEmpty()) return@Canvas

        // Auto-scale Y axis based on data range
        val maxVal = graphPoints.maxOrNull() ?: 1f
        val minVal = graphPoints.minOrNull() ?: -1f
        val range = (maxVal - minVal).coerceAtLeast(1f)
        val padding = range * 0.1f
        val yScale = height / (range + 2f * padding)
        val yOffset = maxVal + padding

        val path = Path()
        val stepX = width / graphPoints.size.toFloat()

        graphPoints.forEachIndexed { index, value ->
            val x = index * stepX
            val y = (yOffset - value) * yScale
            if (index == 0) {
                path.moveTo(x, y)
            } else {
                path.lineTo(x, y)
            }
        }

        // Glow effect
        drawPath(
            path = path,
            color = NeonRed.copy(alpha = 0.3f),
            style = Stroke(width = 12f, cap = StrokeCap.Round)
        )

        // Main ECG trace
        drawPath(
            path = path,
            color = NeonRed,
            style = Stroke(
                width = 3f,
                cap = StrokeCap.Round,
                join = StrokeJoin.Round
            )
        )
    }
}

@Composable
fun BlinkingDot() {
    val infiniteTransition = rememberInfiniteTransition(label = "blink")
    val alpha by infiniteTransition.animateFloat(
        initialValue = 1f,
        targetValue = 0.2f,
        animationSpec = infiniteRepeatable(
            animation = tween(800, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ), label = "alpha"
    )

    Box(
        modifier = Modifier
            .size(8.dp)
            .background(NeonRed.copy(alpha = alpha), CircleShape)
            .border(1.dp, NeonRed.copy(alpha = 0.5f), CircleShape)
    )
}

@Composable
fun ScanlineAnimation() {
    val infiniteTransition = rememberInfiniteTransition(label = "scan")
    val fraction by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(3000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ), label = "scanline"
    )

    BoxWithConstraints(modifier = Modifier.fillMaxSize()) {
        val scanX = this.maxWidth * fraction
        Box(
            modifier = Modifier
                .fillMaxHeight()
                .width(2.dp)
                .offset(x = scanX)
                .background(
                    brush = Brush.verticalGradient(
                        colors = listOf(Color.Transparent, NeonBlue, Color.Transparent)
                    )
                )
        )
    }
}

@Composable
fun AnalysisRow(label: String, value: String, valueColor: Color) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodySmall,
            color = TextSecondary
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodySmall,
            fontWeight = FontWeight.Bold,
            color = valueColor
        )
    }
}
