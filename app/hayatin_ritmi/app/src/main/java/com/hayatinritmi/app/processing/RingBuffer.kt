package com.hayatinritmi.app.processing

import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

class RingBuffer(private val capacity: Int) {
    private val buffer = FloatArray(capacity)
    private var head = 0
    private var count = 0
    private val lock = ReentrantLock()

    fun add(value: Float) = lock.withLock {
        buffer[head] = value
        head = (head + 1) % capacity
        if (count < capacity) count++
    }

    fun getLastN(n: Int): FloatArray = lock.withLock {
        val actualN = n.coerceAtMost(count)
        val result = FloatArray(actualN)
        for (i in 0 until actualN) {
            val index = (head - actualN + i + capacity) % capacity
            result[i] = buffer[index]
        }
        return result
    }

    fun getAll(): FloatArray = getLastN(count)

    fun size(): Int = lock.withLock { count }

    fun clear() = lock.withLock {
        head = 0
        count = 0
    }
}
