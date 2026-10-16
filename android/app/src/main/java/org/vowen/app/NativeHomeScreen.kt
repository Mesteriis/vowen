package org.vowen.app

import androidx.compose.foundation.clickable
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

/** Home presents server-visible records. Capabilities are rechecked in the report screen/API. */
@Composable fun NativeHomeScreen(member:Member,data:WorkspaceState,busy:Boolean,error:String?,refresh:()->Unit,open:(RitualOccurrence)->Unit,navigate:(String)->Unit) {
 val compact=LocalConfiguration.current.screenWidthDp<720
 val ru=member.language=="ru"
 fun t(en:String,rus:String)=if(ru)rus else en
 var selectedId by remember(member.id){mutableStateOf<String?>(null)}
 var choosing by remember{mutableStateOf(false)}
 var now by remember{mutableStateOf(Instant.now())}
 LaunchedEffect(Unit){while(true){kotlinx.coroutines.delay(60000);now=Instant.now()}}
 val relation=data.relations.find{it.id==selectedId}
 val agenda=homeAgenda(member,data,relation,now)
 val locale=if(ru)Locale.forLanguageTag("ru") else Locale.UK
 fun date(value:Instant)=value.atZone(ZoneId.of(member.timezone)).format(DateTimeFormatter.ofPattern("EEEE, d MMMM",locale))
 fun time(o:RitualOccurrence)=Instant.parse(o.due_at).atZone(ZoneId.of(member.timezone)).format(DateTimeFormatter.ofPattern("HH:mm"))
 fun name(id:String)=data.participants.find{it.id==id}?.display_name?:t("Participant","Участник")
 fun context(r:Relation):String {val dominant=r.dominant_user_id==member.id;return name(if(dominant)r.submissive_user_id else r.dominant_user_id)+" · "+if(dominant)t("You are Dominant","Вы доминант") else t("You are Submissive","Вы подчинённый")}
 Column(Modifier.fillMaxWidth().testTag("home"),verticalArrangement=Arrangement.spacedBy(16.dp)){
  Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically){Image(painterResource(R.drawable.vowen_crest),null,modifier=Modifier.size(36.dp));Text("Vowen",style=MaterialTheme.typography.headlineMedium,color=MaterialTheme.colorScheme.primary,modifier=Modifier.weight(1f));TextButton(onClick={navigate("profile")}){Text(member.display_name.take(1))}}
  if(!compact)Text(date(now),style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
  if(!compact)Text(t("Good day, ","Добрый день, ")+member.display_name,style=MaterialTheme.typography.headlineMedium)
  if(!compact)Text(t("Closeness begins with attention.","Близость начинается с внимания."),style=MaterialTheme.typography.bodyMedium,color=MaterialTheme.colorScheme.onSurfaceVariant)
  Box{OutlinedButton(shape=androidx.compose.foundation.shape.RoundedCornerShape(6.dp),onClick={choosing=true},modifier=Modifier.fillMaxWidth().heightIn(min=48.dp).testTag("home-context")){Text(relation?.let(::context)?:t("Shared day · all relationships","Общий день · все отношения"),modifier=Modifier.weight(1f));Icon(painterResource(android.R.drawable.arrow_down_float),contentDescription=null,modifier=Modifier.size(16.dp))};DropdownMenu(choosing,{choosing=false}){DropdownMenuItem(text={Text(t("Shared day · all relationships","Общий день · все отношения"))},onClick={selectedId=null;choosing=false});data.relations.forEach{r->DropdownMenuItem(text={Text(context(r)+if(r.status=="paused")t(" · Paused"," · На паузе") else "")},onClick={selectedId=r.id;choosing=false})}}}
  if(member.paused)Text(t("Personal pause is active. Earned history and private diary remain available.","Личная пауза действует. История и личный дневник доступны."),style=MaterialTheme.typography.bodySmall)
  if(error!=null){Text(t("Your day could not be loaded.","Не удалось загрузить ваш день."),color=MaterialTheme.colorScheme.error);OutlinedButton(shape=androidx.compose.foundation.shape.RoundedCornerShape(6.dp),onClick=refresh,enabled=!busy){Text(t("Try again","Повторить"))}}
  BoxWithConstraints{
   val wide=maxWidth>=580.dp
   val timeline:@Composable ()->Unit={Column(Modifier.fillMaxWidth(),verticalArrangement=Arrangement.spacedBy(8.dp)){
    Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically){Text(t("Today","Сегодня"),style=MaterialTheme.typography.headlineSmall,modifier=Modifier.weight(1f));Text(date(now),style=MaterialTheme.typography.labelSmall)}
    if(agenda.reviews.isNotEmpty())Surface(color=MaterialTheme.colorScheme.surface,shape=MaterialTheme.shapes.small){Row(Modifier.fillMaxWidth().padding(10.dp),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(8.dp)){Text(t("Reports to review: ","Ждут проверки: ")+agenda.reviews.size,style=MaterialTheme.typography.bodySmall,modifier=Modifier.weight(1f));OutlinedButton(shape=androidx.compose.foundation.shape.RoundedCornerShape(6.dp),onClick={open(agenda.reviews.first())},enabled=!busy,modifier=Modifier.testTag("home-review")){Text(t("Review","Проверить"))}}}
    if(!busy&&error==null&&agenda.today.isEmpty())Text(t("No rituals scheduled for today.","На сегодня ритуалов нет."),style=MaterialTheme.typography.bodyMedium,modifier=Modifier.padding(vertical=20.dp))
    agenda.today.forEach{o->Row(Modifier.fillMaxWidth().heightIn(min=76.dp).clickable{open(o)}.padding(vertical=12.dp).testTag("home-occurrence-${o.id}"),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(12.dp)){Text(time(o),style=MaterialTheme.typography.bodySmall,modifier=Modifier.width(40.dp));Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(4.dp)){Text(o.title,style=MaterialTheme.typography.bodyLarge,fontSize=16.sp);Text(name(o.recipient_id),style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant);Text(if(o.can_review)t("Awaiting your review","Ждёт вашей проверки") else ritualStateLabel(o.status,ru),style=MaterialTheme.typography.bodySmall,color=if(o.can_review)MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant)}};HorizontalDivider(color=MaterialTheme.colorScheme.outline.copy(alpha=.3f))}
    TextButton(onClick={navigate("journal")},modifier=Modifier.fillMaxWidth().heightIn(min=56.dp)){Icon(painterResource(android.R.drawable.ic_menu_edit),contentDescription=null,modifier=Modifier.size(20.dp));Spacer(Modifier.width(12.dp));Text(t("My diary","Мой дневник"),modifier=Modifier.weight(1f),style=MaterialTheme.typography.bodyLarge)}
   }}
   val aside:@Composable ()->Unit={Column(verticalArrangement=Arrangement.spacedBy(16.dp)){
    if(wide)agenda.reviews.firstOrNull()?.let{o->Image(painterResource(R.drawable.vowen_trust),null,contentScale=androidx.compose.ui.layout.ContentScale.Crop,modifier=Modifier.fillMaxWidth().height(140.dp));Text(t("Awaiting your attention","Ожидает вашего внимания"),style=MaterialTheme.typography.headlineSmall);Text(t("Report · ","Отчёт · ")+name(o.recipient_id),style=MaterialTheme.typography.bodySmall);Text(o.title,style=MaterialTheme.typography.titleLarge);Text(o.reports.lastOrNull()?.text?:"",maxLines=4,style=MaterialTheme.typography.bodyMedium);OutlinedButton(shape=androidx.compose.foundation.shape.RoundedCornerShape(6.dp),onClick={open(o)},enabled=!busy){Text(t("Open report","Открыть отчёт"))};HorizontalDivider()}
    if(agenda.upcoming.isNotEmpty())Text(t("Coming up","Ближайшее"),style=MaterialTheme.typography.headlineSmall)
    agenda.upcoming.forEach{o->Column(Modifier.fillMaxWidth().heightIn(min=64.dp).clickable{open(o)},verticalArrangement=Arrangement.spacedBy(4.dp)){Text(date(Instant.parse(o.due_at))+" · "+time(o),style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant);Text(o.title,style=MaterialTheme.typography.bodyMedium);Text(name(o.recipient_id),style=MaterialTheme.typography.bodySmall)}}
   }}
   if(wide)Row(horizontalArrangement=Arrangement.spacedBy(24.dp)){Column(Modifier.weight(1f)){timeline()};Column(Modifier.width(220.dp).testTag("home-expanded")){aside()}} else Column(verticalArrangement=Arrangement.spacedBy(20.dp)){timeline();aside()}
  }
 }
}
