package com.hayatinritmi.app.screens

import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.hayatinritmi.app.ui.theme.JakartaFont
import kotlinx.coroutines.delay

@Composable
fun ForgotPasswordScreen(navController: NavHostController) {
    var currentStep by remember { mutableIntStateOf(1) }
    var phoneNumber by remember { mutableStateOf("") }

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
                .background(MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.15f), CircleShape)
                .blur(90.dp)
        )

        AnimatedContent(
            targetState = currentStep,
            transitionSpec = {
                slideInHorizontally { it } + fadeIn() togetherWith
                        slideOutHorizontally { -it } + fadeOut()
            },
            label = "step_transition"
        ) { step ->
            when (step) {
                1 -> StepOnePhoneInput(
                    phoneNumber = phoneNumber,
                    onPhoneChanged = { phoneNumber = it },
                    onBack = { navController.popBackStack() },
                    onSendCode = { currentStep = 2 }
                )
                2 -> StepTwoOtpVerify(
                    onBack = { currentStep = 1 },
                    onVerify = {
                        // Doğrulama başarılı - Login'e dön
                        navController.popBackStack()
                    }
                )
            }
        }
    }
}

// --- ADIM 1: TELEFON NUMARASI ---
@Composable
private fun StepOnePhoneInput(
    phoneNumber: String,
    onPhoneChanged: (String) -> Unit,
    onBack: () -> Unit,
    onSendCode: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 24.dp)
    ) {
        Spacer(modifier = Modifier.height(40.dp))

        // Geri Butonu
        Box(
            modifier = Modifier
                .size(40.dp)
                .background(MaterialTheme.colorScheme.onBackground.copy(alpha = 0.05f), CircleShape)
                .border(1.dp, MaterialTheme.colorScheme.outlineVariant, CircleShape)
                .clickable { onBack() },
            contentAlignment = Alignment.Center
        ) {
            Icon(
                Icons.AutoMirrored.Filled.ArrowBack,
                contentDescription = "Geri",
                tint = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.6f),
                modifier = Modifier.size(20.dp)
            )
        }

        Spacer(modifier = Modifier.height(32.dp))

        // Kalkan İkonu
        Icon(
            Icons.Default.Shield,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.primary,
            modifier = Modifier.size(56.dp)
        )

        Spacer(modifier = Modifier.height(20.dp))

        Text(
            text = "Şifremi Unuttum",
            fontFamily = JakartaFont,
            fontSize = 28.sp,
            fontWeight = FontWeight.ExtraBold,
            color = MaterialTheme.colorScheme.onBackground
        )

        Spacer(modifier = Modifier.height(12.dp))

        Text(
            text = "Hesabınıza kayıtlı telefon numarasını girin. Size 4 haneli bir güvenlik kodu göndereceğiz.",
            fontFamily = JakartaFont,
            fontSize = 14.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            fontWeight = FontWeight.Medium,
            lineHeight = 22.sp
        )

        Spacer(modifier = Modifier.height(40.dp))

        PremiumInput(
            value = phoneNumber,
            onValueChange = { if (it.all { c -> c.isDigit() } && it.length <= 11) onPhoneChanged(it) },
            label = "05XX XXX XX XX",
            icon = Icons.Default.Phone,
            keyboardType = KeyboardType.Phone
        )

        Spacer(modifier = Modifier.weight(1f))

        // Kodu Gönder Butonu Alanı
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 40.dp)
                .height(56.dp)
                // DEĞİŞTİ: Orijinal parlama efektini (glow) geri ekledik
                .background(
                    brush = Brush.radialGradient(
                        colors = listOf(MaterialTheme.colorScheme.primary.copy(alpha = 0.3f), Color.Transparent),
                        radius = 180f
                    ),
                    shape = RoundedCornerShape(16.dp)
                )
        ) {
            Button(
                onClick = onSendCode,
                modifier = Modifier.fillMaxSize(),
                colors = ButtonDefaults.buttonColors(containerColor = Color.Transparent),
                contentPadding = PaddingValues(),
                shape = RoundedCornerShape(16.dp)
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        // DEĞİŞTİ: Üstten gelen o hafif beyaz parlama efektini geri ekledik
                        .border(
                            1.dp,
                            Brush.verticalGradient(listOf(Color.White.copy(0.3f), Color.Transparent)),
                            RoundedCornerShape(16.dp)
                        )
                        .background(
                            // DEĞİŞTİ: Solukluk yaratan primaryContainer yerine orijinal canlı koyu pembe/kırmızı tonunu verdik
                            brush = Brush.horizontalGradient(
                                colors = listOf(MaterialTheme.colorScheme.primary, Color(0xFF9F1239))
                            ),
                            shape = RoundedCornerShape(16.dp)
                        ),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "Kodu Gönder",
                        fontFamily = JakartaFont,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White // Buton zemini koyu renk olduğu için yazı her zaman tam beyaz olmalı
                    )
                }
            }
        }
    }
}

// --- ADIM 2: OTP DOĞRULAMA ---
@Composable
private fun StepTwoOtpVerify(
    onBack: () -> Unit,
    onVerify: () -> Unit
) {
    val otpFields = remember { mutableStateListOf("", "", "", "") }
    val focusRequesters = remember { List(4) { FocusRequester() } }
    var resendTimer by remember { mutableIntStateOf(59) }

    LaunchedEffect(resendTimer) {
        if (resendTimer > 0) {
            delay(1000L)
            resendTimer--
        }
    }

    LaunchedEffect(Unit) {
        focusRequesters[0].requestFocus()
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 24.dp)
    ) {
        Spacer(modifier = Modifier.height(40.dp))

        // Geri Butonu
        Box(
            modifier = Modifier
                .size(40.dp)
                .background(MaterialTheme.colorScheme.onBackground.copy(alpha = 0.05f), CircleShape)
                .border(1.dp, MaterialTheme.colorScheme.outlineVariant, CircleShape)
                .clickable { onBack() },
            contentAlignment = Alignment.Center
        ) {
            Icon(
                Icons.AutoMirrored.Filled.ArrowBack,
                contentDescription = "Geri",
                tint = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.6f),
                modifier = Modifier.size(20.dp)
            )
        }

        Spacer(modifier = Modifier.height(32.dp))

        Text(
            text = "Kodu Girin",
            fontFamily = JakartaFont,
            fontSize = 28.sp,
            fontWeight = FontWeight.ExtraBold,
            color = MaterialTheme.colorScheme.onBackground
        )

        Spacer(modifier = Modifier.height(12.dp))

        Text(
            text = "Telefonunuza gönderilen 4 haneli doğrulama kodunu girin.",
            fontFamily = JakartaFont,
            fontSize = 14.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            fontWeight = FontWeight.Medium,
            lineHeight = 22.sp
        )

        Spacer(modifier = Modifier.height(40.dp))

        // OTP Kutucukları
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            for (i in 0..3) {
                OtpInputBox(
                    value = otpFields[i],
                    onValueChange = { newValue ->
                        if (newValue.length <= 1 && newValue.all { it.isDigit() }) {
                            otpFields[i] = newValue
                            if (newValue.isNotEmpty() && i < 3) {
                                focusRequesters[i + 1].requestFocus()
                            }
                        } else if (newValue.isEmpty() && i > 0) {
                            otpFields[i] = ""
                            focusRequesters[i - 1].requestFocus()
                        }
                    },
                    focusRequester = focusRequesters[i],
                    isFocused = otpFields[i].isNotEmpty()
                )
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        // Tekrar Gönder
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.Center
        ) {
            Text(
                text = "Kodu almadınız mı? ",
                fontFamily = JakartaFont,
                fontSize = 14.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                fontWeight = FontWeight.Medium
            )
            Text(
                text = if (resendTimer > 0) "Tekrar Gönder (0:${resendTimer.toString().padStart(2, '0')})"
                else "Tekrar Gönder",
                fontFamily = JakartaFont,
                fontSize = 14.sp,
                color = MaterialTheme.colorScheme.primary,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.clickable {
                    if (resendTimer == 0) resendTimer = 59
                }
            )
        }

        Spacer(modifier = Modifier.weight(1f))

        // Doğrula Butonu
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 40.dp)
                .height(56.dp)
                .background(
                    brush = Brush.radialGradient(
                        colors = listOf(MaterialTheme.colorScheme.primary.copy(alpha = 0.3f), Color.Transparent),
                        radius = 180f
                    ),
                    shape = RoundedCornerShape(16.dp)
                )
        ) {
            Button(
                onClick = onVerify,
                modifier = Modifier.fillMaxSize(),
                colors = ButtonDefaults.buttonColors(containerColor = Color.Transparent),
                contentPadding = PaddingValues(),
                shape = RoundedCornerShape(16.dp)
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .border(
                            1.dp,
                            Brush.verticalGradient(listOf(Color.White.copy(0.3f), Color.Transparent)),
                            RoundedCornerShape(16.dp)
                        )
                        .background(
                            brush = Brush.horizontalGradient(
                                colors = listOf(MaterialTheme.colorScheme.primary, Color(0xFF9F1239))
                            ),
                            shape = RoundedCornerShape(16.dp)
                        ),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "Doğrula",
                        fontFamily = JakartaFont,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White
                    )
                }
            }
        }
    }
}

// --- OTP KUTUCUĞU ---
@Composable
private fun OtpInputBox(
    value: String,
    onValueChange: (String) -> Unit,
    focusRequester: FocusRequester,
    isFocused: Boolean
) {
    BasicTextField(
        value = value,
        onValueChange = onValueChange,
        modifier = Modifier
            .size(width = 68.dp, height = 76.dp)
            .focusRequester(focusRequester)
            .background(
                if (isFocused) MaterialTheme.colorScheme.primary.copy(alpha = 0.05f)
                else MaterialTheme.colorScheme.onBackground.copy(alpha = 0.03f),
                RoundedCornerShape(16.dp)
            )
            .border(
                2.dp,
                if (isFocused) MaterialTheme.colorScheme.primary
                else MaterialTheme.colorScheme.outlineVariant,
                RoundedCornerShape(16.dp)
            ),
        textStyle = TextStyle(
            color = MaterialTheme.colorScheme.onBackground,
            fontSize = 32.sp,
            fontWeight = FontWeight.Bold,
            fontFamily = JakartaFont,
            textAlign = TextAlign.Center
        ),
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
        singleLine = true,
        decorationBox = { innerTextField ->
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                innerTextField()
            }
        }
    )
}