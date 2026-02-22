package com.hayatinritmi.app.data

import com.hayatinritmi.app.data.model.EcgSample
import java.nio.ByteBuffer
import java.nio.ByteOrder

object EcgPacketParser {
    /**
     * Parse 10-byte BLE packet:
     * [Header:1B=0xAA][Channel:1B][Timestamp:4B uint32][ECG:3B int24][Checksum:1B XOR]
     */
    fun parse(data: ByteArray): EcgSample? {
        if (data.size < BleConstants.PACKET_SIZE) return null
        if (data[0] != BleConstants.PACKET_HEADER) return null

        // Verify checksum (XOR of bytes 0..8)
        var xor: Byte = 0
        for (i in 0 until 9) {
            xor = (xor.toInt() xor data[i].toInt()).toByte()
        }
        if (xor != data[9]) return null

        val channel = data[1].toInt() and 0xFF

        // Timestamp: bytes 2-5, little-endian uint32
        val timestamp = ByteBuffer.wrap(data, 2, 4)
            .order(ByteOrder.LITTLE_ENDIAN)
            .int
            .toLong() and 0xFFFFFFFFL

        // ECG: bytes 6-8, 24-bit signed integer (big-endian)
        val b0 = data[6].toInt() and 0xFF
        val b1 = data[7].toInt() and 0xFF
        val b2 = data[8].toInt() and 0xFF
        var rawAdc = (b0 shl 16) or (b1 shl 8) or b2
        // Sign extend 24-bit to 32-bit
        if (rawAdc and 0x800000 != 0) {
            rawAdc = rawAdc or (0xFF shl 24)
        }

        return EcgSample.fromRawAdc(timestamp, channel, rawAdc)
    }
}
