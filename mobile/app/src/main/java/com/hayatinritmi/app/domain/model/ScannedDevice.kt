package com.hayatinritmi.app.domain.model

data class ScannedDevice(
    val name: String,
    val macAddress: String,
    val rssi: Int
)
