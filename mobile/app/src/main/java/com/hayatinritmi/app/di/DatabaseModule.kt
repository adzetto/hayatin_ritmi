package com.hayatinritmi.app.di

import android.content.Context
import androidx.room.Room
import com.hayatinritmi.app.data.local.HayatinRitmiDatabase
import com.hayatinritmi.app.data.local.dao.*
import com.hayatinritmi.app.data.repository.SessionRepositoryImpl
import com.hayatinritmi.app.data.repository.UserRepositoryImpl
import com.hayatinritmi.app.domain.repository.SessionRepository
import com.hayatinritmi.app.domain.repository.UserRepository
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import net.zetetic.database.sqlcipher.SupportOpenHelperFactory
import java.security.SecureRandom
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): HayatinRitmiDatabase {
        // SQLCipher passphrase — stored in Android Keystore via SharedPreferences
        val passphrase = getOrCreatePassphrase(context)
        val factory = SupportOpenHelperFactory(passphrase)

        return Room.databaseBuilder(
            context.applicationContext,
            HayatinRitmiDatabase::class.java,
            "hayatinritmi.db"
        )
            .openHelperFactory(factory)
            .fallbackToDestructiveMigration()
            .build()
    }

    @Provides
    fun provideUserDao(db: HayatinRitmiDatabase): UserDao = db.userDao()

    @Provides
    fun provideEcgSessionDao(db: HayatinRitmiDatabase): EcgSessionDao = db.ecgSessionDao()

    @Provides
    fun provideEcgAlertDao(db: HayatinRitmiDatabase): EcgAlertDao = db.ecgAlertDao()

    @Provides
    fun provideDeviceInfoDao(db: HayatinRitmiDatabase): DeviceInfoDao = db.deviceInfoDao()

    @Provides
    @Singleton
    fun provideUserRepository(userDao: UserDao): UserRepository = UserRepositoryImpl(userDao)

    @Provides
    @Singleton
    fun provideSessionRepository(
        sessionDao: EcgSessionDao,
        alertDao: EcgAlertDao
    ): SessionRepository = SessionRepositoryImpl(sessionDao, alertDao)

    // ─── SQLCipher Key Management ──────────────────────────────────────────
    private fun getOrCreatePassphrase(context: Context): ByteArray {
        val prefs = context.getSharedPreferences("db_key_prefs", Context.MODE_PRIVATE)
        val existing = prefs.getString("db_passphrase_hex", null)
        if (existing != null) {
            return existing.chunked(2).map { it.toInt(16).toByte() }.toByteArray()
        }
        // Generate new 32-byte passphrase
        val passphrase = ByteArray(32)
        SecureRandom().nextBytes(passphrase)
        val hex = passphrase.joinToString("") { "%02x".format(it) }
        prefs.edit().putString("db_passphrase_hex", hex).apply()
        return passphrase
    }
}
