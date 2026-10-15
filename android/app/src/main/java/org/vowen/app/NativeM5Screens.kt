package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import java.time.LocalDate
import java.time.LocalTime
import java.time.ZoneId
import java.util.UUID

data class SurveyActions(val create:(SurveyCreate)->Unit,val transition:(SurveyPlan,String)->Unit,val send:(SurveyPlan,String,()->Unit)->Unit,val history:(SurveyPlan,(List<SurveyWave>)->Unit)->Unit)
data class NotificationActions(val save:(NotificationPatch)->Unit)

@Composable
fun NativeNotificationScreen(settings:NotificationSettings?,busy:Boolean,actions:NotificationActions,ru:Boolean){
 fun t(en:String,r:String)=if(ru)r else en
 if(settings==null){Text(t("Refresh to load notification settings","Обновите настройки уведомлений"));return}
 var channels by remember(settings.revision){mutableStateOf(settings.channels)}
 var quiet by remember(settings.revision){mutableStateOf(settings.quiet_enabled)}
 fun clock(m:Int)="%02d:%02d".format(java.util.Locale.ROOT,m/60,m%60)
 var start by remember(settings.revision){mutableStateOf(clock(settings.quiet_start))}
 var end by remember(settings.revision){mutableStateOf(clock(settings.quiet_end))}
 fun minutes(s:String)=runCatching{LocalTime.parse(s).let{it.hour*60+it.minute}}.getOrNull()
 Column(verticalArrangement=Arrangement.spacedBy(8.dp)){
  Text(t("Notifications","Уведомления"),style=MaterialTheme.typography.headlineSmall)
  listOf("in_app" to t("In-app notices","Уведомления в приложении"),"telegram" to "Telegram").forEach{(id,label)->Row{Checkbox(id in channels,{channels=if(it)channels+id else channels-id},enabled=!busy,modifier=Modifier.testTag("channel-$id").semantics{contentDescription=label});Text(label)}}
  Text(if(settings.telegram_connected)t("Bot connected","Бот подключён") else t("Bot not connected","Бот не подключён"))
  Text(t("Enable delivery personally with /notifications_on in the bot. Channel selection does not grant consent.","Включите доставку лично командой /notifications_on в боте. Выбор канала не заменяет согласие."))
  Row{Checkbox(quiet,{quiet=it},enabled=!busy,modifier=Modifier.testTag("quiet-enabled").semantics{contentDescription=t("Quiet hours","Тихие часы")});Text(t("Quiet hours","Тихие часы"))}
  OutlinedTextField(start,{start=it},label={Text(t("Quiet from · HH:mm","Тишина с · ЧЧ:мм"))},enabled=!busy,modifier=Modifier.testTag("quiet-start"))
  OutlinedTextField(end,{end=it},label={Text(t("Quiet until · HH:mm","Тишина до · ЧЧ:мм"))},enabled=!busy,modifier=Modifier.testTag("quiet-end"))
  Text(t("Profile timezone: ","Часовой пояс профиля: ")+settings.timezone)
  Text(t("Telegram waits until quiet hours end. Tasks stay available. Re-enabling a channel does not resend cancelled messages.","Telegram ждёт окончания тишины. Задания доступны. Повторное включение канала не возвращает отменённые сообщения."))
  val a=minutes(start);val b=minutes(end)
  VowenActionButton(onClick={actions.save(NotificationPatch(channels=channels,expected_version=settings.revision,quiet_enabled=quiet,quiet_start=a!!,quiet_end=b!!))},enabled=!busy&&a!=null&&b!=null&&(!quiet||a!=b),modifier=Modifier.testTag("save-notifications")){Text(t("Save notifications","Сохранить уведомления"))}
 }
}

@Composable
fun NativeSurveysScreen(member:Member,data:WorkspaceState,busy:Boolean,completed:Int,actions:SurveyActions){
 val ru=member.language=="ru"
 fun t(en:String,r:String)=if(ru)r else en
 fun name(id:String)=data.participants.find{it.id==id}?.display_name?:id
 var editing by remember{mutableStateOf(false)}
 var history by remember{mutableStateOf("")}
 var waves by remember{mutableStateOf(emptyList<SurveyWave>())}
 val manualKeys=remember{mutableMapOf<String,String>()}
 LaunchedEffect(completed){editing=false}
 Column(verticalArrangement=Arrangement.spacedBy(8.dp)){
  Text(t("Recurring surveys","Повторные анкеты"),style=MaterialTheme.typography.headlineSmall)
  Text(t("Each wave uses a fixed published form version and explicit readers. Guests use fresh manual invitations.","Каждая волна закрепляет опубликованную версию и читателей. Для гостей создавайте новые приглашения вручную."))
  VowenActionButton(onClick={editing=true},enabled=!busy&&!member.paused,modifier=Modifier.testTag("new-survey")){Text(t("New survey schedule","Новое расписание анкеты"))}
  if(editing)SurveyEditor(member,data,busy,actions.create){editing=false}
  if(data.surveys.isEmpty())Text(t("No survey schedules yet","Пока нет расписаний анкет"))
  data.surveys.forEach{p->Card(Modifier.fillMaxWidth()){Column(Modifier.padding(16.dp),verticalArrangement=Arrangement.spacedBy(8.dp)){
   Text(p.title,style=MaterialTheme.typography.titleMedium)
   Text("${name(p.author_id)} → ${name(p.recipient_id)}")
   Text(t("Fixed version: ","Закреплённая версия: ")+p.form_version_id)
   Text(t("Readers: ","Читатели: ")+p.reader_ids.joinToString{ name(it) })
   Text(p.schedule?.let{"${ritualStateLabel(it.kind,ru)} · ${it.hour}:${it.minute.toString().padStart(2,'0')} ${it.timezone}"}?:t("After approved ritual","После принятого ритуала"))
   Text(t("Author pause: ","Пауза автора: ")+p.owner_paused+ t(" · recipient pause: "," · пауза получателя: ")+p.recipient_paused)
   if(!p.source_effective)Text(t("Form or source authority unavailable. Review before creating a new schedule.","Анкета или полномочия источника недоступны. Проверьте их перед созданием нового расписания."))
   val paused=if(p.author_id==member.id)p.owner_paused else p.recipient_paused
   TextButton(onClick={actions.transition(p,if(paused)"resume" else "pause")},enabled=!busy&&(!paused||!member.paused),modifier=Modifier.testTag("pause-survey-${p.id}")){Text(if(paused)t("Resume my survey schedule","Снять мою паузу анкеты") else t("Pause my survey schedule","Поставить мою паузу анкеты"))}
   if(p.author_id==member.id)TextButton(onClick={val key=manualKeys.getOrPut(p.id){UUID.randomUUID().toString()};actions.send(p,key){manualKeys.remove(p.id);actions.history(p){waves=it;history=p.id}}},enabled=!busy&&!member.paused&&!p.owner_paused&&!p.recipient_paused&&p.source_effective,modifier=Modifier.testTag("send-survey-${p.id}")){Text(t("Send a new wave now","Создать новую волну сейчас"))}
   TextButton(onClick={actions.history(p){waves=it;history=p.id}},enabled=!busy,modifier=Modifier.testTag("history-survey-${p.id}")){Text(t("Wave history","История волн"))}
   if(history==p.id)waves.forEach{w->Text("${w.due_at} · ${surveyWaveLabel(w.status,ru)} · ${w.reason?.let{surveyWaveLabel(it,ru)}?:""}");w.invitation_id?.let{Text(t("Invitation: ","Приглашение: ")+it)}}
  }}}
 }

}

@Composable
private fun SurveyEditor(member:Member,data:WorkspaceState,busy:Boolean,save:(SurveyCreate)->Unit,cancel:()->Unit){
 val ru=member.language=="ru";fun t(en:String,r:String)=if(ru)r else en
 var version by remember{mutableStateOf("")};var recipient by remember{mutableStateOf("")};var readers by remember{mutableStateOf(emptyList<String>())}
 var mode by remember{mutableStateOf("periodic")};var assignment by remember{mutableStateOf("")}
 var kind by remember{mutableStateOf("daily")};var zone by remember{mutableStateOf(member.timezone)}
 var date by remember{mutableStateOf(LocalDate.now(ZoneId.of(member.timezone)).toString())}
 var hour by remember{mutableStateOf("10")};var minute by remember{mutableStateOf("0")};var days by remember{mutableStateOf(emptyList<Int>())};var window by remember{mutableStateOf("24")}
 var retention by remember{mutableStateOf("90")};var ttl by remember{mutableStateOf("7")};var deliver by remember{mutableStateOf(true)}
 val key=remember(version,recipient,readers,mode,assignment,kind,zone,date,hour,minute,days,window,retention,ttl,deliver){UUID.randomUUID().toString()}
 M4Choice(t("Published form version","Опубликованная версия анкеты"),version,data.forms.filter{it.status=="published"}.map{it.version_id to "${it.schema_body.title} · v${it.revision}"},busy){version=it}
 M4Choice(t("Survey trigger","Условие анкеты"),mode,listOf("periodic" to t("Schedule","Расписание"),"feedback" to t("After approved ritual","После принятого ритуала")),busy){mode=it}
 if(mode=="periodic"){
  M4Choice(t("Survey recipient","Получатель анкеты"),recipient,data.participants.map{it.id to it.display_name},busy){recipient=it}
  M4Choice(t("Repeat","Повтор"),kind,listOf("once","daily","weekly").map{it to ritualStateLabel(it,ru)},busy){kind=it;days=if(it=="weekly")listOf(0) else emptyList()}
  if(kind=="weekly")(if(ru)listOf("Пн","Вт","Ср","Чт","Пт","Сб","Вс") else listOf("Mon","Tue","Wed","Thu","Fri","Sat","Sun")).forEachIndexed{i,d->Row{Checkbox(i in days,{days=if(it)days+i else days-i},enabled=!busy,modifier=Modifier.semantics{contentDescription=d});Text(d)}}
  OutlinedTextField(date,{date=it},label={Text(t("Start date · YYYY-MM-DD","Начало · ГГГГ-ММ-ДД"))},enabled=!busy,modifier=Modifier.testTag("survey-date"))
  OutlinedTextField(zone,{zone=it},label={Text(t("IANA timezone","Часовой пояс IANA"))},enabled=!busy)
  Row{OutlinedTextField(hour,{hour=it},label={Text(t("Hour","Час"))},enabled=!busy,modifier=Modifier.weight(1f));OutlinedTextField(minute,{minute=it},label={Text(t("Minute","Минута"))},enabled=!busy,modifier=Modifier.weight(1f))}
  OutlinedTextField(window,{window=it},label={Text(t("Invitation window · hours","Окно приглашения · часы"))},enabled=!busy)
 }else{M4Choice(t("Source ritual assignment","Назначенный ритуал"),assignment,data.ritualAssignments.filter{it.issuer_id==member.id&&it.effective}.map{it.id to (it.title+" → "+(data.participants.find{p->p.id==it.recipient_id}?.display_name?:it.recipient_id))},busy){assignment=it};OutlinedTextField(ttl,{ttl=it},label={Text(t("Feedback invitation days","Срок обратной связи, дней"))},enabled=!busy)}
 Text(t("Survey readers","Читатели анкеты"))
 data.participants.forEach{p->Row{Checkbox(p.id in readers,{readers=if(it)readers+p.id else readers-p.id},enabled=!busy,modifier=Modifier.semantics{contentDescription=t("Survey reader: ","Читатель анкеты: ")+p.display_name});Text(p.display_name)}}
 OutlinedTextField(retention,{retention=it},label={Text(t("Survey retention days","Хранение анкеты, дней"))},enabled=!busy)
 Row{Checkbox(deliver,{deliver=it},enabled=!busy,modifier=Modifier.semantics{contentDescription=t("Try Telegram delivery","Попробовать доставку в Telegram")});Text(t("Try Telegram delivery","Попробовать доставку в Telegram"))}
 Text(t("DST: missing time shifts forward; repeated time runs once. Each participant controls their own pause.","DST: отсутствующее время сдвигается вперёд; повторяющееся выполняется один раз. Каждый управляет своей паузой."))
 val source=data.ritualAssignments.find{it.id==assignment}
 val valid=version.isNotBlank()&&retention.toIntOrNull() in 1..365&&ttl.toIntOrNull() in 1..7&&(if(mode=="feedback")source!=null else recipient.isNotBlank()&&hour.toIntOrNull() in 0..23&&minute.toIntOrNull() in 0..59&&window.toIntOrNull() in 1..168&&(kind!="weekly"||days.isNotEmpty())&&runCatching{LocalDate.parse(date);ZoneId.of(zone)}.isSuccess)
 VowenActionButton(onClick={save(SurveyCreate(form_version_id=version,recipient_id=if(mode=="feedback")source!!.recipient_id else recipient,reader_ids=readers,schedule=if(mode=="periodic")RitualSchedule(kind=kind,timezone=zone,start_date=date,hour=hour.toInt(),minute=minute.toInt(),weekdays=days,window_hours=window.toInt()) else null,ritual_assignment_id=if(mode=="feedback")assignment else null,retention_days=retention.toInt(),ttl_days=ttl.toInt(),deliver=deliver,idempotency_key=key))},enabled=!busy&&valid,modifier=Modifier.testTag("create-survey")){Text(t("Create survey schedule","Создать расписание анкеты"))}
 TextButton(onClick=cancel,enabled=!busy){Text(t("Cancel","Отмена"))}
}

internal fun surveyWaveLabel(value:String,ru:Boolean):String=(if(ru)mapOf("created" to "Создано","skipped" to "Пропущено","paused" to "На паузе","before_creation" to "До создания расписания","expired" to "Окно приглашения истекло","audience_unavailable" to "Участник недоступен","source_unavailable" to "Источник недоступен") else mapOf("created" to "Created","skipped" to "Skipped","paused" to "Paused","before_creation" to "Before plan creation","expired" to "Invitation window expired","audience_unavailable" to "Participant unavailable","source_unavailable" to "Source unavailable"))[value]?:if(ru)"Недоступно" else "Unavailable"
