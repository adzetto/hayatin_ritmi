package com.hayatinritmi.app.data.export

import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.graphics.*
import android.graphics.pdf.PdfDocument
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import androidx.core.content.FileProvider
import com.hayatinritmi.app.data.local.entity.EcgAlertEntity
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
 * PDF Rapor Oluşturucu — EKG oturumunu profesyonel PDF raporuna dönüştürür.
 *
 * Sayfa 1: Başlık + Hasta bilgileri + Özet metrikler
 * Sayfa 2: EKG grafiği (Lead II, 25mm/s, 10mm/mV standart)
 * Sayfa 3: AI sonuçları + Uyarı geçmişi tablosu
 */
@Singleton
class PdfReportGenerator @Inject constructor(
    @ApplicationContext private val context: Context
) {
    companion object {
        private const val PAGE_WIDTH = 595   // A4 @ 72 DPI
        private const val PAGE_HEIGHT = 842
        private const val MARGIN = 40f
        private const val CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN.toInt()
    }

    // Paints
    private val titlePaint = Paint().apply {
        color = Color.rgb(30, 30, 60)
        textSize = 24f
        typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        isAntiAlias = true
    }
    private val headerPaint = Paint().apply {
        color = Color.rgb(60, 60, 100)
        textSize = 16f
        typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        isAntiAlias = true
    }
    private val bodyPaint = Paint().apply {
        color = Color.rgb(40, 40, 40)
        textSize = 12f
        isAntiAlias = true
    }
    private val smallPaint = Paint().apply {
        color = Color.rgb(100, 100, 100)
        textSize = 10f
        isAntiAlias = true
    }
    private val ecgPaint = Paint().apply {
        color = Color.rgb(220, 30, 30)
        strokeWidth = 1.5f
        style = Paint.Style.STROKE
        isAntiAlias = true
    }
    private val gridPaint = Paint().apply {
        color = Color.rgb(240, 200, 200)
        strokeWidth = 0.5f
        style = Paint.Style.STROKE
    }
    private val gridMajorPaint = Paint().apply {
        color = Color.rgb(220, 160, 160)
        strokeWidth = 1f
        style = Paint.Style.STROKE
    }
    private val accentPaint = Paint().apply {
        color = Color.rgb(40, 120, 200)
        textSize = 14f
        typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        isAntiAlias = true
    }
    private val tableBorderPaint = Paint().apply {
        color = Color.rgb(180, 180, 180)
        strokeWidth = 0.5f
        style = Paint.Style.STROKE
    }

    suspend fun generateReport(
        session: EcgSessionEntity,
        patientName: String = "",
        patientBloodType: String = "",
        alerts: List<EcgAlertEntity> = emptyList(),
        aiLabel: String = "",
        aiConfidence: Float = 0f,
        signalQualityScore: Int = 0
    ): Uri? = withContext(Dispatchers.IO) {
        val document = PdfDocument()
        val dateFormat = SimpleDateFormat("dd.MM.yyyy HH:mm:ss", Locale("tr"))
        val fileNameDateFormat = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US)

        try {
            // ═══ PAGE 1: Title + Patient Info + Summary ═══
            val pageInfo1 = PdfDocument.PageInfo.Builder(PAGE_WIDTH, PAGE_HEIGHT, 1).create()
            val page1 = document.startPage(pageInfo1)
            drawPage1(page1.canvas, session, patientName, patientBloodType, dateFormat, signalQualityScore)
            document.finishPage(page1)

            // ═══ PAGE 2: ECG Graph ═══
            val pageInfo2 = PdfDocument.PageInfo.Builder(PAGE_WIDTH, PAGE_HEIGHT, 2).create()
            val page2 = document.startPage(pageInfo2)
            drawPage2EcgGraph(page2.canvas, session)
            document.finishPage(page2)

            // ═══ PAGE 3: AI + Alerts ═══
            val pageInfo3 = PdfDocument.PageInfo.Builder(PAGE_WIDTH, PAGE_HEIGHT, 3).create()
            val page3 = document.startPage(pageInfo3)
            drawPage3AiAlerts(page3.canvas, session, alerts, aiLabel, aiConfidence, dateFormat)
            document.finishPage(page3)

            // Save PDF
            val fileName = "EKG_Rapor_${fileNameDateFormat.format(Date(session.startTimeMs))}.pdf"
            val outputUri = savePdf(document, fileName)
            document.close()
            outputUri
        } catch (e: Exception) {
            e.printStackTrace()
            document.close()
            null
        }
    }

    private fun drawPage1(
        canvas: Canvas,
        session: EcgSessionEntity,
        patientName: String,
        patientBloodType: String,
        dateFormat: SimpleDateFormat,
        qualityScore: Int
    ) {
        var y = MARGIN + 30f

        // Title bar
        val titleBarPaint = Paint().apply {
            color = Color.rgb(30, 30, 80)
        }
        canvas.drawRect(0f, 0f, PAGE_WIDTH.toFloat(), 80f, titleBarPaint)

        val whitePaint = Paint(titlePaint).apply { color = Color.WHITE }
        canvas.drawText("HAYATIN RİTMİ", MARGIN, 35f, whitePaint)
        val subtitlePaint = Paint(bodyPaint).apply { color = Color.rgb(180, 200, 255) }
        canvas.drawText("EKG Analiz Raporu", MARGIN, 60f, subtitlePaint)

        y = 110f

        // Patient Info Section
        canvas.drawText("Hasta Bilgileri", MARGIN, y, headerPaint)
        y += 25f
        drawInfoRow(canvas, "Ad Soyad:", if (patientName.isNotBlank()) patientName else "—", y)
        y += 20f
        drawInfoRow(canvas, "Kan Grubu:", if (patientBloodType.isNotBlank()) patientBloodType else "—", y)
        y += 20f
        drawInfoRow(canvas, "Rapor Tarihi:", dateFormat.format(Date(session.startTimeMs)), y)
        y += 20f
        val durationMin = session.durationMs / 60000
        val durationSec = (session.durationMs % 60000) / 1000
        drawInfoRow(canvas, "Kayıt Süresi:", "${durationMin}dk ${durationSec}sn", y)

        y += 40f

        // Metrics Section
        canvas.drawText("Kalp Ritmi Metrikleri", MARGIN, y, headerPaint)
        y += 30f

        // BPM box
        drawMetricBox(canvas, MARGIN, y, "Ortalama BPM", "${session.avgBpm}", Color.rgb(40, 120, 200))
        drawMetricBox(canvas, MARGIN + 170f, y, "Min BPM", "${session.minBpm}", Color.rgb(40, 160, 80))
        drawMetricBox(canvas, MARGIN + 340f, y, "Max BPM", "${session.maxBpm}", Color.rgb(200, 60, 60))

        y += 100f

        // Signal Quality
        canvas.drawText("Sinyal Kalitesi", MARGIN, y, headerPaint)
        y += 25f
        val qualityText = when {
            qualityScore >= 80 -> "Mükemmel ($qualityScore/100)"
            qualityScore >= 60 -> "İyi ($qualityScore/100)"
            qualityScore >= 40 -> "Orta ($qualityScore/100)"
            else -> "Düşük ($qualityScore/100)"
        }
        val qualityColor = when {
            qualityScore >= 80 -> Color.rgb(40, 160, 80)
            qualityScore >= 60 -> Color.rgb(80, 160, 40)
            qualityScore >= 40 -> Color.rgb(200, 160, 40)
            else -> Color.rgb(200, 60, 60)
        }
        val qualityPaint = Paint(accentPaint).apply { color = qualityColor }
        canvas.drawText(qualityText, MARGIN, y, qualityPaint)

        y += 30f
        drawInfoRow(canvas, "Toplam Örnek:", "${session.sampleCount}", y)
        y += 20f
        drawInfoRow(canvas, "Kanal Sayısı:", "${session.channelCount}", y)

        // Footer
        canvas.drawText(
            "Bu rapor Hayatın Ritmi uygulaması tarafından otomatik olarak oluşturulmuştur.",
            MARGIN, PAGE_HEIGHT - 30f, smallPaint
        )
        canvas.drawText(
            "Tanı amaçlı kullanılmaz — bir sağlık uzmanına danışınız.",
            MARGIN, PAGE_HEIGHT - 18f, smallPaint
        )
    }

    private fun drawPage2EcgGraph(canvas: Canvas, session: EcgSessionEntity) {
        // Header
        var y = MARGIN + 20f
        canvas.drawText("EKG Kaydı — Lead II", MARGIN, y, headerPaint)
        y += 15f
        canvas.drawText("25 mm/s  |  10 mm/mV  |  250 Hz", MARGIN, y, smallPaint)
        y += 20f

        // Graph area
        val graphTop = y
        val graphBottom = PAGE_HEIGHT - 60f
        val graphHeight = graphBottom - graphTop
        val graphLeft = MARGIN + 20f
        val graphRight = PAGE_WIDTH - MARGIN

        // Draw ECG grid
        val minorStep = 5f   // 1mm equivalent
        val majorStep = 25f  // 5mm equivalent

        // Minor grid
        var gx = graphLeft
        while (gx <= graphRight) {
            canvas.drawLine(gx, graphTop, gx, graphBottom, gridPaint)
            gx += minorStep
        }
        var gy = graphTop
        while (gy <= graphBottom) {
            canvas.drawLine(graphLeft, gy, graphRight, gy, gridPaint)
            gy += minorStep
        }

        // Major grid
        gx = graphLeft
        while (gx <= graphRight) {
            canvas.drawLine(gx, graphTop, gx, graphBottom, gridMajorPaint)
            gx += majorStep
        }
        gy = graphTop
        while (gy <= graphBottom) {
            canvas.drawLine(graphLeft, gy, graphRight, gy, gridMajorPaint)
            gy += majorStep
        }

        // Read binary and plot Lead II
        val binFile = File(session.filePath)
        if (binFile.exists() && binFile.length() > 32) {
            val leadIIData = readLeadIIFromBinary(binFile, maxSamples = 2500)

            if (leadIIData.isNotEmpty()) {
                val midY = graphTop + graphHeight / 2
                val maxVal = leadIIData.maxOrNull()?.let { kotlin.math.abs(it) } ?: 1f
                val minVal = leadIIData.minOrNull()?.let { kotlin.math.abs(it) } ?: 1f
                val scale = (graphHeight * 0.4f) / maxOf(maxVal, minVal, 1f)
                val xStep = (graphRight - graphLeft) / leadIIData.size.toFloat()

                val path = Path()
                for (i in leadIIData.indices) {
                    val x = graphLeft + i * xStep
                    val yVal = midY - leadIIData[i] * scale
                    if (i == 0) path.moveTo(x, yVal) else path.lineTo(x, yVal)
                }
                canvas.drawPath(path, ecgPaint)
            }
        } else {
            canvas.drawText("EKG verisi bulunamadı", graphLeft + 100f, graphTop + graphHeight / 2, bodyPaint)
        }

        // Footer
        canvas.drawText("Sayfa 2/3", PAGE_WIDTH / 2f - 20f, PAGE_HEIGHT - 20f, smallPaint)
    }

    private fun drawPage3AiAlerts(
        canvas: Canvas,
        session: EcgSessionEntity,
        alerts: List<EcgAlertEntity>,
        aiLabel: String,
        aiConfidence: Float,
        dateFormat: SimpleDateFormat
    ) {
        var y = MARGIN + 20f

        // AI Analysis Section
        canvas.drawText("Yapay Zeka Analizi (DCA-CNN)", MARGIN, y, headerPaint)
        y += 30f

        val label = if (aiLabel.isNotBlank()) aiLabel else session.aiLabel.ifBlank { "—" }
        val confidence = if (aiConfidence > 0) aiConfidence else session.aiConfidence
        drawInfoRow(canvas, "Tahmin:", label, y)
        y += 20f
        drawInfoRow(canvas, "Güven:", if (confidence > 0) "${"%.1f".format(confidence * 100)}%" else "—", y)
        y += 20f
        drawInfoRow(canvas, "Model:", "DCA-CNN INT8 (312 KB, <1ms)", y)

        y += 40f

        // Alert History Table
        canvas.drawText("Uyarı Geçmişi", MARGIN, y, headerPaint)
        y += 25f

        if (alerts.isEmpty()) {
            canvas.drawText("Bu oturumda uyarı kaydedilmedi.", MARGIN, y, bodyPaint)
        } else {
            // Table header
            val colWidths = floatArrayOf(130f, 80f, 100f, 200f)
            val headers = arrayOf("Zaman", "Seviye", "Tip", "Detay")
            var x = MARGIN
            for (i in headers.indices) {
                canvas.drawText(headers[i], x + 4f, y, Paint(bodyPaint).apply {
                    typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
                })
                canvas.drawRect(x, y - 14f, x + colWidths[i], y + 4f, tableBorderPaint)
                x += colWidths[i]
            }
            y += 20f

            // Table rows
            for (alert in alerts.take(15)) {
                x = MARGIN
                val timeStr = dateFormat.format(Date(alert.timestampMs))
                val values = arrayOf(timeStr, alert.level, alert.type, alert.details)
                for (i in values.indices) {
                    val text = values[i].take(30)
                    canvas.drawText(text, x + 4f, y, smallPaint)
                    canvas.drawRect(x, y - 12f, x + colWidths[i], y + 4f, tableBorderPaint)
                    x += colWidths[i]
                }
                y += 18f
                if (y > PAGE_HEIGHT - 60f) break
            }
        }

        // Footer
        canvas.drawText("Sayfa 3/3", PAGE_WIDTH / 2f - 20f, PAGE_HEIGHT - 20f, smallPaint)
    }

    // ─── Helper Methods ────────────────────────────────────────────────────

    private fun drawInfoRow(canvas: Canvas, label: String, value: String, y: Float) {
        canvas.drawText(label, MARGIN, y, bodyPaint)
        canvas.drawText(value, MARGIN + 120f, y, Paint(bodyPaint).apply {
            typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        })
    }

    private fun drawMetricBox(canvas: Canvas, x: Float, y: Float, label: String, value: String, color: Int) {
        val boxPaint = Paint().apply {
            this.color = Color.argb(20, Color.red(color), Color.green(color), Color.blue(color))
        }
        val borderPaint = Paint().apply {
            this.color = color
            style = Paint.Style.STROKE
            strokeWidth = 2f
        }
        val rectF = RectF(x, y, x + 150f, y + 80f)
        canvas.drawRoundRect(rectF, 8f, 8f, boxPaint)
        canvas.drawRoundRect(rectF, 8f, 8f, borderPaint)

        val valuePaint = Paint().apply {
            this.color = color
            textSize = 28f
            typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
            textAlign = Paint.Align.CENTER
            isAntiAlias = true
        }
        canvas.drawText(value, x + 75f, y + 40f, valuePaint)

        val labelPaint = Paint(smallPaint).apply { textAlign = Paint.Align.CENTER }
        canvas.drawText(label, x + 75f, y + 65f, labelPaint)
    }

    private fun readLeadIIFromBinary(binFile: File, maxSamples: Int): FloatArray {
        val result = mutableListOf<Float>()
        val stream = binFile.inputStream().buffered()
        stream.skip(32) // skip header

        val recordBuf = ByteArray(18)
        val byteBuffer = ByteBuffer.wrap(recordBuf).order(ByteOrder.LITTLE_ENDIAN)

        while (result.size < maxSamples) {
            val bytesRead = stream.read(recordBuf)
            if (bytesRead < 18) break

            byteBuffer.clear()
            byteBuffer.getLong()  // timestamp
            val channel = byteBuffer.short.toInt()
            byteBuffer.getInt()   // rawAdc
            val voltageUv = byteBuffer.float

            if (channel == 1) {  // Lead II
                result.add(voltageUv)
            }
        }
        stream.close()
        return result.toFloatArray()
    }

    private fun savePdf(document: PdfDocument, fileName: String): Uri? {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val values = ContentValues().apply {
                put(MediaStore.Downloads.DISPLAY_NAME, fileName)
                put(MediaStore.Downloads.MIME_TYPE, "application/pdf")
                put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/HayatinRitmi")
                put(MediaStore.Downloads.IS_PENDING, 1)
            }
            val uri = context.contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
            uri?.let {
                context.contentResolver.openOutputStream(it)?.use { os ->
                    document.writeTo(os)
                }
                val updateValues = ContentValues().apply {
                    put(MediaStore.Downloads.IS_PENDING, 0)
                }
                context.contentResolver.update(it, updateValues, null, null)
            }
            uri
        } else {
            @Suppress("DEPRECATION")
            val dir = File(
                Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS),
                "HayatinRitmi"
            )
            if (!dir.exists()) dir.mkdirs()
            val file = File(dir, fileName)
            FileOutputStream(file).use { document.writeTo(it) }
            FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
        }
    }

    fun createShareIntent(pdfUri: Uri): Intent {
        return Intent(Intent.ACTION_SEND).apply {
            type = "application/pdf"
            putExtra(Intent.EXTRA_STREAM, pdfUri)
            putExtra(Intent.EXTRA_SUBJECT, "Hayatın Ritmi — EKG Raporu")
            putExtra(Intent.EXTRA_TEXT, "Hayatın Ritmi uygulamasından oluşturulan EKG analiz raporu ektedir.")
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
    }
}
