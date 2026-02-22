# Phase 2: Bluetooth & ECG Data Pipeline — Design Document

**Date:** 2026-02-22
**Status:** Approved
**Approach:** Repository Pattern with Interface Abstraction (Mock-first)

---

## 1. Architecture Overview

Repository pattern with mock/real BLE implementations. Manual constructor injection (no DI framework). ViewModels for lifecycle-aware state management.

```
ESP32/Mock → BleManager → EcgRepository → EcgViewModel → UI Screens
                                        → Processing    → DashboardScreen
                                        → Pipeline      → ProModeScreen
                                                        → EmergencyScreen
```

## 2. Package Structure

```
com.hayatinritmi.app/
├── ble/
│   ├── BleManager.kt              # Interface: scan, connect, disconnect
│   ├── RealBleManager.kt          # BluetoothLeScanner + GATT client
│   ├── MockBleManager.kt          # Simulated devices + fake data stream
│   └── BlePermissionHelper.kt     # Dynamic permission requests (Android 12+ aware)
├── data/
│   ├── model/
│   │   ├── EcgSample.kt           # timestamp, channel, rawAdc, voltageUv
│   │   ├── DeviceStatus.kt        # battery, electrode, charging, signalQuality
│   │   ├── ScannedDevice.kt       # name, macAddress, rssi
│   │   └── ConnectionState.kt     # Disconnected, Scanning, Connecting, Connected
│   ├── EcgRepository.kt           # Interface: Flow<EcgSample>, Flow<DeviceStatus>
│   ├── MockEcgRepository.kt       # Realistic PQRST waveform generator
│   ├── BleEcgRepository.kt        # Parses BLE notifications into EcgSample
│   └── EcgPacketParser.kt         # Binary protocol parser
├── processing/
│   ├── RingBuffer.kt              # Thread-safe circular buffer (2500 samples)
│   ├── EcgFilter.kt               # HPF 0.5Hz + Notch 50Hz + LPF 40Hz
│   └── RPeakDetector.kt           # Pan-Tompkins: BPM + HRV (SDNN, RMSSD)
├── viewmodel/
│   ├── EcgViewModel.kt            # Live ECG data, BPM, HRV, connection state
│   ├── DeviceScanViewModel.kt     # Scan results, pairing, permissions
│   └── ServiceViewModel.kt        # Foreground service start/stop, recording
├── service/
│   └── EcgForegroundService.kt    # BLE background connection + notification
├── screens/
│   └── DeviceScanScreen.kt        # NEW: radar animation + device list + pair
└── (existing screens updated)
```

## 3. Data Models

### BLE Protocol (ESP32 → Android)
```
[Header:1B=0xAA] [Channel:1B] [Timestamp:4B uint32_ms] [ECG:3B int24] [Checksum:1B XOR]
Total: 10 bytes per sample, 250 samples/second
```

### Kotlin Models
```kotlin
data class EcgSample(
    val timestamp: Long,      // ms
    val channel: Int,         // 0 = Lead I
    val rawAdc: Int,          // 24-bit signed ADC
    val voltageUv: Float      // (rawAdc * 2.4) / (2^23 * 6) → ±400µV
)

data class DeviceStatus(
    val batteryPercent: Int,         // 0-100
    val isElectrodeConnected: Boolean,
    val isCharging: Boolean,
    val signalQuality: Int           // 0-100
)

data class ScannedDevice(
    val name: String,
    val macAddress: String,
    val rssi: Int
)

enum class ConnectionState {
    DISCONNECTED, SCANNING, CONNECTING, CONNECTED
}
```

## 4. BLE Layer Design

### BleManager Interface
```kotlin
interface BleManager {
    val connectionState: StateFlow<ConnectionState>
    val scannedDevices: StateFlow<List<ScannedDevice>>
    fun startScan(timeoutMs: Long = 30000)
    fun stopScan()
    fun connect(device: ScannedDevice)
    fun disconnect()
    fun observeEcgData(): Flow<ByteArray>       // raw BLE notifications
    fun observeDeviceStatus(): Flow<DeviceStatus>
    fun readBatteryLevel(): Int?
}
```

### MockBleManager
- `startScan()` → emits 2-3 fake "HayatinRitmi" devices after random delay
- `connect()` → transitions to CONNECTED after 1.5s simulated delay
- `observeEcgData()` → generates realistic PQRST packets at 250Hz

### RealBleManager
- Uses `BluetoothLeScanner.startScan()` with `ScanFilter` for "HayatinRitmi"
- `connectGatt()` with `BluetoothGattCallback`
- Service discovery: ECG_SERVICE_UUID, ECG_DATA_CHAR_UUID (NOTIFY), BATTERY_CHAR_UUID (READ)
- `setCharacteristicNotification()` + descriptor write for ECG data subscription
- MTU request: 23 → 247 bytes for potential batch transfers

### BLE Permission Helper
- Android 12+ (API 31): BLUETOOTH_SCAN, BLUETOOTH_CONNECT
- Android 11-: BLUETOOTH_ADMIN, ACCESS_FINE_LOCATION
- FOREGROUND_SERVICE + FOREGROUND_SERVICE_CONNECTED_DEVICE
- Rationale dialog on first denial
- Settings redirect on permanent denial

## 5. Signal Processing Pipeline

### RingBuffer
- Fixed 2500-sample capacity (10 seconds at 250Hz)
- Thread-safe with `ReentrantLock`
- Methods: `add(sample)`, `getLastN(n)`, `getAll()`, `clear()`

### EcgFilter (cascaded IIR filters)
1. **HPF 0.5Hz** — Baseline wander removal
   - `y[n] = α * (y[n-1] + x[n] - x[n-1])`, α = 1/(1 + 2π·0.5/250)
2. **Notch 50Hz** — Power line interference
   - Second-order IIR, Q=30, configurable for 50Hz or 60Hz
3. **LPF 40Hz** — Muscle artifact reduction
   - `y[n] = α·x[n] + (1-α)·y[n-1]`, α = 2π·40/250 / (1 + 2π·40/250)

### RPeakDetector (simplified Pan-Tompkins)
1. Derivative of filtered signal
2. Squaring
3. Moving window integration (150ms = 37 samples)
4. Adaptive threshold (mean + 0.5 * std of integrated signal)
5. Refractory period: 200ms minimum between R-peaks
6. BPM = 60000 / mean(last 10 R-R intervals)
7. HRV: SDNN = std(R-R), RMSSD = rms(successive R-R differences)

### Mock ECG Generator
- PQRST template morphology (not random noise)
- Configurable heart rate: 60-100 BPM with natural variability
- Additive noise: baseline wander (0.3Hz), 50Hz line noise, random artifacts
- Allows pipeline validation without hardware

## 6. ViewModel Layer

### EcgViewModel
- Collects `Flow<EcgSample>` from repository
- Feeds: RingBuffer → EcgFilter → RPeakDetector
- Exposes:
  - `graphPoints: StateFlow<List<Float>>` — filtered voltages for Canvas
  - `bpm: StateFlow<Int>`
  - `hrv: StateFlow<HrvMetrics>` (sdnn, rmssd)
  - `deviceStatus: StateFlow<DeviceStatus>`
  - `connectionState: StateFlow<ConnectionState>`
  - `isRecording: StateFlow<Boolean>`

### DeviceScanViewModel
- Manages permission request flow
- `scannedDevices: StateFlow<List<ScannedDevice>>`
- `connect(device)`, `disconnect()`
- Auto-reconnect on app restart (reads saved MAC from DataStore)

### ServiceViewModel
- `startService()`, `stopService()`
- `startRecording()`, `stopRecording()` — CSV file output
- `isServiceRunning: StateFlow<Boolean>`

## 7. UI Changes

### NEW: DeviceScanScreen
- Radar-style pulse animation (Glassmorphism theme)
- Filtered device list (only "HayatinRitmi" devices)
- Tap to connect → progress → success/failure
- Accessible from Settings "Bagli Cihazlar" card

### ProModeScreen (major update)
- Replace static LiveECGGraph with real-time Canvas from EcgViewModel
- Scrolling 4-second time window, auto-scaled Y-axis
- 25mm/s paper speed, proper EKG grid (0.2s major, 0.04s minor)
- Live BPM + HRV from ViewModel
- Connection status indicator (green/yellow/red dot)

### DashboardScreen (updates)
- "TISORT BAGLI" reflects actual ConnectionState
- Breathing circle color: green=connected, amber=scanning, gray=disconnected
- BPM value displayed in breathing circle

### SettingsScreen (updates)
- "Bagli Cihazlar" card shows real device + battery %
- Tap navigates to DeviceScanScreen
- Battery indicator uses real DeviceStatus

### Navigation
- Add `Screen.DeviceScan` route to NavHost

## 8. Foreground Service

- `EcgForegroundService` extends `Service`
- `startForeground()` with persistent notification
- Notification: "Hayatin Ritmi — EKG izleniyor" + BPM in expanded view
- Maintains BLE connection in background
- CSV recording: `timestamp,channel,rawAdc,voltageUv` per line
- Start/stop from ProModeScreen toolbar

## 9. AndroidManifest Permissions

```xml
<!-- BLE (Android 12+) -->
<uses-permission android:name="android.permission.BLUETOOTH_SCAN" />
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
<!-- BLE (Android 11 and below) -->
<uses-permission android:name="android.permission.BLUETOOTH" />
<uses-permission android:name="android.permission.BLUETOOTH_ADMIN" />
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<!-- Foreground Service -->
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_CONNECTED_DEVICE" />
<!-- BLE feature declaration -->
<uses-feature android:name="android.hardware.bluetooth_le" android:required="true" />
```

## 10. Dependencies to Add

```toml
# libs.versions.toml additions
datastorePreferences = "1.1.1"
lifecycleViewmodelCompose = "2.8.7"

# New libraries
androidx-datastore-preferences = { group = "androidx.datastore", name = "datastore-preferences", version.ref = "datastorePreferences" }
androidx-lifecycle-viewmodel-compose = { group = "androidx.lifecycle", name = "lifecycle-viewmodel-compose", version.ref = "lifecycleViewmodelCompose" }
```
