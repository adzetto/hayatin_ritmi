package com.hayatinritmi.app.data.export

import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import androidx.core.content.FileProvider
import com.hayatinritmi.app.data.local.entity.EcgSessionEntity
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import java.io.OutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import javax.inject.Inject
import javax.inject.Singleton

/**
 * CSV Exporter — binary .bin kayıtlarını CSV'ye dönüştürür ve Downloads klasörüne yazar.
 *
 * CSV Format:
 * timestamp_ms, channel, rawAdc, voltageUv
 */
@Singleton
class CsvExporter @Inject constructor(
    @ApplicationContext private val context: Context
) {
    /**
     * Export a session's binary file to CSV in Downloads.
     * @return URI of the exported CSV file, or null on failure.
     */
    suspend fun exportSessionToCsv(session: EcgSessionEntity): Uri? = withContext(Dispatchers.IO) {
        val binFile = File(session.filePath)
        if (!binFile.exists() || binFile.length() < 32) return@withContext null

        val dateFormat = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US)
        val dateStr = dateFormat.format(Date(session.startTimeMs))
        val fileName = "EKG_Rapor_${dateStr}.csv"

        try {
            val outputUri: Uri?
            val outputStream: OutputStream?

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                // Scoped Storage (Android 10+)
                val values = ContentValues().apply {
                    put(MediaStore.Downloads.DISPLAY_NAME, fileName)
                    put(MediaStore.Downloads.MIME_TYPE, "text/csv")
                    put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/HayatinRitmi")
                    put(MediaStore.Downloads.IS_PENDING, 1)
                }
                outputUri = context.contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                outputStream = outputUri?.let { context.contentResolver.openOutputStream(it) }

                outputStream?.let { os ->
                    writeCsvFromBinary(binFile, os, session)
                    os.close()
                }

                // Mark as complete
                outputUri?.let {
                    val updateValues = ContentValues().apply {
                        put(MediaStore.Downloads.IS_PENDING, 0)
                    }
                    context.contentResolver.update(it, updateValues, null, null)
                }
            } else {
                // Legacy (Android 9 and below)
                @Suppress("DEPRECATION")
                val downloadsDir = File(
                    Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS),
                    "HayatinRitmi"
                )
                if (!downloadsDir.exists()) downloadsDir.mkdirs()

                val csvFile = File(downloadsDir, fileName)
                outputStream = FileOutputStream(csvFile)
                writeCsvFromBinary(binFile, outputStream, session)
                outputStream.close()

                outputUri = FileProvider.getUriForFile(
                    context,
                    "${context.packageName}.fileprovider",
                    csvFile
                )
            }

            outputUri
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    /**
     * Create a share intent for a CSV URI.
     */
    fun createShareIntent(csvUri: Uri): Intent {
        return Intent(Intent.ACTION_SEND).apply {
            type = "text/csv"
            putExtra(Intent.EXTRA_STREAM, csvUri)
            putExtra(Intent.EXTRA_SUBJECT, "Hayatın Ritmi — EKG Raporu")
            putExtra(
                Intent.EXTRA_TEXT,
                "Hayatın Ritmi uygulamasından oluşturulan EKG kaydı ektedir."
            )
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
    }

    private fun writeCsvFromBinary(binFile: File, output: OutputStream, session: EcgSessionEntity) {
        val writer = output.bufferedWriter()

        // Write CSV header
        writer.write("timestamp_ms,channel,rawAdc,voltageUv\n")

        // Skip 32-byte file header
        val inputStream = binFile.inputStream().buffered()
        inputStream.skip(32)

        // Read 18-byte records
        val recordBuf = ByteArray(18)
        val byteBuffer = ByteBuffer.wrap(recordBuf).order(ByteOrder.LITTLE_ENDIAN)

        while (true) {
            val bytesRead = inputStream.read(recordBuf)
            if (bytesRead < 18) break

            byteBuffer.clear()
            val timestamp = byteBuffer.long
            val channel = byteBuffer.short.toInt()
            val rawAdc = byteBuffer.int
            val voltageUv = byteBuffer.float

            writer.write("$timestamp,$channel,$rawAdc,${"%.2f".format(voltageUv)}\n")
        }

        inputStream.close()
        writer.flush()
    }
}
