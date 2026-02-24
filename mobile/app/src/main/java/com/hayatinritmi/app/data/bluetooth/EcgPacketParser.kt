package com.hayatinritmi.app.data.bluetooth

import com.hayatinritmi.app.domain.model.EcgSample
import java.nio.ByteBuffer
import java.nio.ByteOrder

object EcgPacketParser {
    /**
     * Parse 43-byte 12-lead BLE frame:
     * [Header:1B=0xAA][FrameSeq:1B][Timestamp:4B uint32_ms]
     * [Lead_I:3B][Lead_II:3B][Lead_III:3B][aVR:3B][aVL:3B][aVF:3B]
     * [V1:3B][V2:3B][V3:3B][V4:3B][V5:3B][V6:3B][Checksum:1B XOR]
     * Total: 43 bytes → 12 EcgSample objects emitted per frame
     */
    fun parse(data: ByteArray): List<EcgSample>? {
        if (data.size < BleConstants.PACKET_SIZE) return null
        if (data[0] != BleConstants.PACKET_HEADER) return null

        // Verify checksum (XOR of bytes 0..41)
        var xor: Byte = 0
        for (i in 0 until 42) {
            xor = (xor.toInt() xor data[i].toInt()).toByte()
        }
        if (xor != data[42]) return null

        // Timestamp: bytes 2-5, little-endian uint32
        val timestamp = ByteBuffer.wrap(data, 2, 4)
            .order(ByteOrder.LITTLE_ENDIAN)
            .int
            .toLong() and 0xFFFFFFFFL

        val samples = ArrayList<EcgSample>(BleConstants.CHANNEL_COUNT)
        for (ch in 0 until BleConstants.CHANNEL_COUNT) {
            val offset = 6 + ch * BleConstants.BYTES_PER_LEAD
            val b0 = data[offset].toInt() and 0xFF
            val b1 = data[offset + 1].toInt() and 0xFF
            val b2 = data[offset + 2].toInt() and 0xFF
            var rawAdc = (b0 shl 16) or (b1 shl 8) or b2
            // Sign extend 24-bit → 32-bit
            if (rawAdc and 0x800000 != 0) rawAdc = rawAdc or (0xFF shl 24)
            samples.add(EcgSample.fromRawAdc(timestamp, ch, rawAdc))
        }
        return samples
    }
}
