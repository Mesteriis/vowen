package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.contentDescription

private val relationScopes=listOf("rules.assign","rituals.assign","rituals.review","discipline.propose","discipline.review","rewards.grant")

@Composable
fun RelationsScreen(member:Member,data:WorkspaceState,busy:Boolean,completed:Int,actions:WorkspaceActions) {
 var confirmation by remember {mutableStateOf<Pair<Relation,String>?>(null)}
 var proposing by remember {mutableStateOf(false)}
 var editing by remember {mutableStateOf<Relation?>(null)}
 LaunchedEffect(completed) {confirmation=null;proposing=false;editing=null}
 val ru=member.language=="ru"
 fun name(id:String)=data.participants.find {it.id==id}?.display_name?:id
 Column(verticalArrangement=Arrangement.spacedBy(12.dp)) {
  if(data.relations.isEmpty()) Text(if(ru)"Пока нет отношений" else "No relationships yet")
  data.relations.forEach {relation->
   Card(Modifier.fillMaxWidth()) {Column(Modifier.padding(16.dp),verticalArrangement=Arrangement.spacedBy(8.dp)) {
    Text("${name(relation.dominant_user_id)} → ${name(relation.submissive_user_id)}",style=MaterialTheme.typography.titleMedium)
    Text("${relation.status} · v${relation.version} · ${relation.consent_user_ids.size}/2")
    Text(relation.agreement_text)
    Text(relation.scopes.joinToString(", "))
    if(relation.status=="proposed" && member.id !in relation.consent_user_ids) Button(onClick={confirmation=relation to "accept"},enabled=!busy,modifier=Modifier.testTag("accept-${relation.id}")){Text(if(ru)"Рассмотреть и подтвердить" else "Review and accept")}
    if(relation.status in listOf("active","proposed")) TextButton(onClick={confirmation=relation to "pause"},enabled=!busy){Text(if(ru)"Приостановить" else "Pause")}
    if(relation.status=="paused") TextButton(onClick={confirmation=relation to "resume"},enabled=!busy){Text(if(ru)"Запросить возобновление" else "Request resumption")}
    if(relation.status!="revoked") {
     TextButton(onClick={editing=relation},enabled=!busy){Text(if(ru)"Предложить новую версию" else "Propose new version")}
     TextButton(onClick={confirmation=relation to "revoke"},enabled=!busy){Text(if(ru)"Отозвать" else "Revoke")}
    }
   }}
  }
  Button(onClick={proposing=true},enabled=!busy&&data.participants.any {it.id!=member.id},modifier=Modifier.testTag("propose-relation")){Text(if(ru)"Предложить отношения" else "Propose relationship")}
 }
 confirmation?.let {(relation,action)->
  AlertDialog(onDismissRequest={if(!busy)confirmation=null},title={Text(if(ru)"Подтвердить действие" else "Confirm action")},text={Column(Modifier.heightIn(max=350.dp).verticalScroll(rememberScrollState())) {
   Text("${name(relation.dominant_user_id)} → ${name(relation.submissive_user_id)}")
   Text("v${relation.version} · ${relation.relation_version_id}")
   Text(relation.agreement_text,modifier=Modifier.testTag("agreement-review"))
   Text(relation.scopes.joinToString(", "))
   Text(when(action){"accept"->if(ru)"Подтверждаю именно эту версию и полномочия." else "I accept this exact version and scopes.";"resume"->if(ru)"Возобновление требует новых согласий обоих." else "Resumption requires fresh consent from both participants.";else->action})
  }},confirmButton={TextButton(onClick={actions.relation(relation,action)},enabled=!busy,modifier=Modifier.testTag("confirm-relation")){Text(if(ru)"Подтвердить" else "Confirm")}},dismissButton={TextButton(onClick={confirmation=null},enabled=!busy){Text(if(ru)"Отмена" else "Cancel")}})
 }
 if(proposing || editing!=null) RelationEditor(member,data.participants,editing,busy,onDismiss={proposing=false;editing=null},onSubmit={target,dominant,text,scopes->
  val original=editing
  if(original!=null) actions.change(original,text,scopes)
  else actions.propose(RelationProposal(agreement_text=text,dominant_user_id=if(dominant)member.id else target,submissive_user_id=if(dominant)target else member.id,scopes=scopes))
 })
}

@Composable
private fun RelationEditor(member:Member,participants:List<Participant>,original:Relation?,busy:Boolean,onDismiss:()->Unit,onSubmit:(String,Boolean,String,List<String>)->Unit) {
 var target by remember {mutableStateOf("")}
 var dominant by remember {mutableStateOf(true)}
 var agreement by remember {mutableStateOf(original?.agreement_text?:"")}
 var scopes by remember {mutableStateOf(original?.scopes?:listOf("rules.assign"))}
 var expanded by remember {mutableStateOf(false)}
 val ru=member.language=="ru"
 AlertDialog(onDismissRequest={if(!busy)onDismiss()},title={Text(if(ru)"Предложение соглашения" else "Propose agreement")},text={Column(Modifier.heightIn(max=450.dp).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(8.dp)) {
  if(original==null) {
   Box {
    OutlinedButton(onClick={expanded=true},enabled=!busy,modifier=Modifier.testTag("relation-target")){Text(participants.find {it.id==target}?.display_name?:if(ru)"Выберите участника" else "Select participant")}
    DropdownMenu(expanded=expanded,onDismissRequest={expanded=false}) {participants.filter {it.id!=member.id}.forEach {person->DropdownMenuItem(text={Text("${person.display_name} · ${person.id.take(8)}")},onClick={target=person.id;expanded=false},modifier=Modifier.testTag("participant-${person.id}"))}}
   }
   Row {RadioButton(dominant,{dominant=true},enabled=!busy);Text(if(ru)"Я предлагаю полномочия относительно участника" else "I request authority relative to this participant")}
   Row {RadioButton(!dominant,{dominant=false},enabled=!busy);Text(if(ru)"Участник получает полномочия относительно меня" else "This participant receives authority relative to me")}
  }
  Text(if(ru)"Для активации нужны отдельные согласия обоих участников." else "Both participants must separately accept before activation.")
  OutlinedTextField(agreement,{if(it.length<=10000)agreement=it},label={Text(if(ru)"Текст соглашения" else "Agreement text")},enabled=!busy,minLines=3,modifier=Modifier.testTag("relation-agreement"))
  relationScopes.forEach {scope->Row {Checkbox(scope in scopes,{checked->scopes=if(checked)scopes+scope else scopes-scope},enabled=!busy,modifier=Modifier.testTag("scope-$scope").semantics {contentDescription=scope});Text(scope)}}
 }},confirmButton={TextButton(onClick={onSubmit(target,dominant,agreement,scopes)},enabled=!busy&&agreement.isNotBlank()&&scopes.isNotEmpty()&&(original!=null||target.isNotBlank()),modifier=Modifier.testTag("submit-relation")){Text(if(ru)"Предложить" else "Propose")}},dismissButton={TextButton(onClick=onDismiss,enabled=!busy){Text(if(ru)"Отмена" else "Cancel")}})
}
