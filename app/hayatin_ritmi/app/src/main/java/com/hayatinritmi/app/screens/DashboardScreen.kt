package com.hayatinritmi.app.screens

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
import com.hayatinritmi.app.data.model.ConnectionState
import com.hayatinritmi.app.ui.components.InfoCard
import com.hayatinritmi.app.ui.components.StatusBadge
import com.hayatinritmi.app.ui.theme.*
import com.hayatinritmi.app.viewmodel.EcgViewModel

@Composable
fun DashboardScreen(navController: NavHostController, ecgViewModel: EcgViewModel? = null) {
    val connectionState = ecgViewModel?.connectionState?.collectAsState()?.value
        ?: ConnectionState.DISCONNECTED
    val bpm = ecgViewModel?.bpm?.collectAsState()?.value ?: 0

    val statusColor = when (connectionState) {
        ConnectionState.CONNECTED -> MaterialTheme.colorScheme.tertiary
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
            .background(MaterialTheme.colorScheme.background)
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
                .background(MaterialTheme.colorScheme.secondary.copy(alpha = 0.2f), CircleShape)
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
            TopBarSection(
                statusText = statusText,
                statusColor = statusColor,
                onModeSwitchClick = { navController.navigate(Screen.ProMode.route) } // PRO moda geçiş
            )

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
                                color = MaterialTheme.colorScheme.tertiary.copy(alpha = 0.3f)
                            ),
                            role = Role.Button,
                            onClick = { navController.navigate(Screen.ProMode.route) }
                        )
                        .semantics {
                            contentDescription = "Kalp ritmi durumu. Pro moda gitmek için dokunun."
                        }
                ) {
                    BreathingCircleAnimation(bpm = bpm)
                }
            }

            Spacer(modifier = Modifier.height(40.dp))

            // ── BİLGİ KARTLARI ──────────────────────────────
            InfoCard(
                icon = Icons.Default.AutoAwesome,
                iconColor = MaterialTheme.colorScheme.secondary,
                title = "Yapay Zeka Notu",
                description = "Bugün gayet iyi görünüyorsunuz. Düne göre stresiniz azaldı. İlacınızı aldıysanız günün tadını çıkarabilirsiniz."
            )

            Spacer(modifier = Modifier.height(16.dp))

            InfoCard(
                icon = Icons.Default.PieChart,
                iconColor = MaterialTheme.colorScheme.secondary,
                title = "Detaylı Rapor & EKG",
                description = "Doktorunuz için teknik veriler",
                showArrow = true,
                onClick = { navController.navigate(Screen.ProMode.route) }
            )

            Spacer(modifier = Modifier.height(120.dp))
        }

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
                tint = MaterialTheme.colorScheme.outlineVariant
            )
        }
    }
}

// ══════════════════════════════════════════════════════
//  ÜST BAR — Karşılama + Durum badge + Mod Değiştirici Kapsül
// ══════════════════════════════════════════════════════

@Composable
fun TopBarSection(statusText: String, statusColor: Color, onModeSwitchClick: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column {
            Text(
                text = "Merhaba, Ahmet",
                style = MaterialTheme.typography.headlineSmall,
                color = MaterialTheme.colorScheme.onBackground,
                modifier = Modifier.semantics { heading() }
            )
            Spacer(modifier = Modifier.height(8.dp))
            StatusBadge(
                text = statusText,
                color = statusColor
            )
        }

        // Profil ikonu yerine "Sakin / PRO" Kapsülü Eklendi
        Box(
            modifier = Modifier
                .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(50))
                .padding(4.dp)
                .clip(RoundedCornerShape(50))
                .clickable { onModeSwitchClick() }
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                // SAKİN (Aktif Olan Sekme)
                Box(
                    modifier = Modifier
                        .background(MaterialTheme.colorScheme.primary, RoundedCornerShape(50))
                        .padding(horizontal = 12.dp, vertical = 6.dp)
                ) {
                    Text(
                        text = "Sakin",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                }

                // PRO (Pasif Olan Sekme)
                Text(
                    text = "PRO",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(horizontal = 12.dp)
                )
            }
        }
    }
}

// ══════════════════════════════════════════════════════
//  NEFES ALAN DAİRE — Animasyonlu kalp ritmi göstergesi
// ══════════════════════════════════════════════════════

@Composable
fun BreathingCircleAnimation(bpm: Int = 0) {
    val infiniteTransition = rememberInfiniteTransition(label = "breathing")

    val scale by infiniteTransition.animateFloat(
        initialValue = 1f,
        targetValue = 1.05f,
        animationSpec = infiniteRepeatable(
            animation = tween(4000, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "scale"
    )

    val glowAlpha by infiniteTransition.animateFloat(
        initialValue = 0.15f,
        targetValue = 0.3f,
        animationSpec = infiniteRepeatable(
            animation = tween(4000, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "glow"
    )

    val circleColor = MaterialTheme.colorScheme.tertiary

    Box(
        modifier = Modifier
            .size(220.dp)
            .scale(scale)
            .background(
                brush = Brush.radialGradient(
                    colors = listOf(circleColor.copy(alpha = glowAlpha), Color.Transparent)
                ),
                shape = CircleShape
            )
            .border(2.dp, circleColor.copy(alpha = 0.2f), CircleShape),
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Icon(
                imageVector = Icons.Default.Favorite,
                contentDescription = null,
                tint = circleColor,
                modifier = Modifier.size(48.dp)
            )
            Spacer(modifier = Modifier.height(12.dp))
            Text(
                text = if (bpm > 0) "$bpm" else "Güvendesiniz",
                style = if (bpm > 0) MaterialTheme.typography.headlineLarge
                else MaterialTheme.typography.headlineMedium,
                color = MaterialTheme.colorScheme.onBackground
            )
            Text(
                text = if (bpm > 0) "BPM" else "Kalp ritminiz stabil.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

// ══════════════════════════════════════════════════════
//  YÜZEN NAVİGASYON BARI
// ══════════════════════════════════════════════════════

@Composable
fun FloatingNavBar(
    modifier: Modifier = Modifier,
    navController: NavHostController,
    currentRoute: String
) {
    Row(
        modifier = modifier
            .fillMaxWidth(0.85f)
            .clip(RoundedCornerShape(30.dp))
            .background(MaterialTheme.colorScheme.surface.copy(alpha = 0.95f))
            .border(1.dp, MaterialTheme.colorScheme.outlineVariant, RoundedCornerShape(30.dp))
            .padding(vertical = 8.dp),
        horizontalArrangement = Arrangement.SpaceEvenly,
        verticalAlignment = Alignment.CenterVertically
    ) {
        NavIcon(
            icon = Icons.Default.Home,
            label = "Ana Sayfa",
            isActive = currentRoute == Screen.Dashboard.route || currentRoute == Screen.ProMode.route
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
            // DEĞİŞTİ: Artık Reports rotasına bağlı ve ona tıklayınca oraya gidiyor
            isActive = currentRoute == Screen.Reports.route
        ) {
            if (currentRoute != Screen.Reports.route) {
                navController.navigate(Screen.Reports.route)
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
            tint = if (isActive) MaterialTheme.colorScheme.tertiary else MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f),
            modifier = Modifier.size(24.dp)
        )
    }
}