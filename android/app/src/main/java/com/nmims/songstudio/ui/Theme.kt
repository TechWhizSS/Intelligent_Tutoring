package com.nmims.songstudio.ui

import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

val Paper=Color(0xFFFFF9F3)
val Ink=Color(0xFF302421)
val Sunrise=Color(0xFFC64620)
val Lime=Color(0xFFFFE4CA) // Compatibility alias for the uploaded player's panel.
val Lavender=Color(0xFFFFF0E6)
val Muted=Color(0xFF7C6A63)
@Composable
fun StudioTheme(content:@Composable ()->Unit) {
    MaterialTheme(colorScheme=lightColorScheme(primary=Sunrise,onPrimary=Color.White,
        background=Paper,surface=Color(0xFFFFFCF8),onSurface=Ink,onBackground=Ink,
        surfaceVariant=Lavender,onSurfaceVariant=Muted,secondaryContainer=Lime,onSecondaryContainer=Ink,
        outline=Color(0xFFDCC2AF)), typography=Typography(
        headlineLarge=TextStyle(fontSize=34.sp,lineHeight=39.sp,fontWeight=FontWeight.SemiBold,letterSpacing=(-1).sp),
        headlineMedium=TextStyle(fontSize=27.sp,lineHeight=33.sp,fontWeight=FontWeight.SemiBold,letterSpacing=(-.6).sp),
        titleLarge=TextStyle(fontSize=21.sp,lineHeight=28.sp,fontWeight=FontWeight.SemiBold),
        titleMedium=TextStyle(fontSize=16.sp,fontWeight=FontWeight.SemiBold),
        bodyLarge=TextStyle(fontSize=16.sp,lineHeight=25.sp),bodyMedium=TextStyle(fontSize=14.sp,lineHeight=22.sp),
        bodySmall=TextStyle(fontSize=12.sp,lineHeight=19.sp),labelSmall=TextStyle(fontSize=10.sp,lineHeight=16.sp,fontWeight=FontWeight.Bold,letterSpacing=1.sp)
    ),content=content)
}
