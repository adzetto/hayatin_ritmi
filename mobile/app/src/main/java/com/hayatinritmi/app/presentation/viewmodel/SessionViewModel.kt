package com.hayatinritmi.app.presentation.viewmodel

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.hayatinritmi.app.data.export.CsvExporter
import com.hayatinritmi.app.data.export.PdfReportGenerator
import com.hayatinritmi.app.data.local.entity.EcgSessionEntity
import com.hayatinritmi.app.domain.repository.SessionRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class SessionViewModel @Inject constructor(
    private val sessionRepository: SessionRepository,
    private val csvExporter: CsvExporter,
    private val pdfReportGenerator: PdfReportGenerator
) : ViewModel() {

    private val _sessions = MutableStateFlow<List<EcgSessionEntity>>(emptyList())
    val sessions: StateFlow<List<EcgSessionEntity>> = _sessions.asStateFlow()

    private val _exportState = MutableStateFlow<ExportState>(ExportState.Idle)
    val exportState: StateFlow<ExportState> = _exportState.asStateFlow()

    val unreadAlertCount: Flow<Int> = sessionRepository.getUnreadAlertCount()

    fun loadSessions(userId: Long) {
        viewModelScope.launch {
            sessionRepository.getSessionsByUser(userId).collect { list ->
                _sessions.value = list
            }
        }
    }

    fun exportCsv(session: EcgSessionEntity) {
        viewModelScope.launch {
            _exportState.value = ExportState.Exporting
            val uri = csvExporter.exportSessionToCsv(session)
            _exportState.value = if (uri != null) {
                ExportState.Success(uri, "csv")
            } else {
                ExportState.Error("CSV export başarısız")
            }
        }
    }

    fun exportPdf(
        session: EcgSessionEntity,
        patientName: String = "",
        patientBloodType: String = ""
    ) {
        viewModelScope.launch {
            _exportState.value = ExportState.Exporting
            val alerts = sessionRepository.getRecentAlerts(50)
            val uri = pdfReportGenerator.generateReport(
                session = session,
                patientName = patientName,
                patientBloodType = patientBloodType,
                alerts = alerts,
                aiLabel = session.aiLabel,
                aiConfidence = session.aiConfidence,
                signalQualityScore = session.qualityScore
            )
            _exportState.value = if (uri != null) {
                ExportState.Success(uri, "pdf")
            } else {
                ExportState.Error("PDF oluşturma başarısız")
            }
        }
    }

    fun deleteSession(sessionId: Long) {
        viewModelScope.launch {
            sessionRepository.deleteSession(sessionId)
        }
    }

    fun resetExportState() {
        _exportState.value = ExportState.Idle
    }
}

sealed interface ExportState {
    data object Idle : ExportState
    data object Exporting : ExportState
    data class Success(val uri: Uri, val type: String) : ExportState
    data class Error(val message: String) : ExportState
}
