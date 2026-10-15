package org.vowen.app

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.unit.dp

private val palette=darkColorScheme(primary=Color(0xFFE4BD7A),onPrimary=Color(0xFF25190F),primaryContainer=Color(0xFF63322F),onPrimaryContainer=Color(0xFFFFE4DD),secondary=Color(0xFFEFAAA0),secondaryContainer=Color(0xFF63322F),onSecondaryContainer=Color(0xFFFFE4DD),onSecondary=Color(0xFF321915),background=Color(0xFF0E0D0C),onBackground=Color(0xFFF3E9DC),surface=Color(0xFF191614),onSurface=Color(0xFFF3E9DC),surfaceVariant=Color(0xFF221C18),onSurfaceVariant=Color(0xFFC0AD98),outline=Color(0xFF967958),error=Color(0xFFFFB8AC),surfaceContainer=Color(0xFF191614),surfaceContainerLow=Color(0xFF151210),surfaceContainerHigh=Color(0xFF221C18),surfaceContainerHighest=Color(0xFF2D241D),surfaceContainerLowest=Color(0xFF100F0E))
@Composable fun VowenTheme(content:@Composable ()->Unit) {
 val base=Typography()
 val display=FontFamily(Font(R.font.cormorant_garamond))
 MaterialTheme(colorScheme=palette,typography=base.copy(displayLarge=base.displayLarge.copy(fontFamily=display),displayMedium=base.displayMedium.copy(fontFamily=display),displaySmall=base.displaySmall.copy(fontFamily=display),titleMedium=base.titleMedium.copy(fontFamily=display),headlineLarge=base.headlineLarge.copy(fontFamily=display),headlineMedium=base.headlineMedium.copy(fontFamily=display),headlineSmall=base.headlineSmall.copy(fontFamily=display),titleLarge=base.titleLarge.copy(fontFamily=display)),content=content)
}
@Composable fun StartupGate(loading:Boolean,content:@Composable ()->Unit) {
 if(loading)Box(Modifier.fillMaxSize().background(Color(0xFF090909)).testTag("vowen-startup"),contentAlignment=Alignment.Center) {
  Image(painterResource(R.drawable.vowen_velvet),contentDescription=null,contentScale=ContentScale.Fit,modifier=Modifier.fillMaxWidth().padding(24.dp))
  Column(Modifier.align(Alignment.BottomCenter).safeDrawingPadding().padding(32.dp),horizontalAlignment=Alignment.CenterHorizontally) {Text("Vowen",style=MaterialTheme.typography.headlineLarge,color=MaterialTheme.colorScheme.primary);Text("Opening your workspace / Открываем пространство",style=MaterialTheme.typography.bodySmall)}
 } else content()
}
