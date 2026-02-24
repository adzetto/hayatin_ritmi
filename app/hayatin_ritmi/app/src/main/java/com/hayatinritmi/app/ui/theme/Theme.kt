@file:Suppress("DEPRECATION")

package com.hayatinritmi.app.ui.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

// 1. GECE DOLABI (Senin Orijinal Kodun)
private val DarkColorScheme = darkColorScheme(
    primary = RosePrimary,
    onPrimary = TextWhite,
    primaryContainer = RoseSubtle,
    onPrimaryContainer = RoseLight,
    secondary = NeonBlue,
    onSecondary = TextWhite,
    secondaryContainer = BlueSubtle,
    onSecondaryContainer = BlueLight,
    tertiary = Emerald500,
    onTertiary = TextWhite,
    tertiaryContainer = EmeraldSubtle,
    onTertiaryContainer = Emerald400,
    background = RichBlack,
    onBackground = TextWhite,
    surface = Surface0,
    onSurface = TextWhite,
    surfaceVariant = Surface1,
    onSurfaceVariant = TextSecondary,
    outline = BorderMedium,
    outlineVariant = BorderSubtle,
    error = ErrorRed,
    onError = TextWhite
)

// 2. GÜNDÜZ DOLABI (Yeni Ekledik)
private val LightColorScheme = lightColorScheme(
    primary = RosePrimary, // Pembe rengimiz aynı kalabilir
    onPrimary = Color.White, // Pembenin üstündeki yazı beyaz olsun
    primaryContainer = RoseSubtle,
    onPrimaryContainer = RoseDark,
    secondary = NeonBlue,
    onSecondary = Color.White,
    secondaryContainer = BlueSubtle,
    onSecondaryContainer = BlueLight,
    tertiary = Emerald500,
    onTertiary = Color.White,
    tertiaryContainer = EmeraldSubtle,
    onTertiaryContainer = Emerald400,
    background = LightBackground, // Gündüz arka planı (Kırık beyaz)
    onBackground = LightTextPrimary, // Arka plan üstündeki yazılar (Koyu renk)
    surface = LightSurface0, // Kart arka planları (Tam beyaz)
    onSurface = LightTextPrimary, // Kart üstündeki yazılar
    surfaceVariant = LightSurface1,
    onSurfaceVariant = LightTextSecondary,
    outline = LightBorderMedium,
    outlineVariant = LightBorderSubtle,
    error = ErrorRed,
    onError = Color.White
)

// 3. TEMA SEÇİCİ (Gardırop)
@Composable
fun HayatinRitmiTheme(
    darkTheme: Boolean = isSystemInDarkTheme(), // Telefonun temasına bakar
    content: @Composable () -> Unit
) {
    // Telefon gece modundaysa DarkColorScheme'i, değilse LightColorScheme'i seç
    val colorScheme = when {
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            // Bildirim çubuğunun (saat, şarj) rengini seçilen temaya göre ayarla
            window.statusBarColor = colorScheme.background.toArgb()
            window.navigationBarColor = colorScheme.background.toArgb()

            // Arka plan açıksa saat/şarj yazıları siyah olsun, arka plan koyuysa yazılar beyaz olsun
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = !darkTheme
            WindowCompat.getInsetsController(window, view).isAppearanceLightNavigationBars = !darkTheme
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = AppTypography, // Typography olarak adlandırmış olabilirsin, AppTypography hata verirse onu sadece Typography yap.
        content = content
    )
}