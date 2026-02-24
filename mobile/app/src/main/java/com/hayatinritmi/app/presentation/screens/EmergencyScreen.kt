package com.hayatinritmi.app.presentation.screens

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import com.hayatinritmi.app.domain.model.AlertEvent
import com.hayatinritmi.app.domain.model.AlertLevel
import com.hayatinritmi.app.presentation.components.GlassOutlinedButton
import com.hayatinritmi.app.presentation.components.GradientButton
import com.hayatinritmi.app.presentation.theme.*
import com.hayatinritmi.app.presentation.viewmodel.EcgViewModel
import com.hayatinritmi.app.presentation.viewmodel.EmergencyViewModel
import kotlinx.coroutines.delay

@Composable
fun EmergencyScreen(
    navController: NavHostController,
    ecgViewModel: EcgViewModel,
    emergencyViewModel: EmergencyViewModel
) {
    var countdown by remember { mutableIntStateOf(10) }
    val statusText = "Acil Durum Kişilerine Mesaj Gönderilecek"
    var isCancelled by remember { mutableStateOf(false) }

    val smsSent by emergencyViewModel.smsSent.collectAsState()
    val smsError by emergencyViewModel.smsError.collectAsState()

    LaunchedEffect(key1 = countdown) {
        if (countdown > 0 && !isCancelled) {
            delay(1000L)
            countdown--
        } else if (countdown == 0 && !isCancelled) {
            val event = AlertEvent(
                timestampMs = System.currentTimeMillis(),
                level = AlertLevel.RED,
                alertSource = "EMERGENCY_SCREEN",
                bpm = ecgViewModel.bpm.value,
                aiPrediction = ecgViewModel.aiPrediction.value
            )
            emergencyViewModel.sendEmergencyAlert(event)
            emergencyViewModel.callEmergencyServices()
        }
    }

    val infiniteTransition = rememberInfiniteTransition(label = "alarm")
    val alpha by infiniteTransition.animateFloat(
        initialValue = 0.3f,
        targetValue = 0.8f,
        animationSpec = infiniteRepeatable(
            animation = tween(500, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ), label = "alarm_alpha"
    )

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
    ) {
        // 1. KIRMIZI ALARM ARKA PLANI
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(
                    brush = Brush.radialGradient(
                        colors = listOf(AlarmRed.copy(alpha = alpha), Color.Black),
                        radius = 800f
                    )
                )
        )

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {

            Icon(
                imageVector = Icons.Default.Warning,
                contentDescription = "Uyarı",
                tint = TextPrimary,
                modifier = Modifier.size(80.dp)
            )

            Spacer(modifier = Modifier.height(24.dp))

            Text(
                text = "KRİTİK RİTİM\nBOZUKLUĞU",
                style = MaterialTheme.typography.headlineLarge,
                color = TextPrimary,
                textAlign = TextAlign.Center
            )

            Spacer(modifier = Modifier.height(16.dp))

            Text(
                text = "Kalp atışlarınızda ciddi düzensizlik tespit edildi.",
                style = MaterialTheme.typography.bodyLarge,
                color = TextSecondary,
                textAlign = TextAlign.Center
            )

            Spacer(modifier = Modifier.height(48.dp))

            // 3. GERİ SAYIM ÇEMBERİ
            if (!isCancelled && countdown > 0) {
                Box(contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(
                        progress = { countdown / 10f },
                        modifier = Modifier.size(160.dp),
                        color = TextPrimary,
                        strokeWidth = 8.dp,
                        trackColor = GlassBorder,
                    )
                    Text(
                        text = countdown.toString(),
                        style = MaterialTheme.typography.displayLarge,
                        color = TextPrimary
                    )
                }

                Spacer(modifier = Modifier.height(32.dp))

                Text(
                    text = statusText,
                    style = MaterialTheme.typography.bodyMedium,
                    color = TextSecondary,
                    textAlign = TextAlign.Center
                )
            } else if (countdown == 0) {
                Box(
                    modifier = Modifier
                        .size(160.dp)
                        .background(Color.White, CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(Icons.Default.Call, contentDescription = null, tint = AlarmRed, modifier = Modifier.size(64.dp))
                }
                Spacer(modifier = Modifier.height(24.dp))
                Text(
                    text = "112 ARANIYOR...",
                    style = MaterialTheme.typography.headlineMedium,
                    color = TextPrimary
                )
            } else {
                // İPTAL EDİLDİ
                Icon(Icons.Default.CheckCircle, contentDescription = null, tint = Emerald500, modifier = Modifier.size(100.dp))
                Spacer(modifier = Modifier.height(16.dp))
                Text(
                    text = "Alarm İptal Edildi",
                    style = MaterialTheme.typography.headlineSmall,
                    color = TextPrimary
                )
            }

            Spacer(modifier = Modifier.weight(1f))

            // 4. BUTONLAR
            if (!isCancelled && countdown > 0) {
                Column(modifier = Modifier.fillMaxWidth()) {
                    GradientButton(
                        text = "İYİYİM, İPTAL ET",
                        onClick = { isCancelled = true },
                        modifier = Modifier.fillMaxWidth(),
                        colors = listOf(Color.White, Color.White.copy(alpha = 0.85f)),
                        height = 64.dp
                    )

                    Spacer(modifier = Modifier.height(16.dp))

                    GlassOutlinedButton(
                        text = "HEMEN YARDIM ÇAĞIR",
                        onClick = {
                            countdown = 0
                        },
                        modifier = Modifier.fillMaxWidth(),
                        accentColor = Color.White,
                        height = 56.dp
                    )
                }
            } else if (isCancelled) {
                GlassOutlinedButton(
                    text = "Ana Ekrana Dön",
                    onClick = { navController.popBackStack() },
                    modifier = Modifier.fillMaxWidth(),
                    accentColor = TextSecondary
                )
            }
        }
    }
}
