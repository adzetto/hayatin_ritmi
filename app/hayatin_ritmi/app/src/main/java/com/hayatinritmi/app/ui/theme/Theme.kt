@file:Suppress("DEPRECATION")

package com.hayatinritmi.app.ui.theme

import android.app.Activity
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

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

@Composable
fun HayatinRitmiTheme(
    content: @Composable () -> Unit
) {
    val colorScheme = DarkColorScheme

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = colorScheme.background.toArgb()
            window.navigationBarColor = colorScheme.background.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = false
            WindowCompat.getInsetsController(window, view).isAppearanceLightNavigationBars = false
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = AppTypography,
        content = content
    )
}
