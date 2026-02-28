package com.hayatinritmi.app.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "device_info")
data class DeviceInfoEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val mac: String,
    val name: String,
    val lastConnectedMs: Long = System.currentTimeMillis(),
    val firmwareVersion: String = "",
    val batteryPercent: Int = -1
)
