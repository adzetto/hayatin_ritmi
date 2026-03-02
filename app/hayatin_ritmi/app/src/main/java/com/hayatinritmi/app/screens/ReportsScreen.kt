package com.hayatinritmi.app.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.hayatinritmi.app.ui.components.GlassCard
import com.hayatinritmi.app.ui.components.IconCircle
import com.hayatinritmi.app.ui.theme.AmberWarning

@Composable
fun ReportsScreen(navController: NavHostController) {
    val scrollState = rememberScrollState()

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
    ) {
        // --- AMBİYANS IŞIKLARI ---
        Box(
            modifier = Modifier
                .align(Alignment.TopEnd)
                .offset(x = 50.dp, y = (-50).dp)
                .size(300.dp)
                .background(MaterialTheme.colorScheme.tertiary.copy(alpha = 0.15f), CircleShape)
                .blur(80.dp)
        )
        Box(
            modifier = Modifier
                .align(Alignment.CenterStart)
                .offset(x = (-80).dp, y = 100.dp)
                .size(300.dp)
                .background(MaterialTheme.colorScheme.secondary.copy(alpha = 0.1f), CircleShape)
                .blur(90.dp)
        )

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 24.dp)
                .verticalScroll(scrollState)
        ) {
            Spacer(modifier = Modifier.height(40.dp))

            // --- ÜST BİLGİ (HEADER) ---
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "Raporlar & Arşiv",
                        style = MaterialTheme.typography.headlineLarge,
                        color = MaterialTheme.colorScheme.onBackground
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Geçmiş EKG ve analiz dökümleriniz",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                // Filtreleme/Arama İkonu
                Box(
                    modifier = Modifier
                        .size(44.dp)
                        .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(12.dp))
                        .border(1.dp, MaterialTheme.colorScheme.outlineVariant, RoundedCornerShape(12.dp))
                        .clickable { /* Filtreleme açılacak */ },
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        Icons.Default.FilterList,
                        contentDescription = "Filtrele",
                        tint = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            Spacer(modifier = Modifier.height(32.dp))

            // --- BÖLÜM 1: HAFTALIK / AYLIK ÖZETLER ---
            SectionTitle(title = "HAFTALIK VE AYLIK ÖZETLER")
            Spacer(modifier = Modifier.height(12.dp))
            GlassCard {
                Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)) {
                    ReportDownloadItem(
                        title = "Ekim 2. Hafta Raporu",
                        date = "07 Eki - 14 Eki 2023",
                        description = "Genel kalp hızı ve HRV trend analizi.",
                        icon = Icons.Default.DateRange,
                        iconColor = MaterialTheme.colorScheme.secondary
                    )
                    HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
                    ReportDownloadItem(
                        title = "Eylül Ayı Genel Değerlendirmesi",
                        date = "01 Eyl - 30 Eyl 2023",
                        description = "Aylık ortalama değerler ve AI doktor notu.",
                        icon = Icons.Default.Assessment,
                        iconColor = MaterialTheme.colorScheme.secondary
                    )
                }
            }

            Spacer(modifier = Modifier.height(28.dp))

            // --- BÖLÜM 2: GÜNLÜK EKG DÖKÜMLERİ ---
            SectionTitle(title = "GÜNLÜK EKG DÖKÜMLERİ")
            Spacer(modifier = Modifier.height(12.dp))
            GlassCard {
                Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)) {
                    ReportDownloadItem(
                        title = "Günlük Detaylı Rapor",
                        date = "Bugün, 14 Ekim 2023",
                        description = "NSR ağırlıklı, 24 saatlik kayıt.",
                        icon = Icons.Default.MonitorHeart,
                        iconColor = MaterialTheme.colorScheme.tertiary
                    )
                    HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
                    ReportDownloadItem(
                        title = "Günlük Detaylı Rapor",
                        date = "Dün, 13 Ekim 2023",
                        description = "Hafif eforlu, düzensizlik yok.",
                        icon = Icons.Default.MonitorHeart,
                        iconColor = MaterialTheme.colorScheme.tertiary
                    )
                    HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
                    ReportDownloadItem(
                        title = "Günlük Detaylı Rapor",
                        date = "12 Ekim 2023",
                        description = "Stres kaynaklı ufak HRV düşüşü.",
                        icon = Icons.Default.MonitorHeart,
                        iconColor = MaterialTheme.colorScheme.tertiary
                    )
                }
            }

            Spacer(modifier = Modifier.height(28.dp))

            // --- BÖLÜM 3: KRİZ & ANORMAL DURUM KAYITLARI ---
            SectionTitle(title = "ANORMAL DURUM KAYITLARI")
            Spacer(modifier = Modifier.height(12.dp))
            GlassCard {
                Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)) {
                    ReportDownloadItem(
                        title = "Taşikardi Atağı Tespiti",
                        date = "10 Ekim 2023 - 14:22",
                        description = "135 BPM'e varan ani yükseliş (3 dk sürdü).",
                        icon = Icons.Default.Warning,
                        iconColor = AmberWarning // Uyarı rengi (Sarı/Turuncu)
                    )
                    HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
                    ReportDownloadItem(
                        title = "Ritim Bozukluğu (Aritmi) Şüphesi",
                        date = "28 Eylül 2023 - 09:15",
                        description = "Düzensiz R-R intervalleri tespit edildi.",
                        icon = Icons.Default.Warning,
                        iconColor = MaterialTheme.colorScheme.error // Kritik uyarı (Kırmızı)
                    )
                }
            }

            // Alt bar (Navbar) ile içerik üst üste binmesin diye fazladan boşluk
            Spacer(modifier = Modifier.height(120.dp))
        }
    }
}

// ── YARDIMCI BİLEŞENLER ────────────────────────────────────

@Composable
fun SectionTitle(title: String) {
    Text(
        text = title,
        style = MaterialTheme.typography.labelSmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        letterSpacing = 1.5.sp,
        modifier = Modifier.padding(start = 4.dp)
    )
}

@Composable
fun ReportDownloadItem(
    title: String,
    date: String,
    description: String,
    icon: ImageVector,
    iconColor: Color
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { /* Tıklanınca önizleme açılabilir */ }
            .padding(vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        // İkon Kısmı
        IconCircle(
            icon = icon,
            color = iconColor,
            size = 44.dp,
            iconSize = 22.dp
        )

        Spacer(modifier = Modifier.width(16.dp))

        // Metin Kısmı
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleSmall,
                color = MaterialTheme.colorScheme.onBackground
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = date,
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.primary
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = description,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1
            )
        }

        Spacer(modifier = Modifier.width(12.dp))

        // İndirme / Paylaşma Butonu
        Box(
            modifier = Modifier
                .size(40.dp)
                .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.1f), CircleShape)
                .clickable { /* İndirme işlemi tetiklenecek */ },
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = Icons.Default.Download,
                contentDescription = "PDF İndir",
                tint = MaterialTheme.colorScheme.primary,
                modifier = Modifier.size(20.dp)
            )
        }
    }
}