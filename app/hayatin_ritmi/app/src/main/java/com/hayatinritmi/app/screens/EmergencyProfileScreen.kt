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
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.LocalHospital
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.PersonSearch
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.Save
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.hayatinritmi.app.Screen
import com.hayatinritmi.app.ui.components.GradientButton
import com.hayatinritmi.app.ui.theme.JakartaFont

@Composable
fun EmergencyProfileScreen(navController: NavHostController) {
    // Bunlar örnek olarak dolu geliyor (Gerçek uygulamada veritabanından çekilir)
    var name by remember { mutableStateOf("Ahmet Yılmaz") }
    var phone by remember { mutableStateOf("05551234567") }
    var bloodType by remember { mutableStateOf("A Rh+") }
    var emergencyPhone by remember { mutableStateOf("05329876543") }
    var doctorEmail by remember { mutableStateOf("") }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
    ) {
        // Ambiyans Işıkları
        Box(
            modifier = Modifier
                .offset(x = (-80).dp, y = (-60).dp)
                .size(300.dp)
                .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.15f), CircleShape)
                .blur(80.dp)
        )
        Box(
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .offset(x = 80.dp, y = 80.dp)
                .size(350.dp)
                .background(MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.12f), CircleShape)
                .blur(90.dp)
        )

        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp)
                .padding(bottom = 40.dp)
        ) {
            Spacer(modifier = Modifier.height(40.dp))

            // GERİ BUTONU
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .background(MaterialTheme.colorScheme.onBackground.copy(alpha = 0.05f), CircleShape)
                    .border(1.dp, MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f), CircleShape)
                    .clickable { navController.popBackStack() },
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    Icons.AutoMirrored.Filled.ArrowBack,
                    contentDescription = "Geri",
                    tint = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.6f),
                    modifier = Modifier.size(20.dp)
                )
            }

            Spacer(modifier = Modifier.height(24.dp))

            // BAŞLIK
            Text(
                text = "Hayat Kurtarma\nProfili",
                fontFamily = JakartaFont,
                fontSize = 28.sp,
                fontWeight = FontWeight.ExtraBold,
                color = MaterialTheme.colorScheme.onBackground,
                lineHeight = 36.sp
            )

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = "Bu veriler acil durumlarda ilk müdahale ekipleriyle şifreli olarak paylaşılacaktır.",
                fontFamily = JakartaFont,
                fontSize = 14.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                fontWeight = FontWeight.Medium,
                lineHeight = 20.sp
            )

            Spacer(modifier = Modifier.height(32.dp))

            // 1. AD SOYAD
            UnderlineInput(
                value = name,
                onValueChange = { name = it },
                label = "Adınız ve Soyadınız",
                icon = Icons.Default.Person
            )

            Spacer(modifier = Modifier.height(16.dp))

            // 2. TELEFON VE KAN GRUBU (Yan yana)
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(16.dp),
                verticalAlignment = Alignment.Bottom
            ) {
                UnderlineInput(
                    value = phone,
                    onValueChange = { if (it.all { c -> c.isDigit() } && it.length <= 11) phone = it },
                    label = "Telefon No",
                    icon = Icons.Default.Phone,
                    keyboardType = KeyboardType.Phone,
                    modifier = Modifier.weight(1.2f)
                )

                BloodTypeDropdown(
                    selectedOption = bloodType,
                    onOptionSelected = { bloodType = it },
                    modifier = Modifier.weight(1f)
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            // 3. ACİL DURUM KİŞİSİ
            UnderlineInput(
                value = emergencyPhone,
                onValueChange = { if (it.all { c -> c.isDigit() } && it.length <= 11) emergencyPhone = it },
                label = "Acil Durum Kişisi (Tel No)",
                icon = Icons.Default.LocalHospital,
                iconTint = MaterialTheme.colorScheme.onSurfaceVariant,
                keyboardType = KeyboardType.Phone
            )

            Spacer(modifier = Modifier.height(16.dp))

            // 4. DOKTOR E-POSTASI
            UnderlineInput(
                value = doctorEmail,
                onValueChange = { doctorEmail = it },
                label = "Doktorunuzun E-Postası",
                icon = Icons.Default.PersonSearch,
                keyboardType = KeyboardType.Email,
                trailingContent = {
                    Text(
                        text = "OPSİYONEL",
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.8f),
                        letterSpacing = 1.sp,
                        modifier = Modifier
                            .border(1.dp, MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f), RoundedCornerShape(50))
                            .padding(horizontal = 8.dp, vertical = 3.dp)
                    )
                }
            )

            Spacer(modifier = Modifier.height(48.dp))

            // KAYDET BUTONU
            GradientButton(
                text = "Değişiklikleri Kaydet",
                onClick = {
                    // İşlem bitince bir önceki sayfaya (Ayarlar) geri döner
                    navController.popBackStack()
                },
                icon = Icons.Default.Save,
                colors = listOf(MaterialTheme.colorScheme.primary, Color(0xFF9F1239))
            )

            Spacer(modifier = Modifier.height(40.dp))
        }
    }
}