package com.hayatinritmi.app.presentation.viewmodel

import android.annotation.SuppressLint
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.location.Location
import android.net.Uri
import android.telephony.SmsManager
import android.app.PendingIntent
import androidx.core.content.ContextCompat
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.hayatinritmi.app.domain.model.AlertEvent
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.google.android.gms.tasks.CancellationTokenSource
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await
import kotlinx.coroutines.withTimeoutOrNull

/**
 * Acil durum sistemi ViewModel.
 *
 * Sorumluluklar:
 *  - GPS konum alma (FusedLocationProviderClient)
 *  - Kayıtlı acil kişilere SMS gönderme (SmsManager)
 *  - 112 arama (ACTION_CALL)
 */
class EmergencyViewModel(private val context: Context) : ViewModel() {

    private val _smsSent = MutableStateFlow(false)
    val smsSent: StateFlow<Boolean> = _smsSent.asStateFlow()

    private val _smsError = MutableStateFlow<String?>(null)
    val smsError: StateFlow<String?> = _smsError.asStateFlow()

    private val _currentLocation = MutableStateFlow<Pair<Double, Double>?>(null)
    val currentLocation: StateFlow<Pair<Double, Double>?> = _currentLocation.asStateFlow()

    private val _locationLoading = MutableStateFlow(false)
    val locationLoading: StateFlow<Boolean> = _locationLoading.asStateFlow()

    private val fusedLocationClient = LocationServices.getFusedLocationProviderClient(context)

    var emergencyContactPhone: String = ""
    var emergencyContactName: String = "Acil Kişi"
    var userName: String = "Kullanıcı"

    /** GPS konum al — 10s timeout, HIGH_ACCURACY */
    @SuppressLint("MissingPermission")
    fun fetchLocation() {
        if (!hasLocationPermission()) return
        _locationLoading.value = true
        viewModelScope.launch {
            try {
                val cancellationToken = CancellationTokenSource()
                val location: Location? = withTimeoutOrNull(10_000L) {
                    fusedLocationClient.getCurrentLocation(
                        Priority.PRIORITY_HIGH_ACCURACY,
                        cancellationToken.token
                    ).await()
                }
                if (location != null) {
                    _currentLocation.value = Pair(location.latitude, location.longitude)
                }
            } catch (_: Exception) {
                // Konum alınamadı — devam et
            } finally {
                _locationLoading.value = false
            }
        }
    }

    private fun hasLocationPermission(): Boolean {
        return ContextCompat.checkSelfPermission(
            context, android.Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
    }

    /**
     * Acil durum SMS'i gönder — önce konumu al, sonra SMS at.
     */
    fun sendEmergencyAlert(event: AlertEvent) {
        viewModelScope.launch {
            // Konum mevcut değilse bir kez dene
            if (_currentLocation.value == null) {
                fetchLocation()
                // Kısa bekleme — konum gelebilir veya gelmez
                kotlinx.coroutines.delay(3000)
            }
            val loc = _currentLocation.value
            sendSms(
                lat = loc?.first ?: event.lat,
                lon = loc?.second ?: event.lon,
                bpm = event.bpm,
                aiLabel = event.aiPrediction?.label?.displayName ?: "Belirsiz"
            )
        }
    }

    fun callEmergencyServices() {
        try {
            val intent = Intent(Intent.ACTION_CALL, Uri.parse("tel:112")).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(intent)
        } catch (e: SecurityException) {
            _smsError.value = "Arama izni verilmedi — Ayarlar'dan izin verin."
        } catch (e: Exception) {
            _smsError.value = "Arama başlatılamadı: ${e.message}"
        }
    }

    private fun sendSms(lat: Double?, lon: Double?, bpm: Int, aiLabel: String) {
        if (emergencyContactPhone.isBlank()) {
            _smsError.value = "Acil durum kişisi tanımlanmamış. Ayarlar'dan ekleyin."
            return
        }

        val locationStr = if (lat != null && lon != null)
            "https://maps.google.com/?q=$lat,$lon"
        else "Konum alınamadı"

        val smsBody = buildString {
            appendLine("[ACIL] Hayatın Ritmi Uygulaması")
            appendLine("$userName için kalp ritim anomalisi tespit edildi.")
            appendLine("BPM: $bpm | Analiz: $aiLabel")
            appendLine("Konum: $locationStr")
        }

        try {
            @Suppress("DEPRECATION")
            val smsManager = SmsManager.getDefault()
            val sentIntent = PendingIntent.getBroadcast(
                context, 0,
                Intent("com.hayatinritmi.app.SMS_SENT"),
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
            )
            val parts = smsManager.divideMessage(smsBody)
            val sentIntents = ArrayList<PendingIntent>(parts.size).apply {
                repeat(parts.size) { add(sentIntent) }
            }
            smsManager.sendMultipartTextMessage(
                emergencyContactPhone,
                null,
                parts,
                sentIntents,
                null
            )
            _smsSent.value = true
            _smsError.value = null
        } catch (e: SecurityException) {
            _smsError.value = "SMS izni verilmedi — Ayarlar'dan izin verin."
            _smsSent.value = false
        } catch (e: Exception) {
            _smsError.value = "SMS gönderilemedi: ${e.message}"
            _smsSent.value = false
        }
    }

    fun resetState() {
        _smsSent.value = false
        _smsError.value = null
        _currentLocation.value = null
        _locationLoading.value = false
    }
}
