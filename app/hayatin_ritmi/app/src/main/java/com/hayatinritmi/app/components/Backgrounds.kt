package com.hayatinritmi.app.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.hayatinritmi.app.ui.theme.RichBlack
import com.hayatinritmi.app.ui.theme.RosePrimary

@Composable
fun WorldClassBackground() {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(RichBlack) // Zemin Simsiyah
    ) {
        // Sadece Üstten Aşağı İnen Hafif Bir Işık (Spot Işığı Gibi)
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(500.dp) // Ekranın yarısına kadar inen ışık
                .background(
                    brush = Brush.verticalGradient(
                        colors = listOf(
                            RosePrimary.copy(alpha = 0.15f), // Tepede hafif kırmızı
                            Color.Transparent // Aşağıda kayboluyor
                        )
                    )
                )
        )
    }
}