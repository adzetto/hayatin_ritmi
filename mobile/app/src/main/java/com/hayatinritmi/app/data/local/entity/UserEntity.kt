package com.hayatinritmi.app.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "users")
data class UserEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val name: String,
    val surname: String,
    val phone: String,
    val bloodType: String = "",
    val emergencyContactName: String = "",
    val emergencyContactPhone: String = "",
    val doctorEmail: String = "",
    val profilePhotoUri: String? = null,
    val passwordHash: String,
    val salt: String,
    val createdAt: Long = System.currentTimeMillis(),
    val biometricEnabled: Boolean = false
)
