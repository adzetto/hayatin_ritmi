package com.hayatinritmi.app.domain.repository

import com.hayatinritmi.app.data.local.entity.UserEntity
import kotlinx.coroutines.flow.Flow

interface UserRepository {
    suspend fun register(
        name: String,
        surname: String,
        phone: String,
        password: String,
        bloodType: String = "",
        emergencyContactName: String = "",
        emergencyContactPhone: String = "",
        doctorEmail: String = ""
    ): Result<Long>

    suspend fun authenticate(phone: String, password: String): Result<UserEntity>
    suspend fun getCurrentUser(): UserEntity?
    fun observeCurrentUser(): Flow<UserEntity?>
    suspend fun updateUser(user: UserEntity)
    suspend fun deleteUser(userId: Long)
    suspend fun enableBiometric(userId: Long, enabled: Boolean)
    suspend fun hasRegisteredUsers(): Boolean
}
