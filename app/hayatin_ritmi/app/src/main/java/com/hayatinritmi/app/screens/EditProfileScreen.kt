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
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Phone // EKLENDİ
import androidx.compose.material.icons.filled.Save
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import com.hayatinritmi.app.ui.components.GradientButton
import com.hayatinritmi.app.ui.theme.JakartaFont

@Composable
fun EditProfileScreen(navController: NavHostController) {
    // Örnek veriler, normalde ViewModel'den gelir
    var email by remember { mutableStateOf("ahmet@example.com") }
    var phone by remember { mutableStateOf("05551234567") } // EKLENDİ
    var currentPassword by remember { mutableStateOf("") }
    var newPassword by remember { mutableStateOf("") }
    var confirmNewPassword by remember { mutableStateOf("") }

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

        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp)
        ) {
            Spacer(modifier = Modifier.height(40.dp))

            // Geri Butonu
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

            Text(
                text = "Hesap Bilgileri",
                fontFamily = JakartaFont,
                style = MaterialTheme.typography.headlineLarge,
                color = MaterialTheme.colorScheme.onBackground
            )

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = "E-posta adresinizi, telefonunuzu veya şifrenizi buradan güncelleyebilirsiniz.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Spacer(modifier = Modifier.height(32.dp))

            // E-Posta Alanı
            UnderlineInput(
                value = email,
                onValueChange = { email = it },
                label = "Kayıtlı E-Posta Adresi",
                icon = Icons.Default.Email,
                keyboardType = KeyboardType.Email
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Telefon Numarası Alanı (EKLENDİ)
            UnderlineInput(
                value = phone,
                onValueChange = { if (it.all { char -> char.isDigit() } && it.length <= 11) phone = it },
                label = "Kayıtlı Telefon Numarası",
                icon = Icons.Default.Phone,
                keyboardType = KeyboardType.Phone
            )

            Spacer(modifier = Modifier.height(32.dp))

            Text(
                text = "ŞİFRE DEĞİŞTİR",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.primary,
                modifier = Modifier.padding(start = 4.dp)
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Şifre Alanları
            UnderlineInput(
                value = currentPassword,
                onValueChange = { currentPassword = it },
                label = "Mevcut Şifre",
                icon = Icons.Default.Lock,
                isPassword = true,
                keyboardType = KeyboardType.Password
            )

            Spacer(modifier = Modifier.height(16.dp))

            UnderlineInput(
                value = newPassword,
                onValueChange = { newPassword = it },
                label = "Yeni Şifre",
                icon = Icons.Default.Lock,
                isPassword = true,
                keyboardType = KeyboardType.Password
            )

            Spacer(modifier = Modifier.height(16.dp))

            UnderlineInput(
                value = confirmNewPassword,
                onValueChange = { confirmNewPassword = it },
                label = "Yeni Şifre Tekrar",
                icon = Icons.Default.Lock,
                isPassword = true,
                keyboardType = KeyboardType.Password
            )

            Spacer(modifier = Modifier.height(48.dp))

            // Kaydet Butonu
            GradientButton(
                text = "Değişiklikleri Kaydet",
                onClick = {
                    // Normalde burada API çağrısı yapılır
                    navController.popBackStack()
                },
                icon = Icons.Default.Save,
                colors = listOf(MaterialTheme.colorScheme.primary, Color(0xFF9F1239))
            )

            Spacer(modifier = Modifier.height(40.dp))
        }
    }
}