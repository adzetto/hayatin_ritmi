package com.hayatinritmi.app.screens

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
import com.hayatinritmi.app.ui.components.GlassOutlinedButton
import com.hayatinritmi.app.ui.components.GradientButton
import com.hayatinritmi.app.ui.theme.*
import kotlinx.coroutines.delay

@Composable
fun EmergencyScreen(navController: NavHostController) {
    var countdown by remember { mutableIntStateOf(10) }
    var statusText by remember { mutableStateOf("Acil Durum Kişilerine Konum Gönderiliyor...") }
    var isCancelled by remember { mutableStateOf(false) }

    LaunchedEffect(key1 = countdown) {
        if (countdown > 0 && !isCancelled) {
            delay(1000L)
            countdown--
        } else if (countdown == 0 && !isCancelled) {
            statusText = "YARDIM ÇAĞRISI GÖNDERİLDİ!"
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
            // DEĞİŞTİ: Sabit siyah (Color.Black) yerine temanın ana arka planı
            .background(MaterialTheme.colorScheme.background)
    ) {
        // 1. KIRMIZI ALARM ARKA PLANI
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(
                    brush = Brush.radialGradient(
                        // DEĞİŞTİ: Kırmızı alarm rengi sabit kalıyor ama köşelere doğru siyah yerine temanın arka planına (gündüzse beyaza, geceyse siyaha) eriyor.
                        colors = listOf(AlarmRed.copy(alpha = alpha), MaterialTheme.colorScheme.background),
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
                // DEĞİŞTİ: TextPrimary yerine arka plan zıt rengi
                tint = MaterialTheme.colorScheme.onBackground,
                modifier = Modifier.size(80.dp)
            )

            Spacer(modifier = Modifier.height(24.dp))

            Text(
                text = "KRİTİK RİTİM\nBOZUKLUĞU",
                style = MaterialTheme.typography.headlineLarge,
                // DEĞİŞTİ: Yazı rengi
                color = MaterialTheme.colorScheme.onBackground,
                textAlign = TextAlign.Center
            )

            Spacer(modifier = Modifier.height(16.dp))

            Text(
                text = "Kalp atışlarınızda ciddi düzensizlik tespit edildi.",
                style = MaterialTheme.typography.bodyLarge,
                // DEĞİŞTİ: TextSecondary yerine temanın soluk yazı rengi
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center
            )

            Spacer(modifier = Modifier.height(48.dp))

            // 3. GERİ SAYIM ÇEMBERİ
            if (!isCancelled && countdown > 0) {
                Box(contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(
                        progress = { countdown / 10f },
                        modifier = Modifier.size(160.dp),
                        // DEĞİŞTİ: Çemberin dolan kısmı
                        color = MaterialTheme.colorScheme.onBackground,
                        strokeWidth = 8.dp,
                        // DEĞİŞTİ: Çemberin boş kısmı
                        trackColor = MaterialTheme.colorScheme.outlineVariant,
                    )
                    Text(
                        text = countdown.toString(),
                        style = MaterialTheme.typography.displayLarge,
                        // DEĞİŞTİ: Sayı rengi
                        color = MaterialTheme.colorScheme.onBackground
                    )
                }

                Spacer(modifier = Modifier.height(32.dp))

                Text(
                    text = statusText,
                    style = MaterialTheme.typography.bodyMedium,
                    // DEĞİŞTİ: Alt yazı rengi
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center
                )
            } else if (countdown == 0) {
                Box(
                    modifier = Modifier
                        .size(160.dp)
                        // DEĞİŞTİ: Telefon ikonunun arkasındaki beyaz yuvarlak, temanın kart (surface) rengine bağlandı
                        .background(MaterialTheme.colorScheme.surface, CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    // DEĞİŞTİ: AlarmRed Theme.kt içinde error olarak tanımlıydı, oradan çektik
                    Icon(Icons.Default.Call, contentDescription = null, tint = MaterialTheme.colorScheme.error, modifier = Modifier.size(64.dp))
                }
                Spacer(modifier = Modifier.height(24.dp))
                Text(
                    text = "112 ARANIYOR...",
                    style = MaterialTheme.typography.headlineMedium,
                    // DEĞİŞTİ: Başlık rengi
                    color = MaterialTheme.colorScheme.onBackground
                )
            } else {
                // İPTAL EDİLDİ
                // DEĞİŞTİ: Emerald500 Theme.kt içinde tertiary olarak tanımlıydı
                Icon(Icons.Default.CheckCircle, contentDescription = null, tint = MaterialTheme.colorScheme.tertiary, modifier = Modifier.size(100.dp))
                Spacer(modifier = Modifier.height(16.dp))
                Text(
                    text = "Alarm İptal Edildi",
                    style = MaterialTheme.typography.headlineSmall,
                    // DEĞİŞTİ: Başlık rengi
                    color = MaterialTheme.colorScheme.onBackground
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
                        // DEĞİŞTİ: Buton renkleri temaya uyumlu hale getirildi (Kart rengi kullanıldı)
                        colors = listOf(MaterialTheme.colorScheme.surface, MaterialTheme.colorScheme.surfaceVariant),
                        height = 64.dp
                    )

                    Spacer(modifier = Modifier.height(16.dp))

                    GlassOutlinedButton(
                        text = "HEMEN YARDIM ÇAĞIR",
                        onClick = { countdown = 0 },
                        modifier = Modifier.fillMaxWidth(),
                        // DEĞİŞTİ: Alt butonun çizgisi ve yazısı
                        accentColor = MaterialTheme.colorScheme.onBackground,
                        height = 56.dp
                    )
                }
            } else if (isCancelled) {
                GlassOutlinedButton(
                    text = "Ana Ekrana Dön",
                    onClick = { navController.popBackStack() },
                    modifier = Modifier.fillMaxWidth(),
                    // DEĞİŞTİ: İkincil renk
                    accentColor = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}