package com.hayatinritmi.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.hayatinritmi.app.ble.MockBleManager
import com.hayatinritmi.app.data.MockEcgRepository
import com.hayatinritmi.app.screens.*
import com.hayatinritmi.app.ui.theme.HayatinRitmiTheme
import com.hayatinritmi.app.viewmodel.DeviceScanViewModel
import com.hayatinritmi.app.viewmodel.EcgViewModel

// Navigasyon Rotaları
sealed class Screen(val route: String) {
    data object Login : Screen("login")
    data object SignUp : Screen("signup")
    data object ForgotPassword : Screen("forgot_password")
    data object Dashboard : Screen("dashboard")
    data object ProMode : Screen("promode")
    data object Emergency : Screen("emergency")
    data object Settings : Screen("settings")
    data object Notifications : Screen("notifications")
    data object DeviceScan : Screen("device_scan")
    data object Reports : Screen("reports")
    data object EditProfile : Screen("edit_profile") // YENİ EKLENDİ: Profili Düzenle rotası
    data object EmergencyProfile : Screen("emergency_profile")
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val systemTheme = isSystemInDarkTheme()
            var isDarkMode by remember { mutableStateOf(systemTheme) }

            HayatinRitmiTheme(darkTheme = isDarkMode) {
                // Transparan yerine temanın arka plan rengini veriyoruz (Beyazlığı önler)
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    AppNavigation(
                        isDarkMode = isDarkMode,
                        onThemeToggle = { isDarkMode = !isDarkMode }
                    )
                }
            }
        }
    }
}

@Composable
fun AppNavigation(
    isDarkMode: Boolean,
    onThemeToggle: () -> Unit
) {
    val navController = rememberNavController()
    val context = LocalContext.current

    val bleManager = remember { MockBleManager() }
    val repository = remember { MockEcgRepository(bleManager) }
    val ecgViewModel = remember { EcgViewModel(repository, bleManager) }
    val deviceScanViewModel = remember { DeviceScanViewModel(bleManager, context) }

    // Hangi ekranda olduğumuzu takip ediyoruz
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route

    // Alt barın görünmesini istediğimiz ekranlar (EditProfile gibi alt sayfalarda görünmesini istemediğimiz için buraya eklemiyoruz)
    val screensWithBottomBar = listOf(
        Screen.Dashboard.route,
        Screen.ProMode.route,
        Screen.Settings.route,
        Screen.Notifications.route,
        Screen.Reports.route
    )
    val showBottomBar = currentRoute in screensWithBottomBar

    Scaffold(
        containerColor = Color.Transparent,
        bottomBar = {
            if (showBottomBar) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = 24.dp),
                    contentAlignment = Alignment.Center
                ) {
                    // FloatingNavBar'ı DashboardScreen'den çekiyoruz
                    FloatingNavBar(
                        navController = navController,
                        currentRoute = currentRoute ?: Screen.Dashboard.route
                    )
                }
            }
        }
    ) { _ ->
        // Ekranlar alt barın sınırında kesilmez, barın arkasından aşağıya kadar uzanır.
        NavHost(
            navController = navController,
            startDestination = Screen.Login.route
        ) {
            composable(Screen.Login.route) {
                LoginScreen(
                    navController = navController,
                    isDarkMode = isDarkMode,
                    onThemeToggle = onThemeToggle
                )
            }
            composable(Screen.EmergencyProfile.route) {
                EmergencyProfileScreen(navController = navController)
            }
            composable(Screen.SignUp.route) {
                SignUpScreen(navController = navController)
            }
            composable(Screen.ForgotPassword.route) {
                ForgotPasswordScreen(navController = navController)
            }
            composable(Screen.Dashboard.route) {
                DashboardScreen(navController = navController, ecgViewModel = ecgViewModel)
            }
            composable(Screen.ProMode.route) {
                ProModeScreen(navController = navController, viewModel = ecgViewModel)
            }
            composable(Screen.Emergency.route) {
                EmergencyScreen(navController = navController)
            }
            composable(Screen.Settings.route) {
                SettingsScreen(navController = navController, ecgViewModel = ecgViewModel, deviceScanViewModel = deviceScanViewModel)
            }
            composable(Screen.Notifications.route) {
                NotificationScreen(navController = navController)
            }
            composable(Screen.DeviceScan.route) {
                DeviceScanScreen(navController = navController, viewModel = deviceScanViewModel)
            }
            composable(Screen.Reports.route) {
                ReportsScreen(navController = navController)
            }
            // YENİ EKLENDİ: Profili Düzenle ekranı NavHost'a tanıtıldı
            composable(Screen.EditProfile.route) {
                EditProfileScreen(navController = navController)
            }
        }
    }
}