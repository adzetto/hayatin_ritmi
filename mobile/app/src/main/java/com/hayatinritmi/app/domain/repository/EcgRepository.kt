package com.hayatinritmi.app.domain.repository

import com.hayatinritmi.app.domain.model.DeviceStatus
import com.hayatinritmi.app.domain.model.EcgSample
import kotlinx.coroutines.flow.Flow

interface EcgRepository {
    fun observeEcgSamples(): Flow<EcgSample>
    fun observeDeviceStatus(): Flow<DeviceStatus>
}
