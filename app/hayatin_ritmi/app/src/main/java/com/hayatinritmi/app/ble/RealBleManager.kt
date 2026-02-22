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
