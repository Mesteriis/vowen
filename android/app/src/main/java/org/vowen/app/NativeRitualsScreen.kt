package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.unit.dp
import androidx.compose.ui.platform.testTag
import java.time.LocalDate
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale
import java.time.ZoneId
import java.util.UUID

/** Server-provided capabilities govern reports/reviews. Profile labels grant no authority. */
data class RitualActions(
 val refresh:()->Unit,
 val save:(RitualTemplate?,RitualContent)->Unit,
 val template:(RitualTemplate,String)->Unit,
 val history:(RitualTemplate)->Unit,
 val assign:(RitualTemplate,RitualAssign)->Unit,
 val schedule:(RitualAssignment,RitualSchedule)->Unit,
 val assignment:(RitualAssignment,String)->Unit,
 val report:(RitualOccurrence,String,String)->Unit,
 val review:(RitualOccurrence,String,String)->Unit,
 val skip:(RitualOccurrence)->Unit
)
@Composable fun NativeRitualsScreen(member:Member,data:WorkspaceState,busy:Boolean,completed:Int,actions:RitualActions) {
 val ru=member.language=="ru"
 fun label(value:String)=ritualStateLabel(value,ru)
 fun time(value:String)=OffsetDateTime.parse(value).atZoneSameInstant(ZoneId.of(member.timezone)).format(DateTimeFormatter.ofPattern("d MMM uuuu, HH:mm VV",if(ru)Locale.forLanguageTag("ru") else Locale.UK))
 fun t(en:String,rus:String)=if(ru)rus else en
 fun name(id:String)=data.participants.find{it.id==id}?.display_name?:id
 var selected by remember {mutableStateOf<RitualTemplate?>(null)}
 var editing by remember {mutableStateOf(false)}
 var assigning by remember {mutableStateOf<RitualTemplate?>(null)}
 var scheduleFor by remember {mutableStateOf<RitualAssignment?>(null)}
 var reporting by remember {mutableStateOf<RitualOccurrence?>(null)}
 var reviewing by remember {mutableStateOf<RitualOccurrence?>(null)}
 var filter by remember {mutableStateOf("all")}
 LaunchedEffect(completed){editing=false;assigning=null;scheduleFor=null;reporting=null;reviewing=null}
 Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
  Text(t("Rituals","Ритуалы"),style=MaterialTheme.typography.headlineMedium)
  Row {TextButton(onClick=actions.refresh,enabled=!busy){Text(t("Refresh rituals","Обновить ритуалы"))};Button(onClick={selected=null;editing=true},enabled=!busy&&!member.paused){Text(t("New ritual","Новый ритуал"))}}
  var filtering by remember {mutableStateOf(false)}
  Box {TextButton(onClick={filtering=true}){Text(t("Status: ","Статус: ")+(if(filter=="all")t("All","Все") else label(filter)))};DropdownMenu(filtering,{filtering=false}) {listOf("all","scheduled","submitted","approved","needs_changes","missed","skipped","cancelled").forEach {s->DropdownMenuItem(text={Text(if(s=="all")t("All","Все") else label(s))},onClick={filter=s;filtering=false})}}}
  if(data.ritualOccurrences.isEmpty())Text(t("No visible occurrences yet.","Пока нет доступных выполнений."))
  data.ritualOccurrences.filter{filter=="all"||it.status==filter}.forEach {o->
   Card(Modifier.fillMaxWidth()) {Column(Modifier.padding(16.dp)) {
    Text(o.title,style=MaterialTheme.typography.titleLarge)
    Text("${name(o.recipient_id)} · ${o.local_day}",color=MaterialTheme.colorScheme.onSurfaceVariant)
    Text(o.description)
    Text(label(o.status),color=MaterialTheme.colorScheme.primary)
    Text(t("Due: ","Время: ")+time(o.due_at),style=MaterialTheme.typography.bodySmall)
    Text(t("Report until: ","Отчёт до: ")+time(o.expires_at),style=MaterialTheme.typography.bodySmall)
    o.reports.forEach {r->HorizontalDivider();Text(t("Attempt ","Попытка ")+r.attempt);Text(r.text);r.decision?.let{Text(label(it))};r.comment?.let{if(it.isNotEmpty())Text(it)}}
    if(o.can_report&&!member.paused)TextButton(onClick={reporting=o},enabled=!busy,modifier=Modifier.testTag("report-${o.id}")){Text(t("Write report","Написать отчёт"))}
    if(o.can_review&&!member.paused)TextButton(onClick={reviewing=o},enabled=!busy,modifier=Modifier.testTag("review-${o.id}")){Text(t("Review report","Проверить отчёт"))}
    if(o.recipient_id==member.id&&o.status in listOf("scheduled","needs_changes"))TextButton(onClick={actions.skip(o)},enabled=!busy){Text(t("Skip occurrence","Пропустить выполнение"))}
   }}
  }
  if(editing)key(selected?.id,selected?.revision){RitualEditor(selected,busy||member.paused,ru,{actions.save(selected,it)},{editing=false})}
  Text(t("Ritual library","Библиотека ритуалов"),style=MaterialTheme.typography.titleLarge)
  data.rituals.forEach {r->
   Text(r.title,style=MaterialTheme.typography.titleMedium);Text(r.description);Text("${label(r.status)}",style=MaterialTheme.typography.bodySmall)
   TextButton(onClick={selected=r;editing=true},enabled=!busy&&!member.paused){Text(if(r.status=="draft")t("Edit ritual draft","Изменить черновик") else t("New ritual version","Новая версия"))}
   if(r.status=="draft")TextButton(onClick={actions.template(r,"publish")},enabled=!busy&&!member.paused){Text(t("Publish ritual","Опубликовать ритуал"))}
   if(r.status=="published")TextButton(onClick={assigning=r;scheduleFor=null},enabled=!busy&&!member.paused){Text(t("Assign ritual","Назначить ритуал"))}
   TextButton(onClick={actions.history(r)},enabled=!busy){Text(t("Version history","История версий"))}
   if(r.status!="archived")TextButton(onClick={actions.template(r,"archive")},enabled=!busy){Text(t("Archive ritual","Архивировать ритуал"))}
  }
  if(data.ritualHistory.isNotEmpty()){Text(t("Version history","История версий"));data.ritualHistory.forEach{v->Text(v.title);Text(v.description);Text(label(v.status))}}
  if(assigning!=null||scheduleFor!=null)key(assigning?.id,scheduleFor?.id,scheduleFor?.revision){RitualAssignmentEditor(member,data.participants,assigning,scheduleFor,busy,ru,{command->assigning?.let{actions.assign(it,command)}},{s->scheduleFor?.let{actions.schedule(it,s)}},{assigning=null;scheduleFor=null})}
  Text(t("Assignments","Назначения"),style=MaterialTheme.typography.titleLarge)
  data.ritualAssignments.forEach {a->
   Text(a.title,style=MaterialTheme.typography.titleMedium);Text("${name(a.recipient_id)} · ${label(a.status)}");Text("${label(a.schedule.kind)} · ${a.schedule.hour}:${a.schedule.minute.toString().padStart(2,'0')} ${a.schedule.timezone}")
   if(a.issuer_id==member.id&&a.effective)TextButton(onClick={scheduleFor=a;assigning=null},enabled=!busy){Text(t("Change schedule","Изменить расписание"))}
   if(a.status=="active"&&(a.recipient_id==member.id||a.issuer_id==member.id))TextButton(onClick={actions.assignment(a,"pause")},enabled=!busy){Text(t("Pause ritual","Приостановить ритуал"))}
   if(a.status=="paused"&&a.recipient_id==member.id)TextButton(onClick={actions.assignment(a,"resume")},enabled=!busy&&!member.paused){Text(t("Resume ritual","Возобновить ритуал"))}
   if(a.status!="revoked"&&(a.recipient_id==member.id||a.issuer_id==member.id))TextButton(onClick={actions.assignment(a,"revoke")},enabled=!busy){Text(t("Revoke ritual","Отозвать ритуал"))}
  }
  if(data.ritualNotices.isNotEmpty()) {Text(t("Updates","Обновления"),style=MaterialTheme.typography.titleLarge);data.ritualNotices.take(5).forEach{Text(t("You have an update in the app","У вас есть обновление в приложении"));Text(time(it.created_at),style=MaterialTheme.typography.bodySmall)}}
 }
 reporting?.let {o->key(o.id){RitualReportDialog(o,busy,ru,{text,key->actions.report(o,text,key)},{reporting=null})}}
 reviewing?.let {o->key(o.id){var comment by remember{mutableStateOf("")};AlertDialog(onDismissRequest={if(!busy)reviewing=null},title={Text(o.title)},text={Column(Modifier.verticalScroll(rememberScrollState())){Text(o.reports.lastOrNull()?.text?:"");OutlinedTextField(comment,{if(it.length<=10000)comment=it},label={Text(t("Review comment","Комментарий проверяющего"))},enabled=!busy)}},confirmButton={TextButton(onClick={actions.review(o,"approved",comment)},enabled=!busy,modifier=Modifier.testTag("ritual-approve")){Text(t("Approve report","Одобрить отчёт"))}},dismissButton={Column{TextButton(onClick={actions.review(o,"needs_changes",comment)},enabled=!busy,modifier=Modifier.testTag("ritual-request-changes")){Text(t("Request changes","Вернуть на доработку"))};TextButton(onClick={reviewing=null},enabled=!busy){Text(t("Cancel","Отмена"))}}})}}
}
@Composable private fun RitualReportDialog(o:RitualOccurrence,busy:Boolean,ru:Boolean,submit:(String,String)->Unit,cancel:()->Unit){
 var text by remember{mutableStateOf("")};var key by remember{mutableStateOf(UUID.randomUUID().toString())}
 AlertDialog(onDismissRequest={if(!busy)cancel()},title={Text(o.title)},text={Column(Modifier.verticalScroll(rememberScrollState())){Text(o.description);OutlinedTextField(text,{if(it.length<=10000){text=it;key=UUID.randomUUID().toString()}},label={Text(if(ru)"Отчёт ритуала" else "Ritual report")},enabled=!busy,modifier=Modifier.testTag("ritual-report-text"))}},confirmButton={TextButton(onClick={submit(text,key)},enabled=!busy&&text.isNotBlank(),modifier=Modifier.testTag("submit-ritual-report")){Text(if(ru)"Отправить отчёт" else "Submit report")}},dismissButton={TextButton(onClick=cancel,enabled=!busy){Text(if(ru)"Отмена" else "Cancel")}})
}
@Composable private fun RitualEditor(r:RitualTemplate?,busy:Boolean,ru:Boolean,save:(RitualContent)->Unit,cancel:()->Unit){
 var title by remember{mutableStateOf(r?.title?:"")};var description by remember{mutableStateOf(r?.description?:"")}
 OutlinedTextField(title,{if(it.length<=200)title=it},label={Text(if(ru)"Название ритуала" else "Ritual title")},enabled=!busy)
 OutlinedTextField(description,{if(it.length<=10000)description=it},label={Text(if(ru)"Описание ритуала" else "Ritual description")},enabled=!busy)
 Button(onClick={save(RitualContent(title=title,description=description))},enabled=!busy&&title.isNotBlank()&&description.isNotBlank()){Text(if(ru)"Сохранить ритуал" else "Save ritual")}
 TextButton(onClick=cancel,enabled=!busy){Text(if(ru)"Отмена" else "Cancel")}
}
@Composable private fun RitualAssignmentEditor(member:Member,participants:List<Participant>,template:RitualTemplate?,assignment:RitualAssignment?,busy:Boolean,ru:Boolean,assign:(RitualAssign)->Unit,edit:(RitualSchedule)->Unit,cancel:()->Unit){
 fun t(en:String,rus:String)=if(ru)rus else en
 val old=assignment?.schedule
 var recipient by remember{mutableStateOf("")};var reviewers by remember{mutableStateOf(emptyList<String>())};var expanded by remember{mutableStateOf(false)}
 var kind by remember{mutableStateOf(old?.kind?:"daily")};var timezone by remember{mutableStateOf(old?.timezone?:member.timezone)}
 var date by remember{mutableStateOf(if(old==null)LocalDate.now(ZoneId.of(member.timezone)).toString() else LocalDate.now(ZoneId.of(old.timezone)).plusDays(1).toString())}
 var hour by remember{mutableStateOf((old?.hour?:9).toString())};var minute by remember{mutableStateOf((old?.minute?:0).toString())}
 var days by remember{mutableStateOf(old?.weekdays?:emptyList())};var window by remember{mutableStateOf((old?.window_hours?:24).toString())};var approval by remember{mutableStateOf(true)}
 val key=remember(recipient,reviewers,kind,timezone,date,hour,minute,days,window,approval){UUID.randomUUID().toString()}
 Text(template?.title?:assignment?.title?:"",style=MaterialTheme.typography.titleLarge)
 if(template!=null){Box {TextButton(onClick={expanded=true},enabled=!busy){Text(participants.find{it.id==recipient}?.display_name?:t("Ritual recipient","Адресат ритуала"))};DropdownMenu(expanded,{expanded=false}){participants.filter{it.id!=member.id}.forEach{p->DropdownMenuItem(text={Text(p.display_name)},onClick={recipient=p.id;reviewers=reviewers-p.id;expanded=false})}}}
 participants.filter{it.id!=recipient}.forEach{p->Row{Checkbox(p.id in reviewers,{reviewers=if(it)reviewers+p.id else reviewers-p.id},enabled=!busy,modifier=Modifier.semantics{contentDescription=t("Reviewer: ","Проверяющий: ")+p.display_name});Text(t("Reviewer: ","Проверяющий: ")+p.display_name)}}
 Row{Checkbox(approval,{approval=it},enabled=!busy,modifier=Modifier.semantics{contentDescription=t("Approval required","Требуется проверка")});Text(t("Approval required","Требуется проверка"))}}
 Row{listOf("once","daily","weekly").forEach{k->TextButton(onClick={kind=k;days=if(k=="weekly")listOf(0) else emptyList()},enabled=!busy){Text(k)}}}
 if(kind=="weekly")listOf("Mon","Tue","Wed","Thu","Fri","Sat","Sun").forEachIndexed{i,d->Row{Checkbox(i in days,{days=if(it)days+i else days-i},enabled=!busy,modifier=Modifier.semantics{contentDescription=d});Text(d)}}
 OutlinedTextField(date,{date=it},label={Text(t("Start date · YYYY-MM-DD","Начало · ГГГГ-ММ-ДД"))},enabled=!busy)
 OutlinedTextField(timezone,{timezone=it},label={Text(t("IANA timezone","Часовой пояс IANA"))},enabled=!busy&&assignment==null)
 Row{OutlinedTextField(hour,{hour=it},label={Text(t("Hour","Час"))},enabled=!busy,modifier=Modifier.weight(1f));OutlinedTextField(minute,{minute=it},label={Text(t("Minute","Минута"))},enabled=!busy,modifier=Modifier.weight(1f))}
 OutlinedTextField(window,{window=it},label={Text(t("Report window · hours","Окно отчёта · часы"))},enabled=!busy)
 Text(t("DST: missing time shifts by the gap; repeated time uses the first occurrence. Schedule edits begin tomorrow or later.","DST: отсутствующее время сдвигается на разрыв, повторяющееся — один раз. Изменения — со следующего дня."),style=MaterialTheme.typography.bodySmall)
 val valid=hour.toIntOrNull() in 0..23 && minute.toIntOrNull() in 0..59 && window.toIntOrNull() in 1..168 && runCatching{LocalDate.parse(date);ZoneId.of(timezone)}.isSuccess && (kind!="weekly"||days.isNotEmpty())
 Button(onClick={val s=RitualSchedule(hour=hour.toInt(),minute=minute.toInt(),kind=kind,timezone=timezone,start_date=date,weekdays=days,window_hours=window.toInt());if(template!=null)assign(RitualAssign(approval_required=approval,idempotency_key=key,recipient_id=recipient,reviewer_ids=reviewers,schedule=s)) else edit(s)},enabled=!busy&&valid&&(template==null||(recipient.isNotEmpty()&&(!approval||reviewers.isNotEmpty())))){Text(if(template==null)t("Save schedule","Сохранить расписание") else t("Create ritual assignment","Создать назначение ритуала"))}
 TextButton(onClick=cancel,enabled=!busy){Text(t("Cancel","Отмена"))}
}

internal fun ritualStateLabel(value:String,ru:Boolean):String = (if(ru)mapOf("scheduled" to "Запланировано","submitted" to "Ждёт проверки","needs_changes" to "На доработке","approved" to "Одобрено","missed" to "Пропущено","skipped" to "Пропущено добровольно","cancelled" to "Отменено","draft" to "Черновик","published" to "Опубликовано","archived" to "В архиве","active" to "Действует","paused" to "На паузе","revoked" to "Отозвано","daily" to "Ежедневно","weekly" to "Еженедельно","once" to "Однократно") else mapOf("scheduled" to "Scheduled","submitted" to "Awaiting review","needs_changes" to "Changes requested","approved" to "Approved","missed" to "Missed","skipped" to "Skipped","cancelled" to "Cancelled","draft" to "Draft","published" to "Published","archived" to "Archived","active" to "Active","paused" to "Paused","revoked" to "Revoked","daily" to "Daily","weekly" to "Weekly","once" to "Once"))[value]?:if(ru)"Недоступно" else "Unavailable"
