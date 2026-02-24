package com.hayatinritmi.app.data.repository

import com.hayatinritmi.app.data.bluetooth.BleManager
import com.hayatinritmi.app.data.bluetooth.EcgPacketParser
import com.hayatinritmi.app.domain.model.ConnectionState
import com.hayatinritmi.app.domain.model.DeviceStatus
import com.hayatinritmi.app.domain.model.EcgSample
import com.hayatinritmi.app.domain.repository.EcgRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.asFlow
import kotlinx.coroutines.flow.emptyFlow
import kotlinx.coroutines.flow.flatMapConcat
import kotlinx.coroutines.flow.flatMapLatest

class MockEcgRepository(private val bleManager: BleManager) : EcgRepository {

    override fun observeEcgSamples(): Flow<EcgSample> {
        return bleManager.connectionState.flatMapLatest { state ->
            if (state == ConnectionState.CONNECTED) {
                // Each 43-byte frame → 12 EcgSamples (one per lead)
                bleManager.observeEcgData().flatMapConcat { packet ->
                    (EcgPacketParser.parse(packet) ?: emptyList()).asFlow()
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

