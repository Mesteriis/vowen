package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.Alignment
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.sp
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
 var selectedId by remember {mutableStateOf(data.relations.firstOrNull()?.id?:"")}
 var menu by remember {mutableStateOf(false)}
 var permissionsOpen by remember {mutableStateOf(true)}
 val selected=data.relations.find{it.id==selectedId}?:data.relations.firstOrNull()
 fun status(value:String)=if(ru)when(value){"active"->"Действуют";"paused"->"На паузе";"proposed"->"Ожидают согласия";"revoked"->"Отозваны";else->"Недоступно"} else value
 val wide=LocalConfiguration.current.screenWidthDp>=720
 Column(verticalArrangement=Arrangement.spacedBy(20.dp)) {
  Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween,verticalAlignment=Alignment.CenterVertically){Text(if(ru)"Отношения" else "Relationships",style=MaterialTheme.typography.headlineSmall);selected?.let{r->Row(verticalAlignment=Alignment.CenterVertically){RelationAvatar(name(r.dominant_user_id));Icon(painterResource(android.R.drawable.ic_media_play),null,Modifier.padding(horizontal=8.dp).size(14.dp));RelationAvatar(name(r.submissive_user_id))}}}
  Row(Modifier.horizontalScroll(rememberScrollState()),horizontalArrangement=Arrangement.spacedBy(8.dp)){
   data.relations.forEach{r->OutlinedButton(onClick={selectedId=r.id;menu=false},enabled=!busy,modifier=Modifier.testTag("relation-choice-${r.id}"),shape=RoundedCornerShape(8.dp),border=BorderStroke(1.dp,if(selected?.id==r.id)MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant)){
    val partner=if(r.dominant_user_id==member.id)r.submissive_user_id else r.dominant_user_id
    RelationAvatar(name(partner));Spacer(Modifier.width(8.dp));Column{Text(name(partner),style=MaterialTheme.typography.labelLarge);Text(status(r.status),style=MaterialTheme.typography.labelSmall)}
   }}
  }
  TextButton(onClick={proposing=true},enabled=!busy&&!member.paused&&data.participants.any{it.id!=member.id},modifier=Modifier.testTag("propose-relation")){Icon(painterResource(android.R.drawable.ic_input_add),null,Modifier.size(18.dp));Spacer(Modifier.width(8.dp));Text(if(ru)"Предложить отношения" else "Propose relationship")}
  HorizontalDivider()
  if(selected==null)Text(if(ru)"Пока нет отношений" else "No relationships yet")
  selected?.let{relation->
   val main:@Composable ()->Unit={Column(verticalArrangement=Arrangement.spacedBy(16.dp)){
    Row(verticalAlignment=Alignment.CenterVertically){RelationAvatar(name(relation.dominant_user_id));Icon(painterResource(android.R.drawable.ic_media_play),null,Modifier.padding(horizontal=12.dp).size(16.dp));RelationAvatar(name(relation.submissive_user_id))}
    Text("${name(relation.dominant_user_id)} → ${name(relation.submissive_user_id)}",style=MaterialTheme.typography.titleLarge)
    Text(if(ru)"${name(relation.dominant_user_id)} — верхний · ${name(relation.submissive_user_id)} — нижний" else "${name(relation.dominant_user_id)} — upper · ${name(relation.submissive_user_id)} — lower",style=MaterialTheme.typography.bodySmall)
    Row(verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(8.dp)){
     Text(status(relation.status),style=MaterialTheme.typography.labelMedium)
     if(relation.status in listOf("active","proposed"))IconButton(onClick={confirmation=relation to "pause"},enabled=!busy){Icon(painterResource(android.R.drawable.ic_media_pause),if(ru)"Приостановить отношения" else "Pause relationship")}
     if(relation.status=="paused")IconButton(onClick={confirmation=relation to "resume"},enabled=!busy&&!member.paused){Icon(painterResource(android.R.drawable.ic_media_play),if(ru)"Запросить возобновление" else "Request resumption")}
     if(relation.status!="revoked")Box{IconButton(onClick={menu=true},enabled=!busy){Icon(painterResource(android.R.drawable.ic_menu_more),if(ru)"Действия с отношениями" else "Relationship actions")};DropdownMenu(menu,{menu=false}){
      DropdownMenuItem(text={Text(if(ru)"Предложить новую версию" else "Propose new version")},onClick={menu=false;editing=relation},enabled=!busy&&!member.paused)
      DropdownMenuItem(text={Text(if(ru)"Отозвать соглашение" else "Withdraw agreement")},onClick={menu=false;confirmation=relation to "revoke"},enabled=!busy)
     }}
    }
    HorizontalDivider();Text(if(ru)"Соглашение" else "Agreement",style=MaterialTheme.typography.titleLarge)
    Text(relation.agreement_text)
    Text(if(ru)"Версия ${relation.version} · Подтверждения ${relation.consent_user_ids.size}/2" else "Version ${relation.version} · Confirmations ${relation.consent_user_ids.size}/2",style=MaterialTheme.typography.bodySmall)
    if(relation.status=="proposed"&&member.id !in relation.consent_user_ids)VowenActionButton(onClick={confirmation=relation to "accept"},enabled=!busy&&!member.paused,modifier=Modifier.testTag("accept-${relation.id}")){Text(if(ru)"Рассмотреть и подтвердить" else "Review and accept")}
   }}
   val permissions:@Composable ()->Unit={Column(verticalArrangement=Arrangement.spacedBy(12.dp)){
    TextButton(onClick={permissionsOpen=!permissionsOpen}){Text(if(ru)"Полномочия" else "Permissions",style=MaterialTheme.typography.titleLarge)}
    if(permissionsOpen){relation.scopes.forEach{scope->Text(relationScopeTitle(scope,ru),style=MaterialTheme.typography.bodyMedium);HorizontalDivider()};Text(if(ru)"Полномочия действуют только в этих отношениях." else "Permissions apply only to this relationship.",style=MaterialTheme.typography.bodySmall)}
   }}
   if(wide)Row(horizontalArrangement=Arrangement.spacedBy(28.dp)){Column(Modifier.weight(1.4f)){main()};Column(Modifier.weight(1f)){permissions()}}else{main();HorizontalDivider();permissions()}
  }
 }
 confirmation?.let {(relation,action)->
  AlertDialog(onDismissRequest={if(!busy)confirmation=null},title={Text(if(ru)"Подтвердить действие" else "Confirm action")},text={Column(Modifier.heightIn(max=350.dp).verticalScroll(rememberScrollState())) {
   Text("${name(relation.dominant_user_id)} → ${name(relation.submissive_user_id)}")
   Text("v${relation.version} · ${relation.relation_version_id}")
   Text(relation.agreement_text,modifier=Modifier.testTag("agreement-review"))
   Text(relation.scopes.joinToString("\n"){relationScopeTitle(it,ru)})
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
  relationScopes.forEach {scope->Row {Checkbox(scope in scopes,{checked->scopes=if(checked)scopes+scope else scopes-scope},enabled=!busy,modifier=Modifier.testTag("scope-$scope").semantics {contentDescription=scope});Text(relationScopeTitle(scope,ru))}}
 }},confirmButton={TextButton(onClick={onSubmit(target,dominant,agreement,scopes)},enabled=!busy&&agreement.isNotBlank()&&scopes.isNotEmpty()&&(original!=null||target.isNotBlank()),modifier=Modifier.testTag("submit-relation")){Text(if(ru)"Предложить" else "Propose")}},dismissButton={TextButton(onClick=onDismiss,enabled=!busy){Text(if(ru)"Отмена" else "Cancel")}})
}

@Composable private fun RelationAvatar(name:String){
 Surface(shape=CircleShape,color=MaterialTheme.colorScheme.surfaceVariant,border=BorderStroke(1.dp,MaterialTheme.colorScheme.outlineVariant),modifier=Modifier.size(38.dp)){
  Box(contentAlignment=Alignment.Center){Text(name.take(1),fontSize=23.sp,lineHeight=23.sp,color=MaterialTheme.colorScheme.primary,style=MaterialTheme.typography.bodyLarge.copy(platformStyle=androidx.compose.ui.text.PlatformTextStyle(includeFontPadding=false)))}
 }
}
private fun relationScopeTitle(scope:String,ru:Boolean):String=if(!ru)when(scope){"rules.assign"->"Propose rules";"rituals.assign"->"Assign rituals";"rituals.review"->"Review reports";"discipline.propose"->"Assign punishments";"discipline.review"->"Review punishments";"rewards.grant"->"Grant rewards";else->scope} else when(scope){"rules.assign"->"Предлагать правила";"rituals.assign"->"Назначать ритуалы";"rituals.review"->"Проверять отчёты";"discipline.propose"->"Назначать наказания";"discipline.review"->"Подтверждать выполнение наказаний";"rewards.grant"->"Выдавать награды";else->"Полномочие"}
