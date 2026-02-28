package com.hayatinritmi.app.data.local.dao

import androidx.room.*
import com.hayatinritmi.app.data.local.entity.DeviceInfoEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface DeviceInfoDao {

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertOrUpdate(device: DeviceInfoEntity): Long

    @Query("SELECT * FROM device_info WHERE mac = :mac LIMIT 1")
    suspend fun getByMac(mac: String): DeviceInfoEntity?

    @Query("SELECT * FROM device_info ORDER BY lastConnectedMs DESC")
    fun observeAll(): Flow<List<DeviceInfoEntity>>

    @Query("SELECT * FROM device_info ORDER BY lastConnectedMs DESC LIMIT 1")
    suspend fun getLastConnected(): DeviceInfoEntity?

    @Delete
    suspend fun delete(device: DeviceInfoEntity)

    @Query("DELETE FROM device_info")
    suspend fun deleteAll()
}
