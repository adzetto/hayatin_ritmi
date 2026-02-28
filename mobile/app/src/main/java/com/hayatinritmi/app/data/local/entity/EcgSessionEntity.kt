package com.hayatinritmi.app.data.local.entity

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "ecg_sessions",
    foreignKeys = [
        ForeignKey(
            entity = UserEntity::class,
            parentColumns = ["id"],
            childColumns = ["userId"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [Index("userId")]
)
data class EcgSessionEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val userId: Long,
    val startTimeMs: Long,
    val durationMs: Long = 0,
    val avgBpm: Int = 0,
    val minBpm: Int = 0,
    val maxBpm: Int = 0,
    val filePath: String = "",
    val qualityScore: Int = 0,
    val aiLabel: String = "",
    val aiConfidence: Float = 0f,
    val notes: String = "",
    val sampleCount: Long = 0,
    val channelCount: Int = 12,
    val isExported: Boolean = false
)
