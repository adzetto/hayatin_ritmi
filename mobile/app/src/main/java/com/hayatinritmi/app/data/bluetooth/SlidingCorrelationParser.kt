package com.hayatinritmi.app.data.bluetooth

import com.hayatinritmi.app.domain.model.EcgSample
import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Gelişmiş EKG Paket Ayrıştırıcı — Kayan Korelasyon ile Senkronizasyon
 *
 * Problem: BLE MTU sınırları veya paket fragmentasyonu nedeniyle
 * gelen veri akışı doğrudan 43-byte sınırlarına hizalanmayabilir.
 *
 * Çözüm: Kayan Pencere Korelasyonu
 *   1. Gelen byte'lar dahili tampona eklenir
 *   2. 0xAA header aranır (sliding window)
 *   3. Checksum doğrulanır
 *   4. Geçerli frame çıkarılır, kalan byte'lar bir sonraki çağrıya taşınır
 *
 * İstatistikler: Toplam alınan frame, geçersiz frame, checksum hatasi sayısı.
 */
class SlidingCorrelationParser {

    companion object {
        private const val MAX_BUFFER_SIZE = 1024 // Taşma koruması
    }

    private val buffer = ByteArray(MAX_BUFFER_SIZE)
    private var bufferLen = 0

    // ─── İstatistikler ──────────────────────────────────────────────────
    @Volatile var validFrames: Long = 0; private set
    @Volatile var invalidFrames: Long = 0; private set
    @Volatile var checksumErrors: Long = 0; private set
    @Volatile var alignmentCorrections: Long = 0; private set

    /**
     * Gelen ham BLE byte'larını al, geçerli EKG frame'leri çıkar.
     * Bir BLE notification birden fazla frame (veya kısmi frame) içerebilir.
     *
     * @param incoming Raw bytes from BLE characteristic notification
     * @return List of parsed sample groups (each group = 12 samples from one frame)
     */
    fun feed(incoming: ByteArray): List<List<EcgSample>> {
        val results = mutableListOf<List<EcgSample>>()

        // Tampona ekle (taşma koruması)
        val freeSpace = MAX_BUFFER_SIZE - bufferLen
        val copyLen = incoming.size.coerceAtMost(freeSpace)
        System.arraycopy(incoming, 0, buffer, bufferLen, copyLen)
        bufferLen += copyLen

        // Kayan pencere ile frame arama
        var searchPos = 0
        while (searchPos + BleConstants.PACKET_SIZE <= bufferLen) {
            // 0xAA header ara
            if (buffer[searchPos] != BleConstants.PACKET_HEADER) {
                searchPos++
                alignmentCorrections++
                continue
            }

            // Checksum doğrula (XOR bytes 0..41)
            var xor: Byte = 0
            for (i in 0 until 42) {
                xor = (xor.toInt() xor buffer[searchPos + i].toInt()).toByte()
            }
            if (xor != buffer[searchPos + 42]) {
                checksumErrors++
                invalidFrames++
                searchPos++ // Yanlış hizalama — bir byte ilerle ve tekrar dene
                continue
            }

            // Geçerli frame bulundu — parse et
            val frame = ByteArray(BleConstants.PACKET_SIZE)
            System.arraycopy(buffer, searchPos, frame, 0, BleConstants.PACKET_SIZE)

            val samples = parseFrame(frame)
            if (samples != null) {
                results.add(samples)
                validFrames++
            }

            searchPos += BleConstants.PACKET_SIZE
        }

        // Kalan byte'ları tampona başa taşı
        if (searchPos > 0 && searchPos < bufferLen) {
            System.arraycopy(buffer, searchPos, buffer, 0, bufferLen - searchPos)
            bufferLen -= searchPos
        } else if (searchPos >= bufferLen) {
            bufferLen = 0
        }

        return results
    }

    private fun parseFrame(frame: ByteArray): List<EcgSample>? {
        // Timestamp: bytes 2-5, little-endian uint32
        val timestamp = ByteBuffer.wrap(frame, 2, 4)
            .order(ByteOrder.LITTLE_ENDIAN)
            .int
            .toLong() and 0xFFFFFFFFL

        // Frame sequence: byte 1
        // val frameSeq = frame[1].toInt() and 0xFF

        val samples = ArrayList<EcgSample>(BleConstants.CHANNEL_COUNT)
        for (ch in 0 until BleConstants.CHANNEL_COUNT) {
            val offset = 6 + ch * BleConstants.BYTES_PER_LEAD
            val b0 = frame[offset].toInt() and 0xFF
            val b1 = frame[offset + 1].toInt() and 0xFF
            val b2 = frame[offset + 2].toInt() and 0xFF
            var rawAdc = (b0 shl 16) or (b1 shl 8) or b2
            // Sign extend 24-bit → 32-bit
            if (rawAdc and 0x800000 != 0) rawAdc = rawAdc or (0xFF shl 24)
            samples.add(EcgSample.fromRawAdc(timestamp, ch, rawAdc))
        }
        return samples
    }

    /**
     * Paket kayıp oranı (0.0 = kayıp yok, 1.0 = tamamı kayıp)
     */
    fun getLossRate(): Float {
        val total = validFrames + invalidFrames
        return if (total > 0) invalidFrames.toFloat() / total else 0f
    }

    /**
     * Hizalama düzeltme oranı — yüksek değer kötü BLE kalitesini gösterir
     */
    fun getAlignmentRate(): Float {
        val total = validFrames * BleConstants.PACKET_SIZE + alignmentCorrections
        return if (total > 0) alignmentCorrections.toFloat() / total else 0f
    }

    fun reset() {
        bufferLen = 0
        validFrames = 0
        invalidFrames = 0
        checksumErrors = 0
        alignmentCorrections = 0
    }
}
