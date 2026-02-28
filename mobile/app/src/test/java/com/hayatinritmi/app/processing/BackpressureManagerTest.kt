package com.hayatinritmi.app.processing

import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

class BackpressureManagerTest {

    private lateinit var manager: BackpressureManager

    @Before
    fun setup() {
        manager = BackpressureManager(bufferCapacity = 100)
    }

    @Test
    fun `NORMAL level when buffer is below 60 percent`() {
        val result = manager.shouldProcess(channel = 1, currentBufferSize = 50)
        assertTrue(result)
        assertEquals(BackpressureManager.PressureLevel.NORMAL, manager.currentLevel)
        assertEquals(0.5f, manager.fillRatio, 0.01f)
    }

    @Test
    fun `THROTTLE level when buffer is between 60 and 80 percent`() {
        // First call (odd) — dropped in THROTTLE
        val r1 = manager.shouldProcess(channel = 1, currentBufferSize = 70)
        // Second call (even) — processed in THROTTLE
        val r2 = manager.shouldProcess(channel = 1, currentBufferSize = 70)

        assertEquals(BackpressureManager.PressureLevel.THROTTLE, manager.currentLevel)
        // One should be true, one should be false
        assertNotEquals(r1, r2)
    }

    @Test
    fun `DROP level when buffer is above 80 percent`() {
        // Non-Lead-II channel should be dropped
        val r1 = manager.shouldProcess(channel = 0, currentBufferSize = 85)
        assertFalse(r1)
        assertEquals(BackpressureManager.PressureLevel.DROP, manager.currentLevel)
    }

    @Test
    fun `DROP level passes Lead II at correct interval`() {
        // Process 4 Lead-II samples at >80% fill
        var passCount = 0
        for (i in 1..8) {
            if (manager.shouldProcess(channel = 1, currentBufferSize = 90)) {
                passCount++
            }
        }
        // Should pass ~2 out of 8 (every 4th)
        assertTrue(passCount in 1..3)
    }

    @Test
    fun `battery update changes energy mode`() {
        manager.updateBattery(100)
        assertEquals(BackpressureManager.EnergyMode.FULL, manager.energyMode)

        manager.updateBattery(15)
        assertEquals(BackpressureManager.EnergyMode.LOW_POWER, manager.energyMode)

        manager.updateBattery(5)
        assertEquals(BackpressureManager.EnergyMode.CRITICAL, manager.energyMode)
    }

    @Test
    fun `CRITICAL energy mode drops non Lead II channels`() {
        manager.updateBattery(5)
        val r = manager.shouldProcess(channel = 3, currentBufferSize = 10)
        assertFalse(r)
    }

    @Test
    fun `suggested connection interval increases with low power`() {
        manager.updateBattery(100)
        assertEquals(15, manager.suggestedConnectionIntervalMs())

        manager.updateBattery(15)
        assertEquals(30, manager.suggestedConnectionIntervalMs())

        manager.updateBattery(5)
        assertEquals(50, manager.suggestedConnectionIntervalMs())
    }

    @Test
    fun `effective sample rate multiplier changes with pressure`() {
        // NORMAL
        manager.shouldProcess(1, 10)
        assertEquals(1.0f, manager.effectiveSampleRateMultiplier(), 0.01f)

        // LOW_POWER
        manager.updateBattery(15)
        assertEquals(0.75f, manager.effectiveSampleRateMultiplier(), 0.01f)

        // CRITICAL
        manager.updateBattery(5)
        assertEquals(0.25f, manager.effectiveSampleRateMultiplier(), 0.01f)
    }

    @Test
    fun `drop rate is calculated correctly`() {
        // Process some, drop some
        manager.shouldProcess(1, 10) // NORMAL → processed
        manager.shouldProcess(1, 10) // NORMAL → processed
        manager.updateBattery(5)
        manager.shouldProcess(3, 10) // CRITICAL, non-Lead-II → dropped

        val dropRate = manager.getDropRate()
        assertTrue(dropRate > 0f)
        assertTrue(dropRate < 1f)
    }

    @Test
    fun `reset clears all state`() {
        manager.shouldProcess(1, 90) // DROP level
        manager.updateBattery(5)
        manager.reset()

        assertEquals(BackpressureManager.PressureLevel.NORMAL, manager.currentLevel)
        assertEquals(BackpressureManager.EnergyMode.FULL, manager.energyMode)
        assertEquals(0f, manager.fillRatio, 0.01f)
        assertEquals(100, manager.batteryPercent)
        assertEquals(0L, manager.getTotalProcessed())
        assertEquals(0L, manager.getTotalDropped())
    }
}
