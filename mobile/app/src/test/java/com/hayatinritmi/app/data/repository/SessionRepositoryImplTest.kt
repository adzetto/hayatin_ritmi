package com.hayatinritmi.app.data.repository

import com.hayatinritmi.app.data.local.dao.EcgAlertDao
import com.hayatinritmi.app.data.local.dao.EcgSessionDao
import com.hayatinritmi.app.data.local.dao.SessionStats
import com.hayatinritmi.app.data.local.entity.EcgAlertEntity
import com.hayatinritmi.app.data.local.entity.EcgSessionEntity
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.runTest
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

class SessionRepositoryImplTest {

    private lateinit var sessionDao: FakeSessionDao
    private lateinit var alertDao: FakeAlertDao
    private lateinit var repository: SessionRepositoryImpl

    @Before
    fun setup() {
        sessionDao = FakeSessionDao()
        alertDao = FakeAlertDao()
        repository = SessionRepositoryImpl(sessionDao, alertDao)
    }

    @Test
    fun `createSession inserts correctly`() = runTest {
        val id = repository.createSession(userId = 1, channelCount = 12)
        assertTrue(id > 0)

        val session = repository.getSession(id)
        assertNotNull(session)
        assertEquals(1L, session!!.userId)
        assertEquals(12, session.channelCount)
    }

    @Test
    fun `updateSession modifies correctly`() = runTest {
        val id = repository.createSession(userId = 1)
        val session = repository.getSession(id)!!
        val updated = session.copy(avgBpm = 72, durationMs = 60000)
        repository.updateSession(updated)

        val result = repository.getSession(id)
        assertEquals(72, result!!.avgBpm)
        assertEquals(60000L, result.durationMs)
    }

    @Test
    fun `deleteSession removes correctly`() = runTest {
        val id = repository.createSession(userId = 1)
        repository.deleteSession(id)
        assertNull(repository.getSession(id))
    }

    @Test
    fun `insertAlert and retrieve`() = runTest {
        val sessionId = repository.createSession(userId = 1)
        val alertId = repository.insertAlert(
            EcgAlertEntity(
                sessionId = sessionId,
                timestampMs = System.currentTimeMillis(),
                type = "TACHY",
                level = "YELLOW",
                bpm = 130
            )
        )
        assertTrue(alertId > 0)

        val alerts = repository.getRecentAlerts(10)
        assertEquals(1, alerts.size)
        assertEquals("TACHY", alerts[0].type)
        assertEquals(130, alerts[0].bpm)
    }

    @Test
    fun `markAlertAsRead works`() = runTest {
        val sessionId = repository.createSession(userId = 1)
        val alertId = repository.insertAlert(
            EcgAlertEntity(
                sessionId = sessionId,
                timestampMs = System.currentTimeMillis(),
                type = "AF",
                level = "RED"
            )
        )

        repository.markAlertAsRead(alertId)
        val alerts = repository.getRecentAlerts(10)
        assertTrue(alerts[0].isRead)
    }
}

// ─── Fake DAOs ──────────────────────────────────────────────────────────

class FakeSessionDao : EcgSessionDao {
    private val sessions = mutableListOf<EcgSessionEntity>()
    private var nextId = 1L

    override suspend fun insert(session: EcgSessionEntity): Long {
        val newSession = session.copy(id = nextId++)
        sessions.add(newSession)
        return newSession.id
    }

    override suspend fun update(session: EcgSessionEntity) {
        val idx = sessions.indexOfFirst { it.id == session.id }
        if (idx >= 0) sessions[idx] = session
    }

    override suspend fun getById(id: Long): EcgSessionEntity? =
        sessions.find { it.id == id }

    override fun getSessionsByUser(userId: Long): Flow<List<EcgSessionEntity>> =
        MutableStateFlow(sessions.filter { it.userId == userId })

    override suspend fun getRecentSessions(userId: Long, limit: Int): List<EcgSessionEntity> =
        sessions.filter { it.userId == userId }.takeLast(limit)

    override suspend fun getSessionsBetween(userId: Long, startMs: Long, endMs: Long): List<EcgSessionEntity> =
        sessions.filter { it.userId == userId && it.startTimeMs in startMs..endMs }

    override suspend fun getSessionStats(userId: Long): SessionStats {
        val s = sessions.filter { it.userId == userId }
        return SessionStats(
            sessionCount = s.size,
            avgBpm = s.map { it.avgBpm }.average().toFloat(),
            minBpm = s.minOfOrNull { it.minBpm } ?: 0,
            maxBpm = s.maxOfOrNull { it.maxBpm } ?: 0,
            totalDurationMs = s.sumOf { it.durationMs },
            avgQuality = s.map { it.qualityScore }.average().toFloat()
        )
    }

    override suspend fun delete(session: EcgSessionEntity) {
        sessions.removeAll { it.id == session.id }
    }

    override suspend fun deleteAllByUser(userId: Long) {
        sessions.removeAll { it.userId == userId }
    }
}

class FakeAlertDao : EcgAlertDao {
    private val alerts = mutableListOf<EcgAlertEntity>()
    private var nextId = 1L

    override suspend fun insert(alert: EcgAlertEntity): Long {
        val newAlert = alert.copy(id = nextId++)
        alerts.add(newAlert)
        return newAlert.id
    }

    override suspend fun update(alert: EcgAlertEntity) {
        val idx = alerts.indexOfFirst { it.id == alert.id }
        if (idx >= 0) alerts[idx] = alert
    }

    override fun getAlertsBySession(sessionId: Long): Flow<List<EcgAlertEntity>> =
        MutableStateFlow(alerts.filter { it.sessionId == sessionId })

    override suspend fun getRecentAlerts(limit: Int): List<EcgAlertEntity> =
        alerts.takeLast(limit)

    override fun getUnreadCount(): Flow<Int> =
        MutableStateFlow(alerts.count { !it.isRead })

    override suspend fun markAsRead(id: Long) {
        val idx = alerts.indexOfFirst { it.id == id }
        if (idx >= 0) alerts[idx] = alerts[idx].copy(isRead = true)
    }

    override suspend fun markAllAsRead() {
        for (i in alerts.indices) alerts[i] = alerts[i].copy(isRead = true)
    }

    override suspend fun getAlertsByLevel(level: String): List<EcgAlertEntity> =
        alerts.filter { it.level == level }

    override suspend fun delete(alert: EcgAlertEntity) {
        alerts.removeAll { it.id == alert.id }
    }

    override suspend fun deleteBySession(sessionId: Long) {
        alerts.removeAll { it.sessionId == sessionId }
    }
}
