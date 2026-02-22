# Phase 2: BLE & ECG Data Pipeline — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the complete Bluetooth Low Energy connectivity, ECG data processing pipeline, and live visualization for the Hayatın Ritmi wearable ECG monitoring app.

**Architecture:** Repository pattern with mock/real BLE abstraction. ViewModels for state management. Manual constructor injection. Mock-first approach — all subsystems work with simulated ECG data before real hardware integration.

**Tech Stack:** Kotlin 2.0.21, Jetpack Compose + Material 3, Kotlin Coroutines + Flow, Android BLE API, DataStore Preferences, Canvas API

**Design Doc:** `docs/plans/2026-02-22-phase2-ble-ecg-design.md`

**Base Path:** `app/hayatin_ritmi/app/src/main/java/com/hayatinritmi/app/`

---

## Task 1: Build Configuration & Permissions Setup

**Files:**
- Modify: `app/hayatin_ritmi/gradle/libs.versions.toml`
- Modify: `app/hayatin_ritmi/app/build.gradle.kts`
- Modify: `app/hayatin_ritmi/app/src/main/AndroidManifest.xml`

**Step 1: Add new dependency versions to libs.versions.toml**

Add after `navigation = "2.8.4"`:
```toml
datastorePreferences = "1.1.1"
lifecycleViewmodelCompose = "2.8.7"
```

Add to `[libraries]` section:
```toml
androidx-datastore-preferences = { group = "androidx.datastore", name = "datastore-preferences", version.ref = "datastorePreferences" }
androidx-lifecycle-viewmodel-compose = { group = "androidx.lifecycle", name = "lifecycle-viewmodel-compose", version.ref = "lifecycleViewmodelCompose" }
```

**Step 2: Add dependencies to app/build.gradle.kts**

Add to `dependencies` block:
```kotlin
// BLE & Lifecycle
implementation(libs.androidx.lifecycle.viewmodel.compose)

// DataStore
implementation(libs.androidx.datastore.preferences)
```

**Step 3: Add BLE permissions to AndroidManifest.xml**

Add before `<application>` tag:
```xml
<!-- BLE Hardware Feature -->
<uses-feature android:name="android.hardware.bluetooth_le" android:required="true" />

<!-- BLE Permissions (Android 12+ / API 31+) -->
<uses-permission android:name="android.permission.BLUETOOTH_SCAN"
    android:usesPermissionFlags="neverForLocation" />
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />

<!-- BLE Permissions (Android 11 and below) -->
<uses-permission android:name="android.permission.BLUETOOTH"
    android:maxSdkVersion="30" />
<uses-permission android:name="android.permission.BLUETOOTH_ADMIN"
    android:maxSdkVersion="30" />
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"
    android:maxSdkVersion="30" />

<!-- Foreground Service -->
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_CONNECTED_DEVICE" />
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
```

Add `EcgForegroundService` inside `<application>` tag:
```xml
<service
    android:name=".service.EcgForegroundService"
    android:foregroundServiceType="connectedDevice"
    android:exported="false" />
```

**Step 4: Verify build compiles**

Run: `cd app/hayatin_ritmi && ./gradlew assembleDebug`
Expected: BUILD SUCCESSFUL

---

## Task 2: Data Models & Constants

**Files:**
- Create: `{base}/data/model/EcgSample.kt`
- Create: `{base}/data/model/DeviceStatus.kt`
- Create: `{base}/data/model/ScannedDevice.kt`
- Create: `{base}/data/model/ConnectionState.kt`
- Create: `{base}/data/model/HrvMetrics.kt`
- Create: `{base}/data/BleConstants.kt`

**Step 1: Create EcgSample.kt**

```kotlin
package com.hayatinritmi.app.data.model

data class EcgSample(
    val timestamp: Long,      // milliseconds
    val channel: Int,         // 0 = Lead I
    val rawAdc: Int,          // 24-bit signed ADC value
    val voltageUv: Float      // microvolts (µV)
) {
    companion object {
        // ADS1293 parameters
        const val VREF = 2.4f         // Reference voltage
        const val GAIN = 6f           // Default gain
        const val ADC_MAX = 8388608f  // 2^23

        fun fromRawAdc(timestamp: Long, channel: Int, rawAdc: Int): EcgSample {
            val voltageUv = (rawAdc * VREF) / (ADC_MAX * GAIN) * 1_000_000f
            return EcgSample(timestamp, channel, rawAdc, voltageUv)
        }
    }
}
```

**Step 2: Create DeviceStatus.kt**

```kotlin
package com.hayatinritmi.app.data.model

data class DeviceStatus(
    val batteryPercent: Int,
    val isElectrodeConnected: Boolean,
    val isCharging: Boolean,
    val signalQuality: Int
) {
    companion object {
        fun fromByte(statusByte: Int, batteryByte: Int): DeviceStatus {
            return DeviceStatus(
                batteryPercent = batteryByte.coerceIn(0, 100),
                isElectrodeConnected = (statusByte and 0x01) != 0,
                isCharging = (statusByte and 0x02) != 0,
                signalQuality = if ((statusByte and 0x01) != 0) 100 else 0
            )
        }

        val DISCONNECTED = DeviceStatus(0, false, false, 0)
    }
}
```

**Step 3: Create ScannedDevice.kt**

```kotlin
package com.hayatinritmi.app.data.model

data class ScannedDevice(
    val name: String,
    val macAddress: String,
    val rssi: Int
)
```

**Step 4: Create ConnectionState.kt**

```kotlin
package com.hayatinritmi.app.data.model

enum class ConnectionState {
    DISCONNECTED,
    SCANNING,
    CONNECTING,
    CONNECTED
}
```

**Step 5: Create HrvMetrics.kt**

```kotlin
package com.hayatinritmi.app.data.model

data class HrvMetrics(
    val sdnn: Float = 0f,   // Standard deviation of R-R intervals (ms)
    val rmssd: Float = 0f   // Root mean square of successive differences (ms)
)
```

**Step 6: Create BleConstants.kt**

```kotlin
package com.hayatinritmi.app.data

import java.util.UUID

object BleConstants {
    // ESP32 BLE Service UUIDs
    val ECG_SERVICE_UUID: UUID = UUID.fromString("0000181d-0000-1000-8000-00805f9b34fb")
    val ECG_DATA_CHAR_UUID: UUID = UUID.fromString("00002a37-0000-1000-8000-00805f9b34fb")
    val BATTERY_CHAR_UUID: UUID = UUID.fromString("00002a19-0000-1000-8000-00805f9b34fb")
    val DEVICE_STATUS_CHAR_UUID: UUID = UUID.fromString("00002a38-0000-1000-8000-00805f9b34fb")
    val CCCD_UUID: UUID = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")

    // BLE Protocol
    const val PACKET_HEADER: Byte = 0xAA.toByte()
    const val PACKET_SIZE = 10
    const val SAMPLE_RATE_HZ = 250
    const val DEVICE_NAME_FILTER = "HayatinRitmi"
    const val SCAN_TIMEOUT_MS = 30_000L
    const val DEFAULT_MTU = 247
}
```

**Step 7: Verify build**

Run: `cd app/hayatin_ritmi && ./gradlew assembleDebug`
Expected: BUILD SUCCESSFUL

---

## Task 3: Signal Processing — RingBuffer

**Files:**
- Create: `{base}/processing/RingBuffer.kt`

**Step 1: Implement RingBuffer**

```kotlin
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
```

---

## Task 4: Signal Processing — EcgFilter

**Files:**
- Create: `{base}/processing/EcgFilter.kt`

**Step 1: Implement cascaded IIR filters**

```kotlin
package com.hayatinritmi.app.processing

import kotlin.math.PI
import kotlin.math.cos

class EcgFilter(
    private val sampleRateHz: Int = 250,
    private val notchFreqHz: Float = 50f
) {
    // HPF 0.5 Hz - Baseline wander removal
    private val hpfAlpha: Float = 1f / (1f + 2f * PI.toFloat() * 0.5f / sampleRateHz)
    private var hpfPrevX = 0f
    private var hpfPrevY = 0f

    // Notch filter 50Hz - Power line interference
    private val notchR = 0.985f // Controls bandwidth (Q≈30)
    private val notchW0 = 2f * PI.toFloat() * notchFreqHz / sampleRateHz
    private val notchA1 = -2f * cos(notchW0)
    private val notchA2 = 1f
    private val notchB1 = -2f * notchR * cos(notchW0)
    private val notchB2 = notchR * notchR
    private var notchX1 = 0f
    private var notchX2 = 0f
    private var notchY1 = 0f
    private var notchY2 = 0f

    // LPF 40 Hz - Muscle artifact reduction
    private val lpfAlpha: Float = (2f * PI.toFloat() * 40f / sampleRateHz).let { dt ->
        dt / (1f + dt)
    }
    private var lpfPrevY = 0f

    fun filter(sample: Float): Float {
        // Stage 1: High-pass filter (remove baseline wander)
        val hpfOut = hpfAlpha * (hpfPrevY + sample - hpfPrevX)
        hpfPrevX = sample
        hpfPrevY = hpfOut

        // Stage 2: Notch filter (remove 50/60 Hz)
        val notchOut = hpfOut + notchA1 * notchX1 + notchA2 * notchX2 - notchB1 * notchY1 - notchB2 * notchY2
        notchX2 = notchX1
        notchX1 = hpfOut
        notchY2 = notchY1
        notchY1 = notchOut

        // Stage 3: Low-pass filter (remove muscle artifacts)
        val lpfOut = lpfAlpha * notchOut + (1f - lpfAlpha) * lpfPrevY
        lpfPrevY = lpfOut

        return lpfOut
    }

    fun reset() {
        hpfPrevX = 0f; hpfPrevY = 0f
        notchX1 = 0f; notchX2 = 0f; notchY1 = 0f; notchY2 = 0f
        lpfPrevY = 0f
    }
}
```

---

## Task 5: Signal Processing — RPeakDetector

**Files:**
- Create: `{base}/processing/RPeakDetector.kt`

**Step 1: Implement Pan-Tompkins R-peak detection**

```kotlin
package com.hayatinritmi.app.processing

import com.hayatinritmi.app.data.model.HrvMetrics
import kotlin.math.sqrt

class RPeakDetector(private val sampleRateHz: Int = 250) {
    private val windowSize = (0.150 * sampleRateHz).toInt() // 150ms integration window
    private val refractoryPeriod = (0.200 * sampleRateHz).toInt() // 200ms min between peaks

    private val integrationBuffer = FloatArray(windowSize)
    private var integrationIndex = 0
    private var integrationSum = 0f

    private var prevSample = 0f
    private var threshold = 0f
    private var peakValue = 0f
    private var samplesSinceLastPeak = 0

    private val rrIntervals = mutableListOf<Float>() // in milliseconds
    private val maxRRHistory = 20

    var currentBpm: Int = 0
        private set
    var currentHrv: HrvMetrics = HrvMetrics()
        private set

    fun processSample(filteredSample: Float): Boolean {
        // Step 1: Derivative
        val derivative = filteredSample - prevSample
        prevSample = filteredSample

        // Step 2: Squaring
        val squared = derivative * derivative

        // Step 3: Moving window integration
        integrationSum -= integrationBuffer[integrationIndex]
        integrationBuffer[integrationIndex] = squared
        integrationSum += squared
        integrationIndex = (integrationIndex + 1) % windowSize
        val integrated = integrationSum / windowSize

        // Step 4: Adaptive threshold
        samplesSinceLastPeak++

        if (integrated > threshold && samplesSinceLastPeak > refractoryPeriod) {
            // R-peak detected
            val rrMs = samplesSinceLastPeak * 1000f / sampleRateHz

            // Sanity check: 30-200 BPM range (300-2000ms R-R)
            if (rrMs in 300f..2000f) {
                rrIntervals.add(rrMs)
                if (rrIntervals.size > maxRRHistory) {
                    rrIntervals.removeAt(0)
                }
                updateMetrics()
            }

            samplesSinceLastPeak = 0
            peakValue = integrated
            threshold = 0.5f * peakValue
            return true
        }

        // Slowly decay threshold
        threshold *= 0.998f

        return false
    }

    private fun updateMetrics() {
        if (rrIntervals.size < 3) return

        // BPM from mean R-R interval
        val meanRR = rrIntervals.average().toFloat()
        currentBpm = (60_000f / meanRR).toInt().coerceIn(30, 200)

        // SDNN
        val sdnn = rrIntervals.map { it - meanRR }.map { it * it }.average().let { sqrt(it) }.toFloat()

        // RMSSD
        val successiveDiffs = rrIntervals.zipWithNext { a, b -> (b - a) }
        val rmssd = successiveDiffs.map { it * it }.average().let { sqrt(it) }.toFloat()

        currentHrv = HrvMetrics(sdnn = sdnn, rmssd = rmssd)
    }

    fun reset() {
        prevSample = 0f
        threshold = 0f
        peakValue = 0f
        samplesSinceLastPeak = 0
        integrationBuffer.fill(0f)
        integrationIndex = 0
        integrationSum = 0f
        rrIntervals.clear()
        currentBpm = 0
        currentHrv = HrvMetrics()
    }
}
```

---

## Task 6: EcgPacketParser + Repository Interface

**Files:**
- Create: `{base}/data/EcgPacketParser.kt`
- Create: `{base}/data/EcgRepository.kt`

**Step 1: Implement binary packet parser**

```kotlin
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
```

**Step 2: Create EcgRepository interface**

```kotlin
package com.hayatinritmi.app.data

import com.hayatinritmi.app.data.model.DeviceStatus
import com.hayatinritmi.app.data.model.EcgSample
import kotlinx.coroutines.flow.Flow

interface EcgRepository {
    fun observeEcgSamples(): Flow<EcgSample>
    fun observeDeviceStatus(): Flow<DeviceStatus>
}
```

---

## Task 7: BLE Manager Interface + Mock Implementation

**Files:**
- Create: `{base}/ble/BleManager.kt`
- Create: `{base}/ble/MockBleManager.kt`

**Step 1: Create BleManager interface**

```kotlin
package com.hayatinritmi.app.ble

import com.hayatinritmi.app.data.model.ConnectionState
import com.hayatinritmi.app.data.model.DeviceStatus
import com.hayatinritmi.app.data.model.ScannedDevice
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.StateFlow

interface BleManager {
    val connectionState: StateFlow<ConnectionState>
    val scannedDevices: StateFlow<List<ScannedDevice>>
    fun startScan(timeoutMs: Long = 30_000L)
    fun stopScan()
    fun connect(device: ScannedDevice)
    fun disconnect()
    fun observeEcgData(): Flow<ByteArray>
    fun observeDeviceStatus(): Flow<DeviceStatus>
}
```

**Step 2: Create MockBleManager with realistic PQRST generator**

```kotlin
package com.hayatinritmi.app.ble

import com.hayatinritmi.app.data.BleConstants
import com.hayatinritmi.app.data.model.ConnectionState
import com.hayatinritmi.app.data.model.DeviceStatus
import com.hayatinritmi.app.data.model.ScannedDevice
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.*
import kotlin.random.Random

class MockBleManager : BleManager {
    private val scope = CoroutineScope(Dispatchers.Default + SupervisorJob())

    private val _connectionState = MutableStateFlow(ConnectionState.DISCONNECTED)
    override val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()

    private val _scannedDevices = MutableStateFlow<List<ScannedDevice>>(emptyList())
    override val scannedDevices: StateFlow<List<ScannedDevice>> = _scannedDevices.asStateFlow()

    private var scanJob: Job? = null
    private var dataJob: Job? = null

    override fun startScan(timeoutMs: Long) {
        _connectionState.value = ConnectionState.SCANNING
        _scannedDevices.value = emptyList()

        scanJob?.cancel()
        scanJob = scope.launch {
            // Simulate device discovery with delays
            delay(800)
            _scannedDevices.value = listOf(
                ScannedDevice("HayatinRitmi-T1", "AA:BB:CC:DD:EE:01", -45)
            )
            delay(1200)
            _scannedDevices.value = _scannedDevices.value + ScannedDevice("HayatinRitmi-T2", "AA:BB:CC:DD:EE:02", -68)

            // Auto-timeout
            delay(timeoutMs)
            if (_connectionState.value == ConnectionState.SCANNING) {
                _connectionState.value = ConnectionState.DISCONNECTED
            }
        }
    }

    override fun stopScan() {
        scanJob?.cancel()
        if (_connectionState.value == ConnectionState.SCANNING) {
            _connectionState.value = ConnectionState.DISCONNECTED
        }
    }

    override fun connect(device: ScannedDevice) {
        scanJob?.cancel()
        _connectionState.value = ConnectionState.CONNECTING
        scope.launch {
            delay(1500) // Simulate connection delay
            _connectionState.value = ConnectionState.CONNECTED
        }
    }

    override fun disconnect() {
        dataJob?.cancel()
        _connectionState.value = ConnectionState.DISCONNECTED
    }

    override fun observeEcgData(): Flow<ByteArray> = flow {
        val sampleRate = BleConstants.SAMPLE_RATE_HZ
        val intervalMs = 1000L / sampleRate
        var timestampMs = 0L
        var phase = 0.0

        // Heart rate: ~72 BPM with slight variability
        val baseHeartRateHz = 1.2  // 72 BPM
        val pqrstTemplate = generatePqrstTemplate()

        while (currentCoroutineContext().isActive) {
            // Natural heart rate variability
            val heartRateHz = baseHeartRateHz + 0.05 * sin(timestampMs * 0.001)
            val phaseIncrement = heartRateHz / sampleRate

            phase += phaseIncrement
            if (phase >= 1.0) phase -= 1.0

            // Get PQRST value from template
            val ecgValue = interpolateTemplate(pqrstTemplate, phase.toFloat())

            // Add realistic noise
            val baselineWander = 20f * sin(2.0 * PI * 0.3 * timestampMs / 1000.0).toFloat()
            val lineNoise = 5f * sin(2.0 * PI * 50.0 * timestampMs / 1000.0).toFloat()
            val muscleNoise = Random.nextFloat() * 3f - 1.5f

            val totalUv = ecgValue + baselineWander + lineNoise + muscleNoise

            // Convert µV back to 24-bit ADC value
            val rawAdc = ((totalUv / 1_000_000f) * EcgSample_ADC_MAX * EcgSample_GAIN / EcgSample_VREF).toInt()

            emit(buildPacket(0, timestampMs, rawAdc))
            timestampMs += intervalMs
            delay(intervalMs)
        }
    }.flowOn(Dispatchers.Default)

    override fun observeDeviceStatus(): Flow<DeviceStatus> = flow {
        var battery = 85
        while (currentCoroutineContext().isActive) {
            emit(DeviceStatus(
                batteryPercent = battery,
                isElectrodeConnected = true,
                isCharging = false,
                signalQuality = Random.nextInt(85, 100)
            ))
            delay(10_000) // Update every 10 seconds
            battery = (battery - 1).coerceAtLeast(10)
        }
    }

    private fun generatePqrstTemplate(): FloatArray {
        // 250 points representing one cardiac cycle in µV
        val template = FloatArray(250)
        for (i in template.indices) {
            val t = i / 250f
            template[i] = when {
                // P wave (atrial depolarization)
                t in 0.0f..0.08f -> 30f * sin(PI.toFloat() * t / 0.08f)
                // PR segment
                t in 0.08f..0.12f -> 0f
                // Q wave
                t in 0.12f..0.15f -> -40f * sin(PI.toFloat() * (t - 0.12f) / 0.03f)
                // R wave (ventricular depolarization - the big spike)
                t in 0.15f..0.19f -> 350f * sin(PI.toFloat() * (t - 0.15f) / 0.04f)
                // S wave
                t in 0.19f..0.22f -> -60f * sin(PI.toFloat() * (t - 0.19f) / 0.03f)
                // ST segment
                t in 0.22f..0.30f -> 0f
                // T wave (ventricular repolarization)
                t in 0.30f..0.44f -> 80f * sin(PI.toFloat() * (t - 0.30f) / 0.14f)
                // Baseline
                else -> 0f
            }
        }
        return template
    }

    private fun interpolateTemplate(template: FloatArray, phase: Float): Float {
        val index = (phase * template.size).toInt().coerceIn(0, template.size - 1)
        return template[index]
    }

    private fun buildPacket(channel: Int, timestampMs: Long, rawAdc: Int): ByteArray {
        val packet = ByteArray(10)
        packet[0] = BleConstants.PACKET_HEADER

        packet[1] = channel.toByte()

        // Timestamp: little-endian uint32
        val tsBytes = ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN).putInt(timestampMs.toInt()).array()
        System.arraycopy(tsBytes, 0, packet, 2, 4)

        // ECG: 24-bit signed, big-endian
        packet[6] = ((rawAdc shr 16) and 0xFF).toByte()
        packet[7] = ((rawAdc shr 8) and 0xFF).toByte()
        packet[8] = (rawAdc and 0xFF).toByte()

        // Checksum: XOR of bytes 0..8
        var xor: Byte = 0
        for (i in 0 until 9) {
            xor = (xor.toInt() xor packet[i].toInt()).toByte()
        }
        packet[9] = xor

        return packet
    }

    companion object {
        // Mirror EcgSample constants to avoid circular dep
        private const val EcgSample_VREF = 2.4f
        private const val EcgSample_GAIN = 6f
        private const val EcgSample_ADC_MAX = 8388608f
    }
}
```

---

## Task 8: Mock ECG Repository

**Files:**
- Create: `{base}/data/MockEcgRepository.kt`

**Step 1: Implement MockEcgRepository**

```kotlin
package com.hayatinritmi.app.data

import com.hayatinritmi.app.ble.BleManager
import com.hayatinritmi.app.data.model.ConnectionState
import com.hayatinritmi.app.data.model.DeviceStatus
import com.hayatinritmi.app.data.model.EcgSample
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.emptyFlow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.map

class MockEcgRepository(private val bleManager: BleManager) : EcgRepository {

    override fun observeEcgSamples(): Flow<EcgSample> {
        return bleManager.connectionState.flatMapLatest { state ->
            if (state == ConnectionState.CONNECTED) {
                bleManager.observeEcgData().map { packet ->
                    EcgPacketParser.parse(packet) ?: EcgSample(0, 0, 0, 0f)
                }
            } else {
                emptyFlow()
            }
        }
    }

    override fun observeDeviceStatus(): Flow<DeviceStatus> {
        return bleManager.connectionState.flatMapLatest { state ->
            if (state == ConnectionState.CONNECTED) {
                bleManager.observeDeviceStatus()
            } else {
                emptyFlow()
            }
        }
    }
}
```

---

## Task 9: BLE Permission Helper

**Files:**
- Create: `{base}/ble/BlePermissionHelper.kt`

**Step 1: Implement BLE permission helper**

```kotlin
package com.hayatinritmi.app.ble

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.core.content.ContextCompat

object BlePermissionHelper {

    fun getRequiredPermissions(): Array<String> {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            arrayOf(
                Manifest.permission.BLUETOOTH_SCAN,
                Manifest.permission.BLUETOOTH_CONNECT
            )
        } else {
            arrayOf(
                Manifest.permission.BLUETOOTH,
                Manifest.permission.BLUETOOTH_ADMIN,
                Manifest.permission.ACCESS_FINE_LOCATION
            )
        }
    }

    fun hasAllPermissions(context: Context): Boolean {
        return getRequiredPermissions().all {
            ContextCompat.checkSelfPermission(context, it) == PackageManager.PERMISSION_GRANTED
        }
    }

    fun getNotificationPermission(): String? {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            Manifest.permission.POST_NOTIFICATIONS
        } else null
    }

    fun createAppSettingsIntent(context: Context): Intent {
        return Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
            data = Uri.fromParts("package", context.packageName, null)
        }
    }
}
```

---

## Task 10: Real BLE Manager

**Files:**
- Create: `{base}/ble/RealBleManager.kt`

**Step 1: Implement RealBleManager**

```kotlin
package com.hayatinritmi.app.ble

import android.annotation.SuppressLint
import android.bluetooth.*
import android.bluetooth.le.*
import android.content.Context
import android.os.Build
import com.hayatinritmi.app.data.BleConstants
import com.hayatinritmi.app.data.model.ConnectionState
import com.hayatinritmi.app.data.model.DeviceStatus
import com.hayatinritmi.app.data.model.ScannedDevice
import kotlinx.coroutines.*
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.*

@SuppressLint("MissingPermission")
class RealBleManager(private val context: Context) : BleManager {

    private val scope = CoroutineScope(Dispatchers.Default + SupervisorJob())
    private val bluetoothManager = context.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
    private val bluetoothAdapter: BluetoothAdapter? = bluetoothManager.adapter
    private val scanner: BluetoothLeScanner? get() = bluetoothAdapter?.bluetoothLeScanner

    private val _connectionState = MutableStateFlow(ConnectionState.DISCONNECTED)
    override val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()

    private val _scannedDevices = MutableStateFlow<List<ScannedDevice>>(emptyList())
    override val scannedDevices: StateFlow<List<ScannedDevice>> = _scannedDevices.asStateFlow()

    private var gatt: BluetoothGatt? = null
    private var scanJob: Job? = null
    private val ecgDataFlow = MutableSharedFlow<ByteArray>(extraBufferCapacity = 256)
    private val deviceStatusFlow = MutableSharedFlow<DeviceStatus>(extraBufferCapacity = 16)

    private val scanCallback = object : ScanCallback() {
        override fun onScanResult(callbackType: Int, result: ScanResult) {
            val device = result.device
            val name = device.name ?: return
            val scanned = ScannedDevice(name, device.address, result.rssi)
            val current = _scannedDevices.value.toMutableList()
            val existingIndex = current.indexOfFirst { it.macAddress == scanned.macAddress }
            if (existingIndex >= 0) {
                current[existingIndex] = scanned
            } else {
                current.add(scanned)
            }
            _scannedDevices.value = current
        }
    }

    private val gattCallback = object : BluetoothGattCallback() {
        override fun onConnectionStateChange(gattRef: BluetoothGatt, status: Int, newState: Int) {
            when (newState) {
                BluetoothProfile.STATE_CONNECTED -> {
                    _connectionState.value = ConnectionState.CONNECTED
                    gattRef.requestMtu(BleConstants.DEFAULT_MTU)
                }
                BluetoothProfile.STATE_DISCONNECTED -> {
                    _connectionState.value = ConnectionState.DISCONNECTED
                    gattRef.close()
                    gatt = null
                }
            }
        }

        override fun onMtuChanged(gattRef: BluetoothGatt, mtu: Int, status: Int) {
            if (status == BluetoothGatt.GATT_SUCCESS) {
                gattRef.discoverServices()
            }
        }

        override fun onServicesDiscovered(gattRef: BluetoothGatt, status: Int) {
            if (status != BluetoothGatt.GATT_SUCCESS) return
            val ecgService = gattRef.getService(BleConstants.ECG_SERVICE_UUID) ?: return
            val ecgChar = ecgService.getCharacteristic(BleConstants.ECG_DATA_CHAR_UUID) ?: return

            gattRef.setCharacteristicNotification(ecgChar, true)
            val descriptor = ecgChar.getDescriptor(BleConstants.CCCD_UUID)
            if (descriptor != null) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                    gattRef.writeDescriptor(descriptor, BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE)
                } else {
                    @Suppress("DEPRECATION")
                    descriptor.value = BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE
                    @Suppress("DEPRECATION")
                    gattRef.writeDescriptor(descriptor)
                }
            }
        }

        @Deprecated("Deprecated in API 33")
        override fun onCharacteristicChanged(gattRef: BluetoothGatt, characteristic: BluetoothGattCharacteristic) {
            @Suppress("DEPRECATION")
            val data = characteristic.value ?: return
            handleCharacteristicData(characteristic.uuid, data)
        }

        override fun onCharacteristicChanged(gattRef: BluetoothGatt, characteristic: BluetoothGattCharacteristic, value: ByteArray) {
            handleCharacteristicData(characteristic.uuid, value)
        }

        private fun handleCharacteristicData(uuid: java.util.UUID, data: ByteArray) {
            when (uuid) {
                BleConstants.ECG_DATA_CHAR_UUID -> ecgDataFlow.tryEmit(data)
                BleConstants.DEVICE_STATUS_CHAR_UUID -> {
                    if (data.size >= 2) {
                        deviceStatusFlow.tryEmit(DeviceStatus.fromByte(data[0].toInt(), data[1].toInt()))
                    }
                }
            }
        }
    }

    override fun startScan(timeoutMs: Long) {
        _connectionState.value = ConnectionState.SCANNING
        _scannedDevices.value = emptyList()

        val filters = listOf(
            ScanFilter.Builder()
                .setDeviceName(BleConstants.DEVICE_NAME_FILTER)
                .build()
        )
        val settings = ScanSettings.Builder()
            .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
            .build()

        scanner?.startScan(filters, settings, scanCallback)

        scanJob?.cancel()
        scanJob = scope.launch {
            delay(timeoutMs)
            stopScan()
        }
    }

    override fun stopScan() {
        scanJob?.cancel()
        scanner?.stopScan(scanCallback)
        if (_connectionState.value == ConnectionState.SCANNING) {
            _connectionState.value = ConnectionState.DISCONNECTED
        }
    }

    override fun connect(device: ScannedDevice) {
        stopScan()
        _connectionState.value = ConnectionState.CONNECTING
        val btDevice = bluetoothAdapter?.getRemoteDevice(device.macAddress) ?: return
        gatt = btDevice.connectGatt(context, false, gattCallback, BluetoothDevice.TRANSPORT_LE)
    }

    override fun disconnect() {
        gatt?.disconnect()
        gatt?.close()
        gatt = null
        _connectionState.value = ConnectionState.DISCONNECTED
    }

    override fun observeEcgData(): Flow<ByteArray> = ecgDataFlow.asSharedFlow()

    override fun observeDeviceStatus(): Flow<DeviceStatus> = deviceStatusFlow.asSharedFlow()
}
```

---

## Task 11: ViewModels

**Files:**
- Create: `{base}/viewmodel/EcgViewModel.kt`
- Create: `{base}/viewmodel/DeviceScanViewModel.kt`

**Step 1: Create EcgViewModel**

```kotlin
package com.hayatinritmi.app.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.hayatinritmi.app.data.EcgRepository
import com.hayatinritmi.app.data.model.ConnectionState
import com.hayatinritmi.app.data.model.DeviceStatus
import com.hayatinritmi.app.data.model.HrvMetrics
import com.hayatinritmi.app.ble.BleManager
import com.hayatinritmi.app.processing.EcgFilter
import com.hayatinritmi.app.processing.RPeakDetector
import com.hayatinritmi.app.processing.RingBuffer
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

class EcgViewModel(
    private val repository: EcgRepository,
    private val bleManager: BleManager
) : ViewModel() {

    private val ringBuffer = RingBuffer(2500)  // 10 seconds at 250Hz
    private val filter = EcgFilter()
    private val rPeakDetector = RPeakDetector()

    // Graph points for Canvas (last 4 seconds = 1000 samples)
    private val _graphPoints = MutableStateFlow<List<Float>>(emptyList())
    val graphPoints: StateFlow<List<Float>> = _graphPoints.asStateFlow()

    private val _bpm = MutableStateFlow(0)
    val bpm: StateFlow<Int> = _bpm.asStateFlow()

    private val _hrv = MutableStateFlow(HrvMetrics())
    val hrv: StateFlow<HrvMetrics> = _hrv.asStateFlow()

    private val _deviceStatus = MutableStateFlow(DeviceStatus.DISCONNECTED)
    val deviceStatus: StateFlow<DeviceStatus> = _deviceStatus.asStateFlow()

    val connectionState: StateFlow<ConnectionState> = bleManager.connectionState

    private var sampleCounter = 0

    init {
        // Collect ECG samples
        viewModelScope.launch {
            repository.observeEcgSamples().collect { sample ->
                val filtered = filter.filter(sample.voltageUv)
                ringBuffer.add(filtered)
                rPeakDetector.processSample(filtered)

                sampleCounter++
                // Update UI every ~33ms (30 FPS) = every 8 samples at 250Hz
                if (sampleCounter % 8 == 0) {
                    _graphPoints.value = ringBuffer.getLastN(1000).toList()
                    _bpm.value = rPeakDetector.currentBpm
                    _hrv.value = rPeakDetector.currentHrv
                }
            }
        }

        // Collect device status
        viewModelScope.launch {
            repository.observeDeviceStatus().collect { status ->
                _deviceStatus.value = status
            }
        }
    }

    fun resetProcessing() {
        ringBuffer.clear()
        filter.reset()
        rPeakDetector.reset()
        _graphPoints.value = emptyList()
        _bpm.value = 0
        _hrv.value = HrvMetrics()
    }
}
```

**Step 2: Create DeviceScanViewModel**

```kotlin
package com.hayatinritmi.app.viewmodel

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.hayatinritmi.app.ble.BleManager
import com.hayatinritmi.app.data.model.ConnectionState
import com.hayatinritmi.app.data.model.ScannedDevice
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "ble_settings")

class DeviceScanViewModel(
    private val bleManager: BleManager,
    private val context: Context
) : ViewModel() {

    val scannedDevices: StateFlow<List<ScannedDevice>> = bleManager.scannedDevices
    val connectionState: StateFlow<ConnectionState> = bleManager.connectionState

    private val _savedDeviceMac = MutableStateFlow<String?>(null)
    val savedDeviceMac: StateFlow<String?> = _savedDeviceMac.asStateFlow()

    companion object {
        private val SAVED_DEVICE_MAC_KEY = stringPreferencesKey("saved_device_mac")
        private val SAVED_DEVICE_NAME_KEY = stringPreferencesKey("saved_device_name")
    }

    init {
        viewModelScope.launch {
            context.dataStore.data.map { prefs ->
                prefs[SAVED_DEVICE_MAC_KEY]
            }.collect { mac ->
                _savedDeviceMac.value = mac
            }
        }
    }

    fun startScan() {
        bleManager.startScan()
    }

    fun stopScan() {
        bleManager.stopScan()
    }

    fun connectToDevice(device: ScannedDevice) {
        bleManager.connect(device)
        viewModelScope.launch {
            context.dataStore.edit { prefs ->
                prefs[SAVED_DEVICE_MAC_KEY] = device.macAddress
                prefs[SAVED_DEVICE_NAME_KEY] = device.name
            }
        }
    }

    fun disconnect() {
        bleManager.disconnect()
    }

    fun autoReconnect() {
        viewModelScope.launch {
            val mac = _savedDeviceMac.value ?: return@launch
            context.dataStore.data.map { prefs ->
                prefs[SAVED_DEVICE_NAME_KEY] ?: "HayatinRitmi"
            }.first().let { name ->
                bleManager.connect(ScannedDevice(name, mac, 0))
            }
        }
    }
}
```

---

## Task 12: Foreground Service

**Files:**
- Create: `{base}/service/EcgForegroundService.kt`

**Step 1: Implement EcgForegroundService**

```kotlin
package com.hayatinritmi.app.service

import android.app.*
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.hayatinritmi.app.MainActivity
import com.hayatinritmi.app.R

class EcgForegroundService : Service() {

    companion object {
        const val CHANNEL_ID = "ecg_monitoring_channel"
        const val NOTIFICATION_ID = 1001
        const val ACTION_START = "com.hayatinritmi.START_ECG"
        const val ACTION_STOP = "com.hayatinritmi.STOP_ECG"

        fun startService(context: Context) {
            val intent = Intent(context, EcgForegroundService::class.java).apply {
                action = ACTION_START
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stopService(context: Context) {
            val intent = Intent(context, EcgForegroundService::class.java).apply {
                action = ACTION_STOP
            }
            context.startService(intent)
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> startMonitoring()
            ACTION_STOP -> stopMonitoring()
        }
        return START_STICKY
    }

    private fun startMonitoring() {
        createNotificationChannel()
        val notification = buildNotification("EKG izleniyor...")

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    private fun stopMonitoring() {
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "EKG İzleme",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Hayatın Ritmi EKG izleme servisi"
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(contentText: String): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Hayatın Ritmi")
            .setContentText(contentText)
            .setSmallIcon(android.R.drawable.ic_menu_compass)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
```

---

## Task 13: DeviceScanScreen UI

**Files:**
- Create: `{base}/screens/DeviceScanScreen.kt`

**Step 1: Implement DeviceScanScreen with radar animation**

```kotlin
package com.hayatinritmi.app.screens

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.hayatinritmi.app.data.model.ConnectionState
import com.hayatinritmi.app.data.model.ScannedDevice
import com.hayatinritmi.app.ui.theme.JakartaFont
import com.hayatinritmi.app.ui.theme.NeonBlue
import com.hayatinritmi.app.viewmodel.DeviceScanViewModel

@Composable
fun DeviceScanScreen(
    navController: NavHostController,
    viewModel: DeviceScanViewModel
) {
    val scannedDevices by viewModel.scannedDevices.collectAsState()
    val connectionState by viewModel.connectionState.collectAsState()
    val isScanning = connectionState == ConnectionState.SCANNING

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
    ) {
        // Ambient lights
        Box(
            modifier = Modifier
                .align(Alignment.TopCenter)
                .offset(y = (-50).dp)
                .size(350.dp)
                .background(NeonBlue.copy(alpha = 0.15f), CircleShape)
                .blur(100.dp)
        )

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 24.dp)
        ) {
            Spacer(modifier = Modifier.height(40.dp))

            // Header with back button
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(onClick = { navController.popBackStack() }) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Geri", tint = Color.White)
                }
                Spacer(modifier = Modifier.width(8.dp))
                Column {
                    Text(
                        "Cihaz Tarama",
                        fontFamily = JakartaFont,
                        fontSize = 24.sp,
                        fontWeight = FontWeight.ExtraBold,
                        color = Color.White
                    )
                    Text(
                        if (isScanning) "Cihaz aranıyor..." else "Taramayı başlatın",
                        fontSize = 12.sp,
                        color = Color.White.copy(alpha = 0.5f)
                    )
                }
            }

            Spacer(modifier = Modifier.height(40.dp))

            // Radar animation
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(200.dp),
                contentAlignment = Alignment.Center
            ) {
                if (isScanning) {
                    RadarAnimation()
                } else {
                    Icon(
                        Icons.Default.BluetoothSearching,
                        contentDescription = null,
                        tint = NeonBlue.copy(alpha = 0.3f),
                        modifier = Modifier.size(80.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Scan button
            Button(
                onClick = {
                    if (isScanning) viewModel.stopScan() else viewModel.startScan()
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(56.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (isScanning) Color(0xFFE11D48).copy(alpha = 0.2f) else NeonBlue.copy(alpha = 0.2f)
                ),
                shape = RoundedCornerShape(16.dp),
                border = androidx.compose.foundation.BorderStroke(
                    1.dp,
                    if (isScanning) Color(0xFFE11D48).copy(alpha = 0.3f) else NeonBlue.copy(alpha = 0.3f)
                )
            ) {
                Icon(
                    if (isScanning) Icons.Default.Stop else Icons.Default.BluetoothSearching,
                    contentDescription = null,
                    tint = if (isScanning) Color(0xFFE11D48) else NeonBlue
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    if (isScanning) "Taramayı Durdur" else "Taramayı Başlat",
                    color = if (isScanning) Color(0xFFE11D48) else NeonBlue,
                    fontWeight = FontWeight.Bold
                )
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Device list header
            if (scannedDevices.isNotEmpty()) {
                Text(
                    "BULUNAN CİHAZLAR",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.White.copy(alpha = 0.4f),
                    letterSpacing = 2.sp
                )
                Spacer(modifier = Modifier.height(12.dp))
            }

            // Device list
            LazyColumn {
                items(scannedDevices) { device ->
                    DeviceListItem(
                        device = device,
                        connectionState = connectionState,
                        onClick = { viewModel.connectToDevice(device) }
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                }
            }
        }
    }
}

@Composable
fun RadarAnimation() {
    val infiniteTransition = rememberInfiniteTransition(label = "radar")
    val scale1 by infiniteTransition.animateFloat(
        initialValue = 0.3f, targetValue = 1.5f,
        animationSpec = infiniteRepeatable(tween(2000, easing = LinearEasing), RepeatMode.Restart),
        label = "ring1"
    )
    val scale2 by infiniteTransition.animateFloat(
        initialValue = 0.3f, targetValue = 1.5f,
        animationSpec = infiniteRepeatable(tween(2000, 667, LinearEasing), RepeatMode.Restart),
        label = "ring2"
    )
    val scale3 by infiniteTransition.animateFloat(
        initialValue = 0.3f, targetValue = 1.5f,
        animationSpec = infiniteRepeatable(tween(2000, 1334, LinearEasing), RepeatMode.Restart),
        label = "ring3"
    )

    Box(contentAlignment = Alignment.Center) {
        listOf(scale1, scale2, scale3).forEach { scale ->
            val alpha = (1f - (scale - 0.3f) / 1.2f).coerceIn(0f, 0.5f)
            Box(
                modifier = Modifier
                    .size(120.dp)
                    .scale(scale)
                    .border(2.dp, NeonBlue.copy(alpha = alpha), CircleShape)
            )
        }
        // Center icon
        Box(
            modifier = Modifier
                .size(48.dp)
                .background(NeonBlue.copy(alpha = 0.2f), CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Icon(Icons.Default.Bluetooth, contentDescription = null, tint = NeonBlue, modifier = Modifier.size(24.dp))
        }
    }
}

@Composable
fun DeviceListItem(
    device: ScannedDevice,
    connectionState: ConnectionState,
    onClick: () -> Unit
) {
    val isConnecting = connectionState == ConnectionState.CONNECTING
    val isConnected = connectionState == ConnectionState.CONNECTED

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(Color.White.copy(alpha = 0.05f))
            .border(
                1.dp,
                if (isConnected) Color(0xFF10B981).copy(alpha = 0.3f) else Color.White.copy(alpha = 0.05f),
                RoundedCornerShape(16.dp)
            )
            .clickable(enabled = !isConnecting && !isConnected, onClick = onClick)
            .padding(16.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(40.dp)
                .background(NeonBlue.copy(alpha = 0.1f), CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Icon(Icons.Default.Bluetooth, contentDescription = null, tint = NeonBlue, modifier = Modifier.size(20.dp))
        }
        Spacer(modifier = Modifier.width(16.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(device.name, color = Color.White, fontWeight = FontWeight.Bold, fontSize = 14.sp)
            Text(device.macAddress, color = Color.White.copy(alpha = 0.4f), fontSize = 11.sp)
        }
        // Signal strength
        SignalBars(rssi = device.rssi)
        Spacer(modifier = Modifier.width(12.dp))
        // Status
        when {
            isConnected -> {
                Text("BAĞLI", color = Color(0xFF10B981), fontSize = 10.sp, fontWeight = FontWeight.Bold)
            }
            isConnecting -> {
                CircularProgressIndicator(modifier = Modifier.size(20.dp), color = NeonBlue, strokeWidth = 2.dp)
            }
            else -> {
                Icon(Icons.Default.ChevronRight, contentDescription = null, tint = Color.White.copy(alpha = 0.3f))
            }
        }
    }
}

@Composable
fun SignalBars(rssi: Int) {
    val strength = when {
        rssi >= -50 -> 4
        rssi >= -60 -> 3
        rssi >= -70 -> 2
        else -> 1
    }
    Row(horizontalArrangement = Arrangement.spacedBy(2.dp), verticalAlignment = Alignment.Bottom) {
        for (i in 1..4) {
            Box(
                modifier = Modifier
                    .width(4.dp)
                    .height((6 + i * 4).dp)
                    .background(
                        if (i <= strength) NeonBlue else Color.White.copy(alpha = 0.1f),
                        RoundedCornerShape(1.dp)
                    )
            )
        }
    }
}
```

---

## Task 14: Update ProModeScreen with Real-Time ECG

**Files:**
- Modify: `{base}/screens/ProModeScreen.kt`

**What changes:**
- Replace static `LiveECGGraph()` with `RealTimeEcgGraph(viewModel)` that draws from `EcgViewModel.graphPoints`
- BPM and HRV cards read from ViewModel StateFlows
- AI analysis card shows data derived from R-peak detection
- Add connection status indicator
- Keep existing Glassmorphism styling and layout structure

The full updated ProModeScreen accepts `EcgViewModel` as parameter and replaces hardcoded values with `collectAsState()` from ViewModel flows. The `LiveECGGraph` composable is replaced with a new `RealTimeEcgGraph` that uses Canvas to draw the `graphPoints` StateFlow with proper EKG grid overlay (0.2s major / 0.04s minor grid lines), auto-scaling Y-axis, and 25mm/s paper speed simulation.

---

## Task 15: Update DashboardScreen with Connection State

**Files:**
- Modify: `{base}/screens/DashboardScreen.kt`

**What changes:**
- Accept `EcgViewModel` parameter
- "TİŞÖRT BAĞLI" text reflects `connectionState`
- Breathing circle color: green=CONNECTED, amber=SCANNING/CONNECTING, gray=DISCONNECTED
- Show BPM inside breathing circle when connected

---

## Task 16: Update SettingsScreen with Device Info

**Files:**
- Modify: `{base}/screens/SettingsScreen.kt`

**What changes:**
- Accept `DeviceScanViewModel` and `EcgViewModel` parameters
- "Bağlı Cihazlar" card shows real device name + battery from DeviceStatus
- Battery CircularProgressIndicator uses real percentage
- "Cihazı Kalibre Et" → navigates to DeviceScanScreen
- Tap on entire device card → navigates to DeviceScanScreen

---

## Task 17: Update MainActivity + Navigation

**Files:**
- Modify: `{base}/MainActivity.kt`

**What changes:**
- Add `Screen.DeviceScan` to sealed class
- Create MockBleManager, MockEcgRepository, ViewModels in `onCreate`
- Pass ViewModels to screens via NavHost composable lambdas
- Add DeviceScanScreen route
- Auto-reconnect on app start via DeviceScanViewModel

```kotlin
// In MainActivity.onCreate
val bleManager = MockBleManager()  // Switch to RealBleManager(this) when hardware ready
val repository = MockEcgRepository(bleManager)
val ecgViewModel = EcgViewModel(repository, bleManager)
val deviceScanViewModel = DeviceScanViewModel(bleManager, applicationContext)
```

---

## Task 18: Build Verification & Integration Test

**Step 1:** Run `./gradlew assembleDebug` — must compile with 0 errors
**Step 2:** Manual verification on emulator:
- Login → Dashboard shows "TİŞÖRT BAĞLI DEĞİL" (gray)
- Settings → "Bağlı Cihazlar" → tap → DeviceScanScreen opens
- Tap "Taramayı Başlat" → radar animation → mock devices appear
- Tap device → connecting → connected
- Navigate to ProModeScreen → live ECG graph with real-time BPM/HRV
- Dashboard → breathing circle turns green, shows BPM
- Settings → battery percentage updates

---

## Dependency Order

```
Task 1  (build config)       ← FIRST, everything depends on this
Task 2  (data models)        ← depends on Task 1
Task 3  (RingBuffer)         ← independent
Task 4  (EcgFilter)          ← independent
Task 5  (RPeakDetector)      ← depends on Task 2 (HrvMetrics)
Task 6  (parser+repo)        ← depends on Task 2
Task 7  (BleManager+Mock)    ← depends on Task 2, Task 6
Task 8  (MockEcgRepository)  ← depends on Task 6, Task 7
Task 9  (permissions)        ← independent
Task 10 (RealBleManager)     ← depends on Task 2, Task 6
Task 11 (ViewModels)         ← depends on Tasks 3-8
Task 12 (ForegroundService)  ← depends on Task 1
Task 13 (DeviceScanScreen)   ← depends on Task 11
Task 14 (ProModeScreen)      ← depends on Task 11
Task 15 (DashboardScreen)    ← depends on Task 11
Task 16 (SettingsScreen)     ← depends on Task 11
Task 17 (MainActivity)       ← depends on Tasks 7,8,11,13-16
Task 18 (verification)       ← depends on ALL
```

## Parallelizable Groups for Agent Teams

**Group A (Infrastructure):** Tasks 1, 2, 9, 12
**Group B (Processing):** Tasks 3, 4, 5
**Group C (BLE Layer):** Tasks 6, 7, 8, 10
**Group D (ViewModels):** Task 11 (after A, B, C complete)
**Group E (UI Screens):** Tasks 13, 14, 15, 16 (after D complete)
**Group F (Integration):** Tasks 17, 18 (after all complete)
