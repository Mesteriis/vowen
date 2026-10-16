package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag

/** Explicit commands; neither profile labels nor hidden client state grant authority. */
data class RuleActions(
 val refresh:()->Unit,
 val save:(RuleTemplate?,RuleContent)->Unit,
 val template:(RuleTemplate,String)->Unit,
 val assign:(RuleTemplate,RuleAssign)->Unit,
 val decision:(RuleAssignment,String)->Unit,
 val history:(RuleTemplate)->Unit = {}
)

@Composable
fun NativeRulesScreen(member:Member,data:WorkspaceState,busy:Boolean,completed:Int,actions:RuleActions) {
 val ru=member.language=="ru"
 fun t(en:String,ruText:String)=if(ru)ruText else en
 fun name(id:String)=data.participants.find{it.id==id}?.display_name?:id
 var editing by remember {mutableStateOf(false)}
 var selected by remember {mutableStateOf<RuleTemplate?>(null)}
 var assigning by remember {mutableStateOf<RuleTemplate?>(null)}
 var review by remember {mutableStateOf<RuleAssignment?>(null)}
 LaunchedEffect(completed) {editing=false;assigning=null;review=null}
 Column {
  Text(t("Rules","Правила"),style=MaterialTheme.typography.headlineSmall)
  TextButton(onClick=actions.refresh,enabled=!busy) {Text(t("Refresh rules","Обновить правила"))}
  VowenActionButton(onClick={selected=null;editing=true;assigning=null},enabled=!busy&&!member.paused,modifier=Modifier.testTag("new-rule")) {Text(t("New rule","Новое правило"))}
  if(editing) key(selected?.id,selected?.revision) {RuleEditor(selected,busy||member.paused,ru,{actions.save(selected,it)},{editing=false})}
  data.rules.forEach {rule->
   Text(rule.title,style=MaterialTheme.typography.titleMedium)
   Text(rule.description)
   Text("${rule.status} · ${rule.version_id}")
   TextButton(onClick={selected=rule;editing=true;assigning=null},enabled=!busy&&!member.paused) {Text(if(rule.status=="draft")t("Edit rule draft","Изменить черновик правила") else t("New rule version","Новая версия правила"))}
   if(rule.status=="draft")TextButton(onClick={actions.template(rule,"publish")},enabled=!busy&&!member.paused) {Text(t("Publish rule","Опубликовать правило"))}
   if(rule.status=="published")TextButton(onClick={assigning=rule;editing=false},enabled=!busy&&!member.paused) {Text(t("Assign rule","Назначить правило"))}
   TextButton(onClick={actions.history(rule)},enabled=!busy,modifier=Modifier.testTag("rule-history-${rule.id}")){Text(t("Rule version history","История версий правила"))}
   if(rule.status!="archived")TextButton(onClick={actions.template(rule,"archive")},enabled=!busy) {Text(t("Archive rule","Архивировать правило"))}
  }
  if(data.ruleHistory.isNotEmpty()) {
   Text(t("Version history","История версий"),style=MaterialTheme.typography.titleLarge)
   data.ruleHistory.forEach {v->Text(v.title);Text(v.description);Text("${v.status} · ${v.version_id}")}
  }
  assigning?.let {rule->key(rule.id,rule.version_id){RuleAssignmentEditor(rule,member,data.participants,busy,ru,{actions.assign(rule,it)},{assigning=null})}}
  Text(t("Assignments and history","Назначения и история"),style=MaterialTheme.typography.titleLarge)
  data.ruleAssignments.forEach {a->
   Text("${a.title} · ${name(a.recipient_id)}",style=MaterialTheme.typography.titleMedium)
   Text(a.description);if(!a.discipline.isNullOrBlank())Text(a.discipline)
   Text("${a.status} · ${if(a.effective&&!(member.paused&&a.recipient_id==member.id))t("effective","действует") else t("inactive","не действует")}")
   Text(a.rule_version_id)
   Text(t("Managers: ","Управляющие: ")+a.manager_ids.joinToString {name(it)})
   a.accepted_at?.let {Text(t("Accepted: ","Принято: ")+it)}
   if(a.status=="pending_acceptance"&&a.recipient_id==member.id) {
    TextButton(onClick={review=a},enabled=!busy&&!member.paused,modifier=Modifier.testTag("accept-rule-${a.id}")) {Text(t("Accept rule","Принять правило"))}
    TextButton(onClick={actions.decision(a,"decline")},enabled=!busy) {Text(t("Decline rule","Отклонить правило"))}
   }
   if(a.status in listOf("active","pending_acceptance"))TextButton(onClick={actions.decision(a,"pause")},enabled=!busy,modifier=Modifier.testTag("pause-rule-${a.id}")) {Text(t("Pause rule","Приостановить правило"))}
   if(a.status!="revoked")TextButton(onClick={actions.decision(a,"revoke")},enabled=!busy) {Text(t("Revoke rule","Отозвать правило"))}
  }
 }
 review?.let {a->AlertDialog(onDismissRequest={if(!busy)review=null},title={Text(t("Review exact rule version","Подтверждение точной версии"))},text={Column(Modifier.verticalScroll(rememberScrollState())) {
  Text(a.title)
  Text(a.description,Modifier.testTag("rule-review"));if(!a.discipline.isNullOrBlank())Text(a.discipline)
  Text(a.rule_version_id)
  Text(t("Acceptance replaces the previously active version.","Принятие заменит ранее действовавшую версию."),Modifier.testTag("rule-review-end"))
 }},confirmButton={TextButton(onClick={actions.decision(a,"accept")},enabled=!busy&&!member.paused,modifier=Modifier.testTag("confirm-rule-acceptance")){Text(t("Confirm rule acceptance","Подтверждаю принятие"))}},dismissButton={TextButton(onClick={review=null},enabled=!busy){Text(t("Cancel","Отмена"))}})}
}

@Composable
private fun RuleEditor(rule:RuleTemplate?,busy:Boolean,ru:Boolean,save:(RuleContent)->Unit,cancel:()->Unit) {
 var title by remember {mutableStateOf(rule?.title?:"")}
 var description by remember {mutableStateOf(rule?.description?:"")};var discipline by remember{mutableStateOf(rule?.discipline?:"")}
 Column {
  OutlinedTextField(title,{if(it.length<=200)title=it},label={Text(if(ru)"Название правила" else "Rule title")},enabled=!busy,modifier=Modifier.testTag("rule-title"))
  OutlinedTextField(description,{if(it.length<=10000)description=it},label={Text(if(ru)"Описание правила" else "Rule description")},enabled=!busy,modifier=Modifier.testTag("rule-description"))
  OutlinedTextField(discipline,{if(it.length<=10000)discipline=it},label={Text(if(ru)"Дисциплина по правилу" else "Rule discipline")},enabled=!busy)
  VowenActionButton(onClick={save(RuleContent(title=title,description=description,discipline=discipline))},enabled=!busy&&title.isNotBlank()&&description.isNotBlank(),modifier=Modifier.testTag("save-rule")) {Text(if(ru)"Сохранить правило" else "Save rule")}
  TextButton(onClick=cancel,enabled=!busy){Text(if(ru)"Отмена" else "Cancel")}
 }
}

@Composable
private fun RuleAssignmentEditor(rule:RuleTemplate,member:Member,participants:List<Participant>,busy:Boolean,ru:Boolean,save:(RuleAssign)->Unit,cancel:()->Unit) {
 var recipient by remember {mutableStateOf("")}
 var managers by remember {mutableStateOf(emptyList<String>())}
 var expanded by remember {mutableStateOf(false)}
 Column {
  Text(rule.title)
  Box {
   TextButton(onClick={expanded=true},enabled=!busy){Text(participants.find{it.id==recipient}?.display_name?:if(ru)"Адресат правила" else "Rule recipient")}
   DropdownMenu(expanded,{expanded=false}) {participants.filter{it.id!=member.id}.forEach {p->DropdownMenuItem(text={Text(p.display_name)},onClick={recipient=p.id;managers=managers-p.id;expanded=false})}}
  }
  Text(if(ru)"Явные управляющие с актуальными полномочиями" else "Explicit managers with current authority")
  participants.filter{it.id!=recipient}.forEach {p->Row {Checkbox(p.id in managers,{checked->managers=if(checked)managers+p.id else managers-p.id},enabled=!busy);Text(p.display_name)}}
  VowenActionButton(onClick={save(RuleAssign(rule_version_id=rule.version_id,recipient_id=recipient,manager_ids=managers))},enabled=!busy&&recipient.isNotEmpty()){Text(if(ru)"Предложить правило" else "Send rule proposal")}
  TextButton(onClick=cancel,enabled=!busy){Text(if(ru)"Отмена" else "Cancel")}
 }
}
