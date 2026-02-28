package com.hayatinritmi.app.presentation.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.hayatinritmi.app.data.local.entity.UserEntity
import com.hayatinritmi.app.domain.repository.UserRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val userRepository: UserRepository
) : ViewModel() {

    private val _loginState = MutableStateFlow<AuthState>(AuthState.Idle)
    val loginState: StateFlow<AuthState> = _loginState.asStateFlow()

    private val _registerState = MutableStateFlow<AuthState>(AuthState.Idle)
    val registerState: StateFlow<AuthState> = _registerState.asStateFlow()

    private val _currentUser = MutableStateFlow<UserEntity?>(null)
    val currentUser: StateFlow<UserEntity?> = _currentUser.asStateFlow()

    init {
        viewModelScope.launch {
            _currentUser.value = userRepository.getCurrentUser()
        }
    }

    fun login(phone: String, password: String) {
        if (phone.isBlank() || password.isBlank()) {
            _loginState.value = AuthState.Error("Telefon ve şifre gereklidir")
            return
        }
        viewModelScope.launch {
            _loginState.value = AuthState.Loading
            val result = userRepository.authenticate(phone, password)
            result.fold(
                onSuccess = { user ->
                    _currentUser.value = user
                    _loginState.value = AuthState.Success
                },
                onFailure = { error ->
                    _loginState.value = AuthState.Error(error.message ?: "Giriş başarısız")
                }
            )
        }
    }

    fun register(
        name: String,
        surname: String,
        phone: String,
        password: String,
        bloodType: String = "",
        emergencyContactName: String = "",
        emergencyContactPhone: String = "",
        doctorEmail: String = ""
    ) {
        if (name.isBlank() || surname.isBlank() || phone.isBlank() || password.isBlank()) {
            _registerState.value = AuthState.Error("Ad, soyad, telefon ve şifre gereklidir")
            return
        }
        if (password.length < 6) {
            _registerState.value = AuthState.Error("Şifre en az 6 karakter olmalıdır")
            return
        }
        viewModelScope.launch {
            _registerState.value = AuthState.Loading
            val result = userRepository.register(
                name = name,
                surname = surname,
                phone = phone,
                password = password,
                bloodType = bloodType,
                emergencyContactName = emergencyContactName,
                emergencyContactPhone = emergencyContactPhone,
                doctorEmail = doctorEmail
            )
            result.fold(
                onSuccess = {
                    _currentUser.value = userRepository.getCurrentUser()
                    _registerState.value = AuthState.Success
                },
                onFailure = { error ->
                    _registerState.value = AuthState.Error(error.message ?: "Kayıt başarısız")
                }
            )
        }
    }

    fun logout() {
        _currentUser.value = null
        _loginState.value = AuthState.Idle
    }

    fun resetLoginState() { _loginState.value = AuthState.Idle }
    fun resetRegisterState() { _registerState.value = AuthState.Idle }

    fun getCurrentUserId(): Long = _currentUser.value?.id ?: -1L
}

sealed interface AuthState {
    data object Idle : AuthState
    data object Loading : AuthState
    data object Success : AuthState
    data class Error(val message: String) : AuthState
}
