package com.hayatinritmi.app.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import com.hayatinritmi.app.ui.components.GlassCard
import com.hayatinritmi.app.ui.components.IconCircle
import com.hayatinritmi.app.ui.components.PremiumSwitch
import com.hayatinritmi.app.ui.theme.*

@Composable
fun NotificationScreen(navController: NavHostController) {
    val scrollState = rememberScrollState()

    // Toggle durumlari (opsiyonel bildirimler)
    var medicineReminder by remember { mutableStateOf(true) }
    var dailyAiSummary by remember { mutableStateOf(false) }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
    ) {
        // Arka Plan Isiklari
        Box(
            modifier = Modifier
                .offset(x = (-80).dp, y = (-50).dp)
                .size(350.dp)
                .background(NeonBlue.copy(alpha = 0.15f), CircleShape)
                .blur(90.dp)
        )
        Box(
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .offset(x = 60.dp, y = 60.dp)
                .size(300.dp)
                .background(Color(0xFFE11D48).copy(alpha = 0.1f), CircleShape)
                .blur(80.dp)
        )

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 24.dp)
                .verticalScroll(scrollState)
        ) {
            Spacer(modifier = Modifier.height(40.dp))

            // Geri Butonu ve Baslik
            Row(verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = { navController.popBackStack() }) {
                    Icon(
                        Icons.AutoMirrored.Filled.ArrowBack,
                        contentDescription = "Geri",
                        tint = TextPrimary
                    )
                }
                Text(
                    text = "Bildirim Ayarları",
                    style = MaterialTheme.typography.headlineMedium,
                    color = TextPrimary
                )
            }

            Spacer(modifier = Modifier.height(24.dp))

            // --- KRİTİK GÜVENLİK (Kapatilamaz) ---
            SectionHeader(
                icon = Icons.Default.Shield,
                iconColor = Emerald500,
                title = "KRİTİK GÜVENLİK (KAPATILAMAZ)"
            )

            Spacer(modifier = Modifier.height(12.dp))

            GlassCard {
                NotificationItem(
                    title = "Acil Durum ve Kriz Uyarıları",
                    description = "Ritim bozukluğu veya kalp krizi şüphesinde anında alarm verir.",
                    isLocked = true,
                    isEnabled = true,
                    onToggle = {}
                )
                HorizontalDivider(color = BorderSubtle)
                NotificationItem(
                    title = "Cihaz Bağlantı Durumu",
                    description = "Tişört şarjı biterse veya Bluetooth koparsa uyarır.",
                    isLocked = true,
                    isEnabled = true,
                    onToggle = {}
                )
            }

            Spacer(modifier = Modifier.height(4.dp))

            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.padding(start = 4.dp)
            ) {
                Icon(
                    Icons.Default.Info,
                    contentDescription = null,
                    tint = TextDisabled,
                    modifier = Modifier.size(12.dp)
                )
                Spacer(modifier = Modifier.width(6.dp))
                Text(
                    text = "Hayati güvenliğiniz için bu bildirimler zorunludur.",
                    style = MaterialTheme.typography.labelSmall,
                    color = TextDisabled
                )
            }

            Spacer(modifier = Modifier.height(32.dp))

            // --- AKILLI ASİSTAN (Opsiyonel) ---
            SectionHeader(
                icon = Icons.Default.AutoAwesome,
                iconColor = NeonBlue,
                title = "AKILLI ASİSTAN (OPSİYONEL)"
            )

            Spacer(modifier = Modifier.height(12.dp))

            GlassCard {
                NotificationItem(
                    title = "İlaç ve Su Hatırlatıcıları",
                    description = "Günlük ilaç saatlerinizi ve su tüketiminizi hatırlatır.",
                    isLocked = false,
                    isEnabled = medicineReminder,
                    onToggle = { medicineReminder = it }
                )
                HorizontalDivider(color = BorderSubtle)
                NotificationItem(
                    title = "Günlük AI Sağlık Özeti",
                    description = "Her sabah dünün analizi ve bugünün tavsiyelerini gönderir.",
                    isLocked = false,
                    isEnabled = dailyAiSummary,
                    onToggle = { dailyAiSummary = it }
                )
            }

            Spacer(modifier = Modifier.height(40.dp))
        }
    }
}

@Composable
private fun SectionHeader(icon: ImageVector, iconColor: Color, title: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        IconCircle(
            icon = icon,
            color = iconColor,
            size = 28.dp,
            iconSize = 14.dp
        )
        Spacer(modifier = Modifier.width(8.dp))
        Text(
            text = title,
            style = MaterialTheme.typography.labelSmall,
            color = TextTertiary
        )
    }
}

@Composable
private fun NotificationItem(
    title: String,
    description: String,
    isLocked: Boolean,
    isEnabled: Boolean,
    onToggle: (Boolean) -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 0.dp, vertical = 12.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = title,
                    style = MaterialTheme.typography.titleSmall,
                    color = TextPrimary
                )
                if (isLocked) {
                    Spacer(modifier = Modifier.width(8.dp))
                    Icon(
                        Icons.Default.Lock,
                        contentDescription = null,
                        tint = TextDisabled,
                        modifier = Modifier.size(12.dp)
                    )
                }
            }
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = description,
                style = MaterialTheme.typography.bodySmall,
                color = TextTertiary
            )
        }

        Spacer(modifier = Modifier.width(12.dp))

        PremiumSwitch(
            checked = isEnabled,
            onCheckedChange = onToggle,
            isLocked = isLocked,
            activeColor = if (isLocked) Emerald500 else NeonBlue
        )
    }
}
