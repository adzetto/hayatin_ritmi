package com.hayatinritmi.app.presentation.viewmodel

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.telephony.SmsManager
import android.app.PendingIntent
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.hayatinritmi.app.domain.model.AlertEvent
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * Acil durum sistemi ViewModel.
 *
 * Sorumluluklar:
 *  - GPS konum alma (FusedLocationProviderClient — FAZ 3.6)
 *  - Kayıtlı acil kişilere SMS gönderme (SmsManager)
 *  - EmergencyScreen'e durum bildirimi (StateFlow)
 *
 * Not: GPS entegrasyonu play-services-location bağımlılığı eklenince aktive olur.
 * Şimdilik konumsuz SMS gönderimi çalışır.
 */
class EmergencyViewModel(private val context: Context) : ViewModel() {

    private val _smsSent = MutableStateFlow(false)
    val smsSent: StateFlow<Boolean> = _smsSent.asStateFlow()

    private val _smsError = MutableStateFlow<String?>(null)
    val smsError: StateFlow<String?> = _smsError.asStateFlow()

    private val _currentLocation = MutableStateFlow<Pair<Double, Double>?>(null)
    val currentLocation: StateFlow<Pair<Double, Double>?> = _currentLocation.asStateFlow()

    // Room entegrasyonu (FAZ 4) tamamlanana kadar bu değerler dışarıdan set edilir
    var emergencyContactPhone: String = ""
    var emergencyContactName: String = "Acil Kişi"
    var userName: String = "Kullanıcı"

    /**
     * Acil durum SMS'i gönder (konumsuz).
     * GPS entegrasyonu FAZ 4'te play-services-location ile eklenecek.
     */
    fun sendEmergencyAlert(event: AlertEvent) {
        viewModelScope.launch {
            sendSms(
                lat = event.lat,
                lon = event.lon,
                bpm = event.bpm,
                aiLabel = event.aiPrediction?.label?.displayName ?: "Belirsiz"
            )
        }
    }

    /**
     * 112'yi ara.
     * Caller, CALL_PHONE izninin mevcut olduğunu doğrulamalı.
     */
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
            // SMS >160 karakter olabilir — parçala
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
    }
}
