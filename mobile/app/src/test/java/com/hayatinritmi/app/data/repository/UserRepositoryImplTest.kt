package com.hayatinritmi.app.data.repository

import com.hayatinritmi.app.data.local.dao.UserDao
import com.hayatinritmi.app.data.local.entity.UserEntity
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.test.runTest
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

class UserRepositoryImplTest {

    private lateinit var userDao: FakeUserDao
    private lateinit var repository: UserRepositoryImpl

    @Before
    fun setup() {
        userDao = FakeUserDao()
        repository = UserRepositoryImpl(userDao)
    }

    @Test
    fun `register creates user with hashed password`() = runTest {
        val result = repository.register(
            name = "Test",
            surname = "User",
            phone = "5551234567",
            password = "testpass123"
        )

        assertTrue(result.isSuccess)
        val userId = result.getOrThrow()
        assertTrue(userId > 0)

        val user = userDao.getById(userId)
        assertNotNull(user)
        assertEquals("Test", user!!.name)
        assertEquals("User", user.surname)
        assertEquals("5551234567", user.phone)
        // Password should be hashed, not stored in plain text
        assertNotEquals("testpass123", user.passwordHash)
        assertTrue(user.passwordHash.length == 64) // 256-bit hash = 64 hex chars
        assertTrue(user.salt.length == 64) // 256-bit salt = 64 hex chars
    }

    @Test
    fun `duplicate phone number registration fails`() = runTest {
        repository.register("A", "B", "5551234567", "pass1")
        val result = repository.register("C", "D", "5551234567", "pass2")

        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("zaten kayıtlı"))
    }

    @Test
    fun `authenticate succeeds with correct credentials`() = runTest {
        repository.register("Test", "User", "5551234567", "testpass123")
        val result = repository.authenticate("5551234567", "testpass123")

        assertTrue(result.isSuccess)
        val user = result.getOrThrow()
        assertEquals("Test", user.name)
    }

    @Test
    fun `authenticate fails with wrong password`() = runTest {
        repository.register("Test", "User", "5551234567", "testpass123")
        val result = repository.authenticate("5551234567", "wrongpass")

        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("hatalı"))
    }

    @Test
    fun `authenticate fails for non-existent user`() = runTest {
        val result = repository.authenticate("9999999999", "anypass")

        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("bulunamadı"))
    }

    @Test
    fun `getCurrentUser returns current user after login`() = runTest {
        repository.register("Test", "User", "5551234567", "pass")
        repository.authenticate("5551234567", "pass")

        val user = repository.getCurrentUser()
        assertNotNull(user)
        assertEquals("Test", user!!.name)
    }

    @Test
    fun `enableBiometric updates user`() = runTest {
        val result = repository.register("Test", "User", "5551234567", "pass")
        val userId = result.getOrThrow()

        repository.enableBiometric(userId, true)

        val user = userDao.getById(userId)
        assertTrue(user!!.biometricEnabled)
    }

    @Test
    fun `deleteUser removes user`() = runTest {
        val result = repository.register("Test", "User", "5551234567", "pass")
        val userId = result.getOrThrow()

        repository.deleteUser(userId)

        val user = userDao.getById(userId)
        assertNull(user)
    }

    @Test
    fun `PBKDF2 produces different hashes for same password with different salt`() = runTest {
        repository.register("A", "A", "111", "samepassword")
        repository.register("B", "B", "222", "samepassword")

        val user1 = userDao.getByPhone("111")!!
        val user2 = userDao.getByPhone("222")!!

        assertNotEquals(user1.passwordHash, user2.passwordHash)
        assertNotEquals(user1.salt, user2.salt)
    }

    @Test
    fun `hasRegisteredUsers returns correct value`() = runTest {
        assertFalse(repository.hasRegisteredUsers())
        repository.register("Test", "User", "5551234567", "pass")
        assertTrue(repository.hasRegisteredUsers())
    }
}

// ─── Fake DAO for unit testing ──────────────────────────────────────────

class FakeUserDao : UserDao {
    private val users = mutableListOf<UserEntity>()
    private var nextId = 1L

    override suspend fun insert(user: UserEntity): Long {
        val newUser = user.copy(id = nextId++)
        users.add(newUser)
        return newUser.id
    }

    override suspend fun update(user: UserEntity) {
        val idx = users.indexOfFirst { it.id == user.id }
        if (idx >= 0) users[idx] = user
    }

    override suspend fun getById(id: Long): UserEntity? =
        users.find { it.id == id }

    override fun observeById(id: Long): Flow<UserEntity?> =
        MutableStateFlow(users.find { it.id == id })

    override suspend fun getByPhone(phone: String): UserEntity? =
        users.find { it.phone == phone }

    override suspend fun getFirstUser(): UserEntity? =
        users.firstOrNull()

    override suspend fun getUserCount(): Int = users.size

    override suspend fun delete(user: UserEntity) {
        users.removeAll { it.id == user.id }
    }

    override suspend fun deleteAll() {
        users.clear()
    }
}
