package com.hayatinritmi.app.data.local.dao

import androidx.room.*
import com.hayatinritmi.app.data.local.entity.EcgAlertEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface EcgAlertDao {

    @Insert
    suspend fun insert(alert: EcgAlertEntity): Long

    @Update
    suspend fun update(alert: EcgAlertEntity)

    @Query("SELECT * FROM ecg_alerts WHERE sessionId = :sessionId ORDER BY timestampMs DESC")
    fun getAlertsBySession(sessionId: Long): Flow<List<EcgAlertEntity>>

    @Query("SELECT * FROM ecg_alerts ORDER BY timestampMs DESC LIMIT :limit")
    suspend fun getRecentAlerts(limit: Int = 50): List<EcgAlertEntity>

    @Query("SELECT COUNT(*) FROM ecg_alerts WHERE isRead = 0")
    fun getUnreadCount(): Flow<Int>

    @Query("UPDATE ecg_alerts SET isRead = 1 WHERE id = :id")
    suspend fun markAsRead(id: Long)

    @Query("UPDATE ecg_alerts SET isRead = 1")
    suspend fun markAllAsRead()

    @Query("SELECT * FROM ecg_alerts WHERE level = :level ORDER BY timestampMs DESC")
    suspend fun getAlertsByLevel(level: String): List<EcgAlertEntity>

    @Delete
    suspend fun delete(alert: EcgAlertEntity)

    @Query("DELETE FROM ecg_alerts WHERE sessionId = :sessionId")
    suspend fun deleteBySession(sessionId: Long)
}
