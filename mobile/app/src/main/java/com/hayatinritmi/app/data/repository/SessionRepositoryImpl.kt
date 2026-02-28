package com.hayatinritmi.app.data.repository

import com.hayatinritmi.app.data.local.dao.EcgAlertDao
import com.hayatinritmi.app.data.local.dao.EcgSessionDao
import com.hayatinritmi.app.data.local.dao.SessionStats
import com.hayatinritmi.app.data.local.entity.EcgAlertEntity
import com.hayatinritmi.app.data.local.entity.EcgSessionEntity
import com.hayatinritmi.app.domain.repository.SessionRepository
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SessionRepositoryImpl @Inject constructor(
    private val sessionDao: EcgSessionDao,
    private val alertDao: EcgAlertDao
) : SessionRepository {

    override suspend fun createSession(userId: Long, channelCount: Int): Long {
        val session = EcgSessionEntity(
            userId = userId,
            startTimeMs = System.currentTimeMillis(),
            channelCount = channelCount
        )
        return sessionDao.insert(session)
    }

    override suspend fun updateSession(session: EcgSessionEntity) {
        sessionDao.update(session)
    }

    override suspend fun getSession(sessionId: Long): EcgSessionEntity? {
        return sessionDao.getById(sessionId)
    }

    override fun getSessionsByUser(userId: Long): Flow<List<EcgSessionEntity>> {
        return sessionDao.getSessionsByUser(userId)
    }

    override suspend fun getRecentSessions(userId: Long, limit: Int): List<EcgSessionEntity> {
        return sessionDao.getRecentSessions(userId, limit)
    }

    override suspend fun getSessionsBetween(userId: Long, startMs: Long, endMs: Long): List<EcgSessionEntity> {
        return sessionDao.getSessionsBetween(userId, startMs, endMs)
    }

    override suspend fun getSessionStats(userId: Long): SessionStats {
        return sessionDao.getSessionStats(userId)
    }

    override suspend fun getPendingSyncSessions(limit: Int): List<EcgSessionEntity> {
        return sessionDao.getPendingSyncSessions(limit)
    }

    override suspend fun markSessionExported(sessionId: Long, exported: Boolean) {
        sessionDao.markExported(sessionId, exported)
    }

    override suspend fun deleteSession(sessionId: Long) {
        val session = sessionDao.getById(sessionId)
        if (session != null) {
            sessionDao.delete(session)
        }
    }

    override suspend fun deleteAllByUser(userId: Long) {
        sessionDao.deleteAllByUser(userId)
    }

    // ─── Alert Operations ──────────────────────────────────────────────────
    override suspend fun insertAlert(alert: EcgAlertEntity): Long {
        return alertDao.insert(alert)
    }

    override fun getAlertsBySession(sessionId: Long): Flow<List<EcgAlertEntity>> {
        return alertDao.getAlertsBySession(sessionId)
    }

    override suspend fun getRecentAlerts(limit: Int): List<EcgAlertEntity> {
        return alertDao.getRecentAlerts(limit)
    }

    override fun getUnreadAlertCount(): Flow<Int> {
        return alertDao.getUnreadCount()
    }

    override suspend fun markAlertAsRead(alertId: Long) {
        alertDao.markAsRead(alertId)
    }

    override suspend fun markAllAlertsAsRead() {
        alertDao.markAllAsRead()
    }
}
