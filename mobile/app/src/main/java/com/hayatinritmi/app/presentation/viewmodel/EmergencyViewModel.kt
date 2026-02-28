package com.hayatinritmi.app.presentation.viewmodel

import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import android.telephony.SmsManager
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.google.android.gms.tasks.CancellationTokenSource
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await
import kotlinx.coroutines.withTimeoutOrNull
import javax.inject.Inject

@HiltViewModel
class EmergencyViewModel @Inject constructor(
    @ApplicationContext private val context: Context
) : ViewModel() {

    private val _smsSent = MutableStateFlow(false)
    val smsSent: StateFlow<Boolean> = _smsSent.asStateFlow()

    private val _smsError = MutableStateFlow<String?>(null)
    val smsError: StateFlow<String?> = _smsError.asStateFlow()

    private val _currentLocation = MutableStateFlow<Pair<Double, Double>?>(null)
    val currentLocation: StateFlow<Pair<Double, Double>?> = _currentLocation.asStateFlow()

    private val fusedLocationClient = LocationServices.getFusedLocationProviderClient(context)

    fun fetchLocation() {
        viewModelScope.launch {
            try {
                val location = withTimeoutOrNull(10_000L) {
                    val cts = CancellationTokenSource()
                    @Suppress("MissingPermission")
                    fusedLocationClient.getCurrentLocation(
                        Priority.PRIORITY_HIGH_ACCURACY,
                        cts.token
                    ).await()
                }
                if (location != null) {
                    _currentLocation.value = location.latitude to location.longitude
                }
            } catch (_: Exception) { }
        }
    }

    fun sendEmergencySms(
        phoneNumber: String,
        bpm: Int,
        aiLabel: String,
        customMessage: String = ""
    ) {
        viewModelScope.launch {
            try {
                val loc = _currentLocation.value
                val locationText = if (loc != null) {
                    "Konum: https://maps.google.com/?q=${loc.first},${loc.second}"
                } else {
                    "Konum alınamadı"
                }

                val message = buildString {
                    append("⚠️ ACİL DURUM — Hayatın Ritmi EKG Uyarısı\n")
                    append("BPM: $bpm | AI: $aiLabel\n")
                    append(locationText)
                    if (customMessage.isNotBlank()) {
                        append("\n$customMessage")
                    }
                }

                val smsManager = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                    context.getSystemService(SmsManager::class.java)
                } else {
                    @Suppress("DEPRECATION")
                    SmsManager.getDefault()
                }

                val parts = smsManager.divideMessage(message)
                val sentIntents = ArrayList<PendingIntent>()
                for (i in parts.indices) {
                    val sentPI = PendingIntent.getBroadcast(
                        context, i,
                        Intent("SMS_SENT_$i"),
                        PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                    )
                    sentIntents.add(sentPI)
                }

                smsManager.sendMultipartTextMessage(
                    phoneNumber, null, parts, sentIntents, null
                )

                _smsSent.value = true
                _smsError.value = null
            } catch (e: Exception) {
                _smsSent.value = false
                _smsError.value = e.message ?: "SMS gönderilemedi"
            }
        }
    }

    fun callEmergencyServices() {
        try {
            val intent = Intent(Intent.ACTION_CALL).apply {
                data = android.net.Uri.parse("tel:112")
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
            }
            context.startActivity(intent)
        } catch (_: Exception) { }
    }

    fun resetState() {
        _smsSent.value = false
        _smsError.value = null
    }
}
