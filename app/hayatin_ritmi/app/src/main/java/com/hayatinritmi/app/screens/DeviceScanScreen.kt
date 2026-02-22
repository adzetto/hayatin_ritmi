package com.hayatinritmi.app.screens

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.material3.ripple
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.hayatinritmi.app.data.model.ConnectionState
import com.hayatinritmi.app.data.model.ScannedDevice
import com.hayatinritmi.app.ui.components.GlassOutlinedButton
import com.hayatinritmi.app.ui.components.IconCircle
import com.hayatinritmi.app.ui.components.StatusBadge
import com.hayatinritmi.app.ui.theme.*

@Composable
fun DeviceScanScreen(
    navController: NavHostController,
    viewModel: DeviceScanViewModel
) {
    val scannedDevices by viewModel.scannedDevices.collectAsState()
    val connectionState by viewModel.connectionState.collectAsState()
    val isScanning = connectionState == ConnectionState.SCANNING

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
    ) {
        // Ambient lights
        Box(
            modifier = Modifier
                .align(Alignment.TopCenter)
                .offset(y = (-50).dp)
                .size(350.dp)
                .background(NeonBlue.copy(alpha = 0.15f), CircleShape)
                .blur(100.dp)
        )

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 24.dp)
        ) {
            Spacer(modifier = Modifier.height(40.dp))

            // Header with back button
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(
                    onClick = { navController.popBackStack() },
                    modifier = Modifier.size(48.dp)
                ) {
                    Icon(
                        Icons.AutoMirrored.Filled.ArrowBack,
                        contentDescription = "Geri",
                        tint = TextPrimary
                    )
                }
                Spacer(modifier = Modifier.width(8.dp))
                Column {
                    Text(
                        "Cihaz Tarama",
                        style = MaterialTheme.typography.headlineMedium,
                        color = TextPrimary
                    )
                    Text(
                        if (isScanning) "Cihaz aranıyor..." else "Taramayı başlatın",
                        style = MaterialTheme.typography.bodySmall,
                        color = TextTertiary
                    )
                }
            }

            Spacer(modifier = Modifier.height(40.dp))

            // Radar animation
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(200.dp),
                contentAlignment = Alignment.Center
            ) {
                if (isScanning) {
                    RadarAnimation()
                } else {
                    Icon(
                        Icons.Default.BluetoothSearching,
                        contentDescription = null,
                        tint = NeonBlue.copy(alpha = 0.3f),
                        modifier = Modifier.size(80.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Scan button — GlassOutlinedButton
            GlassOutlinedButton(
                text = if (isScanning) "Taramayı Durdur" else "Taramayı Başlat",
                onClick = {
                    if (isScanning) viewModel.stopScan() else viewModel.startScan()
                },
                modifier = Modifier.fillMaxWidth(),
                accentColor = if (isScanning) RosePrimary else NeonBlue,
                height = 56.dp,
                icon = if (isScanning) Icons.Default.Stop else Icons.Default.BluetoothSearching
            )

            Spacer(modifier = Modifier.height(24.dp))

            // Device list header
            if (scannedDevices.isNotEmpty()) {
                Text(
                    "BULUNAN CİHAZLAR",
                    style = MaterialTheme.typography.labelSmall,
                    color = TextDisabled,
                    letterSpacing = 2.sp
                )
                Spacer(modifier = Modifier.height(12.dp))
            }

            // Device list
            LazyColumn {
                items(scannedDevices) { device ->
                    DeviceListItem(
                        device = device,
                        connectionState = connectionState,
                        onClick = { viewModel.connectToDevice(device) }
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                }
            }
        }
    }
}

@Composable
fun RadarAnimation() {
    val infiniteTransition = rememberInfiniteTransition(label = "radar")
    val scale1 by infiniteTransition.animateFloat(
        initialValue = 0.3f, targetValue = 1.5f,
        animationSpec = infiniteRepeatable(tween(2000, easing = LinearEasing), RepeatMode.Restart),
        label = "ring1"
    )
    val scale2 by infiniteTransition.animateFloat(
        initialValue = 0.3f, targetValue = 1.5f,
        animationSpec = infiniteRepeatable(tween(2000, 667, LinearEasing), RepeatMode.Restart),
        label = "ring2"
    )
    val scale3 by infiniteTransition.animateFloat(
        initialValue = 0.3f, targetValue = 1.5f,
        animationSpec = infiniteRepeatable(tween(2000, 1334, LinearEasing), RepeatMode.Restart),
        label = "ring3"
    )

    Box(contentAlignment = Alignment.Center) {
        listOf(scale1, scale2, scale3).forEach { scale ->
            val alpha = (1f - (scale - 0.3f) / 1.2f).coerceIn(0f, 0.5f)
            Box(
                modifier = Modifier
                    .size(120.dp)
                    .scale(scale)
                    .border(2.dp, NeonBlue.copy(alpha = alpha), CircleShape)
            )
        }
        // Center icon
        Box(
            modifier = Modifier
                .size(48.dp)
                .background(NeonBlue.copy(alpha = 0.2f), CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Icon(Icons.Default.Bluetooth, contentDescription = null, tint = NeonBlue, modifier = Modifier.size(24.dp))
        }
    }
}

@Composable
fun DeviceListItem(
    device: ScannedDevice,
    connectionState: ConnectionState,
    onClick: () -> Unit
) {
    val isConnecting = connectionState == ConnectionState.CONNECTING
    val isConnected = connectionState == ConnectionState.CONNECTED
    val interactionSource = remember { MutableInteractionSource() }
    val shape = RoundedCornerShape(16.dp)

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .defaultMinSize(minHeight = 48.dp)
            .clip(shape)
            .background(GlassWhite)
            .border(
                1.dp,
                if (isConnected) Emerald500.copy(alpha = 0.3f) else GlassBorder,
                shape
            )
            .clickable(
                interactionSource = interactionSource,
                indication = ripple(color = Color.White.copy(alpha = 0.08f)),
                enabled = !isConnecting && !isConnected,
                role = Role.Button,
                onClick = onClick
            )
            .padding(16.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        // Bluetooth icon — using IconCircle component
        IconCircle(
            icon = Icons.Default.Bluetooth,
            color = NeonBlue,
            size = 40.dp,
            iconSize = 20.dp
        )

        Spacer(modifier = Modifier.width(16.dp))

        Column(modifier = Modifier.weight(1f)) {
            Text(
                device.name,
                style = MaterialTheme.typography.titleSmall,
                color = TextPrimary
            )
            Text(
                device.macAddress,
                style = MaterialTheme.typography.labelSmall,
                color = TextTertiary
            )
        }

        // Signal strength
        SignalBars(rssi = device.rssi)
        Spacer(modifier = Modifier.width(12.dp))

        // Status
        when {
            isConnected -> {
                StatusBadge(
                    text = "BAĞLI",
                    color = Emerald500
                )
            }
            isConnecting -> {
                CircularProgressIndicator(
                    modifier = Modifier.size(20.dp),
                    color = NeonBlue,
                    strokeWidth = 2.dp
                )
            }
            else -> {
                Icon(
                    Icons.Default.ChevronRight,
                    contentDescription = null,
                    tint = TextDisabled
                )
            }
        }
    }
}

@Composable
fun SignalBars(rssi: Int) {
    val strength = when {
        rssi >= -50 -> 4
        rssi >= -60 -> 3
        rssi >= -70 -> 2
        else -> 1
    }
    Row(horizontalArrangement = Arrangement.spacedBy(2.dp), verticalAlignment = Alignment.Bottom) {
        for (i in 1..4) {
            Box(
                modifier = Modifier
                    .width(4.dp)
                    .height((6 + i * 4).dp)
                    .background(
                        if (i <= strength) NeonBlue else BorderSubtle,
                        RoundedCornerShape(1.dp)
                    )
            )
        }
    }
}
