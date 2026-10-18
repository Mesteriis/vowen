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

/** Identity, execution state and editing authority are server-owned. */
data class DisciplineActions(val refresh:()->Unit,val create:(DisciplineCreate)->Unit,val revise:(DisciplineRecord,DisciplineEdit)->Unit,val decide:(DisciplineRecord,String,String)->Unit,val dictionary:(String,String,String?,(List<String>)->Unit)->Unit={_,_,_,_->},val templates:(String,(List<PunishmentTemplateView>)->Unit)->Unit={_,_->},val saveTemplate:(PunishmentTemplateView?,PunishmentTemplateCreate,()->Unit)->Unit={_,_,_->},val archiveTemplate:(PunishmentTemplateView,()->Unit)->Unit={_,_->},val assignTemplate:(PunishmentTemplateView,PunishmentAssign,()->Unit)->Unit={_,_,_->})

@Composable
fun NativeDisciplineScreen(member:Member,data:WorkspaceState,busy:Boolean,completed:Int,actions:DisciplineActions) {
 val ru=member.language=="ru"
 fun t(en:String,local:String)=if(ru)local else en
 fun name(id:String)=data.participants.find{it.id==id}?.display_name?:id
 var catalogue by remember{mutableStateOf(true)}
 Row{TextButton(onClick={catalogue=true}){Text(t("Catalogues","Каталоги"))};TextButton(onClick={catalogue=false}){Text(t("Assigned","Назначено"))}}
 if(catalogue){NativePunishmentCatalogue(member,data,busy,actions);return}
 var editing by remember {mutableStateOf(false)}
 var selected by remember {mutableStateOf<DisciplineRecord?>(null)}
 var history by remember {mutableStateOf("")}
 var comment by remember {mutableStateOf("")}
 LaunchedEffect(completed){editing=false;comment=""}
 Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
  Text(t("Punishments","Наказания"),style=MaterialTheme.typography.headlineSmall)
  if(editing) key(selected?.id,selected?.revision){DisciplineEditor(member,data,selected,busy,actions,{editing=false})}
  OutlinedTextField(comment,{if(it.length<=5000)comment=it},label={Text(t("Transition comment","Комментарий к действию"))},enabled=!busy,modifier=Modifier.testTag("discipline-comment"))
  if(data.discipline.isEmpty())Text(t("No visible discipline records","Нет доступных записей о наказаниях"))
  data.discipline.forEach {r->
   val v=r.versions.first {it.id==r.version_id}
   Card(Modifier.fillMaxWidth()) {Column(Modifier.padding(16.dp),verticalArrangement=Arrangement.spacedBy(8.dp)) {
    Text("${name(r.author_id)} → ${name(r.recipient_id)}",style=MaterialTheme.typography.titleMedium)
    Text(v.assignment_title?.takeIf{it.isNotBlank()}?:v.description);Text(v.conditions);v.assignment_comment?.takeIf{it.isNotBlank()}?.let{Text(it)};Text(punishmentSummary(v,ru));Text(punishmentStatus(r.status,ru))
    Text(t("Exact version: ","Точная версия: ")+r.version_id)
    Text(t("Reviewers: ","Проверяющие: ")+r.reviewer_ids.joinToString{ name(it) })
    v.rule_version_id?.let{Text("${v.rule_title} · $it")}
    v.occurrence_id?.let{Text(t("Ritual occurrence: ","Выполнение ритуала: ")+it)}
    v.deadline?.let{Text(t("Deadline: ","Срок: ")+it)}
    if(!r.effective && r.status in listOf("planned","proposed","accepted","in_progress","completed"))Text(t("Execution suspended: current authority required.","Выполнение приостановлено: нужны актуальные полномочия."))
    if(r.recipient_id==member.id){
     if(r.status in listOf("planned","proposed","accepted"))TextButton(onClick={actions.decide(r,"start",comment)},enabled=!busy&&!member.paused&&r.effective){Text(t("Start action","Начать выполнение"))}
     if(r.status=="in_progress")TextButton(onClick={actions.decide(r,"complete",comment)},enabled=!busy&&!member.paused&&r.effective){Text(t("Mark completed","Отметить выполнение"))}
    }
    if(r.status=="completed"&&member.id in r.reviewer_ids)TextButton(onClick={actions.decide(r,"confirm",comment)},enabled=!busy&&!member.paused&&r.effective){Text(t("Confirm completion","Подтвердить выполнение"))}
    if(r.status !in listOf("confirmed","declined","cancelled")){
     if(r.author_id==member.id)TextButton(onClick={selected=r;editing=true},enabled=!busy&&!member.paused,modifier=Modifier.testTag("revise-discipline-${r.id}")){Text(t("Revise conditions","Изменить условия"))}
     if(r.author_id==member.id)TextButton(onClick={actions.decide(r,"cancel",comment)},enabled=!busy,modifier=Modifier.testTag("cancel-discipline-${r.id}")){Text(t("Cancel punishment","Отменить наказание"))}
    }
    TextButton(onClick={history=if(history==r.id)"" else r.id},enabled=!busy){Text(t("Show discipline history","История наказания"))}
    if(history==r.id){r.versions.forEach{old->Text("${old.id} · ${old.created_at}");Text(old.description);Text(old.conditions);Text(punishmentSummary(old,ru));old.rule_version_id?.let{Text("${old.rule_title} · $it")}};r.history.forEach{h->Text("${h.revision} · ${h.status} · ${name(h.actor_id)} · ${h.created_at} · ${h.version_id}\n${h.comment}")}}
   }}
  }
 }
}

@Composable
private fun DisciplineEditor(member:Member,data:WorkspaceState,record:DisciplineRecord?,busy:Boolean,actions:DisciplineActions,cancel:()->Unit){
 val v=record?.versions?.first{it.id==record.version_id}
 val ru=member.language=="ru"
 fun t(en:String,local:String)=if(ru)local else en
 val eligible=data.relations.filter{it.dominant_user_id==member.id&&it.status=="active"&&"discipline.propose" in it.scopes&&it.consent_user_ids.size==2}
 var recipient by remember {mutableStateOf(record?.recipient_id?:eligible.singleOrNull()?.submissive_user_id?:"")}
 var reviewers by remember {mutableStateOf(record?.reviewer_ids?:listOf(member.id))}
 var description by remember {mutableStateOf(v?.description?:"")}
 var conditions by remember {mutableStateOf(v?.conditions?:"")}
 var deadline by remember {mutableStateOf(v?.deadline?:"")}
 var rule by remember {mutableStateOf(v?.rule_version_id?:"")}
 var occurrence by remember {mutableStateOf(v?.occurrence_id?:"")}
 var type by remember{mutableStateOf(v?.punishment_type?:"other")}
 var device by remember{mutableStateOf(v?.device?:"")};var part by remember{mutableStateOf(v?.body_part?:"")}
 var strikes by remember{mutableStateOf(v?.strike_count?.toString()?:"")};var intensity by remember{mutableStateOf(v?.intensity?.toString()?:"")};var days by remember{mutableStateOf(v?.ban_days?.toString()?:"")}
 var devices by remember{mutableStateOf(emptyList<String>())};var parts by remember{mutableStateOf(emptyList<String>())}
 var newDevice by remember{mutableStateOf("")};var newPart by remember{mutableStateOf("")}
 val relationId=eligible.find{it.submissive_user_id==recipient}?.id?:""
 val currentRelationId by rememberUpdatedState(relationId)
 LaunchedEffect(relationId){devices=emptyList();parts=emptyList();if(relationId.isNotBlank()){
  actions.dictionary(relationId,"device",null){if(currentRelationId==relationId)devices=it};actions.dictionary(relationId,"body_part",null){if(currentRelationId==relationId)parts=it}
 }}
 val valid=when(type){"physical"->device in devices&&part in parts&&(strikes.toIntOrNull()?:0) in 1..1000000&&(intensity.toIntOrNull()?:0) in 1..10;"ban"->(days.toIntOrNull()?:0) in 1..36500;else->true}
 val key=remember {UUID.randomUUID().toString()}
 Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
  M4Choice(t("Discipline recipient","Адресат записи"),recipient,data.participants.filter{p->eligible.any{it.submissive_user_id==p.id}}.map{it.id to it.display_name},busy||record!=null){recipient=it;rule="";occurrence="";reviewers=reviewers-it}
  M4Choice(t("Punishment type","Тип наказания"),type,listOf("physical" to t("Physical","Физическое"),"ban" to t("Ban","Запреты"),"other" to t("Other","Другое")),busy){type=it}
  if(type=="physical"){
   M4Choice(t("Device","Девайс"),device,devices.map{it to it},busy){device=it}
   OutlinedTextField(newDevice,{newDevice=it.take(100)},label={Text(t("New device","Новый девайс"))},singleLine=true,enabled=!busy)
   TextButton(onClick={actions.dictionary(relationId,"device",newDevice){devices=it;device=it.first{v->v.equals(newDevice.trim().replace(Regex("\\s+")," "),ignoreCase=true)};newDevice=""}},enabled=!busy&&relationId.isNotBlank()&&newDevice.isNotBlank()){Text(t("Add device","Добавить девайс"))}
   M4Choice(t("Body part","Часть тела"),part,parts.map{it to it},busy){part=it}
   OutlinedTextField(newPart,{newPart=it.take(100)},label={Text(t("New body part","Новая часть тела"))},singleLine=true,enabled=!busy)
   TextButton(onClick={actions.dictionary(relationId,"body_part",newPart){parts=it;part=it.first{v->v.equals(newPart.trim().replace(Regex("\\s+")," "),ignoreCase=true)};newPart=""}},enabled=!busy&&relationId.isNotBlank()&&newPart.isNotBlank()){Text(t("Add body part","Добавить часть тела"))}
   OutlinedTextField(strikes,{strikes=it},label={Text(t("Strike count","Количество ударов"))},singleLine=true,keyboardOptions=androidx.compose.foundation.text.KeyboardOptions(keyboardType=androidx.compose.ui.text.input.KeyboardType.Number),enabled=!busy)
   OutlinedTextField(intensity,{intensity=it},label={Text(t("Intensity (1–10)","Сила воздействия (1–10)"))},singleLine=true,keyboardOptions=androidx.compose.foundation.text.KeyboardOptions(keyboardType=androidx.compose.ui.text.input.KeyboardType.Number),enabled=!busy)
  }
  if(type=="ban")OutlinedTextField(days,{days=it},label={Text(t("Duration in days","Время запрета в днях"))},singleLine=true,keyboardOptions=androidx.compose.foundation.text.KeyboardOptions(keyboardType=androidx.compose.ui.text.input.KeyboardType.Number),enabled=!busy)
  OutlinedTextField(description,{if(it.length<=10000)description=it},label={Text(t("Description of alleged event","Описание предполагаемого события"))},enabled=!busy,modifier=Modifier.testTag("discipline-description"))
  OutlinedTextField(conditions,{if(it.length<=10000)conditions=it},label={Text(t("Conditions","Условия"))},enabled=!busy,modifier=Modifier.testTag("discipline-conditions"))
  OutlinedTextField(deadline,{deadline=it},label={Text(t("Deadline (ISO 8601 with timezone)","Срок (ISO 8601 с часовым поясом)"))},enabled=!busy)
  val ruleOptions=data.ruleAssignments.filter{it.recipient_id==recipient&&it.accepted_at!=null}.map{it.rule_version_id to "${it.title} · ${it.rule_version_id}"}+(v?.rule_version_id?.let{listOf(it to "${v.rule_title} · $it")}?:emptyList())
  M4Choice(t("Exact rule version (optional)","Точная версия правила (необязательно)"),rule,listOf("" to "—")+ruleOptions.distinctBy{it.first},busy){rule=it}
  val occurrenceOptions=data.ritualOccurrences.filter{it.recipient_id==recipient}.map{it.id to "${it.title} · ${it.local_day}"}+(v?.occurrence_id?.let{listOf(it to it)}?:emptyList())
  M4Choice(t("Related ritual occurrence (optional)","Выполнение ритуала (необязательно)"),occurrence,listOf("" to "—")+occurrenceOptions.distinctBy{it.first},busy){occurrence=it}
  Text(t("Explicit reviewers with current authority","Назначенные проверяющие с актуальными полномочиями"))
  data.participants.filter{it.id!=recipient}.forEach{p->Row{Checkbox(p.id in reviewers,{checked->reviewers=if(checked)reviewers+p.id else reviewers-p.id},enabled=!busy&&record==null,modifier=Modifier.testTag("discipline-reviewer-${p.id}"));Text(p.display_name)}}
  Text(t("Participants and reviewers cannot be replaced.","Автор, адресат и проверяющие не заменяются."))
  VowenActionButton(onClick={if(record==null)actions.create(DisciplineCreate(punishment_type=type,device=if(type=="physical")device else null,body_part=if(type=="physical")part else null,strike_count=if(type=="physical")strikes.toIntOrNull() else null,intensity=if(type=="physical")intensity.toIntOrNull() else null,ban_days=if(type=="ban")days.toIntOrNull() else null,description=description,conditions=conditions,deadline=deadline.ifBlank{null},rule_version_id=rule.ifBlank{null},occurrence_id=occurrence.ifBlank{null},recipient_id=recipient,reviewer_ids=reviewers,idempotency_key=key)) else actions.revise(record,DisciplineEdit(punishment_type=type,device=if(type=="physical")device else null,body_part=if(type=="physical")part else null,strike_count=if(type=="physical")strikes.toIntOrNull() else null,intensity=if(type=="physical")intensity.toIntOrNull() else null,ban_days=if(type=="ban")days.toIntOrNull() else null,description=description,conditions=conditions,deadline=deadline.ifBlank{null},rule_version_id=rule.ifBlank{null},occurrence_id=occurrence.ifBlank{null},expected_version=record.revision))},enabled=!busy&&valid&&relationId.isNotBlank()&&recipient.isNotBlank()&&description.isNotBlank()&&conditions.isNotBlank()&&reviewers.isNotEmpty(),modifier=Modifier.testTag("save-discipline")){Text(t("Schedule punishment","Запланировать наказание"))}
  TextButton(onClick=cancel,enabled=!busy){Text(t("Cancel","Отмена"))}
 }
}

@Composable
internal fun M4Choice(label:String,value:String,options:List<Pair<String,String>>,disabled:Boolean,onChange:(String)->Unit){
 var expanded by remember {mutableStateOf(false)}
 Box {TextButton(onClick={expanded=true},enabled=!disabled,modifier=Modifier.testTag(label)){Text(label+": "+(options.find{it.first==value}?.second?:"—"))};DropdownMenu(expanded,{expanded=false}){options.forEach{(id,title)->DropdownMenuItem(text={Text(title)},onClick={onChange(id);expanded=false})}}}
}


private fun punishmentSummary(v:DisciplineVersionView,ru:Boolean):String=when(v.punishment_type){
 "physical"->(if(ru)"Физическое" else "Physical")+" · ${v.device} · ${v.body_part} · ${v.strike_count} · "+(if(ru)"сила " else "intensity ")+"${v.intensity}/10"
 "ban"->(if(ru)"Запрет · ${v.ban_days} дн." else "Ban · ${v.ban_days} days")
 else->if(ru)"Другое" else "Other"
}


private fun punishmentStatus(status:String,ru:Boolean):String=if(!ru)status else mapOf("planned" to "Запланировано","proposed" to "Запланировано","accepted" to "Ранее принято","in_progress" to "Выполняется","completed" to "Выполнено","confirmed" to "Проверено","cancelled" to "Отменено","declined" to "Ранее отклонено","disputed" to "Ранее оспорено")[status]?:status
