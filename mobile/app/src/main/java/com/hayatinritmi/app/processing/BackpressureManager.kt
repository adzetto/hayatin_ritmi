package com.hayatinritmi.app.processing

import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicLong

/**
 * Tampon Backpressure Yöneticisi
 *
 * Ring buffer doluluk oranı (ρ) izler:
 *   ρ < 0.6  → NORMAL — tam hız iletim
 *   ρ ∈ [0.6, 0.8) → THROTTLE — her 2. sample atlanır
 *   ρ ≥ 0.8  → DROP — yalnızca Lead II (kanal 1) iletilir
 *
 * Enerji farkındalığı:
 *   - Düşük batarya (<20%) → BLE bağlantı aralığı artırılır
 *   - Çok düşük (<10%) → yalnızca kritik alert pipeline aktif
 *
 * Thread-safe: tüm alanlar atomic veya volatile.
 */
class BackpressureManager(
    private val bufferCapacity: Int = 2500
) {
    // ─── Backpressure State ─────────────────────────────────────────────
    enum class PressureLevel { NORMAL, THROTTLE, DROP }

    private val sampleCount = AtomicInteger(0)
    private val droppedCount = AtomicLong(0)
    private val processedCount = AtomicLong(0)

    @Volatile
    var currentLevel: PressureLevel = PressureLevel.NORMAL
        private set

    @Volatile
    var fillRatio: Float = 0f
        private set

    // ─── Energy State ───────────────────────────────────────────────────
    enum class EnergyMode { FULL, LOW_POWER, CRITICAL }

    @Volatile
    var energyMode: EnergyMode = EnergyMode.FULL
        private set

    @Volatile
    var batteryPercent: Int = 100
        private set

    /**
     * Her gelen sample için çağrılır. true dönerse sample işlenmeli,
     * false dönerse atlanmalı (backpressure drop).
     */
    fun shouldProcess(channel: Int, currentBufferSize: Int): Boolean {
        sampleCount.incrementAndGet()
        fillRatio = currentBufferSize.toFloat() / bufferCapacity

        currentLevel = when {
            fillRatio >= 0.8f -> PressureLevel.DROP
            fillRatio >= 0.6f -> PressureLevel.THROTTLE
            else -> PressureLevel.NORMAL
        }

        val shouldProcess = when (currentLevel) {
            PressureLevel.NORMAL -> true
            PressureLevel.THROTTLE -> {
                // Her 2. sample'ı atla
                sampleCount.get() % 2 == 0
            }
            PressureLevel.DROP -> {
                // Yalnızca Lead II (kanal 1) + her 4. sample
                channel == 1 && sampleCount.get() % 4 == 0
            }
        }

        if (shouldProcess) {
            processedCount.incrementAndGet()
        } else {
            droppedCount.incrementAndGet()
        }

        // Energy mode'u da backpressure'a entegre et
        if (energyMode == EnergyMode.CRITICAL && channel != 1) {
            droppedCount.incrementAndGet()
            return false // Kritik modda sadece Lead II
        }

        return shouldProcess
    }

    /**
     * Batarya durumunu güncelle → enerji modunu ayarla.
     */
    fun updateBattery(percent: Int) {
        batteryPercent = percent
        energyMode = when {
            percent < 10 -> EnergyMode.CRITICAL
            percent < 20 -> EnergyMode.LOW_POWER
            else -> EnergyMode.FULL
        }
    }

    /**
     * BLE bağlantı aralığı önerisi (ms).
     * LOW_POWER modda 15ms → 30ms çıkararak enerji tasarrufu sağlar.
     */
    fun suggestedConnectionIntervalMs(): Int = when (energyMode) {
        EnergyMode.FULL -> 15
        EnergyMode.LOW_POWER -> 30
        EnergyMode.CRITICAL -> 50
    }

    /**
     * Önerilen sample rate çarpanı.
     * 1.0 = tam hız, 0.5 = yarı hız, 0.25 = çeyrek hız.
     */
    fun effectiveSampleRateMultiplier(): Float = when {
        energyMode == EnergyMode.CRITICAL -> 0.25f
        currentLevel == PressureLevel.DROP -> 0.25f
        currentLevel == PressureLevel.THROTTLE -> 0.5f
        energyMode == EnergyMode.LOW_POWER -> 0.75f
        else -> 1.0f
    }

    // ─── Metrics ────────────────────────────────────────────────────────
    fun getDropRate(): Float {
        val total = processedCount.get() + droppedCount.get()
        return if (total > 0) droppedCount.get().toFloat() / total else 0f
    }

    fun getTotalDropped(): Long = droppedCount.get()
    fun getTotalProcessed(): Long = processedCount.get()

    fun reset() {
        sampleCount.set(0)
        droppedCount.set(0)
        processedCount.set(0)
        currentLevel = PressureLevel.NORMAL
        fillRatio = 0f
        energyMode = EnergyMode.FULL
        batteryPercent = 100
    }
}
