package com.hayatinritmi.app.presentation.viewmodel

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.hayatinritmi.app.data.bluetooth.BleManager
import com.hayatinritmi.app.domain.model.ConnectionState
import com.hayatinritmi.app.domain.model.ScannedDevice
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

private val Context.dataStore by preferencesDataStore(name = "device_prefs")

@HiltViewModel
class DeviceScanViewModel @Inject constructor(
    private val bleManager: BleManager,
    @ApplicationContext private val context: Context
) : ViewModel() {

    private val _scannedDevices = MutableStateFlow<List<ScannedDevice>>(emptyList())
    val scannedDevices: StateFlow<List<ScannedDevice>> = _scannedDevices.asStateFlow()

    val connectionState: StateFlow<ConnectionState> = bleManager.connectionState

    private val _isScanning = MutableStateFlow(false)
    val isScanning: StateFlow<Boolean> = _isScanning.asStateFlow()

    companion object {
        private val SAVED_DEVICE_MAC = stringPreferencesKey("saved_device_mac")
        private val SAVED_DEVICE_NAME = stringPreferencesKey("saved_device_name")
    }

    fun startScan() {
        viewModelScope.launch {
            _isScanning.value = true
            bleManager.startScan()
            bleManager.scannedDevices.collect { devices ->
                _scannedDevices.value = devices
            }
        }
    }

    fun stopScan() {
        bleManager.stopScan()
        _isScanning.value = false
    }

    fun connectToDevice(device: ScannedDevice) {
        viewModelScope.launch {
            bleManager.connect(device)
            // Save device info
            context.dataStore.edit { prefs ->
                prefs[SAVED_DEVICE_MAC] = device.macAddress
                prefs[SAVED_DEVICE_NAME] = device.name
            }
        }
    }

    fun disconnect() {
        bleManager.disconnect()
    }

    fun autoReconnect() {
        viewModelScope.launch {
            val prefs = context.dataStore.data.first()
            val savedMac = prefs[SAVED_DEVICE_MAC]
            val savedName = prefs[SAVED_DEVICE_NAME]
            if (savedMac != null && savedName != null) {
                bleManager.connect(ScannedDevice(savedName, savedMac, 0))
            }
        }
    }
}
