package com.hayatinritmi.app.presentation.accessibility

import androidx.compose.ui.graphics.Color
import org.junit.Assert.*
import org.junit.Test

class AccessibilityUtilsTest {

    @Test
    fun `bpm description for normal range`() {
        val desc = AccessibilityUtils.bpmDescription(72)
        assertTrue(desc.contains("normal"))
        assertTrue(desc.contains("72"))
    }

    @Test
    fun `bpm description for high range`() {
        val desc = AccessibilityUtils.bpmDescription(130)
        assertTrue(desc.contains("yüksek"))
    }

    @Test
    fun `bpm description for low range`() {
        val desc = AccessibilityUtils.bpmDescription(40)
        assertTrue(desc.contains("düşük"))
    }

    @Test
    fun `bpm description for no measurement`() {
        val desc = AccessibilityUtils.bpmDescription(0)
        assertTrue(desc.contains("ölçülmüyor"))
    }

    @Test
    fun `alert description for RED level`() {
        val desc = AccessibilityUtils.alertDescription("RED")
        assertTrue(desc.contains("Kritik") || desc.contains("Acil"))
    }

    @Test
    fun `signal quality description ranges`() {
        assertTrue(AccessibilityUtils.signalQualityDescription(90).contains("mükemmel"))
        assertTrue(AccessibilityUtils.signalQualityDescription(65).contains("iyi"))
        assertTrue(AccessibilityUtils.signalQualityDescription(45).contains("orta"))
        assertTrue(AccessibilityUtils.signalQualityDescription(20).contains("zayıf"))
        assertTrue(AccessibilityUtils.signalQualityDescription(0).contains("ölçülmüyor"))
    }

    @Test
    fun `connection description for all states`() {
        assertTrue(AccessibilityUtils.connectionDescription("CONNECTED").contains("bağlı"))
        assertTrue(AccessibilityUtils.connectionDescription("CONNECTING").contains("bağlanılıyor"))
        assertTrue(AccessibilityUtils.connectionDescription("SCANNING").contains("taranıyor"))
        assertTrue(AccessibilityUtils.connectionDescription("DISCONNECTED").contains("bağlı değil"))
    }

    @Test
    fun `white on black meets contrast requirement`() {
        val white = Color.White
        val black = Color.Black
        val ratio = AccessibilityUtils.contrastRatio(white, black)
        assertTrue("Expected ratio >= 20, got $ratio", ratio >= 20.0f)
        assertTrue(AccessibilityUtils.meetsContrastRequirement(white, black))
    }

    @Test
    fun `light gray on white fails contrast for normal text`() {
        val lightGray = Color(0xFFCCCCCC)
        val white = Color.White
        assertFalse(AccessibilityUtils.meetsContrastRequirement(lightGray, white))
    }

    @Test
    fun `contrast ratio is symmetric`() {
        val c1 = Color(0xFFFF5722)
        val c2 = Color(0xFF121212)
        val r1 = AccessibilityUtils.contrastRatio(c1, c2)
        val r2 = AccessibilityUtils.contrastRatio(c2, c1)
        assertEquals(r1, r2, 0.01f)
    }
}
