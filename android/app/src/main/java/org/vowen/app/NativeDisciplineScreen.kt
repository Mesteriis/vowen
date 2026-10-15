package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import java.util.UUID

/** Identity and exact consent are server-owned. Recipients can withdraw, never rewrite conditions. */
data class DisciplineActions(val refresh:()->Unit,val create:(DisciplineCreate)->Unit,val revise:(DisciplineRecord,DisciplineEdit)->Unit,val decide:(DisciplineRecord,String,String)->Unit)

@Composable
fun NativeDisciplineScreen(member:Member,data:WorkspaceState,busy:Boolean,completed:Int,actions:DisciplineActions) {
 val ru=member.language=="ru"
 fun t(en:String,local:String)=if(ru)local else en
 fun name(id:String)=data.participants.find{it.id==id}?.display_name?:id
 var editing by remember {mutableStateOf(false)}
 var selected by remember {mutableStateOf<DisciplineRecord?>(null)}
 var review by remember {mutableStateOf<DisciplineRecord?>(null)}
 var history by remember {mutableStateOf("")}
 var comment by remember {mutableStateOf("")}
 LaunchedEffect(completed){editing=false;review=null;comment=""}
 Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
  Text(t("Discipline","Дисциплина"),style=MaterialTheme.typography.headlineSmall)
  Text(t("An alleged event is not an agreed fact. Acceptance is personal and can be withdrawn.","Предполагаемое событие не является установленным фактом. Согласие личное и может быть отозвано."))
  TextButton(onClick=actions.refresh,enabled=!busy){Text(t("Refresh discipline","Обновить дисциплину"))}
  VowenActionButton(onClick={selected=null;editing=true},enabled=!busy&&!member.paused,modifier=Modifier.testTag("new-discipline")){Text(t("New discipline proposal","Новое дисциплинарное предложение"))}
  if(editing) key(selected?.id,selected?.revision){DisciplineEditor(member,data,selected,busy,actions,{editing=false})}
  OutlinedTextField(comment,{if(it.length<=5000)comment=it},label={Text(t("Transition comment","Комментарий к действию"))},enabled=!busy,modifier=Modifier.testTag("discipline-comment"))
  if(data.discipline.isEmpty())Text(t("No visible discipline records","Нет доступных дисциплинарных записей"))
  data.discipline.forEach {r->
   val v=r.versions.first {it.id==r.version_id}
   Card(Modifier.fillMaxWidth()) {Column(Modifier.padding(16.dp),verticalArrangement=Arrangement.spacedBy(8.dp)) {
    Text("${name(r.author_id)} → ${name(r.recipient_id)}",style=MaterialTheme.typography.titleMedium)
    Text(v.description);Text(v.conditions);Text(r.status)
    Text(t("Exact version: ","Точная версия: ")+r.version_id)
    Text(t("Reviewers: ","Проверяющие: ")+r.reviewer_ids.joinToString{ name(it) })
    v.rule_version_id?.let{Text("${v.rule_title} · $it")}
    v.occurrence_id?.let{Text(t("Ritual occurrence: ","Выполнение ритуала: ")+it)}
    v.deadline?.let{Text(t("Deadline: ","Срок: ")+it)}
    if(!r.effective && r.status in listOf("accepted","in_progress","completed"))Text(t("Execution suspended: current authority required.","Выполнение приостановлено: нужны актуальные полномочия."))
    if(r.recipient_id==member.id){
     if(r.status=="proposed"){
      TextButton(onClick={review=r},enabled=!busy&&!member.paused,modifier=Modifier.testTag("accept-discipline-${r.id}")){Text(t("Accept proposal","Принять предложение"))}
      TextButton(onClick={actions.decide(r,"decline",comment)},enabled=!busy){Text(t("Decline proposal","Отклонить предложение"))}
     }
     if(r.status=="accepted")TextButton(onClick={actions.decide(r,"start",comment)},enabled=!busy&&!member.paused&&r.effective){Text(t("Start action","Начать выполнение"))}
     if(r.status=="in_progress")TextButton(onClick={actions.decide(r,"complete",comment)},enabled=!busy&&!member.paused&&r.effective){Text(t("Mark completed","Отметить выполнение"))}
     if(r.status in listOf("proposed","accepted","in_progress","completed"))TextButton(onClick={actions.decide(r,"dispute",comment)},enabled=!busy){Text(t("Dispute proposal","Оспорить предложение"))}
    }
    if(r.status=="completed"&&member.id in r.reviewer_ids)TextButton(onClick={actions.decide(r,"confirm",comment)},enabled=!busy&&!member.paused&&r.effective){Text(t("Confirm completion","Подтвердить выполнение"))}
    if(r.status !in listOf("confirmed","declined","cancelled")){
     if(r.author_id==member.id)TextButton(onClick={selected=r;editing=true},enabled=!busy&&!member.paused,modifier=Modifier.testTag("revise-discipline-${r.id}")){Text(t("Revise conditions","Изменить условия"))}
     TextButton(onClick={actions.decide(r,"cancel",comment)},enabled=!busy,modifier=Modifier.testTag("cancel-discipline-${r.id}")){Text(t("Withdraw / cancel","Отозвать / отменить"))}
    }
    TextButton(onClick={history=if(history==r.id)"" else r.id},enabled=!busy){Text(t("Show discipline history","Показать историю дисциплины"))}
    if(history==r.id){r.versions.forEach{old->Text("${old.id} · ${old.created_at}");Text(old.description);Text(old.conditions);old.rule_version_id?.let{Text("${old.rule_title} · $it")}};r.history.forEach{h->Text("${h.revision} · ${h.status} · ${name(h.actor_id)} · ${h.created_at} · ${h.version_id}\n${h.comment}")}}
   }}
  }
 }
 review?.let {r->val v=r.versions.first{it.id==r.version_id};AlertDialog(onDismissRequest={if(!busy)review=null},title={Text(t("Review discipline version","Подтверждение версии дисциплины"))},text={Column(Modifier.verticalScroll(rememberScrollState())){Text(v.description);Text(v.conditions,Modifier.testTag("discipline-review-conditions"));Text(r.version_id);v.rule_version_id?.let{Text("${v.rule_title} · $it")};v.deadline?.let{Text(it)};Text(t("You may decline, dispute or withdraw consent.","Вы можете отклонить, оспорить или отозвать согласие."))}},confirmButton={TextButton(onClick={actions.decide(r,"accept",comment)},enabled=!busy&&!member.paused,modifier=Modifier.testTag("confirm-discipline-version")){Text(t("Confirm exact version","Подтверждаю точную версию"))}},dismissButton={TextButton(onClick={review=null},enabled=!busy){Text(t("Cancel","Отмена"))}})}
}

@Composable
private fun DisciplineEditor(member:Member,data:WorkspaceState,record:DisciplineRecord?,busy:Boolean,actions:DisciplineActions,cancel:()->Unit){
 val v=record?.versions?.first{it.id==record.version_id}
 val ru=member.language=="ru"
 fun t(en:String,local:String)=if(ru)local else en
 var recipient by remember {mutableStateOf(record?.recipient_id?:"")}
 var reviewers by remember {mutableStateOf(record?.reviewer_ids?:emptyList())}
 var description by remember {mutableStateOf(v?.description?:"")}
 var conditions by remember {mutableStateOf(v?.conditions?:"")}
 var deadline by remember {mutableStateOf(v?.deadline?:"")}
 var rule by remember {mutableStateOf(v?.rule_version_id?:"")}
 var occurrence by remember {mutableStateOf(v?.occurrence_id?:"")}
 val key=remember {UUID.randomUUID().toString()}
 Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
  M4Choice(t("Discipline recipient","Адресат записи"),recipient,data.participants.filter{it.id!=member.id}.map{it.id to it.display_name},busy||record!=null){recipient=it;rule="";occurrence="";reviewers=reviewers-it}
  OutlinedTextField(description,{if(it.length<=10000)description=it},label={Text(t("Description of alleged event","Описание предполагаемого события"))},enabled=!busy,modifier=Modifier.testTag("discipline-description"))
  OutlinedTextField(conditions,{if(it.length<=10000)conditions=it},label={Text(t("Proposed conditions","Предлагаемые условия"))},enabled=!busy,modifier=Modifier.testTag("discipline-conditions"))
  OutlinedTextField(deadline,{deadline=it},label={Text(t("Deadline (ISO 8601 with timezone)","Срок (ISO 8601 с часовым поясом)"))},enabled=!busy)
  val ruleOptions=data.ruleAssignments.filter{it.recipient_id==recipient&&it.accepted_at!=null}.map{it.rule_version_id to "${it.title} · ${it.rule_version_id}"}+(v?.rule_version_id?.let{listOf(it to "${v.rule_title} · $it")}?:emptyList())
  M4Choice(t("Exact rule version (optional)","Точная версия правила (необязательно)"),rule,listOf("" to "—")+ruleOptions.distinctBy{it.first},busy){rule=it}
  val occurrenceOptions=data.ritualOccurrences.filter{it.recipient_id==recipient}.map{it.id to "${it.title} · ${it.local_day}"}+(v?.occurrence_id?.let{listOf(it to it)}?:emptyList())
  M4Choice(t("Related ritual occurrence (optional)","Выполнение ритуала (необязательно)"),occurrence,listOf("" to "—")+occurrenceOptions.distinctBy{it.first},busy){occurrence=it}
  Text(t("Explicit reviewers with current authority","Назначенные проверяющие с актуальными полномочиями"))
  data.participants.filter{it.id!=recipient}.forEach{p->Row{Checkbox(p.id in reviewers,{checked->reviewers=if(checked)reviewers+p.id else reviewers-p.id},enabled=!busy&&record==null,modifier=Modifier.testTag("discipline-reviewer-${p.id}"));Text(p.display_name)}}
  Text(t("Every revised version requires fresh recipient acceptance.","Новая версия требует нового согласия адресата."))
  VowenActionButton(onClick={if(record==null)actions.create(DisciplineCreate(description=description,conditions=conditions,deadline=deadline.ifBlank{null},rule_version_id=rule.ifBlank{null},occurrence_id=occurrence.ifBlank{null},recipient_id=recipient,reviewer_ids=reviewers,idempotency_key=key)) else actions.revise(record,DisciplineEdit(description=description,conditions=conditions,deadline=deadline.ifBlank{null},rule_version_id=rule.ifBlank{null},occurrence_id=occurrence.ifBlank{null},expected_version=record.revision))},enabled=!busy&&recipient.isNotBlank()&&description.isNotBlank()&&conditions.isNotBlank()&&reviewers.isNotEmpty(),modifier=Modifier.testTag("save-discipline")){Text(t("Send discipline proposal","Отправить дисциплинарное предложение"))}
  TextButton(onClick=cancel,enabled=!busy){Text(t("Cancel","Отмена"))}
 }
}

@Composable
internal fun M4Choice(label:String,value:String,options:List<Pair<String,String>>,disabled:Boolean,onChange:(String)->Unit){
 var expanded by remember {mutableStateOf(false)}
 Box {TextButton(onClick={expanded=true},enabled=!disabled,modifier=Modifier.testTag(label)){Text(label+": "+(options.find{it.first==value}?.second?:"—"))};DropdownMenu(expanded,{expanded=false}){options.forEach{(id,title)->DropdownMenuItem(text={Text(title)},onClick={onChange(id);expanded=false})}}}
}
