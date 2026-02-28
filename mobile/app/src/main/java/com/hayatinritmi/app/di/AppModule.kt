package com.hayatinritmi.app.di

import android.content.Context
import com.hayatinritmi.app.data.bluetooth.BleManager
import com.hayatinritmi.app.data.bluetooth.MockBleManager
import com.hayatinritmi.app.data.repository.MockEcgRepository
import com.hayatinritmi.app.domain.repository.EcgRepository
import com.hayatinritmi.app.processing.ArrhythmiaClassifier
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides
    @Singleton
    fun provideBleManager(): BleManager = MockBleManager()

    @Provides
    @Singleton
    fun provideEcgRepository(bleManager: BleManager): EcgRepository =
        MockEcgRepository(bleManager as MockBleManager)

    @Provides
    @Singleton
    fun provideArrhythmiaClassifier(@ApplicationContext context: Context): ArrhythmiaClassifier =
        ArrhythmiaClassifier(context)
}
