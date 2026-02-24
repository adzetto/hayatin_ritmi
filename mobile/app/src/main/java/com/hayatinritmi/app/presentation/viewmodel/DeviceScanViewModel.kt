package com.hayatinritmi.app.presentation.viewmodel

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.hayatinritmi.app.data.bluetooth.BleManager
import com.hayatinritmi.app.domain.model.ConnectionState
import com.hayatinritmi.app.domain.model.ScannedDevice
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
