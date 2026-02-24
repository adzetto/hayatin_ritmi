package com.hayatinritmi.app.data.bluetooth

import com.hayatinritmi.app.domain.model.ConnectionState
import com.hayatinritmi.app.domain.model.DeviceStatus
import com.hayatinritmi.app.domain.model.ScannedDevice
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.StateFlow

interface BleManager {
    val connectionState: StateFlow<ConnectionState>
    val scannedDevices: StateFlow<List<ScannedDevice>>
    fun startScan(timeoutMs: Long = 30_000L)
    fun stopScan()
    fun connect(device: ScannedDevice)
    fun disconnect()
    fun observeEcgData(): Flow<ByteArray>
    fun observeDeviceStatus(): Flow<DeviceStatus>
}
