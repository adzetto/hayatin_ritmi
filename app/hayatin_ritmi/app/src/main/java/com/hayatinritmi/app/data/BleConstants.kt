package com.hayatinritmi.app.data

import java.util.UUID

object BleConstants {
    // ESP32 BLE Service UUIDs
    val ECG_SERVICE_UUID: UUID = UUID.fromString("0000181d-0000-1000-8000-00805f9b34fb")
    val ECG_DATA_CHAR_UUID: UUID = UUID.fromString("00002a37-0000-1000-8000-00805f9b34fb")
    val BATTERY_CHAR_UUID: UUID = UUID.fromString("00002a19-0000-1000-8000-00805f9b34fb")
    val DEVICE_STATUS_CHAR_UUID: UUID = UUID.fromString("00002a38-0000-1000-8000-00805f9b34fb")
    val CCCD_UUID: UUID = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")

    // BLE Protocol
    const val PACKET_HEADER: Byte = 0xAA.toByte()
    const val PACKET_SIZE = 10
    const val SAMPLE_RATE_HZ = 250
    const val DEVICE_NAME_FILTER = "HayatinRitmi"
    const val SCAN_TIMEOUT_MS = 30_000L
    const val DEFAULT_MTU = 247
}
