package com.hayatinritmi.app.data.local.entity

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "ecg_alerts",
    foreignKeys = [
        ForeignKey(
            entity = EcgSessionEntity::class,
            parentColumns = ["id"],
            childColumns = ["sessionId"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [Index("sessionId")]
)
data class EcgAlertEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val sessionId: Long,
    val timestampMs: Long,
    val type: String,          // TACHY, BRADY, AF, ST_ANOMALY
    val level: String,         // AlertLevel name
    val details: String = "",
    val aiConfidence: Float = 0f,
    val bpm: Int = 0,
    val lat: Double? = null,
    val lon: Double? = null,
    val isRead: Boolean = false
)
