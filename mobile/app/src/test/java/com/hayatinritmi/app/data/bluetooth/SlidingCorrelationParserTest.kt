package com.hayatinritmi.app.data.bluetooth

import com.hayatinritmi.app.domain.model.EcgSample
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import java.nio.ByteBuffer
import java.nio.ByteOrder

class SlidingCorrelationParserTest {

    private lateinit var parser: SlidingCorrelationParser

    @Before
    fun setup() {
        parser = SlidingCorrelationParser()
    }

    @Test
    fun `parses valid 43-byte frame`() {
        val frame = buildValidFrame(frameSeq = 1, timestampMs = 1000L)
        val results = parser.feed(frame)

        assertEquals(1, results.size)
        assertEquals(12, results[0].size) // 12 leads
        assertEquals(1L, parser.validFrames)
        assertEquals(0L, parser.invalidFrames)
    }

    @Test
    fun `parses multiple frames in single feed`() {
        val frame1 = buildValidFrame(1, 1000L)
        val frame2 = buildValidFrame(2, 1004L)
        val combined = frame1 + frame2

        val results = parser.feed(combined)
        assertEquals(2, results.size)
        assertEquals(2L, parser.validFrames)
    }

    @Test
    fun `handles fragmented frames across feeds`() {
        val frame = buildValidFrame(1, 1000L)
        val part1 = frame.copyOfRange(0, 20)
        val part2 = frame.copyOfRange(20, 43)

        // First feed — incomplete frame, no results
        val r1 = parser.feed(part1)
        assertEquals(0, r1.size)

        // Second feed — completes the frame
        val r2 = parser.feed(part2)
        assertEquals(1, r2.size)
        assertEquals(12, r2[0].size)
    }

    @Test
    fun `skips garbage bytes before valid frame`() {
        val garbage = byteArrayOf(0x01, 0x02, 0x03, 0x04, 0x05)
        val frame = buildValidFrame(1, 1000L)
        val data = garbage + frame

        val results = parser.feed(data)
        assertEquals(1, results.size)
        assertEquals(5L, parser.alignmentCorrections) // 5 garbage bytes skipped
    }

    @Test
    fun `detects checksum errors`() {
        val frame = buildValidFrame(1, 1000L)
        // Corrupt the checksum
        frame[42] = (frame[42].toInt() xor 0xFF).toByte()

        val results = parser.feed(frame)
        assertEquals(0, results.size)
        assertEquals(1L, parser.checksumErrors)
    }

    @Test
    fun `handles empty input`() {
        val results = parser.feed(byteArrayOf())
        assertEquals(0, results.size)
    }

    @Test
    fun `loss rate calculation`() {
        // Process one valid, one invalid
        val validFrame = buildValidFrame(1, 1000L)
        parser.feed(validFrame)

        val invalidFrame = buildValidFrame(2, 2000L)
        invalidFrame[42] = (invalidFrame[42].toInt() xor 0xFF).toByte()
        parser.feed(invalidFrame)

        val lossRate = parser.getLossRate()
        assertEquals(0.5f, lossRate, 0.01f)
    }

    @Test
    fun `reset clears all state`() {
        parser.feed(buildValidFrame(1, 1000L))
        parser.reset()

        assertEquals(0L, parser.validFrames)
        assertEquals(0L, parser.invalidFrames)
        assertEquals(0L, parser.checksumErrors)
        assertEquals(0L, parser.alignmentCorrections)
    }

    @Test
    fun `parsed samples have correct Lead II channel`() {
        val frame = buildValidFrame(1, 1000L, leadIIValue = 500)
        val results = parser.feed(frame)

        assertEquals(1, results.size)
        val leadIISample = results[0][BleConstants.LEAD_II]
        assertEquals(1, leadIISample.channel)
        assertTrue(leadIISample.voltageUv != 0f)
    }

    // ─── Helper ─────────────────────────────────────────────────────────

    private fun buildValidFrame(
        frameSeq: Int,
        timestampMs: Long,
        leadIIValue: Int = 100000
    ): ByteArray {
        val frame = ByteArray(BleConstants.PACKET_SIZE)
        frame[0] = BleConstants.PACKET_HEADER
        frame[1] = frameSeq.toByte()

        val tsBytes = ByteBuffer.allocate(4)
            .order(ByteOrder.LITTLE_ENDIAN)
            .putInt(timestampMs.toInt())
            .array()
        System.arraycopy(tsBytes, 0, frame, 2, 4)

        for (ch in 0 until BleConstants.CHANNEL_COUNT) {
            val offset = 6 + ch * BleConstants.BYTES_PER_LEAD
            val value = if (ch == BleConstants.LEAD_II) leadIIValue else 50000
            frame[offset]     = ((value shr 16) and 0xFF).toByte()
            frame[offset + 1] = ((value shr 8) and 0xFF).toByte()
            frame[offset + 2] = (value and 0xFF).toByte()
        }

        // Checksum: XOR of bytes 0..41
        var xor: Byte = 0
        for (i in 0 until 42) {
            xor = (xor.toInt() xor frame[i].toInt()).toByte()
        }
        frame[42] = xor

        return frame
    }
}
