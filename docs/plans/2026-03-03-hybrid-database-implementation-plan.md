# 🏗️ Hibrit Veritabanı Mimarisi — Detaylı Uygulama Planı

> **Hayatin Ritmi — TÜBİTAK Projesi**
> Tarih: 3 Mart 2026
> Versiyon: 1.0
> Durum: Uygulama planı (onay bekliyor)

---

## 📋 İçindekiler

1. [Mimari Genel Bakış](#1-mimari-genel-bakış)
2. [Faz 1 — Lokal Katman İyileştirmeleri](#2-faz-1--lokal-katman-iyileştirmeleri)
3. [Faz 2 — Firebase Entegrasyonu](#3-faz-2--firebase-entegrasyonu)
4. [Faz 3 — Sync Mekanizması](#4-faz-3--sync-mekanizması)
5. [Faz 4 — EKG Dalga Verisi Yedekleme](#5-faz-4--ekg-dalga-verisi-yedekleme)
6. [Faz 5 — Doktor Paylaşım ve Web Panel](#6-faz-5--doktor-paylaşım-ve-web-panel)
7. [Faz 6 — Güvenlik ve KVKK](#7-faz-6--güvenlik-ve-kvkk)
8. [Faz 7 — Test ve Doğrulama](#8-faz-7--test-ve-doğrulama)
9. [Veritabanı Şemaları](#9-veritabanı-şemaları)
10. [Maliyet Takvimi](#10-maliyet-takvimi)

---

## 1. Mimari Genel Bakış

```
┌──────────────────────────────────────────────────────────────────┐
│                        ANDROID CİHAZ                             │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Room DB (SQLCipher ile şifreli)                             │ │
│  │ ┌──────────┐ ┌──────────────┐ ┌────────────┐ ┌───────────┐ │ │
│  │ │  users   │ │ ecg_sessions │ │ ecg_alerts │ │device_info│ │ │
│  │ └──────────┘ └──────────────┘ └────────────┘ └───────────┘ │ │
│  │ ┌──────────────┐ ┌────────────────┐ ┌────────────────────┐ │ │
│  │ │ sync_status  │ │ ecg_recordings │ │ daily_summaries    │ │ │
│  │ │ (YENİ)       │ │ (YENİ)         │ │ (YENİ)             │ │ │
│  │ └──────────────┘ └────────────────┘ └────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Şifreli Dosya Sistemi (EncryptedFile API)                  │ │
│  │ /data/data/com.hayatinritmi.app/files/recordings/          │ │
│  │   ├── 2026-03-03_14-30-00_session_42.bin  (ham EKG)        │ │
│  │   ├── 2026-03-03_14-30-00_session_42.csv  (export)         │ │
│  │   └── 2026-03-03_14-30-00_session_42.pdf  (rapor)          │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ WorkManager Sync Workers                                   │ │
│  │ ┌────────────────┐ ┌────────────────┐ ┌──────────────────┐ │ │
│  │ │ MetadataSyncW. │ │ AlertSyncW.    │ │ WaveformBackupW.│ │ │
│  │ │ (6 saatte bir) │ │ (acil: anında) │ │ (WiFi + şarj)   │ │ │
│  │ └────────────────┘ └────────────────┘ └──────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                    HTTPS (TLS 1.3) + JWT
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                     FIREBASE (Cloud)                             │
│                                                                  │
│  ┌─────────────────┐   ┌─────────────────┐                      │
│  │ Firebase Auth   │   │ Cloud Messaging  │                      │
│  │ - Email/Pass    │   │ (Push Notif.)    │                      │
│  │ - Google Sign   │   │ - Alert bildirimi│                      │
│  │ - Anon (geçici) │   │ - Doktor yanıtı  │                      │
│  └─────────────────┘   └─────────────────┘                      │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Cloud Firestore                                            │ │
│  │ ├── users/{uid}/profile        (profil backup)             │ │
│  │ ├── users/{uid}/sessions/      (session özetleri)          │ │
│  │ ├── users/{uid}/alerts/        (alert geçmişi)             │ │
│  │ ├── users/{uid}/daily/         (günlük özetler)            │ │
│  │ └── shared_reports/{reportId}  (doktor paylaşımları)       │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Cloud Storage (opsiyonel — kullanıcı izin verirse)         │ │
│  │ └── waveforms/{uid}/{sessionId}.bin.enc                    │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Faz 1 — Lokal Katman İyileştirmeleri

> **Süre tahmini**: 3-4 gün
> **Bağımlılık**: Yok (hemen başlanabilir)

### 2.1 Yeni Room Entity'leri

- [ ] **2.1.1** `SyncStatusEntity` tablosu oluştur
  ```kotlin
  // Dosya: data/local/entity/SyncStatusEntity.kt
  @Entity(tableName = "sync_status")
  data class SyncStatusEntity(
      @PrimaryKey
      val entityType: String,     // "session", "alert", "profile"
      val entityId: Long,
      val syncState: String,      // "PENDING", "SYNCING", "SYNCED", "FAILED"
      val lastSyncAttemptMs: Long = 0,
      val lastSyncSuccessMs: Long = 0,
      val retryCount: Int = 0,
      val errorMessage: String? = null,
      val remoteId: String? = null // Firestore document ID
  )
  ```

- [ ] **2.1.2** `EcgRecordingEntity` tablosu oluştur (dalga verisi metadata ayrıştırma)
  ```kotlin
  // Dosya: data/local/entity/EcgRecordingEntity.kt
  @Entity(
      tableName = "ecg_recordings",
      foreignKeys = [ForeignKey(
          entity = EcgSessionEntity::class,
          parentColumns = ["id"],
          childColumns = ["sessionId"],
          onDelete = ForeignKey.CASCADE
      )],
      indices = [Index("sessionId")]
  )
  data class EcgRecordingEntity(
      @PrimaryKey(autoGenerate = true)
      val id: Long = 0,
      val sessionId: Long,
      val filePath: String,          // recordings/2026-03-03_xxx.bin
      val fileFormat: String,        // "BIN_INT16_LE", "CSV", "PDF"
      val fileSizeBytes: Long,
      val sampleRate: Int,           // 250 veya 500 Hz
      val channelCount: Int,         // 2 (göğüs bandı)
      val durationMs: Long,
      val checksumSha256: String,    // Bütünlük doğrulama
      val isBackedUp: Boolean = false,
      val backupUri: String? = null, // Cloud Storage URI
      val createdAt: Long = System.currentTimeMillis()
  )
  ```

- [ ] **2.1.3** `DailySummaryEntity` tablosu oluştur
  ```kotlin
  // Dosya: data/local/entity/DailySummaryEntity.kt
  @Entity(tableName = "daily_summaries")
  data class DailySummaryEntity(
      @PrimaryKey
      val dateStr: String,           // "2026-03-03"
      val userId: Long,
      val totalRecordingMs: Long = 0,
      val sessionCount: Int = 0,
      val avgBpm: Int = 0,
      val minBpm: Int = 0,
      val maxBpm: Int = 0,
      val alertCount: Int = 0,
      val criticalAlertCount: Int = 0,
      val avgQualityScore: Int = 0,
      val dominantAiLabel: String = "",
      val isSynced: Boolean = false
  )
  ```

- [ ] **2.1.4** `EcgSessionEntity`'ye sync alanları ekle
  ```kotlin
  // Mevcut entity'ye eklenecek alanlar:
  val isSynced: Boolean = false,
  val remoteId: String? = null,    // firestore doc ID
  val syncedAt: Long? = null
  ```

### 2.2 Yeni DAO'lar

- [ ] **2.2.1** `SyncStatusDao` oluştur
  ```kotlin
  // Dosya: data/local/dao/SyncStatusDao.kt
  @Dao
  interface SyncStatusDao {
      @Query("SELECT * FROM sync_status WHERE syncState = 'PENDING' OR syncState = 'FAILED' ORDER BY lastSyncAttemptMs ASC LIMIT :limit")
      suspend fun getPendingItems(limit: Int = 50): List<SyncStatusEntity>

      @Query("SELECT COUNT(*) FROM sync_status WHERE syncState = 'PENDING'")
      fun getPendingCountFlow(): Flow<Int>

      @Insert(onConflict = OnConflictStrategy.REPLACE)
      suspend fun upsert(status: SyncStatusEntity)

      @Query("UPDATE sync_status SET syncState = :state, lastSyncAttemptMs = :now, retryCount = retryCount + 1 WHERE entityType = :type AND entityId = :id")
      suspend fun markAttempted(type: String, id: Long, state: String, now: Long = System.currentTimeMillis())

      @Query("UPDATE sync_status SET syncState = 'SYNCED', lastSyncSuccessMs = :now, remoteId = :remoteId WHERE entityType = :type AND entityId = :id")
      suspend fun markSynced(type: String, id: Long, remoteId: String, now: Long = System.currentTimeMillis())

      @Query("DELETE FROM sync_status WHERE syncState = 'SYNCED' AND lastSyncSuccessMs < :before")
      suspend fun cleanOldSynced(before: Long)
  }
  ```

- [ ] **2.2.2** `EcgRecordingDao` oluştur
  ```kotlin
  @Dao
  interface EcgRecordingDao {
      @Query("SELECT * FROM ecg_recordings WHERE sessionId = :sessionId")
      suspend fun getBySession(sessionId: Long): List<EcgRecordingEntity>

      @Query("SELECT * FROM ecg_recordings WHERE isBackedUp = 0 ORDER BY createdAt ASC LIMIT :limit")
      suspend fun getUnbackedUp(limit: Int = 10): List<EcgRecordingEntity>

      @Insert
      suspend fun insert(recording: EcgRecordingEntity): Long

      @Query("UPDATE ecg_recordings SET isBackedUp = 1, backupUri = :uri WHERE id = :id")
      suspend fun markBackedUp(id: Long, uri: String)

      @Query("SELECT SUM(fileSizeBytes) FROM ecg_recordings WHERE sessionId IN (SELECT id FROM ecg_sessions WHERE userId = :userId)")
      suspend fun getTotalStorageBytes(userId: Long): Long?
  }
  ```

- [ ] **2.2.3** `DailySummaryDao` oluştur
  ```kotlin
  @Dao
  interface DailySummaryDao {
      @Query("SELECT * FROM daily_summaries WHERE userId = :userId ORDER BY dateStr DESC LIMIT :limit")
      suspend fun getRecent(userId: Long, limit: Int = 30): List<DailySummaryEntity>

      @Insert(onConflict = OnConflictStrategy.REPLACE)
      suspend fun upsert(summary: DailySummaryEntity)

      @Query("SELECT * FROM daily_summaries WHERE userId = :userId AND isSynced = 0")
      suspend fun getUnsynced(userId: Long): List<DailySummaryEntity>
  }
  ```

### 2.3 Room Migration

- [ ] **2.3.1** `Migration_1_2` sınıfı yaz
  ```kotlin
  // Dosya: data/local/migration/Migration_1_2.kt
  val MIGRATION_1_2 = object : Migration(1, 2) {
      override fun migrate(db: SupportSQLiteDatabase) {
          // sync_status tablosu
          db.execSQL("""
              CREATE TABLE IF NOT EXISTS sync_status (
                  entityType TEXT NOT NULL,
                  entityId INTEGER NOT NULL,
                  syncState TEXT NOT NULL DEFAULT 'PENDING',
                  lastSyncAttemptMs INTEGER NOT NULL DEFAULT 0,
                  lastSyncSuccessMs INTEGER NOT NULL DEFAULT 0,
                  retryCount INTEGER NOT NULL DEFAULT 0,
                  errorMessage TEXT,
                  remoteId TEXT,
                  PRIMARY KEY (entityType, entityId)
              )
          """)

          // ecg_recordings tablosu
          db.execSQL("""
              CREATE TABLE IF NOT EXISTS ecg_recordings (
                  id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                  sessionId INTEGER NOT NULL,
                  filePath TEXT NOT NULL,
                  fileFormat TEXT NOT NULL,
                  fileSizeBytes INTEGER NOT NULL,
                  sampleRate INTEGER NOT NULL,
                  channelCount INTEGER NOT NULL,
                  durationMs INTEGER NOT NULL,
                  checksumSha256 TEXT NOT NULL,
                  isBackedUp INTEGER NOT NULL DEFAULT 0,
                  backupUri TEXT,
                  createdAt INTEGER NOT NULL,
                  FOREIGN KEY (sessionId) REFERENCES ecg_sessions(id) ON DELETE CASCADE
              )
          """)
          db.execSQL("CREATE INDEX IF NOT EXISTS index_ecg_recordings_sessionId ON ecg_recordings(sessionId)")

          // daily_summaries tablosu
          db.execSQL("""
              CREATE TABLE IF NOT EXISTS daily_summaries (
                  dateStr TEXT NOT NULL PRIMARY KEY,
                  userId INTEGER NOT NULL,
                  totalRecordingMs INTEGER NOT NULL DEFAULT 0,
                  sessionCount INTEGER NOT NULL DEFAULT 0,
                  avgBpm INTEGER NOT NULL DEFAULT 0,
                  minBpm INTEGER NOT NULL DEFAULT 0,
                  maxBpm INTEGER NOT NULL DEFAULT 0,
                  alertCount INTEGER NOT NULL DEFAULT 0,
                  criticalAlertCount INTEGER NOT NULL DEFAULT 0,
                  avgQualityScore INTEGER NOT NULL DEFAULT 0,
                  dominantAiLabel TEXT NOT NULL DEFAULT '',
                  isSynced INTEGER NOT NULL DEFAULT 0
              )
          """)

          // ecg_sessions'a yeni sütunlar
          db.execSQL("ALTER TABLE ecg_sessions ADD COLUMN isSynced INTEGER NOT NULL DEFAULT 0")
          db.execSQL("ALTER TABLE ecg_sessions ADD COLUMN remoteId TEXT")
          db.execSQL("ALTER TABLE ecg_sessions ADD COLUMN syncedAt INTEGER")
      }
  }
  ```
- [ ] **2.3.2** `DatabaseModule.kt`'de migration'ı kaydet
  ```kotlin
  .addMigrations(MIGRATION_1_2)
  // .fallbackToDestructiveMigration() → KALDIR (veri kaybı olur!)
  ```

### 2.4 Şifreli Dosya Depolama

- [ ] **2.4.1** `EncryptedRecordingStorage` sınıfı oluştur
  ```kotlin
  // Dosya: data/storage/EncryptedRecordingStorage.kt
  class EncryptedRecordingStorage(private val context: Context) {

      private val recordingsDir: File
          get() = File(context.filesDir, "recordings").also { it.mkdirs() }

      fun saveRecording(
          sessionId: Long,
          ecgData: ShortArray,     // 2-lead interleaved
          sampleRate: Int,
          channelCount: Int
      ): RecordingResult {
          val timestamp = SimpleDateFormat("yyyy-MM-dd_HH-mm-ss", Locale.US).format(Date())
          val fileName = "${timestamp}_session_${sessionId}.bin"
          val file = File(recordingsDir, fileName)

          // AES-256 GCM ile şifrele
          val encryptedFile = EncryptedFile.Builder(
              context,
              file,
              MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build(),
              EncryptedFile.FileEncryptionScheme.AES256_GCM_HKDF_4KB
          ).build()

          encryptedFile.openFileOutput().use { stream ->
              // Header: sampleRate(4) + channelCount(4) + sampleCount(8)
              val header = ByteBuffer.allocate(16).order(ByteOrder.LITTLE_ENDIAN)
              header.putInt(sampleRate)
              header.putInt(channelCount)
              header.putLong(ecgData.size.toLong())
              stream.write(header.array())

              // Data: int16 LE interleaved
              val buffer = ByteBuffer.allocate(ecgData.size * 2).order(ByteOrder.LITTLE_ENDIAN)
              ecgData.forEach { buffer.putShort(it) }
              stream.write(buffer.array())
          }

          // SHA-256 checksum
          val checksum = MessageDigest.getInstance("SHA-256")
              .digest(file.readBytes())
              .joinToString("") { "%02x".format(it) }

          return RecordingResult(
              filePath = file.absolutePath,
              fileSizeBytes = file.length(),
              checksumSha256 = checksum
          )
      }

      fun readRecording(filePath: String): EcgWaveformData { ... }
      fun deleteRecording(filePath: String): Boolean { ... }
      fun getTotalStorageUsed(): Long { ... }
  }
  ```

- [ ] **2.4.2** `RecordingResult` data class oluştur
- [ ] **2.4.3** `EcgWaveformData` data class oluştur
- [ ] **2.4.4** Eski `filePath` tabanlı sistemi yeni yapıya migrate et

### 2.5 Otomatik Günlük Özet Hesaplama

- [ ] **2.5.1** `DailySummaryCalculator` sınıfı oluştur
  ```kotlin
  // Dosya: domain/usecase/CalculateDailySummaryUseCase.kt
  class CalculateDailySummaryUseCase(
      private val sessionDao: EcgSessionDao,
      private val alertDao: EcgAlertDao,
      private val summaryDao: DailySummaryDao
  ) {
      suspend fun calculateForDate(userId: Long, date: LocalDate) {
          val startMs = date.atStartOfDay().toInstant(ZoneOffset.UTC).toEpochMilli()
          val endMs = startMs + 86_400_000

          val sessions = sessionDao.getSessionsInRange(userId, startMs, endMs)
          val alerts = alertDao.getAlertsInRange(startMs, endMs)

          val summary = DailySummaryEntity(
              dateStr = date.toString(),
              userId = userId,
              totalRecordingMs = sessions.sumOf { it.durationMs },
              sessionCount = sessions.size,
              avgBpm = sessions.map { it.avgBpm }.filter { it > 0 }.average().toInt(),
              minBpm = sessions.minOfOrNull { it.minBpm } ?: 0,
              maxBpm = sessions.maxOfOrNull { it.maxBpm } ?: 0,
              alertCount = alerts.size,
              criticalAlertCount = alerts.count { it.level == "CRITICAL" },
              avgQualityScore = sessions.map { it.qualityScore }.average().toInt(),
              dominantAiLabel = sessions.groupBy { it.aiLabel }
                  .maxByOrNull { it.value.size }?.key ?: ""
          )
          summaryDao.upsert(summary)
      }
  }
  ```

- [ ] **2.5.2** Gece yarısı (00:05) otomatik tetikleme için WorkManager job'ı ekle

---

## 3. Faz 2 — Firebase Entegrasyonu

> **Süre tahmini**: 4-5 gün
> **Bağımlılık**: Firebase console'da proje oluşturulmuş olmalı

### 3.1 Firebase Proje Kurulumu

- [ ] **3.1.1** Firebase Console'da proje oluştur: `hayatin-ritmi`
- [ ] **3.1.2** Android uygulamasını kaydet: `com.hayatinritmi.app`
- [ ] **3.1.3** `google-services.json` dosyasını `mobile/app/` altına koy
- [ ] **3.1.4** Firestore'u etkinleştir (location: `europe-west1`)
- [ ] **3.1.5** Cloud Storage'ı etkinleştir (location: aynı region)
- [ ] **3.1.6** Authentication'ı etkinleştir:
  - [ ] Email/Password provider
  - [ ] Google Sign-In provider
  - [ ] Anonymous provider (ilk kullanım)

### 3.2 Gradle Bağımlılıkları

- [ ] **3.2.1** `build.gradle.kts` (project level):
  ```kotlin
  plugins {
      id("com.google.gms.google-services") version "4.4.2" apply false
  }
  ```

- [ ] **3.2.2** `build.gradle.kts` (app level):
  ```kotlin
  plugins {
      id("com.google.gms.google-services")
  }

  dependencies {
      // Firebase BoM
      implementation(platform("com.google.firebase:firebase-bom:33.7.0"))
      implementation("com.google.firebase:firebase-auth-ktx")
      implementation("com.google.firebase:firebase-firestore-ktx")
      implementation("com.google.firebase:firebase-storage-ktx")
      implementation("com.google.firebase:firebase-messaging-ktx")
      implementation("com.google.firebase:firebase-analytics-ktx")
  }
  ```

### 3.3 Firebase Auth Entegrasyonu

- [ ] **3.3.1** `AuthRepository` interface oluştur
  ```kotlin
  // Dosya: domain/repository/AuthRepository.kt
  interface AuthRepository {
      val currentUser: Flow<FirebaseUser?>
      val isLoggedIn: Boolean
      suspend fun signUpWithEmail(email: String, password: String): Result<FirebaseUser>
      suspend fun signInWithEmail(email: String, password: String): Result<FirebaseUser>
      suspend fun signInWithGoogle(idToken: String): Result<FirebaseUser>
      suspend fun signOut()
      suspend fun deleteAccount()
      suspend fun sendPasswordReset(email: String): Result<Unit>
  }
  ```

- [ ] **3.3.2** `AuthRepositoryImpl` implement et
- [ ] **3.3.3** `AuthModule` Hilt DI modülü oluştur
- [ ] **3.3.4** Mevcut `LoginScreen` ve `SignUpScreen`'i Firebase Auth'a bağla
- [ ] **3.3.5** Mevcut Room `UserEntity` ile Firebase UID eşleştir
  ```kotlin
  // UserEntity'ye ekle:
  val firebaseUid: String? = null
  ```
- [ ] **3.3.6** İlk giriş: Room'daki lokal kullanıcıyı Firebase'e migrate et

### 3.4 Firestore Veri Modelleri

- [ ] **3.4.1** Firestore güvenlik kurallarını yaz
  ```javascript
  // firestore.rules
  rules_version = '2';
  service cloud.firestore {
    match /databases/{database}/documents {
      // Kullanıcı sadece kendi verisine erişebilir
      match /users/{userId}/{document=**} {
        allow read, write: if request.auth != null && request.auth.uid == userId;
      }
      // Paylaşılan raporlar — link bilen herkes okuyabilir
      match /shared_reports/{reportId} {
        allow read: if true;
        allow write: if request.auth != null
                     && request.auth.uid == resource.data.ownerUid;
      }
    }
  }
  ```

- [ ] **3.4.2** `FirestoreModels.kt` oluştur
  ```kotlin
  // Dosya: data/remote/model/FirestoreModels.kt

  data class RemoteUserProfile(
      val uid: String = "",
      val name: String = "",
      val surname: String = "",
      val phone: String = "",
      val bloodType: String = "",
      val emergencyContactName: String = "",
      val emergencyContactPhone: String = "",
      val doctorEmail: String = "",
      val createdAt: Timestamp = Timestamp.now(),
      val lastSyncedAt: Timestamp = Timestamp.now()
  )

  data class RemoteSessionSummary(
      val localId: Long = 0,
      val startTimeMs: Long = 0,
      val durationMs: Long = 0,
      val avgBpm: Int = 0,
      val minBpm: Int = 0,
      val maxBpm: Int = 0,
      val qualityScore: Int = 0,
      val aiLabel: String = "",
      val aiConfidence: Float = 0f,
      val sampleCount: Long = 0,
      val channelCount: Int = 2,
      val hasWaveformBackup: Boolean = false,
      val waveformUri: String? = null,
      val createdAt: Timestamp = Timestamp.now()
  )

  data class RemoteAlert(
      val localId: Long = 0,
      val sessionId: Long = 0,
      val timestampMs: Long = 0,
      val type: String = "",        // TACHY, BRADY, AF, ST_ANOMALY
      val level: String = "",       // INFO, WARNING, CRITICAL
      val details: String = "",
      val aiConfidence: Float = 0f,
      val bpm: Int = 0,
      val lat: Double? = null,
      val lon: Double? = null,
      val createdAt: Timestamp = Timestamp.now()
  )

  data class RemoteDailySummary(
      val dateStr: String = "",
      val totalRecordingMs: Long = 0,
      val sessionCount: Int = 0,
      val avgBpm: Int = 0,
      val minBpm: Int = 0,
      val maxBpm: Int = 0,
      val alertCount: Int = 0,
      val criticalAlertCount: Int = 0,
      val avgQualityScore: Int = 0,
      val dominantAiLabel: String = ""
  )
  ```

- [ ] **3.4.3** `FirestoreRepository` oluştur
  ```kotlin
  // Dosya: data/remote/FirestoreRepository.kt
  class FirestoreRepository(
      private val auth: FirebaseAuth,
      private val firestore: FirebaseFirestore
  ) {
      private val uid get() = auth.currentUser?.uid ?: throw IllegalStateException("Not logged in")

      // ─── Profil ────────────────────────────────
      suspend fun syncProfile(profile: RemoteUserProfile) { ... }
      suspend fun getProfile(): RemoteUserProfile? { ... }

      // ─── Session Özetleri ──────────────────────
      suspend fun uploadSessionSummary(summary: RemoteSessionSummary): String { ... } // returns docId
      suspend fun getSessionSummaries(limit: Int = 50): List<RemoteSessionSummary> { ... }

      // ─── Alertler ──────────────────────────────
      suspend fun uploadAlert(alert: RemoteAlert): String { ... }
      suspend fun getAlerts(since: Long): List<RemoteAlert> { ... }

      // ─── Günlük Özetler ────────────────────────
      suspend fun uploadDailySummary(summary: RemoteDailySummary) { ... }
      suspend fun getDailySummaries(days: Int = 30): List<RemoteDailySummary> { ... }
  }
  ```

---

## 4. Faz 3 — Sync Mekanizması

> **Süre tahmini**: 4-5 gün
> **Bağımlılık**: Faz 1 + Faz 2 tamamlanmış olmalı

### 4.1 Sync Stratejisi

```
┌─────────────────────────────────────────────────┐
│            SYNC PRİORİTE SIRASI                  │
│                                                  │
│  1. 🔴 CRITICAL ALERT  → ANINDA (hücresel bile) │
│  2. 🟡 Session summary → 6 saatte bir           │
│  3. 🟢 Profil backup   → Değiştiğinde           │
│  4. 🔵 Günlük özet     → Gece yarısı            │
│  5. ⚪ EKG waveform    → WiFi + şarj + opsiyonel│
│                                                  │
│  Retry: exponential backoff (1m→5m→15m→1h→6h)   │
│  Max retry: 10 deneme → kullanıcıya bildir       │
└─────────────────────────────────────────────────┘
```

### 4.2 Sync Worker'ları Yeniden Yazma

- [ ] **4.2.1** Mevcut `SessionSyncWorker` → `MetadataSyncWorker` olarak yeniden yaz
  ```kotlin
  // Dosya: sync/MetadataSyncWorker.kt
  @HiltWorker
  class MetadataSyncWorker @AssistedInject constructor(
      @Assisted appContext: Context,
      @Assisted workerParams: WorkerParameters,
      private val syncStatusDao: SyncStatusDao,
      private val sessionDao: EcgSessionDao,
      private val firestoreRepo: FirestoreRepository
  ) : CoroutineWorker(appContext, workerParams) {

      override suspend fun doWork(): Result {
          // 1. sync_status'ten PENDING olanları çek
          val pending = syncStatusDao.getPendingItems(limit = 50)
          if (pending.isEmpty()) return Result.success()

          var failCount = 0
          pending.forEach { item ->
              try {
                  when (item.entityType) {
                      "session" -> syncSession(item)
                      "alert" -> syncAlert(item)
                      "daily" -> syncDailySummary(item)
                  }
              } catch (e: Exception) {
                  failCount++
                  syncStatusDao.markAttempted(
                      item.entityType, item.entityId, "FAILED",
                  )
              }
          }

          return if (failCount < pending.size) Result.success()
                 else Result.retry()
      }

      private suspend fun syncSession(item: SyncStatusEntity) {
          val session = sessionDao.getById(item.entityId) ?: return
          val remote = session.toRemoteSessionSummary()
          val docId = firestoreRepo.uploadSessionSummary(remote)
          syncStatusDao.markSynced(item.entityType, item.entityId, docId)
          sessionDao.markSynced(item.entityId, docId)
      }
      // ... syncAlert, syncDailySummary benzer şekilde
  }
  ```

- [ ] **4.2.2** `AlertSyncWorker` oluştur (acil alertler için anında tetikleme)
  ```kotlin
  // Dosya: sync/AlertSyncWorker.kt
  // Constraint: NetworkType.CONNECTED (hücresel dahil)
  // OneTimeWorkRequest olarak çağrılacak
  ```

- [ ] **4.2.3** `ProfileSyncWorker` oluştur
  ```kotlin
  // Profil değiştiğinde tetiklenir
  // Kullanıcı adını, acil kişiyi, vb. Firestore'a yazar
  ```

### 4.3 SyncScheduler Güncellemesi

- [ ] **4.3.1** `SyncScheduler` yeniden yaz
  ```kotlin
  object SyncScheduler {
      fun schedulePeriodicMetadataSync(context: Context) {
          val constraints = Constraints.Builder()
              .setRequiredNetworkType(NetworkType.CONNECTED)
              .setRequiresBatteryNotLow(true)
              .build()

          val request = PeriodicWorkRequestBuilder<MetadataSyncWorker>(
              6, TimeUnit.HOURS,          // her 6 saatte
              30, TimeUnit.MINUTES        // ±30 dk flex
          ).setConstraints(constraints)
           .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 1, TimeUnit.MINUTES)
           .build()

          WorkManager.getInstance(context).enqueueUniquePeriodicWork(
              "metadata_sync", ExistingPeriodicWorkPolicy.UPDATE, request
          )
      }

      fun triggerImmediateAlertSync(context: Context) {
          val request = OneTimeWorkRequestBuilder<AlertSyncWorker>()
              .setConstraints(
                  Constraints.Builder()
                      .setRequiredNetworkType(NetworkType.CONNECTED)
                      .build()
              )
              .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)
              .build()

          WorkManager.getInstance(context).enqueue(request)
      }

      fun scheduleDailySummarySync(context: Context) { ... }
      fun scheduleWaveformBackup(context: Context) { ... }
  }
  ```

### 4.4 Conflict Resolution (Çakışma Çözümü)

- [ ] **4.4.1** `ConflictResolver` sınıfı oluştur
  ```kotlin
  // Strateji: "last-write-wins" + "local-priority"
  // Lokal veri her zaman doğrudur (cihaz = truth kaynağı)
  // Sunucu sadece backup ve paylaşım için kullanılır
  // Eğer iki cihazdan aynı hesap kullanılıyorsa,
  // en son yazılan kazanır (lastSyncedAt karşılaştırması)
  ```

- [ ] **4.4.2** Multi-device senaryosu tanımla
  ```
  Senaryo: Kullanıcı eski telefondan yeni telefona geçiyor
  1. Yeni telefonda giriş yapar
  2. Firestore'dan profil + session özetleri çekilir
  3. Lokal Room DB populate edilir
  4. Eski telefondaki ham EKG verisi → yeni telefona TAŞINMAZ
     (çok büyük, sadece özet bilgi sync olur)
  ```

### 4.5 Sync Durumu UI

- [ ] **4.5.1** `SyncStatusViewModel` oluştur
  ```kotlin
  // SettingsScreen'de gösterilecek:
  // - Son sync zamanı
  // - Bekleyen öğe sayısı
  // - Toplam sync edilen kayıt
  // - "Şimdi Senkronize Et" butonu
  ```

- [ ] **4.5.2** `SettingsScreen`'e sync durumu section'ı ekle
  ```
  ┌─────────────────────────────────┐
  │ 🔄 Senkronizasyon               │
  │                                  │
  │ Son sync: 14:30 (2 saat önce)   │
  │ Bekleyen: 3 session, 1 alert    │
  │ Toplam: 142 kayıt synced ✅     │
  │                                  │
  │ [  Şimdi Senkronize Et  ]       │
  │                                  │
  │ ☁️ EKG Dalga Yedekleme: KAPALI  │
  │ (WiFi gerekli, ~54 MB/ay)       │
  │ [  Toggle ON/OFF  ]             │
  └─────────────────────────────────┘
  ```

- [ ] **4.5.3** Sync hata bildirimi (notification) ekle

---

## 5. Faz 4 — EKG Dalga Verisi Yedekleme (Opsiyonel)

> **Süre tahmini**: 3 gün
> **Bağımlılık**: Faz 3 tamamlanmış olmalı
> **Tetikleme**: Kullanıcı ayarlardan "EKG Yedekleme" toggle'ını açarsa

### 5.1 Cloud Storage Yapısı

```
Firebase Cloud Storage yapısı:
gs://hayatin-ritmi.appspot.com/
└── waveforms/
    └── {user_uid}/
        ├── 2026-03-03_14-30-00_session_42.bin.enc
        ├── 2026-03-03_15-00-00_session_43.bin.enc
        └── manifest.json  ← hangi dosyaların yüklendiği
```

### 5.2 Uygulama Adımları

- [ ] **5.2.1** `WaveformBackupWorker` oluştur
  ```kotlin
  // Constraints:
  // - NetworkType.UNMETERED (sadece WiFi)
  // - RequiresCharging(true) (sadece şarjda)
  // - StorageNotLow(true)
  // Periyot: Günde 1 kez (gece)
  ```

- [ ] **5.2.2** Upload progress tracking
  ```kotlin
  // Büyük dosyalar için progress:
  // - Dosya zaten şifreli (EncryptedFile ile)
  // - Firebase Storage resumable upload kullan
  // - Upload sırasında foreground notification göster
  ```

- [ ] **5.2.3** `WaveformRestoreWorker` oluştur (cihaz değişiminde)
  ```kotlin
  // Yeni cihazda kullanıcı "Geçmiş EKG'leri İndir" derse:
  // - manifest.json'ı çek
  // - Her dosyayı indir + decrypt
  // - ecg_recordings tablosunu güncelle
  ```

- [ ] **5.2.4** Storage Security Rules
  ```javascript
  // storage.rules
  rules_version = '2';
  service firebase.storage {
    match /b/{bucket}/o {
      match /waveforms/{userId}/{allPaths=**} {
        allow read, write: if request.auth != null
                          && request.auth.uid == userId;
        allow read, write: if request.resource.size < 200 * 1024 * 1024; // max 200 MB
      }
    }
  }
  ```

- [ ] **5.2.5** Depolama limiti uyarısı
  ```
  Kullanıcı başına limit: 2 GB (Free tier)
  %80 dolduğunda → uyarı göster
  %100 dolduğunda → eski kayıtları silme öner
  ```

---

## 6. Faz 5 — Doktor Paylaşım ve Web Panel

> **Süre tahmini**: 5-7 gün
> **Bağımlılık**: Faz 3 tamamlanmış olmalı
> **Öncelik**: Düşük (prototip sonrası)

### 6.1 Paylaşım Link Mekanizması

- [ ] **6.1.1** `SharedReport` modeli oluştur
  ```kotlin
  data class SharedReport(
      val reportId: String = UUID.randomUUID().toString(),
      val ownerUid: String = "",
      val recipientEmail: String = "",   // doktor email
      val sessionIds: List<Long> = emptyList(),
      val includeWaveform: Boolean = false,
      val expiresAt: Timestamp? = null,  // opsiyonel son kullanma
      val accessCount: Int = 0,
      val createdAt: Timestamp = Timestamp.now(),
      val notes: String = ""             // hasta notu
  )
  ```

- [ ] **6.1.2** Paylaşım URL formatı
  ```
  https://hayatinritmi.web.app/report/{reportId}
  ```

- [ ] **6.1.3** `ReportsScreen`'de paylaşım butonu ekle
  ```
  Session detayında → "Doktora Gönder" butonu
  1. Doktor email iste
  2. Session özeti + (opsiyonel) EKG PDF oluştur
  3. Firestore shared_reports'a yaz
  4. Doktora email gönder (Firebase Extensions ile)
  ```

### 6.2 Doktor Web Paneli (Firebase Hosting)

- [ ] **6.2.1** Basit web sayfası (React/plain HTML)
  ```
  /report/{reportId} sayfası:
  - Hasta adı (kısaltılmış: M. Y.)
  - Session tarihi, süresi
  - BPM istatistikleri (min/avg/max)
  - AI tahminleri ve güven skorları
  - EKG grafiği (waveform varsa)
  - PDF indirme butonu
  ```

- [ ] **6.2.2** Firebase Hosting ile deploy et
- [ ] **6.2.3** Link son kullanma (expiry) mekanizması

---

## 7. Faz 6 — Güvenlik ve KVKK

> **Süre tahmini**: 2-3 gün
> **Bağımlılık**: Tüm fazlar

### 7.1 Veri Şifreleme Katmanları

```
Katman 1: Cihazda (at rest)
├── Room DB → SQLCipher (AES-256-CBC)
├── EKG dosyaları → EncryptedFile (AES-256-GCM)
└── DB anahtarı → Android Keystore

Katman 2: İletimde (in transit)
├── HTTPS (TLS 1.3)
└── Certificate pinning (opsiyonel)

Katman 3: Sunucuda (at rest)
├── Firestore → Google-managed encryption (AES-256)
└── Cloud Storage → Google-managed encryption
```

- [ ] **7.1.1** Certificate pinning ekle (Retrofit/OkHttp ile)
- [ ] **7.1.2** Network security config dosyası oluştur
  ```xml
  <!-- res/xml/network_security_config.xml -->
  <network-security-config>
      <domain-config cleartextTrafficPermitted="false">
          <domain includeSubdomains="true">firestore.googleapis.com</domain>
          <domain includeSubdomains="true">storage.googleapis.com</domain>
      </domain-config>
  </network-security-config>
  ```

### 7.2 KVKK Uyumluluk Kontrol Listesi

- [ ] **7.2.1** Uygulama ilk açılışta KVKK aydınlatma metni göster
- [ ] **7.2.2** Açık rıza formu (checkbox):
  - [ ] "Sağlık verilerimin işlenmesini kabul ediyorum"
  - [ ] "Verilerimin bulutta yedeklenmesini kabul ediyorum" (opsiyonel)
  - [ ] "Acil durumlarda konum bilgimin paylaşılmasını kabul ediyorum"
- [ ] **7.2.3** "Verilerimi Sil" butonu (KVKK md. 11)
  ```kotlin
  // Tüm verileri siler:
  // 1. Firestore'daki tüm kullanıcı dökümanları
  // 2. Cloud Storage'daki tüm dosyalar
  // 3. Firebase Auth hesabı
  // 4. Lokal Room DB
  // 5. Lokal dosyalar (recordings/)
  ```
- [ ] **7.2.4** Veri export butonu (KVKK md. 11 - taşınabilirlik hakkı)
  ```kotlin
  // JSON formatında tüm veriyi dışa aktar:
  // - Profil bilgileri
  // - Session özetleri
  // - Alert geçmişi
  // - (Opsiyonel) EKG waveform dosyaları
  ```
- [ ] **7.2.5** Otomatik veri silme politikası
  ```
  90 gün kullanılmayan hesap → uyarı email
  180 gün → veri silme bildirimi
  210 gün → otomatik silme
  ```

### 7.3 Sağlık Verisi Özel Gereksinimleri

- [ ] **7.3.1** Audit log tutma (kim ne zaman erişti)
- [ ] **7.3.2** Paylaşılan raporlarda minimum veri ilkesi
  ```
  Doktora gönderilen raporda:
  ✅ AI sonucu, BPM, EKG grafiği
  ❌ Tam isim (sadece inisyal), telefon, adres
  ```
- [ ] **7.3.3** Veri lokasyonu belgeleme
  ```
  Prototip: Firebase EU (europe-west1)
  Ürün: Türkiye'de self-host (KVKK tam uyum)
  ```

---

## 8. Faz 7 — Test ve Doğrulama

> **Süre tahmini**: 3-4 gün
> **Bağımlılık**: İlgili fazın tamamlanması

### 8.1 Unit Testler

- [ ] **8.1.1** `SyncStatusDao` testleri
- [ ] **8.1.2** `EcgRecordingDao` testleri
- [ ] **8.1.3** `DailySummaryDao` testleri
- [ ] **8.1.4** `CalculateDailySummaryUseCase` testleri
- [ ] **8.1.5** `ConflictResolver` testleri
- [ ] **8.1.6** Room migration testleri (`MigrationTestHelper`)

### 8.2 Entegrasyon Testleri

- [ ] **8.2.1** Offline → Online sync senaryosu
  ```
  1. Airplane mode'da 5 session kaydet
  2. WiFi aç
  3. Tüm session'ların Firestore'a sync olduğunu doğrula
  4. sync_status tablosundaki durumları kontrol et
  ```
- [ ] **8.2.2** Multi-device senaryosu
  ```
  1. Cihaz A'da hesap oluştur, 3 session kaydet
  2. Cihaz B'de aynı hesapla giriş yap
  3. Session özetlerinin B'ye geldiğini doğrula
  4. EKG waveform'un GELMEDİĞİNİ doğrula (opsiyonel)
  ```
- [ ] **8.2.3** Büyük veri senaryosu
  ```
  - 1000 session kaydı oluştur
  - Sync performansını ölç (süre, bellek)
  - Firestore batch write limitlerini test et (500 doc/batch)
  ```
- [ ] **8.2.4** Ağ kesintisi senaryosu
  ```
  - Upload sırasında WiFi kapat
  - Worker'ın retry mekanizmasını doğrula
  - Kısmi upload sonrası tutarlılığı kontrol et
  ```

### 8.3 Güvenlik Testleri

- [ ] **8.3.1** SQLCipher şifreleme doğrulaması (DB dosyasını hex editor ile aç)
- [ ] **8.3.2** EncryptedFile doğrulaması (bin dosyasını okumaya çalış)
- [ ] **8.3.3** Firestore security rules test (başka kullanıcının verisine erişim)
- [ ] **8.3.4** Firebase App Check entegrasyonu (bot koruması)

### 8.4 Performans Testleri

- [ ] **8.4.1** Room query performansı (10K+ session ile)
- [ ] **8.4.2** Sync worker memory footprint
- [ ] **8.4.3** Cloud Storage upload hızı (farklı dosya boyutları)
- [ ] **8.4.4** Pil tüketimi ölçümü (sync sırasında)

---

## 9. Veritabanı Şemaları

### 9.1 Room (Lokal) — Tam Şema

```sql
-- Mevcut tablolar (güncellendi)
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    surname TEXT NOT NULL,
    phone TEXT NOT NULL,
    bloodType TEXT DEFAULT '',
    emergencyContactName TEXT DEFAULT '',
    emergencyContactPhone TEXT DEFAULT '',
    doctorEmail TEXT DEFAULT '',
    profilePhotoUri TEXT,
    passwordHash TEXT NOT NULL,
    salt TEXT NOT NULL,
    createdAt INTEGER NOT NULL,
    biometricEnabled INTEGER NOT NULL DEFAULT 0,
    firebaseUid TEXT                           -- YENİ
);

CREATE TABLE ecg_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    userId INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    startTimeMs INTEGER NOT NULL,
    durationMs INTEGER DEFAULT 0,
    avgBpm INTEGER DEFAULT 0,
    minBpm INTEGER DEFAULT 0,
    maxBpm INTEGER DEFAULT 0,
    filePath TEXT DEFAULT '',
    qualityScore INTEGER DEFAULT 0,
    aiLabel TEXT DEFAULT '',
    aiConfidence REAL DEFAULT 0,
    notes TEXT DEFAULT '',
    sampleCount INTEGER DEFAULT 0,
    channelCount INTEGER DEFAULT 12,
    isExported INTEGER DEFAULT 0,
    isSynced INTEGER DEFAULT 0,               -- YENİ
    remoteId TEXT,                             -- YENİ
    syncedAt INTEGER                           -- YENİ
);

CREATE TABLE ecg_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sessionId INTEGER NOT NULL REFERENCES ecg_sessions(id) ON DELETE CASCADE,
    timestampMs INTEGER NOT NULL,
    type TEXT NOT NULL,
    level TEXT NOT NULL,
    details TEXT DEFAULT '',
    aiConfidence REAL DEFAULT 0,
    bpm INTEGER DEFAULT 0,
    lat REAL,
    lon REAL,
    isRead INTEGER DEFAULT 0
);

CREATE TABLE device_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mac TEXT NOT NULL,
    name TEXT NOT NULL,
    lastConnectedMs INTEGER NOT NULL,
    firmwareVersion TEXT DEFAULT '',
    batteryPercent INTEGER DEFAULT -1
);

-- Yeni tablolar
CREATE TABLE sync_status (
    entityType TEXT NOT NULL,
    entityId INTEGER NOT NULL,
    syncState TEXT NOT NULL DEFAULT 'PENDING',
    lastSyncAttemptMs INTEGER NOT NULL DEFAULT 0,
    lastSyncSuccessMs INTEGER NOT NULL DEFAULT 0,
    retryCount INTEGER NOT NULL DEFAULT 0,
    errorMessage TEXT,
    remoteId TEXT,
    PRIMARY KEY (entityType, entityId)
);

CREATE TABLE ecg_recordings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sessionId INTEGER NOT NULL REFERENCES ecg_sessions(id) ON DELETE CASCADE,
    filePath TEXT NOT NULL,
    fileFormat TEXT NOT NULL,
    fileSizeBytes INTEGER NOT NULL,
    sampleRate INTEGER NOT NULL,
    channelCount INTEGER NOT NULL,
    durationMs INTEGER NOT NULL,
    checksumSha256 TEXT NOT NULL,
    isBackedUp INTEGER DEFAULT 0,
    backupUri TEXT,
    createdAt INTEGER NOT NULL
);

CREATE TABLE daily_summaries (
    dateStr TEXT PRIMARY KEY,
    userId INTEGER NOT NULL,
    totalRecordingMs INTEGER DEFAULT 0,
    sessionCount INTEGER DEFAULT 0,
    avgBpm INTEGER DEFAULT 0,
    minBpm INTEGER DEFAULT 0,
    maxBpm INTEGER DEFAULT 0,
    alertCount INTEGER DEFAULT 0,
    criticalAlertCount INTEGER DEFAULT 0,
    avgQualityScore INTEGER DEFAULT 0,
    dominantAiLabel TEXT DEFAULT '',
    isSynced INTEGER DEFAULT 0
);
```

### 9.2 Firestore (Cloud) — Koleksiyon Yapısı

```
firestore/
├── users/{uid}/
│   ├── profile (document)
│   │   ├── name: string
│   │   ├── surname: string
│   │   ├── phone: string
│   │   ├── bloodType: string
│   │   ├── emergencyContactName: string
│   │   ├── emergencyContactPhone: string
│   │   ├── doctorEmail: string
│   │   ├── createdAt: timestamp
│   │   └── lastSyncedAt: timestamp
│   │
│   ├── sessions/ (subcollection)
│   │   └── {sessionDocId}/
│   │       ├── localId: number
│   │       ├── startTimeMs: number
│   │       ├── durationMs: number
│   │       ├── avgBpm: number
│   │       ├── minBpm: number
│   │       ├── maxBpm: number
│   │       ├── qualityScore: number
│   │       ├── aiLabel: string
│   │       ├── aiConfidence: number
│   │       ├── sampleCount: number
│   │       ├── channelCount: number
│   │       ├── hasWaveformBackup: boolean
│   │       ├── waveformUri: string?
│   │       └── createdAt: timestamp
│   │
│   ├── alerts/ (subcollection)
│   │   └── {alertDocId}/
│   │       ├── localId: number
│   │       ├── sessionId: number
│   │       ├── timestampMs: number
│   │       ├── type: string
│   │       ├── level: string
│   │       ├── details: string
│   │       ├── aiConfidence: number
│   │       ├── bpm: number
│   │       ├── lat: number?
│   │       ├── lon: number?
│   │       └── createdAt: timestamp
│   │
│   └── daily/ (subcollection)
│       └── {dateStr}/
│           ├── totalRecordingMs: number
│           ├── sessionCount: number
│           ├── avgBpm: number
│           ├── minBpm: number
│           ├── maxBpm: number
│           ├── alertCount: number
│           ├── criticalAlertCount: number
│           ├── avgQualityScore: number
│           └── dominantAiLabel: string
│
└── shared_reports/{reportId}/
    ├── ownerUid: string
    ├── recipientEmail: string
    ├── sessionIds: number[]
    ├── includeWaveform: boolean
    ├── expiresAt: timestamp?
    ├── accessCount: number
    ├── createdAt: timestamp
    └── notes: string
```

---

## 10. Maliyet Takvimi

### Tahmini Geliştirme Süresi

| Faz | Açıklama | Süre | Bağımlılık |
|-----|----------|------|------------|
| **Faz 1** | Lokal katman iyileştirmeleri | 3-4 gün | - |
| **Faz 2** | Firebase entegrasyonu | 4-5 gün | Firebase Console |
| **Faz 3** | Sync mekanizması | 4-5 gün | Faz 1 + 2 |
| **Faz 4** | EKG dalga yedekleme | 3 gün | Faz 3 |
| **Faz 5** | Doktor paylaşım + web | 5-7 gün | Faz 3 |
| **Faz 6** | Güvenlik + KVKK | 2-3 gün | Tüm fazlar |
| **Faz 7** | Test + doğrulama | 3-4 gün | İlgili faz |
| **Toplam** | | **~25-30 gün** | |

### Aylık İşletme Maliyeti

| Kullanıcı Sayısı | Firebase (metadata) | Storage (opsiyonel) | Toplam |
|-------------------|--------------------|--------------------|--------|
| 100 (prototip) | $0 | $0 | **$0/ay** |
| 500 (pilot) | $0 | $0 | **$0/ay** |
| 1,000 | ~$5 | ~$3 | **~$8/ay** |
| 5,000 | ~$25 | ~$15 | **~$40/ay** |
| 10,000 | ~$50 | ~$50 | **~$100/ay** |

> **Not**: Sadece metadata sync edilirse (EKG waveform hariç), maliyet prototip
> aşamasında tamamen **$0**'dır. Firebase Spark planı yeterlidir.

---

## 📌 Hemen Başlanabilecek Adımlar

1. ✅ Firebase Console'da proje oluştur
2. ✅ `google-services.json` dosyasını al
3. ✅ Faz 1.1-1.3: Yeni Room entity'leri oluştur
4. ✅ Faz 1.4: Migration yaz ve test et
5. ✅ Faz 2.2: Gradle bağımlılıklarını ekle

Bunlar tamamlandığında Faz 3'e (Sync) geçilir.
