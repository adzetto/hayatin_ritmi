package com.hayatinritmi.app.presentation.screens

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.material3.ripple
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import com.hayatinritmi.app.Screen
import com.hayatinritmi.app.domain.model.AiPrediction
import com.hayatinritmi.app.domain.model.AlertLevel
import com.hayatinritmi.app.domain.model.ArrhythmiaClass
import com.hayatinritmi.app.domain.model.ConnectionState
import com.hayatinritmi.app.presentation.components.InfoCard
import com.hayatinritmi.app.presentation.components.StatusBadge
import com.hayatinritmi.app.presentation.theme.*
import com.hayatinritmi.app.presentation.viewmodel.EcgViewModel

@Composable
fun DashboardScreen(navController: NavHostController, ecgViewModel: EcgViewModel? = null) {
    val connectionState = ecgViewModel?.connectionState?.collectAsState()?.value
        ?: ConnectionState.DISCONNECTED
    val bpm = ecgViewModel?.bpm?.collectAsState()?.value ?: 0
    val alertLevel = ecgViewModel?.alertLevel?.collectAsState()?.value ?: AlertLevel.NONE
    val aiPrediction = ecgViewModel?.aiPrediction?.collectAsState()?.value ?: AiPrediction()
    val alertCircleColor = when (alertLevel) {
        AlertLevel.RED -> AlarmRed
        AlertLevel.YELLOW -> AmberWarning
        else -> Emerald500
    }

    LaunchedEffect(alertLevel) {
        if (alertLevel == AlertLevel.RED) {
            navController.navigate(Screen.Emergency.route)
        }
    }

    val statusColor = when (connectionState) {
        ConnectionState.CONNECTED -> Emerald500
        ConnectionState.SCANNING, ConnectionState.CONNECTING -> AmberWarning
        ConnectionState.DISCONNECTED -> NeutralGray
    }
    val statusText = when (connectionState) {
        ConnectionState.CONNECTED -> "TİŞÖRT BAĞLI"
        ConnectionState.SCANNING -> "TARAMA YAPILIYOR..."
        ConnectionState.CONNECTING -> "BAĞLANIYOR..."
        ConnectionState.DISCONNECTED -> "TİŞÖRT BAĞLI DEĞİL"
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
    ) {
        // ── AMBİYANS IŞIKLARI ──────────────────────────────
        Box(
            modifier = Modifier
                .offset(x = (-50).dp, y = (-50).dp)
                .size(300.dp)
                .background(statusColor.copy(alpha = 0.2f), CircleShape)
                .blur(80.dp)
        )
        Box(
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .offset(x = 50.dp, y = 50.dp)
                .size(300.dp)
                .background(NeonBlue.copy(alpha = 0.2f), CircleShape)
                .blur(80.dp)
        )

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 24.dp)
                .verticalScroll(rememberScrollState())
        ) {
            // ── ÜST BAR ────────────────────────────────────
            Spacer(modifier = Modifier.height(40.dp))
            TopBarSection(statusText = statusText, statusColor = statusColor)

            Spacer(modifier = Modifier.height(60.dp))

            // ── NEFES ALAN DAİRE ────────────────────────────
            Box(
                modifier = Modifier.fillMaxWidth(),
                contentAlignment = Alignment.Center
            ) {
                val interactionSource = remember { MutableInteractionSource() }
                Box(
                    modifier = Modifier
                        .size(220.dp)
                        .clip(CircleShape)
                        .clickable(
                            interactionSource = interactionSource,
                            indication = ripple(
                                bounded = true,
                                color = alertCircleColor.copy(alpha = 0.3f)
                            ),
                            role = Role.Button,
                            onClick = { navController.navigate(Screen.ProMode.route) }
                        )
                        .semantics {
                            contentDescription = "Kalp ritmi durumu. Pro moda gitmek için dokunun."
                        }
                ) {
                    BreathingCircleAnimation(
                        bpm = bpm,
                        alertColor = alertCircleColor,
                        alertLevel = alertLevel
                    )
                }
            }

            Spacer(modifier = Modifier.height(40.dp))

            // ── BİLGİ KARTLARI (InfoCard from CommonComponents) ─
            val aiNote = when {
                aiPrediction.label == ArrhythmiaClass.UNKNOWN ->
                    "Henüz bir analiz yapılmadı. Sensör bağlandığında AI taraması başlayacak."
                aiPrediction.label == ArrhythmiaClass.NORMAL ->
                    "Kalp ritminiz normal görünüyor (%${(aiPrediction.confidence * 100).toInt()} güven). " +
                        "İlacınızı aldıysanız günün tadını çıkarabilirsiniz."
                aiPrediction.label.isCritical ->
                    "⚠️ ${aiPrediction.label.displayName} tespit edildi (%${(aiPrediction.confidence * 100).toInt()} güven). " +
                        "Lütfen doktorunuza danışın."
                else ->
                    "${aiPrediction.label.displayName} tespit edildi (%${(aiPrediction.confidence * 100).toInt()} güven). Detaylar için Pro moda geçin."
            }

            val aiIconColor = when {
                aiPrediction.label.isCritical -> AlarmRed
                aiPrediction.label == ArrhythmiaClass.NORMAL -> Emerald500
                aiPrediction.label == ArrhythmiaClass.UNKNOWN -> NeonBlue
                else -> AmberWarning
            }

            InfoCard(
                icon = Icons.Default.AutoAwesome,
                iconColor = aiIconColor,
                title = "Yapay Zeka Notu",
                description = aiNote
            )

            Spacer(modifier = Modifier.height(16.dp))

            InfoCard(
                icon = Icons.Default.PieChart,
                iconColor = NeonBlue,
                title = "Detaylı Rapor & EKG",
                description = "Doktorunuz için teknik veriler",
                showArrow = true,
                onClick = { navController.navigate(Screen.ProMode.route) }
            )

            // NavBar ile çakışmaması için alt boşluk
            Spacer(modifier = Modifier.height(100.dp))
        }

        // ── YÜZEN NAVİGASYON ───────────────────────────────
        FloatingNavBar(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(bottom = 30.dp),
            navController = navController,
            currentRoute = Screen.Dashboard.route
        )

        // ── GİZLİ ACİL DURUM BUTONU (DEMO) ─────────────────
        IconButton(
            onClick = { navController.navigate(Screen.Emergency.route) },
            modifier = Modifier
                .align(Alignment.TopEnd)
                .padding(top = 40.dp)
                .semantics { contentDescription = "Acil Durum Test" }
        ) {
            Icon(
                Icons.Default.Warning,
                contentDescription = null,
                tint = TextDisabled
            )
        }
    }
}

// ══════════════════════════════════════════════════════
//  ÜST BAR — Karşılama + Durum badge + Profil ikonu
// ══════════════════════════════════════════════════════

@Composable
fun TopBarSection(statusText: String = "TİŞÖRT BAĞLI", statusColor: Color = Emerald500) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column {
            Text(
                text = "Merhaba, Ahmet",
                style = MaterialTheme.typography.headlineSmall,
                color = TextPrimary,
                modifier = Modifier.semantics { heading() }
            )
            Spacer(modifier = Modifier.height(8.dp))
            StatusBadge(
                text = statusText,
                color = statusColor
            )
        }

        val interactionSource = remember { MutableInteractionSource() }
        Box(
            modifier = Modifier
                .size(44.dp)
                .background(SurfaceElevated, CircleShape)
                .border(1.dp, GlassBorder, CircleShape)
                .clip(CircleShape)
                .clickable(
                    interactionSource = interactionSource,
                    indication = ripple(bounded = true, color = TextSecondary),
                    role = Role.Button,
                    onClick = { /* Profil eylemi */ }
                )
                .semantics { contentDescription = "Profil" },
            contentAlignment = Alignment.Center
        ) {
            Icon(
                Icons.Default.Person,
                contentDescription = null,
                tint = TextSecondary,
                modifier = Modifier.size(22.dp)
            )
        }
    }
}

// ══════════════════════════════════════════════════════
//  NEFES ALAN DAİRE — Animasyonlu kalp ritmi göstergesi
// ══════════════════════════════════════════════════════

@Composable
fun BreathingCircleAnimation(bpm: Int = 0, alertColor: Color = Emerald500, alertLevel: AlertLevel = AlertLevel.NONE) {
    val animDuration = when (alertLevel) {
        AlertLevel.RED -> 600
        AlertLevel.YELLOW -> 1800
        else -> 4000
    }
    val infiniteTransition = rememberInfiniteTransition(label = "breathing")

    val scale by infiniteTransition.animateFloat(
        initialValue = 1f,
        targetValue = 1.08f,
        animationSpec = infiniteRepeatable(
            animation = tween(animDuration, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "scale"
    )

    val glowAlpha by infiniteTransition.animateFloat(
        initialValue = 0.15f,
        targetValue = 0.35f,
        animationSpec = infiniteRepeatable(
            animation = tween(animDuration, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "glow"
    )

    Box(
        modifier = Modifier
            .size(220.dp)
            .scale(scale)
            .background(
                brush = Brush.radialGradient(
                    colors = listOf(alertColor.copy(alpha = glowAlpha), Color.Transparent)
                ),
                shape = CircleShape
            )
            .border(2.dp, alertColor.copy(alpha = 0.3f), CircleShape),
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Icon(
                imageVector = Icons.Default.Favorite,
                contentDescription = null,
                tint = alertColor,
                modifier = Modifier.size(48.dp)
            )
            Spacer(modifier = Modifier.height(12.dp))
            Text(
                text = if (bpm > 0) "$bpm" else alertLevel.displayText,
                style = if (bpm > 0) MaterialTheme.typography.headlineLarge
                else MaterialTheme.typography.headlineMedium,
                color = TextPrimary
            )
            Text(
                text = if (bpm > 0) "BPM" else alertLevel.subText,
                style = MaterialTheme.typography.bodyMedium,
                color = alertColor.copy(alpha = 0.8f)
            )
        }
    }
}

// ══════════════════════════════════════════════════════
//  YÜZEN NAVİGASYON BARI — Diğer ekranlar da kullanır
// ══════════════════════════════════════════════════════

@Composable
fun FloatingNavBar(
    modifier: Modifier = Modifier,
    navController: NavHostController,
    currentRoute: String = Screen.Dashboard.route
) {
    Row(
        modifier = modifier
            .fillMaxWidth(0.85f)
            .clip(RoundedCornerShape(30.dp))
            .background(Surface1.copy(alpha = 0.95f))
            .border(1.dp, GlassBorder, RoundedCornerShape(30.dp))
            .padding(vertical = 8.dp),
        horizontalArrangement = Arrangement.SpaceEvenly,
        verticalAlignment = Alignment.CenterVertically
    ) {
        NavIcon(
            icon = Icons.Default.Home,
            label = "Ana Sayfa",
            isActive = currentRoute == Screen.Dashboard.route
        ) {
            if (currentRoute != Screen.Dashboard.route) {
                navController.navigate(Screen.Dashboard.route) {
                    popUpTo(Screen.Dashboard.route) { inclusive = true }
                }
            }
        }
        NavIcon(
            icon = Icons.Default.Description,
            label = "Raporlar",
            isActive = currentRoute == Screen.ProMode.route
        ) {
            if (currentRoute != Screen.ProMode.route) {
                navController.navigate(Screen.ProMode.route)
            }
        }
        NavIcon(
            icon = Icons.Default.Notifications,
            label = "Bildirimler",
            isActive = currentRoute == Screen.Notifications.route
        ) {
            if (currentRoute != Screen.Notifications.route) {
                navController.navigate(Screen.Notifications.route)
            }
        }
        NavIcon(
            icon = Icons.Default.Settings,
            label = "Ayarlar",
            isActive = currentRoute == Screen.Settings.route
        ) {
            if (currentRoute != Screen.Settings.route) {
                navController.navigate(Screen.Settings.route)
            }
        }
    }
}

@Composable
fun NavIcon(
    icon: ImageVector,
    label: String,
    isActive: Boolean,
    onClick: () -> Unit
) {
    IconButton(
        onClick = onClick,
        modifier = Modifier
            .sizeIn(minWidth = 48.dp, minHeight = 48.dp)
            .semantics { contentDescription = label }
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = if (isActive) Emerald500 else TextDisabled,
            modifier = Modifier.size(24.dp)
        )
    }
}
