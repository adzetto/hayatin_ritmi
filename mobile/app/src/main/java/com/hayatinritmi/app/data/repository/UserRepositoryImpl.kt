package com.hayatinritmi.app.data.repository

import com.hayatinritmi.app.data.local.dao.UserDao
import com.hayatinritmi.app.data.local.entity.UserEntity
import com.hayatinritmi.app.domain.repository.UserRepository
import kotlinx.coroutines.flow.Flow
import java.security.SecureRandom
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.PBEKeySpec
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class UserRepositoryImpl @Inject constructor(
    private val userDao: UserDao
) : UserRepository {

    // Cached current user ID (set after login)
    @Volatile
    private var currentUserId: Long = -1L

    override suspend fun register(
        name: String,
        surname: String,
        phone: String,
        password: String,
        bloodType: String,
        emergencyContactName: String,
        emergencyContactPhone: String,
        doctorEmail: String
    ): Result<Long> {
        return try {
            // Check if phone already exists
            val existing = userDao.getByPhone(phone)
            if (existing != null) {
                return Result.failure(IllegalArgumentException("Bu telefon numarası zaten kayıtlı"))
            }

            val salt = generateSalt()
            val hash = hashPassword(password, salt)

            val user = UserEntity(
                name = name,
                surname = surname,
                phone = phone,
                bloodType = bloodType,
                emergencyContactName = emergencyContactName,
                emergencyContactPhone = emergencyContactPhone,
                doctorEmail = doctorEmail,
                passwordHash = hash,
                salt = salt
            )
            val id = userDao.insert(user)
            currentUserId = id
            Result.success(id)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun authenticate(phone: String, password: String): Result<UserEntity> {
        return try {
            val user = userDao.getByPhone(phone)
                ?: return Result.failure(IllegalArgumentException("Kullanıcı bulunamadı"))

            val hash = hashPassword(password, user.salt)
            if (hash != user.passwordHash) {
                return Result.failure(IllegalArgumentException("Şifre hatalı"))
            }
            currentUserId = user.id
            Result.success(user)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun getCurrentUser(): UserEntity? {
        if (currentUserId > 0) {
            return userDao.getById(currentUserId)
        }
        // Fallback: get first user
        return userDao.getFirstUser()?.also { currentUserId = it.id }
    }

    override fun observeCurrentUser(): Flow<UserEntity?> {
        return userDao.observeById(if (currentUserId > 0) currentUserId else 1)
    }

    override suspend fun updateUser(user: UserEntity) {
        userDao.update(user)
    }

    override suspend fun deleteUser(userId: Long) {
        val user = userDao.getById(userId)
        if (user != null) {
            userDao.delete(user)
            if (currentUserId == userId) currentUserId = -1
        }
    }

    override suspend fun enableBiometric(userId: Long, enabled: Boolean) {
        val user = userDao.getById(userId) ?: return
        userDao.update(user.copy(biometricEnabled = enabled))
    }

    override suspend fun hasRegisteredUsers(): Boolean {
        return userDao.getUserCount() > 0
    }

    fun setCurrentUserId(id: Long) {
        currentUserId = id
    }

    // ─── PBKDF2 Password Hashing ───────────────────────────────────────────
    private fun generateSalt(): String {
        val salt = ByteArray(32)
        SecureRandom().nextBytes(salt)
        return salt.joinToString("") { "%02x".format(it) }
    }

    private fun hashPassword(password: String, saltHex: String): String {
        val salt = saltHex.chunked(2).map { it.toInt(16).toByte() }.toByteArray()
        val spec = PBEKeySpec(password.toCharArray(), salt, 65536, 256)
        val factory = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
        val hash = factory.generateSecret(spec).encoded
        return hash.joinToString("") { "%02x".format(it) }
    }
}
