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
            // DEĞİŞTİ: Sabit siyah yerine temaya duyarlı arka plan
            .background(MaterialTheme.colorScheme.background)
    ) {
        // Arka Plan Işıkları
        Box(
            modifier = Modifier
                .align(Alignment.TopStart)
                .offset(x = (-50).dp, y = (-50).dp)
                .size(300.dp)
                // DEĞİŞTİ: NeonBlue yerine ikincil renk
                .background(MaterialTheme.colorScheme.secondary.copy(alpha = 0.15f), CircleShape)
                .blur(80.dp)
        )
        Box(
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .offset(x = 50.dp, y = 50.dp)
                .size(300.dp)
                // DEĞİŞTİ: PurpleAccent yerine temanın yüzey varyantı veya ana rengi kullanılabilir
                .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.1f), CircleShape)
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
                // DEĞİŞTİ: Başlık rengi
                color = MaterialTheme.colorScheme.onBackground
            )

            Spacer(modifier = Modifier.height(24.dp))

            // ── Profil Kartı ──────────────────────────────────
            GlassCard {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // Avatar — gradient border
                    Box(
                        modifier = Modifier
                            .size(64.dp)
                            .background(
                                // DEĞİŞTİ: Sabit renkler yerine temanın renkleri
                                brush = Brush.linearGradient(listOf(MaterialTheme.colorScheme.secondary, MaterialTheme.colorScheme.primary)),
                                shape = CircleShape
                            )
                            .padding(2.dp)
                    ) {
                        Box(
                            modifier = Modifier
                                .fillMaxSize()
                                // DEĞİŞTİ: Avatar içi siyah yerine temanın arka planı
                                .background(MaterialTheme.colorScheme.background, CircleShape),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                Icons.Default.Person,
                                contentDescription = null,
                                // DEĞİŞTİ: İkon rengi
                                tint = MaterialTheme.colorScheme.onBackground,
                                modifier = Modifier.size(32.dp)
                            )
                        }
                    }
                    Spacer(modifier = Modifier.width(16.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "Ahmet Yılmaz",
                            style = MaterialTheme.typography.titleLarge,
                            // DEĞİŞTİ: İsim rengi
                            color = MaterialTheme.colorScheme.onBackground
                        )
                        Text(
                            text = "ahmet@example.com",
                            style = MaterialTheme.typography.bodySmall,
                            // DEĞİŞTİ: E-posta rengi
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    // Kan grubu badge
                    Box(
                        modifier = Modifier
                            // DEĞİŞTİ: Badge arka planı ve çerçevesi
                            .background(MaterialTheme.colorScheme.primaryContainer, RoundedCornerShape(8.dp))
                            .border(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.3f), RoundedCornerShape(8.dp))
                            .padding(horizontal = 8.dp, vertical = 4.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Icon(
                                Icons.Default.Favorite,
                                contentDescription = null,
                                // DEĞİŞTİ: Kalp ikonu
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(12.dp)
                            )
                            Text(
                                text = "A Rh+",
                                style = MaterialTheme.typography.labelSmall,
                                // DEĞİŞTİ: Kan grubu yazısı
                                color = MaterialTheme.colorScheme.onPrimaryContainer
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
                            // DEĞİŞTİ: Mavi ikon
                            tint = MaterialTheme.colorScheme.secondary,
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "BAĞLI CİHAZLAR",
                            style = MaterialTheme.typography.labelSmall,
                            // DEĞİŞTİ: Üst başlık rengi
                            color = MaterialTheme.colorScheme.onBackground
                        )
                    }
                    StatusBadge(
                        text = if (isDeviceConnected) "AKTİF" else "BAĞLI DEĞİL",
                        // DEĞİŞTİ: Badge renkleri
                        color = if (isDeviceConnected) MaterialTheme.colorScheme.tertiary else MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Spacer(modifier = Modifier.height(16.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "Hayatın Ritmi Tişörtü",
                            style = MaterialTheme.typography.titleMedium,
                            // DEĞİŞTİ: Cihaz adı
                            color = MaterialTheme.colorScheme.onBackground
                        )
                        Text(
                            text = "Sensör Durumu: Mükemmel",
                            style = MaterialTheme.typography.bodySmall,
                            // DEĞİŞTİ: Durum yazısı
                            color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f)
                        )
                        val calibrateInteraction = remember { MutableInteractionSource() }
                        Text(
                            text = "Cihazı Kalibre Et",
                            style = MaterialTheme.typography.labelMedium,
                            // DEĞİŞTİ: Tıklanabilir link rengi
                            color = MaterialTheme.colorScheme.secondary,
                            modifier = Modifier
                                .padding(top = 8.dp)
                                .clickable(
                                    interactionSource = calibrateInteraction,
                                    indication = ripple(
                                        bounded = false,
                                        color = MaterialTheme.colorScheme.secondary.copy(alpha = 0.15f)
                                    ),
                                    onClick = { }
                                )
                        )
                    }
                    Box(contentAlignment = Alignment.Center) {
                        CircularProgressIndicator(
                            progress = { if (isDeviceConnected) batteryPercent / 100f else 0f },
                            modifier = Modifier.size(48.dp),
                            // DEĞİŞTİ: Şarj dairesi rengi
                            color = if (isDeviceConnected) MaterialTheme.colorScheme.tertiary else MaterialTheme.colorScheme.onSurfaceVariant,
                            strokeWidth = 4.dp,
                            // DEĞİŞTİ: Şarj dairesi boşluk rengi
                            trackColor = MaterialTheme.colorScheme.surfaceVariant
                        )
                        Text(
                            text = if (isDeviceConnected) "$batteryPercent%" else "--%",
                            style = MaterialTheme.typography.bodySmall,
                            // DEĞİŞTİ: Şarj yüzdesi yazısı
                            color = MaterialTheme.colorScheme.onBackground
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
                    // DEĞİŞTİ: Menü dış kutusu arka planı
                    .background(MaterialTheme.colorScheme.surface)
                    .border(1.dp, MaterialTheme.colorScheme.outlineVariant, RoundedCornerShape(20.dp))
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
                        // DEĞİŞTİ: İkon rengi
                        color = MaterialTheme.colorScheme.secondary,
                        size = 36.dp,
                        iconSize = 18.dp
                    )
                    Spacer(modifier = Modifier.width(16.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "Arayüz Modu",
                            style = MaterialTheme.typography.titleSmall,
                            // DEĞİŞTİ: Menü yazısı
                            color = MaterialTheme.colorScheme.onBackground
                        )
                        Text(
                            text = "Sakin veya Pro Mod seçimi",
                            style = MaterialTheme.typography.bodySmall,
                            // DEĞİŞTİ: Menü alt yazısı
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    // PRO / Sakin Toggle Pill
                    Row(
                        modifier = Modifier
                            // DEĞİŞTİ: Geçiş butonu arka planı
                            .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(50))
                            .border(1.dp, MaterialTheme.colorScheme.outlineVariant, RoundedCornerShape(50))
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
                                    // DEĞİŞTİ: Aktif sekme rengi
                                    if (isProMode) MaterialTheme.colorScheme.secondary else Color.Transparent,
                                    RoundedCornerShape(50)
                                )
                                .then(
                                    if (isProMode) Modifier.border(
                                        1.dp,
                                        MaterialTheme.colorScheme.secondary.copy(alpha = 0.5f),
                                        RoundedCornerShape(50)
                                    ) else Modifier
                                )
                                .clickable(
                                    interactionSource = proInteraction,
                                    indication = ripple(color = MaterialTheme.colorScheme.secondary.copy(alpha = 0.2f)),
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
                                // DEĞİŞTİ: Sekme yazı rengi
                                color = if (isProMode) MaterialTheme.colorScheme.onSecondary else MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        // Sakin
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(50))
                                .background(
                                    // DEĞİŞTİ: Aktif sekme rengi
                                    if (!isProMode) MaterialTheme.colorScheme.secondary else Color.Transparent,
                                    RoundedCornerShape(50)
                                )
                                .then(
                                    if (!isProMode) Modifier.border(
                                        1.dp,
                                        MaterialTheme.colorScheme.secondary.copy(alpha = 0.5f),
                                        RoundedCornerShape(50)
                                    ) else Modifier
                                )
                                .clickable(
                                    interactionSource = sakinInteraction,
                                    indication = ripple(color = MaterialTheme.colorScheme.secondary.copy(alpha = 0.2f)),
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
                                // DEĞİŞTİ: Sekme yazı rengi
                                color = if (!isProMode) MaterialTheme.colorScheme.onSecondary else MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }

                // DEĞİŞTİ: Ayırıcı çizgiler
                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)

                // 2. Hayat Kurtarma Profili
                SettingsMenuItem(
                    icon = Icons.Default.HealthAndSafety,
                    // DEĞİŞTİ: İkon renkleri temaya bağlandı
                    iconColor = MaterialTheme.colorScheme.primary,
                    title = "Hayat Kurtarma Profili",
                    subtitle = "Acil durum kişileri ve doktor bilgisi"
                ) {
                    navController.navigate(Screen.SignUp.route)
                }

                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)

                // 3. Veri Paylaşımı
                SettingsMenuItem(
                    icon = Icons.Default.FileDownload,
                    iconColor = MaterialTheme.colorScheme.tertiary,
                    title = "Veri Paylaşımı",
                    subtitle = "EKG Raporlarını PDF olarak indir"
                ) { }

                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)

                // 4. Bildirim Tercihleri
                SettingsMenuItem(
                    icon = Icons.Default.Notifications,
                    // AmberWarning kalsa da olur ama sistemle uyumlu olması adına temaya bağlayabiliriz, uyarı rengi (error) ya da secondary verebiliriz.
                    iconColor = MaterialTheme.colorScheme.error,
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
                // DEĞİŞTİ: Çıkış butonu rengi
                accentColor = MaterialTheme.colorScheme.primary,
                height = 56.dp,
                icon = Icons.AutoMirrored.Filled.Logout
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Versiyon etiketi
            Text(
                text = "HAYATIN RİTMİ - BİGG PROTOTİP V1.0",
                style = MaterialTheme.typography.labelSmall,
                // DEĞİŞTİ: Versiyon yazı rengi
                color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f),
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
    iconColor: Color,
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
                // DEĞİŞTİ: Menü tıklama efekti rengi
                indication = ripple(color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.08f)),
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
                // DEĞİŞTİ: Menü item başlığı
                color = MaterialTheme.colorScheme.onBackground
            )
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodySmall,
                // DEĞİŞTİ: Menü item açıklaması
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        Icon(
            Icons.Default.ChevronRight,
            contentDescription = null,
            // DEĞİŞTİ: Sağ ok ikonu
            tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f)
        )
    }
}