package com.hayatinritmi.app.data.bluetooth

import java.util.UUID

object BleConstants {
    // ESP32 BLE Service UUIDs
    val ECG_SERVICE_UUID: UUID = UUID.fromString("0000181d-0000-1000-8000-00805f9b34fb")
    val ECG_DATA_CHAR_UUID: UUID = UUID.fromString("00002a37-0000-1000-8000-00805f9b34fb")
    val BATTERY_CHAR_UUID: UUID = UUID.fromString("00002a19-0000-1000-8000-00805f9b34fb")
    val DEVICE_STATUS_CHAR_UUID: UUID = UUID.fromString("00002a38-0000-1000-8000-00805f9b34fb")
    val CCCD_UUID: UUID = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")

    // BLE Protocol — 12-Lead Multi-Frame Format
    // Frame: [Header:1B=0xAA][FrameSeq:1B][Timestamp:4B uint32_ms][12×Lead:36B int24 BE][Checksum:1B XOR] = 43 bytes
    const val PACKET_HEADER: Byte = 0xAA.toByte()
    const val PACKET_SIZE = 43              // 12-lead multi-channel frame
    const val CHANNEL_COUNT = 12            // Standard 12-lead ECG
    const val BYTES_PER_LEAD = 3            // 24-bit per lead
    const val SAMPLE_RATE_HZ = 250
    const val DEVICE_NAME_FILTER = "HayatinRitmi"
    const val SCAN_TIMEOUT_MS = 30_000L
    const val DEFAULT_MTU = 247             // fits up to 5 complete 43-byte frames

    // Lead index mapping (0-based)
    const val LEAD_I   = 0
    const val LEAD_II  = 1
    const val LEAD_III = 2
    const val LEAD_AVR = 3
    const val LEAD_AVL = 4
    const val LEAD_AVF = 5
    const val LEAD_V1  = 6
    const val LEAD_V2  = 7
    const val LEAD_V3  = 8
    const val LEAD_V4  = 9
    const val LEAD_V5  = 10
    const val LEAD_V6  = 11

    val LEAD_NAMES = arrayOf("I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6")
}
