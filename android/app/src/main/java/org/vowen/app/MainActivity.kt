package org.vowen.app

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.Image
import androidx.compose.ui.res.painterResource
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
  val guestModel=ViewModelProvider(this)[GuestViewModel::class.java]
  setContent {
   val screen by model.screen.collectAsState()
   var origin by remember { mutableStateOf(screen.origin) }
   var choosingInstance by remember {mutableStateOf(false)}
   val context=LocalContext.current
   val guest by guestModel.visibleState
   var firstFrame by remember {mutableStateOf(true)}
   LaunchedEffect(Unit){withFrameNanos{};firstFrame=false}
   VowenTheme {
    StartupGate(firstFrame||screen.booting) {
    Surface(Modifier.fillMaxSize()) {
     Column(Modifier.safeDrawingPadding().padding(24.dp).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(16.dp)) {
      Row(verticalAlignment=androidx.compose.ui.Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(12.dp)){Image(painterResource(R.drawable.vowen_crest),contentDescription=null,modifier=Modifier.size(40.dp));Column{Text("Vowen",style=MaterialTheme.typography.headlineMedium,color=MaterialTheme.colorScheme.primary);screen.member?.let{Text(it.display_name,style=MaterialTheme.typography.bodySmall)}};if(screen.member!=null)TextButton(onClick={choosingInstance=!choosingInstance},enabled=!screen.busy){Text(if(screen.member?.language=="ru")"Инстанс" else "Instance")}}
      if(screen.member==null||choosingInstance||guest)TextButton(onClick={if(guest)guestModel.close() else guestModel.visibleState.value=true},enabled=!guestModel.busyState.value) {Text("Guest form / Гостевая анкета")}
      if(guest)NativeGuestScreen(guestModel) {guestModel.close()}
      if(!guest) {
      if(screen.member==null||choosingInstance){
      OutlinedTextField(value=origin,onValueChange={origin=it},label={Text(stringResource(R.string.instance))},singleLine=true,enabled=!screen.busy)
      Button(onClick={model.select(origin)},enabled=!screen.busy) {Text(stringResource(R.string.connect))}
      if(screen.origin.isNotBlank()) Text(screen.origin)
      }
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
       Row {
       TextButton(onClick={model.pause()},enabled=!screen.busy) {Text(if(member.language=="ru") if(member.paused)"Снять личную паузу" else "Личная пауза" else if(member.paused)"End personal pause" else "Personal pause")}
       TextButton(onClick={model.logout()},enabled=!screen.busy) {Text(if(member.language=="ru")"Выйти" else "Sign out")}
       }
       WorkspaceScreen(member,screen.workspace,screen.sessionId,screen.busy,screen.completed,
        WorkspaceActions(model::refreshWorkspace,model::propose,model::relationAction,model::changeRelation,model::saveProfile,model::revokeSession),
        FormActions(model::refreshWorkspace,model::saveForm,model::publishForm,model::inviteForm,model::saveFormDraft,model::submitForm,model::deleteFormResult),screen.formLink,RuleActions(model::refreshWorkspace,model::saveRule,model::ruleTemplate,model::assignRule,model::decideRule,model::ruleHistory),RitualActions(model::refreshWorkspace,model::saveRitual,model::ritualTemplate,model::ritualHistory,model::assignRitual,model::scheduleRitual,model::ritualAssignment,model::reportRitual,model::reviewRitual,model::skipRitual))
      }
      }
     }
    }
    }
   }
  }
 }
}
