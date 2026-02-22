package com.hayatinritmi.app.data

import com.hayatinritmi.app.ble.BleManager
import com.hayatinritmi.app.data.model.ConnectionState
import com.hayatinritmi.app.data.model.DeviceStatus
import com.hayatinritmi.app.data.model.EcgSample
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.emptyFlow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.map

class BleEcgRepository(private val bleManager: BleManager) : EcgRepository {

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
