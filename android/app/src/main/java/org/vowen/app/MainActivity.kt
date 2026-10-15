package org.vowen.app

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModelProvider

class MainActivity:ComponentActivity() {
 override fun onCreate(savedInstanceState:Bundle?) {
  super.onCreate(savedInstanceState)
  val model=ViewModelProvider(this)[AuthViewModel::class.java]
  setContent {
   val screen by model.screen.collectAsState()
   var origin by remember { mutableStateOf(screen.origin) }
   val context=LocalContext.current
   var guest by remember {mutableStateOf(false)}
   MaterialTheme {
    Surface(Modifier.fillMaxSize()) {
     Column(Modifier.safeDrawingPadding().padding(24.dp).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(16.dp)) {
      Text("Vowen",style=MaterialTheme.typography.headlineLarge)
      Text(stringResource(R.string.alpha))
      TextButton(onClick={guest=!guest}) {Text("Guest form / Гостевая анкета")}
      if(guest)NativeGuestScreen {guest=false}
      if(!guest) {
      OutlinedTextField(value=origin,onValueChange={origin=it},label={Text(stringResource(R.string.instance))},singleLine=true,enabled=!screen.busy)
      Button(onClick={model.select(origin)},enabled=!screen.busy) {Text(stringResource(R.string.connect))}
      if(screen.origin.isNotBlank()) Text(screen.origin)
      screen.error?.let { Text(it,color=MaterialTheme.colorScheme.error) }
      if(screen.busy) LinearProgressIndicator(Modifier.fillMaxWidth())
      if(screen.member==null && screen.origin.isNotBlank()) {
       Button(onClick={model.begin()},enabled=!screen.busy) {Text(stringResource(R.string.signin))}
      }
      screen.challenge?.let { challenge ->
       Text("${stringResource(R.string.confirm)}: ${challenge.display_code}",style=MaterialTheme.typography.headlineSmall)
       Button(onClick={context.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(challenge.bot_url)))},enabled=!screen.busy) {Text("Telegram")}
       Button(onClick={model.poll()},enabled=!screen.busy) {Text(stringResource(R.string.poll))}
      }
      screen.member?.let { member ->
       Text(member.display_name,style=MaterialTheme.typography.headlineMedium)
       Button(onClick={model.pause()},enabled=!screen.busy) {Text(if(member.language=="ru") if(member.paused)"Снять личную паузу" else "Личная пауза" else if(member.paused)"End personal pause" else "Personal pause")}
       Button(onClick={model.logout()},enabled=!screen.busy) {Text(if(member.language=="ru")"Выйти" else "Sign out")}
       WorkspaceScreen(member,screen.workspace,screen.sessionId,screen.busy,screen.completed,
        WorkspaceActions(model::refreshWorkspace,model::propose,model::relationAction,model::changeRelation,model::saveProfile,model::revokeSession),
        FormActions(model::refreshWorkspace,model::saveForm,model::publishForm,model::inviteForm,model::saveFormDraft,model::submitForm,model::deleteFormResult),screen.formLink)
      }
      }
     }
    }
   }
  }
 }
}
