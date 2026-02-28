package com.hayatinritmi.app.data.local.dao

import androidx.room.*
import com.hayatinritmi.app.data.local.entity.EcgSessionEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface EcgSessionDao {

    @Insert
    suspend fun insert(session: EcgSessionEntity): Long

    @Update
    suspend fun update(session: EcgSessionEntity)

    @Query("SELECT * FROM ecg_sessions WHERE id = :id")
    suspend fun getById(id: Long): EcgSessionEntity?

    @Query("SELECT * FROM ecg_sessions WHERE userId = :userId ORDER BY startTimeMs DESC")
    fun getSessionsByUser(userId: Long): Flow<List<EcgSessionEntity>>

    @Query("SELECT * FROM ecg_sessions WHERE userId = :userId ORDER BY startTimeMs DESC LIMIT :limit")
    suspend fun getRecentSessions(userId: Long, limit: Int = 10): List<EcgSessionEntity>

    @Query("""
        SELECT * FROM ecg_sessions 
        WHERE userId = :userId AND startTimeMs BETWEEN :startMs AND :endMs 
        ORDER BY startTimeMs DESC
    """)
    suspend fun getSessionsBetween(userId: Long, startMs: Long, endMs: Long): List<EcgSessionEntity>

    @Query("""
        SELECT COUNT(*) as sessionCount,
               AVG(avgBpm) as avgBpm,
               MIN(minBpm) as minBpm,
               MAX(maxBpm) as maxBpm,
               SUM(durationMs) as totalDurationMs,
               AVG(qualityScore) as avgQuality
        FROM ecg_sessions WHERE userId = :userId
    """)
    suspend fun getSessionStats(userId: Long): SessionStats

    @Delete
    suspend fun delete(session: EcgSessionEntity)

    @Query("DELETE FROM ecg_sessions WHERE userId = :userId")
    suspend fun deleteAllByUser(userId: Long)

    @Query("SELECT * FROM ecg_sessions WHERE isExported = 0 ORDER BY startTimeMs ASC LIMIT :limit")
    suspend fun getPendingSyncSessions(limit: Int = 50): List<EcgSessionEntity>

    @Query("UPDATE ecg_sessions SET isExported = :isExported WHERE id = :sessionId")
    suspend fun markExported(sessionId: Long, isExported: Boolean)
}

data class SessionStats(
    val sessionCount: Int,
    val avgBpm: Float,
    val minBpm: Int,
    val maxBpm: Int,
    val totalDurationMs: Long,
    val avgQuality: Float
)
