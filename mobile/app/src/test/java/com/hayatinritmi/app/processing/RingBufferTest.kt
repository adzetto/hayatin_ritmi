package com.hayatinritmi.app.processing

import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors

class RingBufferTest {

    private lateinit var buffer: RingBuffer

    @Before
    fun setup() {
        buffer = RingBuffer(10)
    }

    @Test
    fun `empty buffer returns empty array`() {
        assertEquals(0, buffer.size())
        assertEquals(0, buffer.getAll().size)
        assertEquals(0, buffer.getLastN(5).size)
    }

    @Test
    fun `add and retrieve single element`() {
        buffer.add(42f)
        assertEquals(1, buffer.size())
        assertArrayEquals(floatArrayOf(42f), buffer.getAll(), 0.001f)
    }

    @Test
    fun `getLastN returns correct subset`() {
        for (i in 1..5) buffer.add(i.toFloat())
        val last3 = buffer.getLastN(3)
        assertArrayEquals(floatArrayOf(3f, 4f, 5f), last3, 0.001f)
    }

    @Test
    fun `overflow wraps correctly`() {
        for (i in 1..15) buffer.add(i.toFloat())
        assertEquals(10, buffer.size())
        val all = buffer.getAll()
        assertArrayEquals(floatArrayOf(6f, 7f, 8f, 9f, 10f, 11f, 12f, 13f, 14f, 15f), all, 0.001f)
    }

    @Test
    fun `getLastN with n greater than size returns all`() {
        for (i in 1..3) buffer.add(i.toFloat())
        val result = buffer.getLastN(100)
        assertEquals(3, result.size)
    }

    @Test
    fun `clear resets buffer`() {
        for (i in 1..5) buffer.add(i.toFloat())
        buffer.clear()
        assertEquals(0, buffer.size())
        assertEquals(0, buffer.getAll().size)
    }

    @Test
    fun `thread safety - concurrent add and read`() {
        val bigBuffer = RingBuffer(2500)
        val executor = Executors.newFixedThreadPool(4)
        val latch = CountDownLatch(4)

        repeat(2) {
            executor.submit {
                for (i in 0 until 5000) bigBuffer.add(i.toFloat())
                latch.countDown()
            }
        }
        repeat(2) {
            executor.submit {
                for (i in 0 until 5000) bigBuffer.getLastN(100)
                latch.countDown()
            }
        }
        latch.await()
        assertTrue("Buffer size should be <= capacity", bigBuffer.size() <= 2500)
        executor.shutdown()
    }
}
