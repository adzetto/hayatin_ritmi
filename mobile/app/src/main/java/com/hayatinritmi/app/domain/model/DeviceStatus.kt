package com.hayatinritmi.app.domain.model

data class DeviceStatus(
    val batteryPercent: Int,
    val isElectrodeConnected: Boolean,
    val isCharging: Boolean,
    val signalQuality: Int
) {
    companion object {
        fun fromByte(statusByte: Int, batteryByte: Int): DeviceStatus {
            return DeviceStatus(
                batteryPercent = batteryByte.coerceIn(0, 100),
                isElectrodeConnected = (statusByte and 0x01) != 0,
                isCharging = (statusByte and 0x02) != 0,
                signalQuality = if ((statusByte and 0x01) != 0) 100 else 0
            )
        }

        val DISCONNECTED = DeviceStatus(0, false, false, 0)
    }
}
