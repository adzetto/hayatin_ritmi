package com.hayatinritmi.app.ble

import com.hayatinritmi.app.data.model.ConnectionState
import com.hayatinritmi.app.data.model.DeviceStatus
import com.hayatinritmi.app.data.model.ScannedDevice
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
