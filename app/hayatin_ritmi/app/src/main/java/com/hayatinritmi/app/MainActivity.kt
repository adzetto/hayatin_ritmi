package com.hayatinritmi.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.hayatinritmi.app.screens.*
import com.hayatinritmi.app.ui.theme.HayatinRitmiTheme
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import com.hayatinritmi.app.ble.MockBleManager
import com.hayatinritmi.app.data.MockEcgRepository
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
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            HayatinRitmiTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = Color.Transparent
                ) {
                    AppNavigation()
                }
            }
        }
    }
}

@Composable
fun AppNavigation() {
    val navController = rememberNavController()
    val context = LocalContext.current

    // Create instances (mock-first approach)
    val bleManager = remember { MockBleManager() }
    val repository = remember { MockEcgRepository(bleManager) }
    val ecgViewModel = remember { EcgViewModel(repository, bleManager) }
    val deviceScanViewModel = remember { DeviceScanViewModel(bleManager, context) }

    NavHost(navController = navController, startDestination = Screen.Login.route) {
        composable(Screen.Login.route) {
            LoginScreen(navController = navController)
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
    }
}