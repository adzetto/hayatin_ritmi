package com.hayatinritmi.app.screens

import android.Manifest
import android.content.Intent
import android.net.Uri
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
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
import androidx.compose.ui.platform.LocalContext
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
            .background(MaterialTheme.colorScheme.background)
    ) {
        // Arka Plan Işıkları
        Box(
            modifier = Modifier
                .align(Alignment.TopStart)
                .offset(x = (-50).dp, y = (-50).dp)
                .size(300.dp)
                .background(MaterialTheme.colorScheme.secondary.copy(alpha = 0.15f), CircleShape)
                .blur(80.dp)
        )
        Box(
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .offset(x = 50.dp, y = 50.dp)
                .size(300.dp)
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
                                brush = Brush.linearGradient(listOf(MaterialTheme.colorScheme.secondary, MaterialTheme.colorScheme.primary)),
                                shape = CircleShape
                            )
                            .padding(2.dp)
                    ) {
                        Box(
                            modifier = Modifier
                                .fillMaxSize()
                                .background(MaterialTheme.colorScheme.background, CircleShape),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                Icons.Default.Person,
                                contentDescription = null,
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
                            color = MaterialTheme.colorScheme.onBackground
                        )
                        Text(
                            text = "ahmet@example.com",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    // Kan grubu badge
                    Box(
                        modifier = Modifier
                            .background(MaterialTheme.colorScheme.primaryContainer, RoundedCornerShape(8.dp))
                            .border(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.3f), RoundedCornerShape(8.dp))
                            .padding(horizontal = 8.dp, vertical = 4.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Icon(
                                Icons.Default.Favorite,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(12.dp)
                            )
                            Text(
                                text = "A Rh+",
                                style = MaterialTheme.typography.labelSmall,
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
                            tint = MaterialTheme.colorScheme.secondary,
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "BAĞLI CİHAZLAR",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onBackground
                        )
                    }
                    StatusBadge(
                        text = if (isDeviceConnected) "AKTİF" else "BAĞLI DEĞİL",
                        color = if (isDeviceConnected) MaterialTheme.colorScheme.tertiary else MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Spacer(modifier = Modifier.height(16.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "Hayatın Ritmi Tişörtü",
                            style = MaterialTheme.typography.titleMedium,
                            color = MaterialTheme.colorScheme.onBackground
                        )
                        Text(
                            text = "Sensör Durumu: Mükemmel",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f)
                        )
                        val calibrateInteraction = remember { MutableInteractionSource() }
                        Text(
                            text = "Cihazı Kalibre Et",
                            style = MaterialTheme.typography.labelMedium,
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
                            color = if (isDeviceConnected) MaterialTheme.colorScheme.tertiary else MaterialTheme.colorScheme.onSurfaceVariant,
                            strokeWidth = 4.dp,
                            trackColor = MaterialTheme.colorScheme.surfaceVariant
                        )
                        Text(
                            text = if (isDeviceConnected) "$batteryPercent%" else "--%",
                            style = MaterialTheme.typography.bodySmall,
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
                        color = MaterialTheme.colorScheme.secondary,
                        size = 36.dp,
                        iconSize = 18.dp
                    )
                    Spacer(modifier = Modifier.width(16.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "Arayüz Modu",
                            style = MaterialTheme.typography.titleSmall,
                            color = MaterialTheme.colorScheme.onBackground
                        )
                        Text(
                            text = "Sakin veya Pro Mod seçimi",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    // PRO / Sakin Toggle Pill
                    Row(
                        modifier = Modifier
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
                                color = if (isProMode) MaterialTheme.colorScheme.onSecondary else MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        // Sakin
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(50))
                                .background(
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
                                color = if (!isProMode) MaterialTheme.colorScheme.onSecondary else MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }

                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)

                // 2. Hayat Kurtarma Profili
                SettingsMenuItem(
                    icon = Icons.Default.HealthAndSafety,
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

                // 4. EKLENEN KISIM: Acil Durum İzinleri (Temaya Uyumlu)
                EmergencyPermissionSection()

                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)

                // 5. Bildirim Tercihleri
                SettingsMenuItem(
                    icon = Icons.Default.Notifications,
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
                accentColor = MaterialTheme.colorScheme.primary,
                height = 56.dp,
                icon = Icons.AutoMirrored.Filled.Logout
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Versiyon etiketi
            Text(
                text = "HAYATIN RİTMİ - BİGG PROTOTİP V1.0",
                style = MaterialTheme.typography.labelSmall,
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
                color = MaterialTheme.colorScheme.onBackground
            )
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        Icon(
            Icons.Default.ChevronRight,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f)
        )
    }
}

// YENİ EKLENEN VE TEMAYA UYARLANAN KISIM
@Composable
fun EmergencyPermissionSection() {
    val context = LocalContext.current

    // İzin durumlarını tuttuğumuz state'ler
    var smsGranted by remember { mutableStateOf(false) }
    var phoneGranted by remember { mutableStateOf(false) }
    var showSettingsDialog by remember { mutableStateOf(false) }

    val permissions = arrayOf(
        Manifest.permission.SEND_SMS,
        Manifest.permission.CALL_PHONE
    )

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions()
    ) { result ->
        smsGranted = result[Manifest.permission.SEND_SMS] ?: false
        phoneGranted = result[Manifest.permission.CALL_PHONE] ?: false

        if (!smsGranted || !phoneGranted) {
            showSettingsDialog = true
        }
    }

    // Temaya uyumlu tıklanabilir satır tasarımı (SettingsMenuItem gibi)
    val interactionSource = remember { MutableInteractionSource() }

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(
                interactionSource = interactionSource,
                indication = ripple(color = MaterialTheme.colorScheme.error.copy(alpha = 0.1f)),
                role = Role.Button,
                onClick = { permissionLauncher.launch(permissions) }
            )
            .padding(16.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        IconCircle(
            icon = Icons.Default.Warning, // Uyarı ikonu
            color = MaterialTheme.colorScheme.error, // Hata/Uyarı rengi
            size = 36.dp,
            iconSize = 18.dp
        )
        Spacer(modifier = Modifier.width(16.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = "Acil Durum İzinleri",
                style = MaterialTheme.typography.titleSmall,
                color = MaterialTheme.colorScheme.onBackground
            )
            Text(
                text = if (smsGranted && phoneGranted) "İzinler sağlandı, sistem hazır" else "Otomatik arama ve SMS için izin verin",
                style = MaterialTheme.typography.bodySmall,
                color = if (smsGranted && phoneGranted) MaterialTheme.colorScheme.tertiary else MaterialTheme.colorScheme.error
            )
        }
        // Eğer izinler verilmişse onay tiki, verilmemişse kırmızı bir ok gösterelim
        Icon(
            if (smsGranted && phoneGranted) Icons.Default.Check else Icons.Default.ChevronRight,
            contentDescription = null,
            tint = if (smsGranted && phoneGranted) MaterialTheme.colorScheme.tertiary else MaterialTheme.colorScheme.error
        )
    }

    // Kullanıcı izinleri kalıcı reddettiyse Ayarlara yönlendirme Dialog'u
    if (showSettingsDialog) {
        AlertDialog(
            onDismissRequest = { showSettingsDialog = false },
            containerColor = MaterialTheme.colorScheme.surface,
            titleContentColor = MaterialTheme.colorScheme.onBackground,
            textContentColor = MaterialTheme.colorScheme.onSurfaceVariant,
            title = { Text("İzin Gerekli") },
            text = { Text("Acil durumlarda 112'yi arayabilmemiz ve yakınlarına SMS atabilmemiz için ayarlardan izinleri manuel olarak açmalısınız.") },
            confirmButton = {
                TextButton(onClick = {
                    showSettingsDialog = false
                    val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                        data = Uri.fromParts("package", context.packageName, null)
                    }
                    context.startActivity(intent)
                }) {
                    Text("Ayarlara Git", color = MaterialTheme.colorScheme.primary)
                }
            },
            dismissButton = {
                TextButton(onClick = { showSettingsDialog = false }) {
                    Text("Vazgeç", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        )
    }
}