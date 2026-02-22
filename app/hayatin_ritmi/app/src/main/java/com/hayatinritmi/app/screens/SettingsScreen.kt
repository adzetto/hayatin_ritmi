package com.hayatinritmi.app.screens

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
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.material3.ripple
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.hayatinritmi.app.Screen
import com.hayatinritmi.app.data.model.ConnectionState
import com.hayatinritmi.app.ui.components.GlassCard
import com.hayatinritmi.app.ui.components.GlassOutlinedButton
import com.hayatinritmi.app.ui.components.IconCircle
import com.hayatinritmi.app.ui.components.StatusBadge
import com.hayatinritmi.app.ui.theme.*
import com.hayatinritmi.app.viewmodel.DeviceScanViewModel
import com.hayatinritmi.app.viewmodel.EcgViewModel

@Composable
fun SettingsScreen(
    navController: NavHostController,
    ecgViewModel: EcgViewModel? = null,
    deviceScanViewModel: DeviceScanViewModel? = null
) {
    val scrollState = rememberScrollState()
    var isProMode by remember { mutableStateOf(true) }
    val connectionState =
        ecgViewModel?.connectionState?.collectAsState()?.value ?: ConnectionState.DISCONNECTED
    val deviceStatus = ecgViewModel?.deviceStatus?.collectAsState()?.value
    val batteryPercent = deviceStatus?.batteryPercent ?: 0
    val isDeviceConnected = connectionState == ConnectionState.CONNECTED

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
    ) {
        // Arka Plan Işıkları
        Box(
            modifier = Modifier
                .align(Alignment.TopStart)
                .offset(x = (-50).dp, y = (-50).dp)
                .size(300.dp)
                .background(NeonBlue.copy(alpha = 0.15f), CircleShape)
                .blur(80.dp)
        )
        Box(
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .offset(x = 50.dp, y = 50.dp)
                .size(300.dp)
                .background(PurpleAccent.copy(alpha = 0.15f), CircleShape)
                .blur(80.dp)
        )

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 24.dp)
                .verticalScroll(scrollState)
        ) {
            Spacer(modifier = Modifier.height(40.dp))

            // Başlık
            Text(
                text = "Ayarlar",
                style = MaterialTheme.typography.headlineLarge,
                color = TextPrimary
            )

            Spacer(modifier = Modifier.height(24.dp))

            // ── Profil Kartı ──────────────────────────────────
            GlassCard {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // Avatar — gradient border with NeonBlue → RosePrimary
                    Box(
                        modifier = Modifier
                            .size(64.dp)
                            .background(
                                brush = Brush.linearGradient(listOf(NeonBlue, RosePrimary)),
                                shape = CircleShape
                            )
                            .padding(2.dp)
                    ) {
                        Box(
                            modifier = Modifier
                                .fillMaxSize()
                                .background(Color.Black, CircleShape),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                Icons.Default.Person,
                                contentDescription = null,
                                tint = TextPrimary,
                                modifier = Modifier.size(32.dp)
                            )
                        }
                    }
                    Spacer(modifier = Modifier.width(16.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "Ahmet Yılmaz",
                            style = MaterialTheme.typography.titleLarge,
                            color = TextPrimary
                        )
                        Text(
                            text = "ahmet@example.com",
                            style = MaterialTheme.typography.bodySmall,
                            color = TextSecondary
                        )
                    }
                    // Kan grubu badge
                    Box(
                        modifier = Modifier
                            .background(RoseSubtle, RoundedCornerShape(8.dp))
                            .border(1.dp, RosePrimary.copy(alpha = 0.3f), RoundedCornerShape(8.dp))
                            .padding(horizontal = 8.dp, vertical = 4.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Icon(
                                Icons.Default.Favorite,
                                contentDescription = null,
                                tint = RosePrimary,
                                modifier = Modifier.size(12.dp)
                            )
                            Text(
                                text = "A Rh+",
                                style = MaterialTheme.typography.labelSmall,
                                color = TextPrimary
                            )
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // ── Cihaz Kartı ───────────────────────────────────
            GlassCard(
                glassAlpha = 0.03f,
                onClick = { navController.navigate(Screen.DeviceScan.route) }
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            Icons.Default.Bluetooth,
                            contentDescription = null,
                            tint = NeonBlue,
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "BAĞLI CİHAZLAR",
                            style = MaterialTheme.typography.labelSmall,
                            color = TextPrimary
                        )
                    }
                    StatusBadge(
                        text = if (isDeviceConnected) "AKTİF" else "BAĞLI DEĞİL",
                        color = if (isDeviceConnected) Emerald500 else NeutralGray
                    )
                }
                Spacer(modifier = Modifier.height(16.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "Hayatın Ritmi Tişörtü",
                            style = MaterialTheme.typography.titleMedium,
                            color = TextPrimary
                        )
                        Text(
                            text = "Sensör Durumu: Mükemmel",
                            style = MaterialTheme.typography.bodySmall,
                            color = TextTertiary
                        )
                        val calibrateInteraction = remember { MutableInteractionSource() }
                        Text(
                            text = "Cihazı Kalibre Et",
                            style = MaterialTheme.typography.labelMedium,
                            color = NeonBlue,
                            modifier = Modifier
                                .padding(top = 8.dp)
                                .clickable(
                                    interactionSource = calibrateInteraction,
                                    indication = ripple(
                                        bounded = false,
                                        color = NeonBlue.copy(alpha = 0.15f)
                                    ),
                                    onClick = { }
                                )
                        )
                    }
                    Box(contentAlignment = Alignment.Center) {
                        CircularProgressIndicator(
                            progress = { if (isDeviceConnected) batteryPercent / 100f else 0f },
                            modifier = Modifier.size(48.dp),
                            color = if (isDeviceConnected) Emerald500 else NeutralGray,
                            strokeWidth = 4.dp,
                            trackColor = GlassBright
                        )
                        Text(
                            text = if (isDeviceConnected) "$batteryPercent%" else "--%",
                            style = MaterialTheme.typography.bodySmall,
                            color = TextPrimary
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // ── Menü Listesi ──────────────────────────────────
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(20.dp))
                    .background(GlassWhite)
                    .border(1.dp, GlassBorder, RoundedCornerShape(20.dp))
            ) {
                // 1. Arayüz Modu — PRO / Sakin toggle
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    IconCircle(
                        icon = Icons.Default.Layers,
                        color = NeonBlue,
                        size = 36.dp,
                        iconSize = 18.dp
                    )
                    Spacer(modifier = Modifier.width(16.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "Arayüz Modu",
                            style = MaterialTheme.typography.titleSmall,
                            color = TextPrimary
                        )
                        Text(
                            text = "Sakin veya Pro Mod seçimi",
                            style = MaterialTheme.typography.bodySmall,
                            color = TextTertiary
                        )
                    }
                    // PRO / Sakin Toggle Pill
                    Row(
                        modifier = Modifier
                            .background(GlassBright, RoundedCornerShape(50))
                            .border(1.dp, BorderSubtle, RoundedCornerShape(50))
                            .padding(2.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        val proInteraction = remember { MutableInteractionSource() }
                        val sakinInteraction = remember { MutableInteractionSource() }

                        // PRO
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(50))
                                .background(
                                    if (isProMode) NeonBlue else Color.Transparent,
                                    RoundedCornerShape(50)
                                )
                                .then(
                                    if (isProMode) Modifier.border(
                                        1.dp,
                                        NeonBlue.copy(alpha = 0.5f),
                                        RoundedCornerShape(50)
                                    ) else Modifier
                                )
                                .clickable(
                                    interactionSource = proInteraction,
                                    indication = ripple(color = NeonBlue.copy(alpha = 0.2f)),
                                    role = Role.Tab,
                                    onClick = {
                                        isProMode = true
                                        navController.navigate(Screen.ProMode.route)
                                    }
                                )
                                .padding(horizontal = 12.dp, vertical = 6.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                text = "PRO",
                                style = MaterialTheme.typography.labelSmall,
                                color = if (isProMode) Color.White else TextSecondary
                            )
                        }
                        // Sakin
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(50))
                                .background(
                                    if (!isProMode) NeonBlue else Color.Transparent,
                                    RoundedCornerShape(50)
                                )
                                .then(
                                    if (!isProMode) Modifier.border(
                                        1.dp,
                                        NeonBlue.copy(alpha = 0.5f),
                                        RoundedCornerShape(50)
                                    ) else Modifier
                                )
                                .clickable(
                                    interactionSource = sakinInteraction,
                                    indication = ripple(color = NeonBlue.copy(alpha = 0.2f)),
                                    role = Role.Tab,
                                    onClick = {
                                        isProMode = false
                                        navController.navigate(Screen.Dashboard.route)
                                    }
                                )
                                .padding(horizontal = 12.dp, vertical = 6.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                text = "Sakin",
                                style = MaterialTheme.typography.labelSmall,
                                color = if (!isProMode) Color.White else TextSecondary
                            )
                        }
                    }
                }

                HorizontalDivider(color = BorderSubtle)

                // 2. Hayat Kurtarma Profili — Rose
                SettingsMenuItem(
                    icon = Icons.Default.HealthAndSafety,
                    iconColor = RosePrimary,
                    title = "Hayat Kurtarma Profili",
                    subtitle = "Acil durum kişileri ve doktor bilgisi"
                ) {
                    navController.navigate(Screen.SignUp.route)
                }

                HorizontalDivider(color = BorderSubtle)

                // 3. Veri Paylaşımı — Emerald
                SettingsMenuItem(
                    icon = Icons.Default.FileDownload,
                    iconColor = Emerald500,
                    title = "Veri Paylaşımı",
                    subtitle = "EKG Raporlarını PDF olarak indir"
                ) { }

                HorizontalDivider(color = BorderSubtle)

                // 4. Bildirim Tercihleri — Amber
                SettingsMenuItem(
                    icon = Icons.Default.Notifications,
                    iconColor = AmberWarning,
                    title = "Bildirim Tercihleri",
                    subtitle = "AI uyarıları ve asistan sesleri"
                ) {
                    navController.navigate(Screen.Notifications.route)
                }
            }

            Spacer(modifier = Modifier.height(32.dp))

            // ── Çıkış Butonu ──────────────────────────────────
            GlassOutlinedButton(
                text = "Çıkış Yap",
                onClick = { navController.navigate(Screen.Login.route) { popUpTo(0) } },
                modifier = Modifier.fillMaxWidth(),
                accentColor = RosePrimary,
                height = 56.dp,
                icon = Icons.AutoMirrored.Filled.Logout
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Versiyon etiketi
            Text(
                text = "HAYATIN RİTMİ - BİGG PROTOTİP V1.0",
                style = MaterialTheme.typography.labelSmall,
                color = TextDisabled,
                letterSpacing = 2.sp,
                modifier = Modifier.align(Alignment.CenterHorizontally)
            )
            Spacer(modifier = Modifier.height(40.dp))
        }
    }
}

@Composable
fun SettingsMenuItem(
    icon: ImageVector,
    iconColor: Color = NeonBlue,
    title: String,
    subtitle: String,
    onClick: () -> Unit
) {
    val interactionSource = remember { MutableInteractionSource() }

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(
                interactionSource = interactionSource,
                indication = ripple(color = Color.White.copy(alpha = 0.08f)),
                role = Role.Button,
                onClick = onClick
            )
            .padding(16.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        IconCircle(
            icon = icon,
            color = iconColor,
            size = 36.dp,
            iconSize = 18.dp
        )
        Spacer(modifier = Modifier.width(16.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleSmall,
                color = TextPrimary
            )
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodySmall,
                color = TextTertiary
            )
        }
        Icon(
            Icons.Default.ChevronRight,
            contentDescription = null,
            tint = TextDisabled
        )
    }
}
