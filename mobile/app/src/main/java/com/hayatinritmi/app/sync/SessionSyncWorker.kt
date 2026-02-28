package com.hayatinritmi.app.sync

import android.content.Context
import androidx.room.Room
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.hayatinritmi.app.data.local.HayatinRitmiDatabase
import net.zetetic.database.sqlcipher.SupportOpenHelperFactory
import org.json.JSONObject
import java.io.File
import java.security.SecureRandom

/**
 * Offline sync worker:
 * - Collects completed sessions that are not exported yet.
 * - Stores metadata as local queue files for later upload.
 * - Marks sessions as exported when queue write succeeds.
 */
class SessionSyncWorker(
    appContext: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(appContext, workerParams) {

    override suspend fun doWork(): Result {
        return runCatching {
            val db = openDatabase()
            try {
                val sessionDao = db.ecgSessionDao()
                val pending = sessionDao.getPendingSyncSessions(limit = 100)
                if (pending.isEmpty()) return Result.success()

                val queueDir = File(applicationContext.filesDir, "sync_queue")
                if (!queueDir.exists()) queueDir.mkdirs()

                pending.forEach { session ->
                    if (session.filePath.isBlank()) return@forEach
                    val recordingFile = File(session.filePath)
                    if (!recordingFile.exists()) return@forEach

                    val payload = JSONObject()
                        .put("sessionId", session.id)
                        .put("userId", session.userId)
                        .put("startTimeMs", session.startTimeMs)
                        .put("durationMs", session.durationMs)
                        .put("avgBpm", session.avgBpm)
                        .put("minBpm", session.minBpm)
                        .put("maxBpm", session.maxBpm)
                        .put("sampleCount", session.sampleCount)
                        .put("channelCount", session.channelCount)
                        .put("filePath", session.filePath)
                        .put("aiLabel", session.aiLabel)
                        .put("aiConfidence", session.aiConfidence)

                    val queueFile = File(queueDir, "session_${session.id}.json")
                    queueFile.writeText(payload.toString(), Charsets.UTF_8)
                    sessionDao.markExported(session.id, isExported = true)
                }
            } finally {
                db.close()
            }
            Result.success()
        }.getOrElse {
            Result.retry()
        }
    }

    private fun openDatabase(): HayatinRitmiDatabase {
        val passphrase = getOrCreatePassphrase()
        val factory = SupportOpenHelperFactory(passphrase)
        return Room.databaseBuilder(
            applicationContext,
            HayatinRitmiDatabase::class.java,
            "hayatinritmi.db"
        ).openHelperFactory(factory)
            .fallbackToDestructiveMigration()
            .build()
    }

    private fun getOrCreatePassphrase(): ByteArray {
        val prefs = applicationContext.getSharedPreferences("db_key_prefs", Context.MODE_PRIVATE)
        val existing = prefs.getString("db_passphrase_hex", null)
        if (existing != null) {
            return existing.chunked(2).map { it.toInt(16).toByte() }.toByteArray()
        }
        val passphrase = ByteArray(32)
        SecureRandom().nextBytes(passphrase)
        val hex = passphrase.joinToString("") { "%02x".format(it) }
        prefs.edit().putString("db_passphrase_hex", hex).apply()
        return passphrase
    }
}
