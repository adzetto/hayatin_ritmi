package com.hayatinritmi.app.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import com.hayatinritmi.app.data.local.dao.*
import com.hayatinritmi.app.data.local.entity.*

@Database(
    entities = [
        UserEntity::class,
        EcgSessionEntity::class,
        EcgAlertEntity::class,
        DeviceInfoEntity::class
    ],
    version = 1,
    exportSchema = false
)
abstract class HayatinRitmiDatabase : RoomDatabase() {
    abstract fun userDao(): UserDao
    abstract fun ecgSessionDao(): EcgSessionDao
    abstract fun ecgAlertDao(): EcgAlertDao
    abstract fun deviceInfoDao(): DeviceInfoDao
}
