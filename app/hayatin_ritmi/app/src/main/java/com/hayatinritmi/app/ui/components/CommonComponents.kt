package com.hayatinritmi.app.ui.components

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material3.*
import androidx.compose.material3.ripple
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.hayatinritmi.app.ui.theme.*

// ══════════════════════════════════════════════════════
//  GLASSMORPHISM KART — Standart cam efekti bileşeni
// ══════════════════════════════════════════════════════

@Composable
fun GlassCard(
    modifier: Modifier = Modifier,
    cornerRadius: Dp = 20.dp,
    glassAlpha: Float = 0.05f,
    borderAlpha: Float = 0.08f,
    onClick: (() -> Unit)? = null,
    content: @Composable ColumnScope.() -> Unit
) {
    val shape = RoundedCornerShape(cornerRadius)
    val interactionSource = remember { MutableInteractionSource() }

    // DEĞİŞTİ: Sabit beyaz yerine, temanın yazı renginin (zıt rengin) saydam hali kullanıldı.
    // Böylece gündüz siyahımsı bir şeffaflık, gece beyazımsı bir şeffaflık olur.
    val baseColor = MaterialTheme.colorScheme.onBackground

    Column(
        modifier = modifier
            .fillMaxWidth()
            .clip(shape)
            .background(baseColor.copy(alpha = glassAlpha))
            .border(1.dp, baseColor.copy(alpha = borderAlpha), shape)
            .then(
                if (onClick != null) Modifier.clickable(
                    interactionSource = interactionSource,
                    indication = ripple(color = baseColor.copy(alpha = 0.08f)),
                    role = Role.Button,
                    onClick = onClick
                ) else Modifier
            )
            .padding(20.dp),
        content = content
    )
}

// ══════════════════════════════════════════════════════
//  BİLGİ KARTI — İkon + Başlık + Açıklama + Ok
// ══════════════════════════════════════════════════════

@Composable
fun InfoCard(
    icon: ImageVector,
    iconColor: Color,
    title: String,
    description: String,
    showArrow: Boolean = false,
    onClick: (() -> Unit)? = null
) {
    val shape = RoundedCornerShape(20.dp)
    val interactionSource = remember { MutableInteractionSource() }
    // DEĞİŞTİ: Kartın cam efekti temaya bağlandı
    val baseColor = MaterialTheme.colorScheme.onBackground

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(shape)
            .background(baseColor.copy(alpha = 0.05f))
            .border(1.dp, baseColor.copy(alpha = 0.08f), shape)
            .then(
                if (onClick != null) Modifier.clickable(
                    interactionSource = interactionSource,
                    indication = ripple(color = baseColor.copy(alpha = 0.08f)),
                    role = Role.Button,
                    onClick = onClick
                ) else Modifier
            )
            .padding(20.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        // İkon container
        Box(
            modifier = Modifier
                .size(44.dp)
                .background(iconColor.copy(alpha = 0.12f), CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Icon(icon, contentDescription = null, tint = iconColor, modifier = Modifier.size(22.dp))
        }

        Spacer(modifier = Modifier.width(16.dp))

        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleSmall,
                // DEĞİŞTİ: TextPrimary yerine onBackground
                color = MaterialTheme.colorScheme.onBackground
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = description,
                style = MaterialTheme.typography.bodySmall,
                // DEĞİŞTİ: TextTertiary yerine onSurfaceVariant
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                lineHeight = 18.sp
            )
        }

        if (showArrow) {
            Spacer(modifier = Modifier.width(8.dp))
            Icon(
                androidx.compose.material.icons.Icons.Default.ChevronRight,
                contentDescription = null,
                // DEĞİŞTİ: Ok ikonu rengi
                tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f),
                modifier = Modifier.size(20.dp)
            )
        }
    }
}

// ══════════════════════════════════════════════════════
//  GRADIENT BUTON — Rose veya custom gradient
// ══════════════════════════════════════════════════════

@Composable
fun GradientButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    // DEĞİŞTİ: Varsayılan renkler temanın ana rengine bağlandı
    colors: List<Color> = listOf(MaterialTheme.colorScheme.primary, MaterialTheme.colorScheme.primaryContainer),
    enabled: Boolean = true,
    height: Dp = 56.dp,
    icon: ImageVector? = null
) {
    val interactionSource = remember { MutableInteractionSource() }
    val shape = RoundedCornerShape(16.dp)

    // Gradient butonlar ana eylem butonudur.
    // Üzerindeki yazı, zemin rengi ne olursa olsun okunabilmesi için genelde kontrast bir renkte (beyaz veya onPrimary) tutulur.
    val textColor = MaterialTheme.colorScheme.onPrimary

    Box(
        modifier = modifier
            .fillMaxWidth()
            .height(height)
            .clip(shape)
            .background(
                brush = if (enabled) Brush.horizontalGradient(colors)
                else Brush.horizontalGradient(listOf(MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f), MaterialTheme.colorScheme.onSurface.copy(alpha = 0.2f)))
            )
            .border(
                1.dp,
                Brush.verticalGradient(
                    listOf(Color.White.copy(alpha = if (enabled) 0.2f else 0.05f), Color.Transparent)
                ),
                shape
            )
            .clickable(
                interactionSource = interactionSource,
                indication = ripple(color = Color.White.copy(alpha = 0.15f)),
                enabled = enabled,
                role = Role.Button,
                onClick = onClick
            ),
        contentAlignment = Alignment.Center
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            if (icon != null) {
                Icon(icon, contentDescription = null, tint = textColor, modifier = Modifier.size(20.dp))
                Spacer(modifier = Modifier.width(8.dp))
            }
            Text(
                text = text,
                style = MaterialTheme.typography.labelLarge,
                color = if (enabled) textColor else MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f),
                letterSpacing = 0.5.sp
            )
        }
    }
}

// ══════════════════════════════════════════════════════
//  OUTLINED GLASS BUTON — İkincil eylem butonları
// ══════════════════════════════════════════════════════

@Composable
fun GlassOutlinedButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    // Eğer dışarıdan renk verilmezse ikincil (mavi) renk varsayılan olur
    accentColor: Color = MaterialTheme.colorScheme.secondary,
    height: Dp = 52.dp,
    icon: ImageVector? = null
) {
    val interactionSource = remember { MutableInteractionSource() }
    val shape = RoundedCornerShape(14.dp)

    Box(
        modifier = modifier
            .fillMaxWidth()
            .height(height)
            .clip(shape)
            .background(accentColor.copy(alpha = 0.08f))
            .border(1.dp, accentColor.copy(alpha = 0.25f), shape)
            .clickable(
                interactionSource = interactionSource,
                indication = ripple(color = accentColor.copy(alpha = 0.15f)),
                role = Role.Button,
                onClick = onClick
            ),
        contentAlignment = Alignment.Center
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            if (icon != null) {
                Icon(icon, contentDescription = null, tint = accentColor, modifier = Modifier.size(18.dp))
                Spacer(modifier = Modifier.width(8.dp))
            }
            Text(
                text = text,
                style = MaterialTheme.typography.labelLarge,
                color = accentColor
            )
        }
    }
}

// ══════════════════════════════════════════════════════
//  DURUM BADGE — Bağlı/Bağlı Değil/Taranıyor
// ══════════════════════════════════════════════════════

@Composable
fun StatusBadge(
    text: String,
    color: Color,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .background(color.copy(alpha = 0.15f), RoundedCornerShape(20.dp))
            .border(1.dp, color.copy(alpha = 0.25f), RoundedCornerShape(20.dp))
            .padding(horizontal = 10.dp, vertical = 4.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(6.dp)
                    .background(color, CircleShape)
            )
            Spacer(modifier = Modifier.width(6.dp))
            Text(
                text = text,
                style = MaterialTheme.typography.labelSmall,
                color = color,
                fontWeight = FontWeight.Bold
            )
        }
    }
}

// ══════════════════════════════════════════════════════
//  İKON CONTAINER — Standartlaştırılmış ikon çerçevesi
// ══════════════════════════════════════════════════════

@Composable
fun IconCircle(
    icon: ImageVector,
    color: Color,
    modifier: Modifier = Modifier,
    size: Dp = 40.dp,
    iconSize: Dp = 20.dp
) {
    Box(
        modifier = modifier
            .size(size)
            .background(color.copy(alpha = 0.12f), CircleShape),
        contentAlignment = Alignment.Center
    ) {
        Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(iconSize))
    }
}

// ══════════════════════════════════════════════════════
//  PREMIUM SWITCH — Medikal uygulama toggle
// ══════════════════════════════════════════════════════

@Composable
fun PremiumSwitch(
    checked: Boolean,
    onCheckedChange: ((Boolean) -> Unit)?,
    isLocked: Boolean = false,
    activeColor: Color = MaterialTheme.colorScheme.secondary
) {
    // DEĞİŞTİ: Switch'in boş arka planı (track) temaya bağlandı
    val baseColor = MaterialTheme.colorScheme.onSurfaceVariant
    val trackColor = animateColorAsState(
        targetValue = if (checked) activeColor else baseColor.copy(alpha = 0.15f),
        animationSpec = tween(250),
        label = "track"
    )

    Switch(
        checked = checked,
        onCheckedChange = if (isLocked) null else onCheckedChange,
        colors = SwitchDefaults.colors(
            // DEĞİŞTİ: Switch'in yuvarlağı (thumb) artık temaya duyarlı
            checkedThumbColor = MaterialTheme.colorScheme.surface,
            checkedTrackColor = trackColor.value,
            uncheckedThumbColor = MaterialTheme.colorScheme.surfaceVariant,
            uncheckedTrackColor = trackColor.value,
            uncheckedBorderColor = Color.Transparent,
            checkedBorderColor = Color.Transparent
        )
    )
}

// ══════════════════════════════════════════════════════
//  VERİ KARTI — ProMode alt kartlar
// ══════════════════════════════════════════════════════

@Composable
fun MetricCard(
    modifier: Modifier = Modifier,
    title: String,
    value: String,
    unit: String,
    icon: ImageVector,
    color: Color
) {
    val shape = RoundedCornerShape(18.dp)
    // DEĞİŞTİ: Kart arka planı (Glass effect) temaya bağlandı
    val baseColor = MaterialTheme.colorScheme.onBackground

    Box(
        modifier = modifier
            .clip(shape)
            .background(baseColor.copy(alpha = 0.05f))
            .border(1.dp, color.copy(alpha = 0.1f), shape)
            .padding(18.dp)
    ) {
        Column {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(16.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = title,
                    style = MaterialTheme.typography.labelSmall,
                    // DEĞİŞTİ: Başlık rengi
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            Spacer(modifier = Modifier.height(10.dp))
            Row(verticalAlignment = Alignment.Bottom) {
                Text(
                    text = value,
                    style = MaterialTheme.typography.displaySmall.copy(fontSize = 30.sp),
                    // DEĞİŞTİ: Değer (Sayı) rengi
                    color = MaterialTheme.colorScheme.onBackground
                )
                Spacer(modifier = Modifier.width(4.dp))
                Text(
                    text = unit,
                    style = MaterialTheme.typography.bodySmall,
                    // DEĞİŞTİ: Birim rengi
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(bottom = 6.dp)
                )
            }
        }
    }
}