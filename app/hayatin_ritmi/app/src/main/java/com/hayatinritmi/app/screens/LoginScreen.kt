package com.hayatinritmi.app.screens

import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Code
import androidx.compose.material.icons.filled.Fingerprint
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.hayatinritmi.app.Screen
import com.hayatinritmi.app.ui.components.GlassOutlinedButton
import com.hayatinritmi.app.ui.components.GradientButton
import com.hayatinritmi.app.ui.theme.*

// --- UNDERLINE STYLE INPUT ---
@Composable
fun PremiumInput(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    icon: ImageVector,
    isPassword: Boolean = false,
    keyboardType: KeyboardType = KeyboardType.Text
) {
    TextField(
        value = value,
        onValueChange = onValueChange,
        label = {
            Text(
                text = label,
                style = MaterialTheme.typography.bodyMedium
            )
        },
        leadingIcon = {
            Icon(icon, contentDescription = null, tint = TextTertiary, modifier = Modifier.size(20.dp))
        },
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 24.dp),
        visualTransformation = if (isPassword) PasswordVisualTransformation() else VisualTransformation.None,
        keyboardOptions = KeyboardOptions(keyboardType = keyboardType),
        singleLine = true,
        colors = TextFieldDefaults.colors(
            focusedTextColor = TextPrimary,
            unfocusedTextColor = TextPrimary,
            cursorColor = RosePrimary,
            focusedIndicatorColor = RosePrimary,
            unfocusedIndicatorColor = BorderMedium,
            focusedLabelColor = RosePrimary,
            unfocusedLabelColor = TextTertiary,
            focusedContainerColor = Color.Transparent,
            unfocusedContainerColor = Color.Transparent,
            focusedLeadingIconColor = RosePrimary,
            unfocusedLeadingIconColor = TextTertiary
        )
    )
}

// --- EKG ANİMASYONU ---
@Composable
fun EkgAnimation(modifier: Modifier = Modifier) {
    val infiniteTransition = rememberInfiniteTransition(label = "ekg")
    val phase by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(3000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "ekg_phase"
    )

    Canvas(modifier = modifier) {
        val w = size.width
        val h = size.height

        // EKG noktaları (normalize edilmiş)
        val points = listOf(
            0f to 0.5f,
            0.2f to 0.5f,
            0.25f to 0.17f,
            0.3f to 0.83f,
            0.35f to 0.5f,
            0.5f to 0.5f,
            0.55f to 0.33f,
            0.6f to 0.5f,
            0.8f to 0.5f,
            0.85f to 0f,
            0.9f to 0.93f,
            0.95f to 0.5f,
            1f to 0.5f
        )

        val path = Path()
        points.forEachIndexed { index, (nx, ny) ->
            val x = nx * w
            val y = ny * h
            if (index == 0) path.moveTo(x, y)
            else path.lineTo(x, y)
        }

        // Draw with animated dash
        val pathLength = w * 1.5f
        drawPath(
            path = path,
            color = RosePrimary.copy(alpha = 0.8f + (phase * 0.2f)),
            style = Stroke(
                width = 2.5.dp.toPx(),
                cap = StrokeCap.Round,
                join = StrokeJoin.Round,
                pathEffect = androidx.compose.ui.graphics.PathEffect.dashPathEffect(
                    floatArrayOf(pathLength * phase, pathLength * (1f - phase)),
                    0f
                )
            )
        )

        // Glow effect
        drawPath(
            path = path,
            color = RosePrimary.copy(alpha = 0.3f),
            style = Stroke(
                width = 6.dp.toPx(),
                cap = StrokeCap.Round,
                join = StrokeJoin.Round,
                pathEffect = androidx.compose.ui.graphics.PathEffect.dashPathEffect(
                    floatArrayOf(pathLength * phase, pathLength * (1f - phase)),
                    0f
                )
            )
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LoginScreen(navController: NavHostController) {
    var phone by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var showBiometricSheet by remember { mutableStateOf(false) }

    // Biyometrik Bottom Sheet state
    val sheetState = rememberModalBottomSheetState()

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
    ) {
        // Ambiyans Işıkları
        Box(
            modifier = Modifier
                .offset(x = (-80).dp, y = (-100).dp)
                .size(350.dp)
                .background(RosePrimary.copy(alpha = 0.15f), CircleShape)
                .blur(100.dp)
        )
        Box(
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .offset(x = 80.dp, y = 100.dp)
                .size(300.dp)
                .background(RoseDark.copy(alpha = 0.12f), CircleShape)
                .blur(90.dp)
        )

        Column(
            modifier = Modifier.fillMaxSize(),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {

            // EKG Animasyonu
            EkgAnimation(
                modifier = Modifier
                    .width(200.dp)
                    .height(60.dp)
                    .padding(bottom = 16.dp)
            )

            Text(
                text = "Hayatın Ritmi",
                style = MaterialTheme.typography.headlineLarge,
                color = TextPrimary
            )

            Text(
                text = "YAPAY ZEKA DESTEKLİ TAKİP",
                style = MaterialTheme.typography.labelSmall.copy(letterSpacing = 4.sp),
                color = RosePrimary,
                modifier = Modifier.padding(top = 8.dp, bottom = 60.dp)
            )

            PremiumInput(
                value = phone,
                onValueChange = { if (it.all { char -> char.isDigit() } && it.length <= 11) phone = it },
                label = "Telefon Numarası",
                icon = Icons.Default.Person,
                keyboardType = KeyboardType.Number
            )

            Spacer(modifier = Modifier.height(16.dp))

            PremiumInput(
                value = password,
                onValueChange = { password = it },
                label = "Şifre",
                icon = Icons.Default.Lock,
                isPassword = true,
                keyboardType = KeyboardType.Password
            )

            // Şifremi Unuttum Linki
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 24.dp, vertical = 8.dp),
                contentAlignment = Alignment.CenterEnd
            ) {
                Text(
                    text = "Şifremi Unuttum",
                    style = MaterialTheme.typography.labelMedium,
                    color = RosePrimary,
                    modifier = Modifier.clickable(
                        interactionSource = remember { MutableInteractionSource() },
                        indication = ripple(bounded = true, color = RosePrimary),
                        onClick = { navController.navigate(Screen.ForgotPassword.route) }
                    )
                )
            }

            Spacer(modifier = Modifier.height(24.dp))

            // GİRİŞ YAP BUTONU
            GradientButton(
                text = "Giriş Yap",
                onClick = { showBiometricSheet = true },
                modifier = Modifier.padding(horizontal = 24.dp)
            )

            Spacer(modifier = Modifier.height(16.dp))

            // DEVELOPER SIGN IN BUTONU
            GlassOutlinedButton(
                text = "Developer Sign In",
                onClick = {
                    navController.navigate(Screen.Dashboard.route) {
                        popUpTo(Screen.Login.route) { inclusive = true }
                    }
                },
                modifier = Modifier.padding(horizontal = 24.dp),
                icon = Icons.Default.Code,
                height = 48.dp
            )

            Spacer(modifier = Modifier.height(24.dp))

            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = "Hesabın yok mu?",
                    style = MaterialTheme.typography.bodyMedium,
                    color = TextSecondary
                )
                Spacer(modifier = Modifier.width(6.dp))
                Text(
                    text = "Kayıt Ol",
                    style = MaterialTheme.typography.titleSmall,
                    color = RosePrimary,
                    modifier = Modifier.clickable(
                        interactionSource = remember { MutableInteractionSource() },
                        indication = ripple(bounded = true, color = RosePrimary),
                        onClick = { navController.navigate(Screen.SignUp.route) }
                    )
                )
            }
        }
    }

    // BİYOMETRİK BOTTOM SHEET
    if (showBiometricSheet) {
        ModalBottomSheet(
            onDismissRequest = {
                showBiometricSheet = false
                // Sheet kapatılınca dashboard'a git
                navController.navigate(Screen.Dashboard.route) {
                    popUpTo(Screen.Login.route) { inclusive = true }
                }
            },
            sheetState = sheetState,
            containerColor = Surface1,
            shape = RoundedCornerShape(topStart = 32.dp, topEnd = 32.dp),
            dragHandle = {
                Box(
                    modifier = Modifier
                        .padding(top = 16.dp)
                        .width(48.dp)
                        .height(4.dp)
                        .background(BorderFocus, RoundedCornerShape(50))
                )
            }
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 24.dp)
                    .padding(top = 16.dp, bottom = 40.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                // Parmak İzi İkonu
                Box(
                    modifier = Modifier
                        .size(80.dp)
                        .background(RoseSubtle, CircleShape)
                        .border(1.dp, RosePrimary.copy(alpha = 0.2f), CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        Icons.Default.Fingerprint,
                        contentDescription = null,
                        tint = RosePrimary,
                        modifier = Modifier.size(40.dp)
                    )
                }

                Spacer(modifier = Modifier.height(24.dp))

                Text(
                    text = "Daha Hızlı Giriş Yapın",
                    style = MaterialTheme.typography.headlineMedium,
                    color = TextPrimary
                )

                Spacer(modifier = Modifier.height(12.dp))

                Text(
                    text = "Bundan sonraki girişlerinizde şifre girmeden, sadece parmak izi veya yüz tanıma ile giriş yapmak ister misiniz?",
                    style = MaterialTheme.typography.bodyMedium,
                    color = TextSecondary,
                    textAlign = TextAlign.Center
                )

                Spacer(modifier = Modifier.height(32.dp))

                // Evet, Aktifleştir Butonu
                GradientButton(
                    text = "Evet, Aktifleştir",
                    onClick = {
                        showBiometricSheet = false
                        navController.navigate(Screen.Dashboard.route) {
                            popUpTo(Screen.Login.route) { inclusive = true }
                        }
                    },
                    icon = Icons.Default.Check
                )

                Spacer(modifier = Modifier.height(12.dp))

                // Şimdi Değil Butonu
                TextButton(
                    onClick = {
                        showBiometricSheet = false
                        navController.navigate(Screen.Dashboard.route) {
                            popUpTo(Screen.Login.route) { inclusive = true }
                        }
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(48.dp)
                ) {
                    Text(
                        text = "Şimdi Değil",
                        style = MaterialTheme.typography.titleMedium,
                        color = TextSecondary
                    )
                }
            }
        }
    }
}
