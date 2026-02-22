package com.hayatinritmi.app.data

import com.hayatinritmi.app.data.model.DeviceStatus
import com.hayatinritmi.app.data.model.EcgSample
import kotlinx.coroutines.flow.Flow

interface EcgRepository {
    fun observeEcgSamples(): Flow<EcgSample>
    fun observeDeviceStatus(): Flow<DeviceStatus>
}
