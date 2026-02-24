package com.hayatinritmi.app.presentation.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Bluetooth
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.LocalHospital
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.PersonSearch
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.hayatinritmi.app.Screen
import com.hayatinritmi.app.presentation.theme.JakartaFont
import com.hayatinritmi.app.presentation.theme.RosePrimary

// --- KAN GRUBU SEÇİCİ (Underline Style) ---
@OptIn(ExperimentalMaterial3Api::class)
@Suppress("DEPRECATION")
@Composable
fun BloodTypeDropdown(
    selectedOption: String,
    onOptionSelected: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    var expanded by remember { mutableStateOf(false) }
    val bloodTypes = listOf("A Rh+", "A Rh-", "B Rh+", "B Rh-", "AB Rh+", "AB Rh-", "0 Rh+", "0 Rh-")

    ExposedDropdownMenuBox(
        expanded = expanded,
        onExpandedChange = { expanded = !expanded },
        modifier = modifier
    ) {
        TextField(
            value = selectedOption,
            onValueChange = {},
            readOnly = true,
            label = { Text("Kan Grubu", fontSize = 14.sp, fontFamily = JakartaFont, fontWeight = FontWeight.Medium) },
            leadingIcon = {
                Icon(Icons.Default.Favorite, contentDescription = null, tint = RosePrimary, modifier = Modifier.size(18.dp))
            },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
            modifier = Modifier.menuAnchor().fillMaxWidth(),
            singleLine = true,
            colors = TextFieldDefaults.colors(
                focusedTextColor = Color.White,
                unfocusedTextColor = Color.White.copy(alpha = 0.8f),
                cursorColor = RosePrimary,
                focusedIndicatorColor = RosePrimary,
                unfocusedIndicatorColor = Color.White.copy(alpha = 0.15f),
                focusedLabelColor = RosePrimary,
                unfocusedLabelColor = Color.White.copy(alpha = 0.4f),
                focusedContainerColor = Color.Transparent,
                unfocusedContainerColor = Color.Transparent
            )
        )
        ExposedDropdownMenu(
            expanded = expanded,
            onDismissRequest = { expanded = false },
            modifier = Modifier.background(Color(0xFF0F172A))
        ) {
            bloodTypes.forEach { selectionOption ->
                DropdownMenuItem(
                    text = { Text(selectionOption, color = Color.White, fontFamily = JakartaFont) },
                    onClick = {
                        onOptionSelected(selectionOption)
                        expanded = false
                    },
                    contentPadding = ExposedDropdownMenuDefaults.ItemContentPadding
                )
            }
        }
    }
}

// --- UNDERLINE INPUT (Kayıt Ekranı İçin) ---
@Composable
fun UnderlineInput(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    icon: ImageVector,
    iconTint: Color = Color.White.copy(alpha = 0.4f),
    isPassword: Boolean = false,
    keyboardType: KeyboardType = KeyboardType.Text,
    modifier: Modifier = Modifier,
    trailingContent: @Composable (() -> Unit)? = null
) {
    TextField(
        value = value,
        onValueChange = onValueChange,
        label = { Text(label, fontSize = 15.sp, fontFamily = JakartaFont, fontWeight = FontWeight.Medium) },
        leadingIcon = {
            Icon(icon, contentDescription = null, tint = iconTint, modifier = Modifier.size(20.dp))
        },
        trailingIcon = trailingContent,
        modifier = modifier.fillMaxWidth(),
        visualTransformation = if (isPassword) PasswordVisualTransformation() else VisualTransformation.None,
        keyboardOptions = KeyboardOptions(keyboardType = keyboardType),
        singleLine = true,
        colors = TextFieldDefaults.colors(
            focusedTextColor = Color.White,
            unfocusedTextColor = Color.White,
            cursorColor = RosePrimary,
            focusedIndicatorColor = RosePrimary,
            unfocusedIndicatorColor = Color.White.copy(alpha = 0.15f),
            focusedLabelColor = RosePrimary,
            unfocusedLabelColor = Color.White.copy(alpha = 0.4f),
            focusedContainerColor = Color.Transparent,
            unfocusedContainerColor = Color.Transparent,
            focusedLeadingIconColor = RosePrimary.copy(alpha = 0.8f),
            unfocusedLeadingIconColor = iconTint
        )
    )
}

@Composable
fun SignUpScreen(navController: NavHostController) {
    var name by remember { mutableStateOf("") }
    var bloodType by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var emergencyPhone by remember { mutableStateOf("") }
    var doctorEmail by remember { mutableStateOf("") }
    var isChecked by remember { mutableStateOf(false) }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
    ) {
        // Ambiyans Işıkları (HTML'deki orb-1 ve orb-2)
        Box(
            modifier = Modifier
                .offset(x = (-80).dp, y = (-60).dp)
                .size(300.dp)
                .background(RosePrimary.copy(alpha = 0.15f), CircleShape)
                .blur(80.dp)
        )
        Box(
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .offset(x = 80.dp, y = 80.dp)
                .size(350.dp)
                .background(Color(0xFFBE123C).copy(alpha = 0.12f), CircleShape)
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

            // GERİ BUTONU (HTML'deki gibi cam buton)
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .background(Color.White.copy(alpha = 0.05f), CircleShape)
                    .border(1.dp, Color.White.copy(alpha = 0.1f), CircleShape)
                    .clickable { navController.popBackStack() },
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    Icons.AutoMirrored.Filled.ArrowBack,
                    contentDescription = "Geri",
                    tint = Color.White.copy(alpha = 0.6f),
                    modifier = Modifier.size(20.dp)
                )
            }

            Spacer(modifier = Modifier.height(24.dp))

            // BAŞLIK
            Text(
                text = "Hayat Kurtarma\nProfili Oluştur",
                fontFamily = JakartaFont,
                fontSize = 28.sp,
                fontWeight = FontWeight.ExtraBold,
                color = Color.White,
                lineHeight = 36.sp
            )

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = "Bu veriler acil durumlarda ilk müdahale ekipleriyle şifreli olarak paylaşılacaktır.",
                fontFamily = JakartaFont,
                fontSize = 14.sp,
                color = Color.White.copy(alpha = 0.4f),
                fontWeight = FontWeight.Medium,
                lineHeight = 20.sp
            )

            Spacer(modifier = Modifier.height(32.dp))

            // FORM ALANLARI (HTML'deki underline style)
            UnderlineInput(
                value = name,
                onValueChange = { name = it },
                label = "Adınız ve Soyadınız",
                icon = Icons.Default.Person
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Kan Grubu ve Şifre (yan yana - HTML'deki grid-cols-2 gibi)
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                BloodTypeDropdown(
                    selectedOption = bloodType,
                    onOptionSelected = { bloodType = it },
                    modifier = Modifier.weight(1f)
                )

                UnderlineInput(
                    value = password,
                    onValueChange = { password = it },
                    label = "Şifre Belirle",
                    icon = Icons.Default.Lock,
                    isPassword = true,
                    keyboardType = KeyboardType.Password,
                    modifier = Modifier.weight(1f)
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Acil Durum Kişisi
            UnderlineInput(
                value = emergencyPhone,
                onValueChange = { if (it.all { c -> c.isDigit() } && it.length <= 11) emergencyPhone = it },
                label = "Acil Durum Kişisi (Tel No)",
                icon = Icons.Default.LocalHospital,
                iconTint = Color.White.copy(alpha = 0.4f),
                keyboardType = KeyboardType.Phone
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Doktor E-Postası (Opsiyonel badge ile)
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
                        color = Color.White.copy(alpha = 0.3f),
                        letterSpacing = 1.sp,
                        modifier = Modifier
                            .border(1.dp, Color.White.copy(alpha = 0.1f), RoundedCornerShape(50))
                            .padding(horizontal = 8.dp, vertical = 3.dp)
                    )
                }
            )

            Spacer(modifier = Modifier.height(32.dp))

            // ONAY KUTUSU
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.Top
            ) {
                Checkbox(
                    checked = isChecked,
                    onCheckedChange = { isChecked = it },
                    colors = CheckboxDefaults.colors(
                        checkedColor = RosePrimary,
                        uncheckedColor = Color.White.copy(alpha = 0.3f),
                        checkmarkColor = Color.White
                    )
                )

                val annotatedText = buildAnnotatedString {
                    withStyle(style = SpanStyle(color = RosePrimary, fontWeight = FontWeight.Bold)) {
                        append("Kullanım Koşullarını")
                    }
                    withStyle(style = SpanStyle(color = Color.White.copy(alpha = 0.5f))) {
                        append(" ve tıbbi verilerimin uçtan uca şifrelenerek işlenmesine dair ")
                    }
                    withStyle(style = SpanStyle(color = RosePrimary, fontWeight = FontWeight.Bold)) {
                        append("KVKK Metnini")
                    }
                    withStyle(style = SpanStyle(color = Color.White.copy(alpha = 0.5f))) {
                        append(" okudum, onaylıyorum.")
                    }
                }

                Text(
                    text = annotatedText,
                    fontFamily = JakartaFont,
                    fontSize = 12.sp,
                    lineHeight = 18.sp,
                    modifier = Modifier.padding(top = 12.dp)
                )
            }

            Spacer(modifier = Modifier.height(32.dp))

            // KAYIT BUTONU (HTML'deki glass-btn)
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(56.dp)
                    .background(
                        brush = Brush.radialGradient(
                            colors = listOf(RosePrimary.copy(alpha = 0.3f), Color.Transparent),
                            radius = 180f
                        ),
                        shape = RoundedCornerShape(16.dp)
                    )
            ) {
                Button(
                    onClick = {
                        navController.navigate(Screen.Login.route) {
                            popUpTo(Screen.SignUp.route) { inclusive = true }
                        }
                    },
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
                                    colors = listOf(RosePrimary, Color(0xFF9F1239))
                                ),
                                shape = RoundedCornerShape(16.dp)
                            ),
                        contentAlignment = Alignment.Center
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                text = "Tişörtü Bağla",
                                fontFamily = JakartaFont,
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color.White
                            )
                            Spacer(modifier = Modifier.width(10.dp))
                            Icon(
                                Icons.Default.Bluetooth,
                                contentDescription = null,
                                tint = Color.White,
                                modifier = Modifier.size(20.dp)
                            )
                        }
                    }
                }
            }
        }
    }
}
