package org.vowen.app

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

/** Shared compact outline with a practical phone/tablet touch target. */
@Composable
fun VowenActionButton(
 onClick:()->Unit,
 modifier:Modifier=Modifier,
 enabled:Boolean=true,
 content:@Composable RowScope.()->Unit
) {
 OutlinedButton(
  onClick=onClick,
  modifier=modifier.heightIn(min=44.dp),
  enabled=enabled,
  shape=RoundedCornerShape(8.dp),
  border=BorderStroke(1.dp,if(enabled)MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outline),
  contentPadding=PaddingValues(horizontal=12.dp,vertical=8.dp),
  content=content
 )
}
