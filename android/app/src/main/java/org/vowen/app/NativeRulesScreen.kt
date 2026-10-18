package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.compose.ui.platform.testTag

/** Explicit commands; neither profile labels nor hidden client state grant authority. */
data class RuleActions(
 val refresh:()->Unit,
 val save:(RuleTemplate?,RuleContent)->Unit,
 val template:(RuleTemplate,String)->Unit,
 val assign:(RuleTemplate,RuleAssign)->Unit,
 val decision:(RuleAssignment,String)->Unit,
 val history:(RuleTemplate)->Unit = {},
 val requestChange:((ChangeRequestCreate)->Unit)?=null,
 val decideChange:((ChangeRequestView,String,String)->Unit)?=null
)

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun NativeRulesScreen(member:Member,data:WorkspaceState,busy:Boolean,completed:Int,actions:RuleActions,punishmentActions:DisciplineActions?=null) {
 val ru=member.language=="ru"
 fun t(en:String,ruText:String)=if(ru)ruText else en
 fun name(id:String)=data.participants.find{it.id==id}?.display_name?:id
 var punishmentRule by remember{mutableStateOf<RuleAssignment?>(null)}
 var punishmentTemplates by remember{mutableStateOf(emptyList<PunishmentTemplateView>())}
 var punishmentVariant by remember{mutableStateOf<PunishmentTemplateView?>(null)}
 var changeDraft by remember {mutableStateOf<ChangeRequestCreate?>(null)}
 var tab by remember {mutableStateOf(0)}
 var expanded by remember {mutableStateOf("")}
 var menu by remember {mutableStateOf("")}
 var historyOpen by remember {mutableStateOf(false)}
 var proposing by remember {mutableStateOf(false)}
 val canManage=data.relations.any{it.dominant_user_id==member.id&&it.status=="active"&&"rules.assign" in it.scopes}
 val superiors=data.relations.filter{it.submissive_user_id==member.id&&it.status=="active"&&"rules.assign" in it.scopes}
 LaunchedEffect(completed){changeDraft=null}
 changeDraft?.let{draft->NativeChangeRequestEditor(draft,busy||member.paused,ru,{actions.requestChange?.invoke(it)},{changeDraft=null},data.discipline)}
 var editing by remember {mutableStateOf(false)}
 var selected by remember {mutableStateOf<RuleTemplate?>(null)}
 var assigning by remember {mutableStateOf<RuleTemplate?>(null)}
 var review by remember {mutableStateOf<RuleAssignment?>(null)}
 LaunchedEffect(completed) {editing=false;assigning=null;review=null}
 Column {
  Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Text(t("Rules","Правила"),style=MaterialTheme.typography.headlineSmall);RuleIcon(android.R.drawable.ic_input_add,if(!canManage&&superiors.isNotEmpty())t("Propose rule","Предложить правило") else t("New rule","Новое правило"),!busy&&!member.paused,Modifier.testTag("new-rule")){if(!canManage&&superiors.isNotEmpty())proposing=true else{selected=null;editing=true;assigning=null}}}
  val pending=data.changeRequests.count{it.kind.startsWith("rule_")&&it.status=="pending"}
  ScrollableTabRow(selectedTabIndex=tab,edgePadding=0.dp){listOf(t("Rules","Действуют"),t("Requests","Заявки")+(if(pending>0)" · $pending" else ""),t("Templates","Шаблоны")).forEachIndexed{index,label->Tab(selected=tab==index,onClick={tab=index},text={Text(label,style=MaterialTheme.typography.labelMedium)})}}
  Spacer(Modifier.height(12.dp))
  if(tab==1){NativeChangeRequests(member,data,"rule",busy,completed,actions.decideChange);if(pending==0)Text(t("No pending requests","Нет ожидающих заявок"),style=MaterialTheme.typography.bodySmall)}
  if(superiors.isNotEmpty())Box{if(canManage)TextButton(onClick={proposing=true},enabled=!busy&&!member.paused){Text(t("Propose rule","Предложить правило"))};DropdownMenu(proposing,{proposing=false}){superiors.forEach{r->DropdownMenuItem(text={Text(name(r.dominant_user_id))},onClick={proposing=false;changeDraft=ChangeRequestCreate(kind="rule_add",relation_id=r.id,idempotency_key=java.util.UUID.randomUUID().toString(),reason="")})}}}
  if(editing)RuleTaskDialog(if(selected==null)t("New rule","Новое правило") else t("Edit rule","Редактирование правила"),busy,{editing=false}){key(selected?.id,selected?.revision){RuleEditor(selected,data.discipline,busy||member.paused,ru,{actions.save(selected,it)},{editing=false})}}
  if(tab==2){if(data.rules.isEmpty())Text(t("Create a rule, then assign it.","Создайте правило и назначьте его участнику."),style=MaterialTheme.typography.bodySmall)
  data.rules.forEach {rule->RuleAccordion(rule.title,rule.status,expanded==rule.id,{expanded=if(expanded==rule.id)"" else rule.id}){
   Text(rule.description,style=MaterialTheme.typography.bodyMedium)
   rule.discipline?.takeIf{it.isNotBlank()}?.let{HorizontalDivider();Text(t("Punishment","Наказание"),style=MaterialTheme.typography.labelSmall);Text(it,style=MaterialTheme.typography.bodyMedium)}
   FlowRow(horizontalArrangement=Arrangement.spacedBy(8.dp)){
    RuleIcon(android.R.drawable.ic_menu_edit,t("Edit rule","Редактировать правило"),!busy&&!member.paused){selected=rule;editing=true;assigning=null}
    if(rule.status=="draft")OutlinedButton(onClick={actions.template(rule,"publish")},enabled=!busy&&!member.paused){Text(t("Publish","Опубликовать"))}
    if(rule.status=="published")OutlinedButton(onClick={assigning=rule;editing=false},enabled=!busy&&!member.paused){Text(t("Assign","Назначить"))}
    RuleIcon(android.R.drawable.ic_menu_recent_history,t("Version history","История версий"),!busy,Modifier.testTag("rule-history-${rule.id}")){historyOpen=true;actions.history(rule)}
    if(rule.status!="archived")RuleIcon(android.R.drawable.ic_menu_save,t("Archive rule","Архивировать правило"),!busy){actions.template(rule,"archive")}
   }
  }}}
  if(historyOpen)RuleTaskDialog(t("Version history","История версий"),busy,{historyOpen=false}) {
   Text(t("Version history","История версий"),style=MaterialTheme.typography.titleLarge)
   data.ruleHistory.forEach {v->Text(v.title);Text(v.description);Text("${v.status} · ${v.version_id}")}
  }
  assigning?.let {rule->RuleTaskDialog(t("Assign rule","Назначить правило"),busy,{assigning=null}){key(rule.id,rule.version_id){RuleAssignmentEditor(rule,member,data.participants,busy,ru,{actions.assign(rule,it)},{assigning=null})}}}
  if(tab==0){if(data.ruleAssignments.isEmpty())Text(t("No rules yet","Пока нет правил"),style=MaterialTheme.typography.bodySmall)
  data.ruleAssignments.forEach {a->RuleAccordion(a.title,changeRequestLabel(a.status,ru),expanded==a.id,{expanded=if(expanded==a.id)"" else a.id}){
   Text(name(a.recipient_id),style=MaterialTheme.typography.labelSmall)
   Text(a.description);if(!a.discipline.isNullOrBlank())Text(a.discipline)
   val punishmentRelation=data.relations.find{it.dominant_user_id==member.id&&it.submissive_user_id==a.recipient_id&&it.status=="active"&&"discipline.propose" in it.scopes}
   if(punishmentActions!=null&&punishmentRelation!=null&&a.accepted_at!=null)TextButton(onClick={punishmentRule=a;punishmentTemplates=emptyList();punishmentActions.templates(punishmentRelation.id){punishmentTemplates=it}},enabled=!busy&&!member.paused){Text(t("Assign punishment for violation","Назначить наказание за нарушение"))}
   Text("${a.status} · ${if(a.effective&&!(member.paused&&a.recipient_id==member.id))t("effective","действует") else t("inactive","не действует")}")
   HorizontalDivider()
   Text(a.rule_version_id,style=MaterialTheme.typography.labelSmall)
   Text(t("Managers: ","Управляющие: ")+a.manager_ids.joinToString {name(it)})
   a.accepted_at?.let {Text(t("Accepted: ","Принято: ")+it)}
   if(a.status=="pending_acceptance"&&a.recipient_id==member.id) {
    TextButton(onClick={review=a},enabled=!busy&&!member.paused,modifier=Modifier.testTag("accept-rule-${a.id}")) {Text(t("Accept rule","Принять правило"))}
    TextButton(onClick={actions.decision(a,"decline")},enabled=!busy) {Text(t("Decline rule","Отклонить правило"))}
   }
   FlowRow(horizontalArrangement=Arrangement.spacedBy(8.dp)){
    if(a.recipient_id==member.id&&a.status!="revoked")RuleIcon(android.R.drawable.ic_menu_edit,t("Propose changes","Предложить изменения"),!busy&&!member.paused){changeDraft=ChangeRequestCreate(kind="rule_edit",assignment_id=a.id,expected_version=a.revision,idempotency_key=java.util.UUID.randomUUID().toString(),reason="",content=RuleContent(title=a.title,description=a.description,discipline=a.discipline))}
    if(a.status in listOf("active","pending_acceptance"))RuleIcon(android.R.drawable.ic_media_pause,t("Pause rule","Пауза правила"),!busy,Modifier.testTag("pause-rule-${a.id}")){actions.decision(a,"pause")}
    if(a.status!="revoked")Box{RuleIcon(android.R.drawable.ic_menu_more,t("More actions","Другие действия"),!busy){menu=a.id};DropdownMenu(menu==a.id,{menu=""}){
     if(a.recipient_id==member.id)DropdownMenuItem(text={Text(t("Request removal","Запросить удаление"))},onClick={menu="";changeDraft=ChangeRequestCreate(kind="rule_delete",assignment_id=a.id,expected_version=a.revision,idempotency_key=java.util.UUID.randomUUID().toString(),reason="")},enabled=!busy&&!member.paused)
     DropdownMenuItem(text={Text(if(a.recipient_id==member.id)t("Withdraw consent","Отозвать согласие") else t("Revoke rule","Отозвать правило"))},onClick={menu="";actions.decision(a,"revoke")},enabled=!busy)
    }}
   }
  }}}
 }
 review?.let {a->AlertDialog(onDismissRequest={if(!busy)review=null},title={Text(t("Review exact rule version","Подтверждение точной версии"))},text={Column(Modifier.verticalScroll(rememberScrollState())) {
  Text(a.title)
  Text(a.description,Modifier.testTag("rule-review"));if(!a.discipline.isNullOrBlank())Text(a.discipline)
  Text(a.rule_version_id)
  Text(t("Acceptance replaces the previously active version.","Принятие заменит ранее действовавшую версию."),Modifier.testTag("rule-review-end"))
 }},confirmButton={TextButton(onClick={actions.decision(a,"accept")},enabled=!busy&&!member.paused,modifier=Modifier.testTag("confirm-rule-acceptance")){Text(t("Confirm rule acceptance","Подтверждаю принятие"))}},dismissButton={TextButton(onClick={review=null},enabled=!busy){Text(t("Cancel","Отмена"))}})}
 punishmentRule?.let{rule->if(punishmentActions!=null){
  if(punishmentVariant==null)AlertDialog(onDismissRequest={if(!busy)punishmentRule=null},title={Text(t("Choose punishment","Выбрать наказание"))},text={Column(Modifier.verticalScroll(rememberScrollState())){if(punishmentTemplates.isEmpty())Text(t("No saved variants.","Нет сохранённых вариантов."));punishmentTemplates.forEach{item->TextButton(onClick={punishmentVariant=item},enabled=!busy){Text(item.title)}}}},confirmButton={},dismissButton={TextButton(onClick={punishmentRule=null},enabled=!busy){Text(t("Cancel","Отмена"))}})
  else NativePunishmentAssign(punishmentVariant!!,name(rule.recipient_id),ru,busy,punishmentActions,rule.rule_version_id){punishmentRule=null;punishmentVariant=null}
 }}

}

@Composable
private fun RuleEditor(rule:RuleTemplate?,punishments:List<DisciplineRecord>,busy:Boolean,ru:Boolean,save:(RuleContent)->Unit,cancel:()->Unit) {
 var title by remember {mutableStateOf(rule?.title?:"")}
 var description by remember {mutableStateOf(rule?.description?:"")};var discipline by remember{mutableStateOf(rule?.discipline?:"")}
 Column(Modifier.fillMaxWidth(),verticalArrangement=Arrangement.spacedBy(10.dp)) {
  OutlinedTextField(title,{if(it.length<=200)title=it},label={Text(if(ru)"Название правила" else "Rule title")},enabled=!busy,modifier=Modifier.fillMaxWidth().testTag("rule-title"))
  OutlinedTextField(description,{if(it.length<=10000)description=it},label={Text(if(ru)"Описание правила" else "Rule description")},enabled=!busy,modifier=Modifier.fillMaxWidth().testTag("rule-description"))
  NativePunishmentPicker(punishments,discipline,busy,ru){discipline=it}
  if(rule!=null&&rule.status!="draft")Text(if(ru)"Новая версия требует нового согласия. Принятая действует до замены." else "A new version requires fresh consent. The accepted version continues until replacement.",style=MaterialTheme.typography.bodySmall)
  VowenActionButton(onClick={save(RuleContent(title=title,description=description,discipline=discipline))},enabled=!busy&&title.isNotBlank()&&description.isNotBlank(),modifier=Modifier.testTag("save-rule")) {Text(if(ru)"Сохранить правило" else "Save rule")}
  TextButton(onClick=cancel,enabled=!busy){Text(if(ru)"Отмена" else "Cancel")}
 }
}

@Composable
private fun RuleAssignmentEditor(rule:RuleTemplate,member:Member,participants:List<Participant>,busy:Boolean,ru:Boolean,save:(RuleAssign)->Unit,cancel:()->Unit) {
 var recipient by remember {mutableStateOf("")}
 var managers by remember {mutableStateOf(listOf(member.id))}
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


@Composable private fun RuleIcon(resource:Int,label:String,enabled:Boolean,modifier:Modifier=Modifier,click:()->Unit){OutlinedIconButton(onClick=click,enabled=enabled,modifier=modifier.size(44.dp)){Icon(painterResource(resource),contentDescription=label,modifier=Modifier.size(20.dp))}}
@Composable private fun RuleAccordion(title:String,status:String,open:Boolean,toggle:()->Unit,content:@Composable ColumnScope.()->Unit){
 OutlinedCard(Modifier.fillMaxWidth().padding(bottom=10.dp),shape=RoundedCornerShape(10.dp),border=BorderStroke(1.dp,MaterialTheme.colorScheme.outlineVariant)){
  TextButton(onClick=toggle,modifier=Modifier.fillMaxWidth()){Column(Modifier.weight(1f)){Text(title,style=MaterialTheme.typography.titleMedium,color=MaterialTheme.colorScheme.onSurface);Text(status,style=MaterialTheme.typography.labelSmall,color=MaterialTheme.colorScheme.onSurfaceVariant)};Icon(painterResource(if(open)android.R.drawable.arrow_up_float else android.R.drawable.arrow_down_float),contentDescription=null,modifier=Modifier.size(18.dp))}
  AnimatedVisibility(open){Column(Modifier.fillMaxWidth().padding(14.dp),verticalArrangement=Arrangement.spacedBy(10.dp),content=content)}
 }
}
@Composable internal fun RuleTaskDialog(title:String,busy:Boolean,close:()->Unit,content:@Composable ColumnScope.()->Unit){
 val phone=LocalConfiguration.current.screenWidthDp<600
 Dialog(onDismissRequest={if(!busy)close()},properties=DialogProperties(usePlatformDefaultWidth=false)){
  Surface(modifier=if(phone)Modifier.fillMaxSize() else Modifier.widthIn(max=540.dp).fillMaxWidth().heightIn(max=800.dp),shape=RoundedCornerShape(if(phone)0.dp else 12.dp)){
   Column(Modifier.safeDrawingPadding().padding(16.dp).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(12.dp)){
    Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Text(title,style=MaterialTheme.typography.headlineSmall,modifier=Modifier.weight(1f));RuleIcon(android.R.drawable.ic_menu_close_clear_cancel,if(LocalConfiguration.current.locales[0].language=="ru")"Закрыть" else "Close",!busy,click=close)}
    content()
   }
  }
 }
}
