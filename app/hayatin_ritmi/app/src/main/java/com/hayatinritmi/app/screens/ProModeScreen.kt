package com.hayatinritmi.app.screens

import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState // EKLENDİ
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll // EKLENDİ
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
import com.hayatinritmi.app.data.model.ConnectionState
import com.hayatinritmi.app.ui.components.GlassCard
import com.hayatinritmi.app.ui.components.MetricCard
import com.hayatinritmi.app.ui.components.StatusBadge
import com.hayatinritmi.app.ui.theme.*
import com.hayatinritmi.app.viewmodel.EcgViewModel

@Composable
fun ProModeScreen(navController: NavHostController, viewModel: EcgViewModel) {
    val bpm by viewModel.bpm.collectAsState()
    val hrv by viewModel.hrv.collectAsState()
    val graphPoints by viewModel.graphPoints.collectAsState()
    val connectionState by viewModel.connectionState.collectAsState()

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
    ) {
        // 1. ARKA PLAN ISIKLARI
        Box(
            modifier = Modifier
                .align(Alignment.TopStart)
                .offset(x = (-100).dp, y = 50.dp)
                .size(400.dp)
                .background(MaterialTheme.colorScheme.secondary.copy(alpha = 0.15f), CircleShape)
                .blur(100.dp)
        )
        Box(
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .offset(x = 100.dp, y = 100.dp)
                .size(300.dp)
                .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.1f), CircleShape)
                .blur(90.dp)
        )

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 24.dp)
                .verticalScroll(rememberScrollState()) // EKLENDİ: Ekranı kaydırılabilir yaptık
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
                            text = "Canlı Monitör",
                            style = MaterialTheme.typography.headlineSmall,
                            color = MaterialTheme.colorScheme.onBackground
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        BlinkingDot()
                        Spacer(modifier = Modifier.width(8.dp))
                        // Connection status dot
                        ConnectionStatusDot(connectionState)
                    }
                    Text(
                        text = when (connectionState) {
                            ConnectionState.CONNECTED -> "SENSÖR AKTİF"
                            ConnectionState.CONNECTING -> "BAĞLANIYOR..."
                            ConnectionState.SCANNING -> "TARANIYOR..."
                            ConnectionState.DISCONNECTED -> "SENSÖR BAĞLI DEĞİL"
                        },
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        letterSpacing = 2.sp
                    )
                }

                // Mod Degistirici
                Box(
                    modifier = Modifier
                        .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(50))
                        .padding(4.dp)
                        .clickable { navController.popBackStack() }
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            text = "Sakin",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.padding(horizontal = 12.dp)
                        )
                        Box(
                            modifier = Modifier
                                .background(MaterialTheme.colorScheme.primary, RoundedCornerShape(50))
                                .padding(horizontal = 12.dp, vertical = 6.dp)
                        ) {
                            Text(
                                text = "PRO",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onPrimary
                            )
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(30.dp))

            // 3. BUYUK BPM GOSTERGESI
            Row(verticalAlignment = Alignment.Bottom) {
                Text(
                    text = if (bpm > 0) bpm.toString() else "--",
                    style = MaterialTheme.typography.displayLarge.copy(
                        fontSize = 80.sp,
                        letterSpacing = (-4).sp
                    ),
                    color = MaterialTheme.colorScheme.onBackground
                )
                Text(
                    text = "BPM",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(bottom = 16.dp, start = 8.dp)
                )
            }

            // 4. CANLI EKG GRAFIGI
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(200.dp)
                    .background(MaterialTheme.colorScheme.surface, RoundedCornerShape(16.dp))
                    .border(1.dp, MaterialTheme.colorScheme.outlineVariant, RoundedCornerShape(16.dp))
                    .clip(RoundedCornerShape(16.dp))
            ) {
                RealTimeEcgGraph(graphPoints)
                ScanlineAnimation()
            }

            Spacer(modifier = Modifier.height(24.dp))

            // 5. AI ANALIZ KARTI
            GlassCard {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.AutoAwesome, contentDescription = null, tint = MaterialTheme.colorScheme.secondary, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "KLİNİK AI ANALİZİ",
                                style = MaterialTheme.typography.labelMedium,
                                color = MaterialTheme.colorScheme.onBackground
                            )
                        }
                        StatusBadge(
                            text = if (connectionState == ConnectionState.CONNECTED) "CANLI TARAMA" else "BEKLEMEDE",
                            color = if (connectionState == ConnectionState.CONNECTED) MaterialTheme.colorScheme.secondary else MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    val rhythmStatus = if (bpm in 60..100) "Düzenli (NSR)" else if (bpm > 0) "Analiz Ediliyor..." else "Veri Bekleniyor"
                    val rhythmColor = if (bpm in 60..100) MaterialTheme.colorScheme.tertiary else AmberWarning
                    AnalysisRow("Sinüs Ritmi:", rhythmStatus, rhythmColor)
                    Spacer(modifier = Modifier.height(8.dp))

                    val rrText = if (bpm > 0) "Stabil (${String.format("%.2f", 60f / bpm)}s)" else "-- s"
                    AnalysisRow("R-R İnterval:", rrText, MaterialTheme.colorScheme.onBackground)
                    Spacer(modifier = Modifier.height(8.dp))

                    val sdnnText = if (hrv.sdnn > 0f) String.format("%.1f ms", hrv.sdnn) else "-- ms"
                    AnalysisRow("SDNN:", sdnnText, MaterialTheme.colorScheme.tertiary)
                }
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
                    color = MaterialTheme.colorScheme.secondary
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

            // EKLENDİ: Alt barın (NavBar) altında kalmaması için bırakılan boşluk
            Spacer(modifier = Modifier.height(120.dp))
        }
    }
}

@Composable
fun ConnectionStatusDot(connectionState: ConnectionState) {
    val color = when (connectionState) {
        ConnectionState.CONNECTED -> MaterialTheme.colorScheme.tertiary
        ConnectionState.CONNECTING, ConnectionState.SCANNING -> AmberWarning
        ConnectionState.DISCONNECTED -> MaterialTheme.colorScheme.error
    }
    Box(
        modifier = Modifier
            .size(8.dp)
            .background(color, CircleShape)
    )
}

@Composable
fun RealTimeEcgGraph(graphPoints: List<Float>) {
    val bgColor = MaterialTheme.colorScheme.surface
    val gridColor = MaterialTheme.colorScheme.onSurface
    val ecgLineColor = MaterialTheme.colorScheme.primary

    Canvas(modifier = Modifier.fillMaxSize()) {
        val width = size.width
        val height = size.height

        drawRect(color = bgColor)

        val minorStepX = width / 100f
        val majorStepX = width / 20f

        for (i in 0..(width / minorStepX).toInt()) {
            drawLine(
                color = gridColor.copy(alpha = 0.05f),
                start = Offset(i * minorStepX, 0f),
                end = Offset(i * minorStepX, height)
            )
        }
        for (i in 0..(width / majorStepX).toInt()) {
            drawLine(
                color = gridColor.copy(alpha = 0.1f),
                start = Offset(i * majorStepX, 0f),
                end = Offset(i * majorStepX, height),
                strokeWidth = 1.5f
            )
        }

        val hGridStep = height / 8f
        for (i in 0..8) {
            val alpha = if (i == 4) 0.15f else 0.05f
            val sw = if (i == 4) 1.5f else 1f
            drawLine(
                color = gridColor.copy(alpha = alpha),
                start = Offset(0f, i * hGridStep),
                end = Offset(width, i * hGridStep),
                strokeWidth = sw
            )
        }

        if (graphPoints.isEmpty()) return@Canvas

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

        drawPath(
            path = path,
            color = ecgLineColor.copy(alpha = 0.3f),
            style = Stroke(width = 12f, cap = StrokeCap.Round)
        )

        drawPath(
            path = path,
            color = ecgLineColor,
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

    val dotColor = MaterialTheme.colorScheme.primary

    Box(
        modifier = Modifier
            .size(8.dp)
            .background(dotColor.copy(alpha = alpha), CircleShape)
            .border(1.dp, dotColor.copy(alpha = 0.5f), CircleShape)
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

    val scanColor = MaterialTheme.colorScheme.secondary

    BoxWithConstraints(modifier = Modifier.fillMaxSize()) {
        val scanX = this.maxWidth * fraction
        Box(
            modifier = Modifier
                .fillMaxHeight()
                .width(2.dp)
                .offset(x = scanX)
                .background(
                    brush = Brush.verticalGradient(
                        colors = listOf(Color.Transparent, scanColor, Color.Transparent)
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
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodySmall,
            fontWeight = FontWeight.Bold,
            color = valueColor
        )
    }
}