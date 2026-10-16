package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.ui.platform.LocalContext
import android.util.Base64
import android.content.Intent
import android.net.Uri
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.Dispatchers
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.compose.foundation.clickable
import androidx.compose.foundation.Image
import androidx.compose.ui.res.painterResource
import androidx.compose.foundation.shape.RoundedCornerShape
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
 val report:(RitualOccurrence,String,String,List<String>,List<String>)->Unit,
 val review:(RitualOccurrence,String,String)->Unit,
 val skip:(RitualOccurrence)->Unit,
 val upload:((RitualOccurrence,EvidenceUpload,(EvidenceView)->Unit)->Unit)?=null,
 val saveEvidence:((EvidenceView)->Unit)?=null,
 val discard:((EvidenceView,()->Unit)->Unit)?=null,
 val staged:((RitualOccurrence,(List<EvidenceView>)->Unit)->Unit)?=null,
 val create:((RitualContent,(RitualTemplate)->Unit)->Unit)?=null,
 val rewards:((RitualAssignment,RewardBundleEdit)->Unit)?=null
)
@Composable fun NativeRitualsScreen(member:Member,data:WorkspaceState,busy:Boolean,completed:Int,actions:RitualActions,error:String?=null,homeTarget:String?=null) {
 val ru=member.language=="ru"
 val context=LocalContext.current
 var mediaError by remember{mutableStateOf<String?>(null)}

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
 LaunchedEffect(homeTarget){data.ritualOccurrences.find{it.id==homeTarget}?.let{o->if(!member.paused){if(o.can_review)reviewing=o else if(o.can_report)reporting=o}}}
 var relationId by remember{mutableStateOf<String?>(null)}
 var choosing by remember{mutableStateOf(false)}
 var view by remember{mutableStateOf("assignments")}
 var detailId by remember{mutableStateOf<String?>(null)}
 var detailOpen by remember{mutableStateOf(false)}
 var rewardFor by remember{mutableStateOf<RitualAssignment?>(null)}
 var historyOpen by remember{mutableStateOf(false)}
 LaunchedEffect(completed){editing=false;assigning=null;scheduleFor=null;rewardFor=null;reporting=null;reviewing=null}
 val relation=data.relations.find{it.id==relationId}
 val allowedRecipients=data.relations.filter{it.dominant_user_id==member.id&&it.status=="active"&&"rituals.assign" in it.scopes&&it.consent_user_ids.containsAll(listOf(it.dominant_user_id,it.submissive_user_id))&&(relation==null||it.id==relation.id)&&!member.paused}.map{it.submissive_user_id}
 val canManage=relation?.dominant_user_id==member.id||relation==null&&data.ritualAssignments.any{it.issuer_id==member.id}||allowedRecipients.isNotEmpty()
 val contextAssignments=data.ritualAssignments.filter{homeMatches(it.issuer_id,it.recipient_id,it.reviewer_ids,member.id,relation)}
 val contextOccurrences=data.ritualOccurrences.filter{o->relation==null||contextAssignments.any{it.id==o.assignment_id}}
 val performer=relation?.submissive_user_id==member.id||relation==null&&contextOccurrences.any{it.recipient_id==member.id}
 val current=if(view=="assignments"&&!canManage&&performer)"mine" else view
 val assigned=contextAssignments.filter{it.issuer_id==member.id}
 val inspected=assigned.find{it.id==detailId}?:assigned.firstOrNull()
 LaunchedEffect(relationId){detailOpen=false;detailId=null;view=if(canManage)"assignments" else if(performer)"mine" else "review"}
 LaunchedEffect(homeTarget){if(homeTarget!=null)view=data.ritualOccurrences.find{it.id==homeTarget}?.let{if(it.recipient_id==member.id)"mine" else "review"}?:view}
 Column(Modifier.fillMaxWidth(),verticalArrangement=Arrangement.spacedBy(12.dp)) {
  Row(Modifier.fillMaxWidth().heightIn(min=44.dp),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(8.dp)){
   Image(painterResource(R.drawable.vowen_crest),null,modifier=Modifier.size(28.dp))
   Text(t("Rituals","Ритуалы"),style=MaterialTheme.typography.headlineSmall,fontSize=22.sp,modifier=Modifier.weight(1f))
   Box{
    val partner=relation?.let{r->name(if(r.dominant_user_id==member.id)r.submissive_user_id else r.dominant_user_id)}
    val role=relation?.let{if(it.dominant_user_id==member.id)t("You are Dominant","Вы доминант") else t("You are Submissive","Вы подчинённый")}
    TextButton(onClick={choosing=true},modifier=Modifier.heightIn(min=44.dp).testTag("ritual-context").semantics{contentDescription=partner?.let{"${member.display_name} · $it · $role · ${label(relation!!.status)}"}?:t("All relationships","Все отношения")},contentPadding=PaddingValues(horizontal=4.dp)){
     Surface(shape=androidx.compose.foundation.shape.CircleShape,color=MaterialTheme.colorScheme.surfaceVariant,modifier=Modifier.size(32.dp)){Box(contentAlignment=Alignment.Center){Text(member.display_name.take(1),color=MaterialTheme.colorScheme.primary)}}
     Icon(painterResource(when{relation==null->android.R.drawable.ic_menu_myplaces;relation.status=="paused"->android.R.drawable.ic_media_pause;relation.status=="revoked"->android.R.drawable.ic_menu_close_clear_cancel;relation.status=="proposed"->android.R.drawable.ic_input_add;relation.dominant_user_id==member.id->android.R.drawable.ic_media_ff;else->android.R.drawable.ic_media_rew}),contentDescription=null,modifier=Modifier.padding(horizontal=6.dp).size(18.dp))
     if(partner!=null)Surface(shape=androidx.compose.foundation.shape.CircleShape,color=MaterialTheme.colorScheme.surfaceVariant,modifier=Modifier.size(32.dp)){Box(contentAlignment=Alignment.Center){Text(partner.take(1),color=MaterialTheme.colorScheme.primary)}}
    }
    DropdownMenu(choosing,{choosing=false}){DropdownMenuItem(text={Text(t("All relationships","Все отношения"))},onClick={relationId=null;choosing=false});data.relations.forEach{r->DropdownMenuItem(text={Text(name(if(r.dominant_user_id==member.id)r.submissive_user_id else r.dominant_user_id)+" · "+(if(r.dominant_user_id==member.id)t("You are Dominant","Вы доминант") else t("You are Submissive","Вы подчинённый"))+" · "+label(r.status))},onClick={relationId=r.id;choosing=false})}}
   }
   if(allowedRecipients.isNotEmpty())OutlinedIconButton(onClick={selected=null;editing=true},enabled=!busy,modifier=Modifier.size(44.dp).testTag("new-ritual")){Icon(painterResource(android.R.drawable.ic_input_add),contentDescription=t("New ritual","Новый ритуал"),modifier=Modifier.size(20.dp))}
  }
  mediaError?.let{Text(it,color=MaterialTheme.colorScheme.error)}

  ScrollableTabRow(selectedTabIndex=(listOfNotNull(if(canManage)"assignments" else null,"review",if(performer)"mine" else null,if(allowedRecipients.isNotEmpty())"templates" else null)).indexOf(current).coerceAtLeast(0),edgePadding=0.dp,containerColor=MaterialTheme.colorScheme.background){listOfNotNull(if(canManage)"assignments" else null,"review",if(performer)"mine" else null,if(allowedRecipients.isNotEmpty())"templates" else null).forEach{tab->Tab(selected=current==tab,onClick={view=tab},text={Text(when(tab){"assignments"->t("Rituals","Ритуалы");"review"->t("Review","Проверка")+" · "+contextOccurrences.count{it.can_review};"mine"->t("My executions","Мои выполнения");else->t("Templates","Шаблоны")},fontSize=12.sp)},modifier=Modifier.testTag("ritual-view-$tab"))}}
  if(current=="assignments")BoxWithConstraints{
   val wide=maxWidth>=560.dp
   val details:@Composable ()->Unit={inspected?.let{a->NativeRitualDetails(a,member,name(a.recipient_id),busy,{scheduleFor=a;assigning=null;detailOpen=false},actions.rewards?.let{{rewardFor=a;detailOpen=false}},{actions.assignment(a,it)})}}
   val list:@Composable ()->Unit={Column(verticalArrangement=Arrangement.spacedBy(8.dp)){
    if(assigned.isEmpty())Text(t("No assigned rituals in this context.","В этих отношениях пока нет ритуалов."),style=MaterialTheme.typography.bodySmall)
    listOf("daily","weekly","once").forEach{kind->val rows=assigned.filter{it.schedule.kind==kind};if(rows.isNotEmpty()){Text(if(kind=="daily")t("Daily","Ежедневно") else if(kind=="weekly")t("Weekly","По дням недели") else t("Once","Однократно"),style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant);rows.forEach{a->OutlinedCard(onClick={detailId=a.id;detailOpen=true},modifier=Modifier.fillMaxWidth().testTag("ritual-assignment-${a.id}")){Column(Modifier.padding(12.dp),verticalArrangement=Arrangement.spacedBy(5.dp)){Text(a.title,style=MaterialTheme.typography.bodyLarge,fontSize=16.sp);Text(ritualScheduleSummary(a.schedule,ru)+" · "+name(a.recipient_id),style=MaterialTheme.typography.bodySmall);Text((if(a.approval_required)t("Review required","Проверка обязательна") else t("Without review","Без проверки"))+" · "+label(a.status),style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)}}}}}
   }}
   if(wide)Row(horizontalArrangement=Arrangement.spacedBy(20.dp)){Column(Modifier.weight(1f)){list()};Column(Modifier.weight(1f).testTag("ritual-inspector")){details()}} else{list();if(detailOpen&&inspected!=null)Dialog(onDismissRequest={detailOpen=false},properties=DialogProperties(usePlatformDefaultWidth=false)){Surface(Modifier.fillMaxSize()){Column(Modifier.safeDrawingPadding().padding(20.dp).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(12.dp)){TextButton(onClick={detailOpen=false}){Text(t("Back to rituals","К ритуалам"))};details()}}}}
  }
  if(current=="review"||current=="mine"){
   if(current=="review")TextButton(onClick={historyOpen=!historyOpen}){Text(if(historyOpen)t("Back to pending reports","К ожидающим отчётам") else t("Review history","История проверок"))}
   val rows=contextOccurrences.filter{if(current=="mine")it.recipient_id==member.id else it.recipient_id!=member.id&&(historyOpen||it.can_review&&it.status=="submitted")}
   if(rows.isEmpty())Text(if(current=="review")t("No reports awaiting review.","Нет отчётов для проверки.") else t("No visible executions.","Нет доступных выполнений."),style=MaterialTheme.typography.bodySmall)
   rows.forEach{o->key(o.id){var expanded by remember{mutableStateOf(false)};Column(Modifier.fillMaxWidth().padding(vertical=12.dp),verticalArrangement=Arrangement.spacedBy(5.dp)){
    Text(o.title,style=MaterialTheme.typography.bodyLarge,fontSize=16.sp);Text(name(o.recipient_id)+" · "+time(o.due_at),style=MaterialTheme.typography.bodySmall);Text(label(o.status),style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.primary)
    if(o.reports.isNotEmpty())TextButton(onClick={expanded=!expanded}){Text(t("Report history","История отчётов")+" · "+o.reports.size)}
    if(expanded)o.reports.forEach{r->Text(r.text,style=MaterialTheme.typography.bodyMedium);r.comment?.let{if(it.isNotEmpty())Text(it)};r.links.orEmpty().forEach{link->TextButton(onClick={runCatching{context.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(link)))}.onFailure{mediaError="Cannot open external link"}}){Text(t("Open evidence link · external site","Открыть доказательство · внешний сайт"))}};r.attachments.orEmpty().forEach{e->actions.saveEvidence?.let{save->TextButton(onClick={save(e)},enabled=!busy){Text(if(e.kind=="photo")t("Save photo evidence","Сохранить фото-доказательство") else t("Save video evidence","Сохранить видео-доказательство"))}}}}
    if(o.can_report&&!member.paused)OutlinedButton(onClick={reporting=o},enabled=!busy,modifier=Modifier.testTag("report-${o.id}")){Text(t("Write report","Написать отчёт"))}
    if(o.can_review&&!member.paused)OutlinedButton(onClick={reviewing=o},enabled=!busy,modifier=Modifier.testTag("review-${o.id}")){Text(t("Review report","Проверить отчёт"))}
    if(o.recipient_id==member.id&&o.status in listOf("scheduled","needs_changes"))TextButton(onClick={actions.skip(o)},enabled=!busy){Text(t("Skip occurrence","Пропустить выполнение"))}
   };HorizontalDivider(color=MaterialTheme.colorScheme.outline.copy(alpha=.3f))}}
  }
  if(current=="templates")data.rituals.forEach{r->Column(verticalArrangement=Arrangement.spacedBy(5.dp)){Text(r.title,style=MaterialTheme.typography.bodyLarge);Text(label(r.status),style=MaterialTheme.typography.bodySmall);TextButton(onClick={selected=r;editing=true},enabled=!busy){Text(if(r.status=="draft")t("Edit ritual draft","Изменить черновик") else t("New ritual version","Новая версия"))};if(r.status=="draft")TextButton(onClick={actions.template(r,"publish")},enabled=!busy){Text(t("Publish ritual","Опубликовать ритуал"))};if(r.status=="published")TextButton(onClick={assigning=r;scheduleFor=null},enabled=!busy){Text(t("Assign ritual","Назначить ритуал"))};TextButton(onClick={actions.history(r)}){Text(t("Version history","История версий"))};if(r.status!="archived")TextButton(onClick={actions.template(r,"archive")},enabled=!busy){Text(t("Archive ritual","Архивировать ритуал"))}};HorizontalDivider()}
  if(current=="templates")data.ritualHistory.forEach{v->Text(v.title);Text(v.description);Text(label(v.status))}
 }
 if(editing||assigning!=null||scheduleFor!=null||rewardFor!=null)Dialog(onDismissRequest={if(!busy){editing=false;assigning=null;scheduleFor=null;rewardFor=null}}){Surface(shape=RoundedCornerShape(12.dp)){Column(Modifier.padding(16.dp).heightIn(max=700.dp).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(12.dp)){
  error?.let{Text(it,color=MaterialTheme.colorScheme.error)}
  if(editing)key(selected?.id,selected?.revision){RitualEditor(selected,busy||member.paused,ru,{body->if(selected==null&&actions.create!=null)actions.create.invoke(body){r->editing=false;assigning=r} else actions.save(selected,body)},{editing=false},selected==null&&actions.create!=null)}
  if(assigning!=null||scheduleFor!=null)key(assigning?.id,scheduleFor?.id,scheduleFor?.revision){RitualAssignmentEditor(member,data.participants,data.rewards,assigning,scheduleFor,busy,ru,{command->assigning?.let{actions.assign(it,command)}},{s->scheduleFor?.let{actions.schedule(it,s)}},{assigning=null;scheduleFor=null},allowedRecipients)}
  rewardFor?.let{a->NativeRitualRewardEditor(a,data.rewards,busy,ru,{body->actions.rewards?.invoke(a,body)},{rewardFor=null})}
 }}}
  reporting?.let {o->key(o.id){RitualReportDialog(o,busy,ru,actions,error,{reporting=null})}}
 reviewing?.let {o->key(o.id){var comment by remember{mutableStateOf("")};AlertDialog(onDismissRequest={if(!busy)reviewing=null},title={Text(o.title)},text={Column(Modifier.verticalScroll(rememberScrollState())){Text(o.reports.lastOrNull()?.text?:"");OutlinedTextField(comment,{if(it.length<=10000)comment=it},label={Text(t("Review comment","Комментарий проверяющего"))},enabled=!busy)}},confirmButton={TextButton(onClick={actions.review(o,"approved",comment)},enabled=!busy,modifier=Modifier.testTag("ritual-approve")){Text(t("Approve report","Одобрить отчёт"))}},dismissButton={Column{TextButton(onClick={actions.review(o,"needs_changes",comment)},enabled=!busy,modifier=Modifier.testTag("ritual-request-changes")){Text(t("Request changes","Вернуть на доработку"))};TextButton(onClick={reviewing=null},enabled=!busy){Text(t("Cancel","Отмена"))}}})}}
}

@Composable private fun RitualReportDialog(o:RitualOccurrence,busy:Boolean,ru:Boolean,actions:RitualActions,requestError:String?,cancel:()->Unit){
 fun t(en:String,r:String)=if(ru)r else en
 val context=LocalContext.current;val scope=rememberCoroutineScope()
 var text by remember{mutableStateOf("")};var links by remember{mutableStateOf("")};var requestKey by remember{mutableStateOf(UUID.randomUUID().toString())}
 var uploaded by remember{mutableStateOf(emptyList<EvidenceView>())};var pending by remember{mutableStateOf<EvidenceUpload?>(null)}
 var reading by remember{mutableStateOf(false)};var error by remember{mutableStateOf<String?>(null)}
 LaunchedEffect(o.id){actions.staged?.invoke(o){uploaded=it}}
 val allowed=o.evidence_policy?.allowed_types?:listOf("link","photo","video")
 val linkList=links.lines().map{it.trim()}.filter{it.isNotEmpty()}
 val valid=linkList.all{runCatching{val u=Uri.parse(it);u.scheme=="https"&&!u.host.isNullOrBlank()}.getOrDefault(false)}&&uploaded.size+linkList.size<=3
 val enough=o.evidence_policy?.required!=true||uploaded.isNotEmpty()||linkList.isNotEmpty()
 fun sendUpload(body:EvidenceUpload){actions.upload?.invoke(o,body){e->uploaded=uploaded+e;pending=null;requestKey=UUID.randomUUID().toString()}}
 val picker=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()){uri->if(uri!=null)scope.launch{
  reading=true;error=null
  try{val body=withContext(Dispatchers.IO){val mime=context.contentResolver.getType(uri)?:error("Unknown media type");require(mime in listOf("image/jpeg","image/png","video/mp4","video/webm")){"JPEG, PNG, MP4 or WebM required"};val bytes=context.contentResolver.openInputStream(uri)?.use{readEvidenceBytes(it)}?:error("Cannot read file");EvidenceUpload(idempotency_key=UUID.randomUUID().toString(),kind=if(mime.startsWith("image/"))"photo" else "video",media_type=mime,data_base64=Base64.encodeToString(bytes,Base64.NO_WRAP))};pending=body;sendUpload(body)}catch(e:Exception){error=e.message}finally{reading=false}
 }}
 AlertDialog(onDismissRequest={if(!busy&&!reading)cancel()},title={Text(o.title)},text={Column(Modifier.verticalScroll(rememberScrollState())){
  Text(o.description)
  Text(if(o.evidence_policy?.required==true)t("Evidence required","Доказательство обязательно") else t("Evidence optional","Доказательство необязательно"))
  Text(t("Up to 3 items, 8 MiB per file. Original metadata is preserved.","До 3 доказательств, 8 МиБ на файл. Исходные метаданные сохраняются."),style=MaterialTheme.typography.bodySmall)
  OutlinedTextField(text,{if(it.length<=10000){text=it;requestKey=UUID.randomUUID().toString()}},label={Text(t("Ritual report","Отчёт ритуала"))},enabled=!busy,modifier=Modifier.testTag("ritual-report-text"))
  if("link" in allowed)OutlinedTextField(links,{if(it.length<=6146){links=it;requestKey=UUID.randomUUID().toString()}},label={Text(t("Evidence links · HTTPS, one per line","Ссылки-доказательства · HTTPS, по одной на строку"))},enabled=!busy,modifier=Modifier.testTag("ritual-evidence-links"))
  if(actions.upload!=null&&("photo" in allowed||"video" in allowed))TextButton(onClick={picker.launch((if("photo" in allowed)listOf("image/jpeg","image/png") else emptyList()).plus(if("video" in allowed)listOf("video/mp4","video/webm") else emptyList()).toTypedArray())},enabled=!busy&&!reading&&pending==null&&uploaded.size+linkList.size<3){Text(t("Choose photo or video","Выбрать фото или видео"))}
  pending?.let{body->
   TextButton(onClick={sendUpload(body)},enabled=!busy&&!reading){Text(t("Retry evidence upload","Повторить загрузку доказательства"))}
   TextButton(onClick={pending=null;error=null},enabled=!busy&&!reading){Text(t("Replace pending file","Заменить ожидающий файл"))}
  }
  uploaded.forEach{e->Text("${if(e.kind=="photo")t("Photo","Фото") else t("Video","Видео")} · ${e.media_type}");actions.discard?.let{discard->TextButton(onClick={discard(e){uploaded=uploaded-e;requestKey=UUID.randomUUID().toString()}},enabled=!busy){Text(t("Remove evidence","Удалить доказательство"))}}}
  (error?:requestError)?.let{Text(it,color=MaterialTheme.colorScheme.error)}
 }},confirmButton={TextButton(onClick={actions.report(o,text,requestKey,linkList,uploaded.map{it.id})},enabled=!busy&&!reading&&pending==null&&text.isNotBlank()&&enough&&valid,modifier=Modifier.testTag("submit-ritual-report")){Text(t("Submit report","Отправить отчёт"))}},dismissButton={TextButton(onClick=cancel,enabled=!busy&&!reading){Text(t("Cancel","Отмена"))}})
}

@Composable private fun RitualEditor(r:RitualTemplate?,busy:Boolean,ru:Boolean,save:(RitualContent)->Unit,cancel:()->Unit,next:Boolean=false){
 var title by remember{mutableStateOf(r?.title?:"")};var description by remember{mutableStateOf(r?.description?:"")}
 OutlinedTextField(title,{if(it.length<=200)title=it},label={Text(if(ru)"Название ритуала" else "Ritual title")},enabled=!busy)
 OutlinedTextField(description,{if(it.length<=10000)description=it},label={Text(if(ru)"Описание ритуала" else "Ritual description")},enabled=!busy)
 VowenActionButton(onClick={save(RitualContent(title=title,description=description))},enabled=!busy&&title.isNotBlank()&&description.isNotBlank()){Text(if(next)if(ru)"Далее: расписание" else "Next: schedule" else if(ru)"Сохранить ритуал" else "Save ritual")}
 TextButton(onClick=cancel,enabled=!busy){Text(if(ru)"Отмена" else "Cancel")}
}
@Composable private fun RitualAssignmentEditor(member:Member,participants:List<Participant>,rewards:List<RewardDefinition>,template:RitualTemplate?,assignment:RitualAssignment?,busy:Boolean,ru:Boolean,assign:(RitualAssign)->Unit,edit:(RitualSchedule)->Unit,cancel:()->Unit,recipientIds:List<String>?=null){
 fun t(en:String,rus:String)=if(ru)rus else en
 var evidenceRequired by remember{mutableStateOf(false)};var evidenceTypes by remember{mutableStateOf(listOf("link","photo","video"))};var rewardIds by remember{mutableStateOf(emptyList<String>())};var coins by remember{mutableStateOf("0")}
 val old=assignment?.schedule
 var recipient by remember{mutableStateOf("")};var reviewers by remember{mutableStateOf(emptyList<String>())};var expanded by remember{mutableStateOf(false)}
 var kind by remember{mutableStateOf(old?.kind?:"daily")};var timezone by remember{mutableStateOf(old?.timezone?:member.timezone)}
 var date by remember{mutableStateOf(if(old==null)LocalDate.now(ZoneId.of(member.timezone)).toString() else LocalDate.now(ZoneId.of(old.timezone)).plusDays(1).toString())}
 var hour by remember{mutableStateOf((old?.hour?:9).toString())};var minute by remember{mutableStateOf((old?.minute?:0).toString())}
 var days by remember{mutableStateOf(old?.weekdays?:emptyList())};var window by remember{mutableStateOf((old?.window_hours?:24).toString())};var approval by remember{mutableStateOf(true)}
 val key=remember(recipient,reviewers,kind,timezone,date,hour,minute,days,window,approval,rewardIds,coins,evidenceRequired,evidenceTypes){UUID.randomUUID().toString()}
 Text(template?.title?:assignment?.title?:"",style=MaterialTheme.typography.titleLarge)
 if(template!=null){Box {TextButton(onClick={expanded=true},enabled=!busy){Text(participants.find{it.id==recipient}?.display_name?:t("Ritual recipient","Адресат ритуала"))};DropdownMenu(expanded,{expanded=false}){participants.filter{it.id!=member.id&&(recipientIds==null||it.id in recipientIds)}.forEach{p->DropdownMenuItem(text={Text(p.display_name)},onClick={recipient=p.id;reviewers=reviewers-p.id;expanded=false})}}}
 participants.filter{it.id!=recipient}.forEach{p->Row{Checkbox(p.id in reviewers,{reviewers=if(it)reviewers+p.id else reviewers-p.id},enabled=!busy,modifier=Modifier.semantics{contentDescription=t("Reviewer: ","Проверяющий: ")+p.display_name});Text(t("Reviewer: ","Проверяющий: ")+p.display_name)}}
 Row{Checkbox(approval,{approval=it},enabled=!busy,modifier=Modifier.semantics{contentDescription=t("Approval required","Требуется проверка")});Text(t("Approval required","Требуется проверка"))}}
 if(template!=null){
  Row{Checkbox(evidenceRequired,{evidenceRequired=it},enabled=!busy,modifier=Modifier.semantics{contentDescription=t("Evidence required","Доказательство обязательно")});Text(t("Evidence required","Доказательство обязательно"))}
  listOf("link","photo","video").forEach{kind->Row{Checkbox(kind in evidenceTypes,{evidenceTypes=if(it)evidenceTypes+kind else evidenceTypes-kind},enabled=!busy,modifier=Modifier.semantics{contentDescription=if(kind=="link")t("Link","Ссылка") else if(kind=="photo")t("Photo","Фото") else t("Video","Видео")});Text(if(kind=="link")t("Link","Ссылка") else if(kind=="photo")t("Photo","Фото") else t("Video","Видео"))}}
  Text(t("Completion rewards","Награды за выполнение"),style=MaterialTheme.typography.titleMedium)
  rewards.forEach{r->Row{Checkbox(r.version_id in rewardIds,{rewardIds=if(it)rewardIds+r.version_id else rewardIds-r.version_id},enabled=!busy,modifier=Modifier.semantics{contentDescription=r.title});Text(r.title)}}
  OutlinedTextField(coins,{coins=it},label={Text(t("Coins per completion","Монет за выполнение"))},enabled=!busy)
  Text(t("Awarded automatically after completion or required approval.","Автоматическая выдача после завершения или обязательной проверки."),style=MaterialTheme.typography.bodySmall)
 }
 Row{listOf("once","daily","weekly").forEach{k->TextButton(onClick={kind=k;days=if(k=="weekly")listOf(0) else emptyList()},enabled=!busy){Text(k)}}}
 if(kind=="weekly")listOf("Mon","Tue","Wed","Thu","Fri","Sat","Sun").forEachIndexed{i,d->Row{Checkbox(i in days,{days=if(it)days+i else days-i},enabled=!busy,modifier=Modifier.semantics{contentDescription=d});Text(d)}}
 OutlinedTextField(date,{date=it},label={Text(t("Start date · YYYY-MM-DD","Начало · ГГГГ-ММ-ДД"))},enabled=!busy)
 OutlinedTextField(timezone,{timezone=it},label={Text(t("IANA timezone","Часовой пояс IANA"))},enabled=!busy&&assignment==null)
 Row{OutlinedTextField(hour,{hour=it},label={Text(t("Hour","Час"))},enabled=!busy,modifier=Modifier.weight(1f));OutlinedTextField(minute,{minute=it},label={Text(t("Minute","Минута"))},enabled=!busy,modifier=Modifier.weight(1f))}
 OutlinedTextField(window,{window=it},label={Text(t("Report window · hours","Окно отчёта · часы"))},enabled=!busy)
 Text(t("DST: missing time shifts by the gap; repeated time uses the first occurrence. Schedule edits begin tomorrow or later.","DST: отсутствующее время сдвигается на разрыв, повторяющееся — один раз. Изменения — со следующего дня."),style=MaterialTheme.typography.bodySmall)
 val valid=evidenceTypes.isNotEmpty() && hour.toIntOrNull() in 0..23 && minute.toIntOrNull() in 0..59 && window.toIntOrNull() in 1..168 && runCatching{LocalDate.parse(date);ZoneId.of(timezone)}.isSuccess && (kind!="weekly"||days.isNotEmpty())
 VowenActionButton(onClick={val s=RitualSchedule(hour=hour.toInt(),minute=minute.toInt(),kind=kind,timezone=timezone,start_date=date,weekdays=days,window_hours=window.toInt());if(template!=null)assign(RitualAssign(evidence_policy=EvidencePolicy(required=evidenceRequired,allowed_types=evidenceTypes),reward_version_ids=rewardIds,currency_amount=coins.toIntOrNull()?:0,approval_required=approval,idempotency_key=key,recipient_id=recipient,reviewer_ids=reviewers,schedule=s)) else edit(s)},enabled=!busy&&valid&&(coins.toIntOrNull()?.let{it in 0..1000000000}==true)&&(template==null||(recipient.isNotEmpty()&&(!approval||reviewers.isNotEmpty())))){Text(if(template==null)t("Save schedule","Сохранить расписание") else t("Create ritual assignment","Создать назначение ритуала"))}
 TextButton(onClick=cancel,enabled=!busy){Text(t("Cancel","Отмена"))}
}

internal fun ritualStateLabel(value:String,ru:Boolean):String = (if(ru)mapOf("scheduled" to "Запланировано","submitted" to "Ждёт проверки","needs_changes" to "На доработке","approved" to "Одобрено","missed" to "Пропущено","skipped" to "Пропущено добровольно","cancelled" to "Отменено","draft" to "Черновик","published" to "Опубликовано","archived" to "В архиве","active" to "Действует","paused" to "На паузе","revoked" to "Отозвано","daily" to "Ежедневно","weekly" to "Еженедельно","once" to "Однократно") else mapOf("scheduled" to "Scheduled","submitted" to "Awaiting review","needs_changes" to "Changes requested","approved" to "Approved","missed" to "Missed","skipped" to "Skipped","cancelled" to "Cancelled","draft" to "Draft","published" to "Published","archived" to "Archived","active" to "Active","paused" to "Paused","revoked" to "Revoked","daily" to "Daily","weekly" to "Weekly","once" to "Once"))[value]?:if(ru)"Недоступно" else "Unavailable"
