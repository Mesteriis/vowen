package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp

@Composable
fun SessionsScreen(member:Member,sessions:List<DeviceSession>,currentId:String?,busy:Boolean,completed:Int,onRevoke:(DeviceSession)->Unit) {
 var selected by remember {mutableStateOf<DeviceSession?>(null)}
 LaunchedEffect(completed) {selected=null}
 val ru=member.language=="ru"
 Column(verticalArrangement=Arrangement.spacedBy(12.dp)) {
  if(sessions.isEmpty()) Text(if(ru)"Нет сессий" else "No sessions")
  sessions.forEach {session->
   Card(Modifier.fillMaxWidth()) {Column(Modifier.padding(16.dp)) {
    Text(session.device_label,style=MaterialTheme.typography.titleMedium)
    if(session.id==currentId) Text(if(ru)"Текущая сессия" else "Current session")
    Text("${session.client} · ${if(session.revoked) if(ru)"Отозвана" else "Revoked" else if(ru)"Активна" else "Active"}")
    Text((if(ru)"Создана: " else "Created: ")+session.created_at)
    Text((if(ru)"Истекает: " else "Expires: ")+session.expires_at)
    if(!session.revoked) TextButton(onClick={selected=session},enabled=!busy,modifier=Modifier.testTag("revoke-session-${session.id}")) {Text(if(ru)"Отозвать сессию" else "Revoke session")}
   }}
  }
 }
 selected?.let {session->
  AlertDialog(onDismissRequest={if(!busy)selected=null},title={Text(if(ru)"Отозвать сессию?" else "Revoke this session?")},text={Text(session.device_label+"\n"+if(session.id==currentId) if(ru)"Это завершит текущий вход." else "This signs out this device." else if(ru)"Устройство потеряет доступ." else "This device will lose access.")},confirmButton={TextButton(onClick={onRevoke(session)},enabled=!busy,modifier=Modifier.testTag("confirm-session-revoke")){Text(if(ru)"Отозвать" else "Revoke")}},dismissButton={TextButton(onClick={selected=null},enabled=!busy){Text(if(ru)"Отмена" else "Cancel")}})
 }
}
