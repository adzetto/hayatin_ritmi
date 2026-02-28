package com.hayatinritmi.app.data.recording

import android.content.Context
import androidx.security.crypto.EncryptedFile
import androidx.security.crypto.MasterKey
import com.hayatinritmi.app.data.local.entity.EcgSessionEntity
import com.hayatinritmi.app.domain.model.EcgSample
import com.hayatinritmi.app.domain.repository.SessionRepository
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.BufferedOutputStream
import java.io.File
import java.io.FileOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import javax.inject.Inject
import javax.inject.Singleton

/**
 * EKG Oturum Kaydedici — binary formatta disk'e yazar, oturum sonunda Room'a kaydeder.
 *
 * Binary format (per sample, 18 bytes):
 * [timestampMs:8B LE int64][channel:2B LE int16][rawAdc:4B LE int32][voltageUv:4B LE float32]
 *
 * File header (32 bytes):
 * [magic:4B "EKGR"][version:2B][sampleRate:2B][channelCount:2B][startTimeMs:8B][reserved:14B]
 */
@Singleton
class EcgSessionRecorder @Inject constructor(
    @ApplicationContext private val context: Context,
    private val sessionRepository: SessionRepository
) {
    private var outputStream: BufferedOutputStream? = null
    private var currentFile: File? = null
    private var currentSessionId: Long = -1L
    private var currentUserId: Long = -1L
    private var startTimeMs: Long = 0L
    private var sampleCount: Long = 0L
    private var minBpm: Int = Int.MAX_VALUE
    private var maxBpm: Int = 0
    private var bpmSum: Long = 0L
    private var bpmCount: Int = 0

    @Volatile
    var isRecording: Boolean = false
        private set

    private val buffer = ByteBuffer.allocate(18).order(ByteOrder.LITTLE_ENDIAN)

    suspend fun startRecording(userId: Long, channelCount: Int = 12): Long {
        if (isRecording) stopRecording()

        currentUserId = userId
        startTimeMs = System.currentTimeMillis()

        // Create session in Room
        currentSessionId = sessionRepository.createSession(userId, channelCount)

        // Create recording directory
        val recordingDir = File(context.filesDir, "ecg_recordings")
        if (!recordingDir.exists()) recordingDir.mkdirs()

        // Create file
        currentFile = File(recordingDir, "ecg_${userId}_${startTimeMs}.bin.enc")
        outputStream = createSecureOutputStream(currentFile!!)

        // Write header
        writeHeader(channelCount)

        sampleCount = 0
        minBpm = Int.MAX_VALUE
        maxBpm = 0
        bpmSum = 0
        bpmCount = 0
        isRecording = true

        return currentSessionId
    }

    fun addSample(sample: EcgSample) {
        if (!isRecording) return
        val os = outputStream ?: return

        buffer.clear()
        buffer.putLong(sample.timestamp)
        buffer.putShort(sample.channel.toShort())
        buffer.putInt(sample.rawAdc)
        buffer.putFloat(sample.voltageUv)

        try {
            os.write(buffer.array(), 0, 18)
            sampleCount++
        } catch (_: Exception) {
            // Disk full or IO error — silently stop
        }
    }

    fun updateBpm(bpm: Int) {
        if (!isRecording || bpm <= 0) return
        if (bpm < minBpm) minBpm = bpm
        if (bpm > maxBpm) maxBpm = bpm
        bpmSum += bpm
        bpmCount++
    }

    suspend fun stopRecording(): EcgSessionEntity? = withContext(Dispatchers.IO) {
        if (!isRecording) return@withContext null
        isRecording = false

        try {
            outputStream?.flush()
            outputStream?.close()
        } catch (_: Exception) { }
        outputStream = null

        val endTimeMs = System.currentTimeMillis()
        val durationMs = endTimeMs - startTimeMs
        val avgBpm = if (bpmCount > 0) (bpmSum / bpmCount).toInt() else 0
        val safeMinBpm = if (minBpm == Int.MAX_VALUE) 0 else minBpm

        // Update session in Room
        val session = sessionRepository.getSession(currentSessionId)?.copy(
            durationMs = durationMs,
            avgBpm = avgBpm,
            minBpm = safeMinBpm,
            maxBpm = maxBpm,
            filePath = currentFile?.absolutePath ?: "",
            sampleCount = sampleCount
        )

        if (session != null) {
            sessionRepository.updateSession(session)
        }

        currentSessionId = -1L
        currentFile = null
        session
    }

    fun getCurrentSessionId(): Long = currentSessionId
    fun getRecordingDurationMs(): Long = if (isRecording) System.currentTimeMillis() - startTimeMs else 0

    private fun writeHeader(channelCount: Int) {
        val headerBuf = ByteBuffer.allocate(32).order(ByteOrder.LITTLE_ENDIAN)
        headerBuf.put("EKGR".toByteArray())       // magic (4B)
        headerBuf.putShort(1)                       // version (2B)
        headerBuf.putShort(250)                     // sampleRate (2B)
        headerBuf.putShort(channelCount.toShort())  // channelCount (2B)
        headerBuf.putLong(startTimeMs)              // startTimeMs (8B)
        // reserved (14B) — zero-filled
        headerBuf.position(32)
        outputStream?.write(headerBuf.array())
    }

    private fun createSecureOutputStream(file: File): BufferedOutputStream {
        return try {
            val masterKey = MasterKey.Builder(context)
                .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
                .build()

            val encryptedFile = EncryptedFile.Builder(
                context,
                file,
                masterKey,
                EncryptedFile.FileEncryptionScheme.AES256_GCM_HKDF_4KB
            ).build()

            BufferedOutputStream(encryptedFile.openFileOutput(), 8192)
        } catch (_: Exception) {
            // Fallback to plain stream if encrypted backend cannot be initialized.
            BufferedOutputStream(FileOutputStream(file), 8192)
        }
    }
}
