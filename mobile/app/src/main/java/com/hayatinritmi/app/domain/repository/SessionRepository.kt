package com.hayatinritmi.app.domain.repository

import com.hayatinritmi.app.data.local.dao.SessionStats
import com.hayatinritmi.app.data.local.entity.EcgAlertEntity
import com.hayatinritmi.app.data.local.entity.EcgSessionEntity
import kotlinx.coroutines.flow.Flow

interface SessionRepository {
    suspend fun createSession(userId: Long, channelCount: Int = 12): Long
    suspend fun updateSession(session: EcgSessionEntity)
    suspend fun getSession(sessionId: Long): EcgSessionEntity?
    fun getSessionsByUser(userId: Long): Flow<List<EcgSessionEntity>>
    suspend fun getRecentSessions(userId: Long, limit: Int = 10): List<EcgSessionEntity>
    suspend fun getSessionsBetween(userId: Long, startMs: Long, endMs: Long): List<EcgSessionEntity>
    suspend fun getSessionStats(userId: Long): SessionStats
    suspend fun deleteSession(sessionId: Long)
    suspend fun deleteAllByUser(userId: Long)

    // Alerts
    suspend fun insertAlert(alert: EcgAlertEntity): Long
    fun getAlertsBySession(sessionId: Long): Flow<List<EcgAlertEntity>>
    suspend fun getRecentAlerts(limit: Int = 50): List<EcgAlertEntity>
    fun getUnreadAlertCount(): Flow<Int>
    suspend fun markAlertAsRead(alertId: Long)
    suspend fun markAllAlertsAsRead()
}
