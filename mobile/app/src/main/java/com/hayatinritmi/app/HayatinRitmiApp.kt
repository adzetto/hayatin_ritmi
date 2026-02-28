package com.hayatinritmi.app

import android.app.Application
import com.hayatinritmi.app.sync.SyncScheduler
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class HayatinRitmiApp : Application() {

    override fun onCreate() {
        super.onCreate()
        SyncScheduler.schedulePeriodic(this)
    }
}
