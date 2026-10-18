package org.vowen.app

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.time.LocalTime

/** Personal delivery preferences; bot opt-in is independent of the Telegram switch. */
@Composable
fun NativeNotificationScreen(settings:NotificationSettings?,busy:Boolean,actions:NotificationActions,ru:Boolean,displayName:String="",onRefresh:()->Unit={}){
 fun t(en:String,r:String)=if(ru)r else en
 Column(verticalArrangement=Arrangement.spacedBy(18.dp)){
  Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween,verticalAlignment=Alignment.CenterVertically){
   Text(t("Notifications","Уведомления"),style=MaterialTheme.typography.headlineSmall)
   if(displayName.isNotBlank())Surface(shape=CircleShape,color=MaterialTheme.colorScheme.surfaceVariant,border=BorderStroke(1.dp,MaterialTheme.colorScheme.outlineVariant),modifier=Modifier.size(36.dp)){Box(contentAlignment=Alignment.Center){Text(displayName.take(1),fontSize=22.sp,lineHeight=22.sp,color=MaterialTheme.colorScheme.primary,style=MaterialTheme.typography.bodyLarge.copy(platformStyle=androidx.compose.ui.text.PlatformTextStyle(includeFontPadding=false)))}}
  }
  Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.End){IconButton(onClick=onRefresh,enabled=!busy){Icon(painterResource(android.R.drawable.ic_popup_sync),t("Reload notification settings","Загрузить настройки уведомлений заново"))}}
  if(settings==null){Text(t("Reload to load notification settings","Загрузите настройки уведомлений"));return@Column}
  var channels by remember(settings.revision){mutableStateOf(settings.channels)}
  var quiet by remember(settings.revision){mutableStateOf(settings.quiet_enabled)}
  fun clock(m:Int)="%02d:%02d".format(java.util.Locale.ROOT,m/60,m%60)
  var start by remember(settings.revision){mutableStateOf(clock(settings.quiet_start))}
  var end by remember(settings.revision){mutableStateOf(clock(settings.quiet_end))}
  var connectionHelp by remember{mutableStateOf(false)}
  var info by remember{mutableStateOf(false)}
  fun minutes(s:String)=runCatching{LocalTime.parse(s).let{it.hour*60+it.minute}}.getOrNull()
  val a=minutes(start);val b=minutes(end)
  val valid=!quiet||(a!=null&&b!=null&&a!=b)
  val channelsContent:@Composable ()->Unit={Column(verticalArrangement=Arrangement.spacedBy(12.dp)){
   Text(t("Where to deliver","Куда доставлять"),style=MaterialTheme.typography.titleLarge)
   Text(t("Choose where to receive notifications.","Выберите, где получать уведомления."),style=MaterialTheme.typography.bodySmall)
   listOf("in_app" to t("In the app","В приложении"),"telegram" to "Telegram").forEach{(id,label)->
    Row(Modifier.fillMaxWidth().heightIn(min=56.dp),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(12.dp)){
     Icon(painterResource(if(id=="telegram")android.R.drawable.ic_menu_send else android.R.drawable.ic_menu_view),null,Modifier.size(24.dp),tint=MaterialTheme.colorScheme.primary)
     Column(Modifier.weight(1f)){Text(label,style=MaterialTheme.typography.bodyMedium);Text(if(id=="telegram")t("Delivery to your private chat with the bot","Доставка в ваш личный чат с ботом") else t("Notifications inside Vowen","Уведомления внутри Vowen"),style=MaterialTheme.typography.bodySmall)}
     Switch(id in channels,{channels=if(it)(channels+id).distinct() else channels-id},enabled=!busy,modifier=Modifier.testTag("channel-$id").semantics{contentDescription=label})
    }
    if(id=="telegram"){
     Text(if(settings.telegram_connected)t("Bot connected","Бот подключён") else t("Bot not connected","Бот не подключён"),style=MaterialTheme.typography.bodySmall,color=if(settings.telegram_connected)MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error)
     TextButton(onClick={connectionHelp=!connectionHelp}){Text(t("How to connect","Как подключить"))}
     if(connectionHelp)Text(t("Send /notifications_on personally in the bot. The channel switch does not connect the bot.","Отправьте /notifications_on лично в боте. Переключатель канала не подключает бота."),style=MaterialTheme.typography.bodySmall)
    }
    HorizontalDivider()
   }
  }}
  val quietContent:@Composable ()->Unit={Column(verticalArrangement=Arrangement.spacedBy(12.dp)){
   Text(t("When not to disturb","Когда не беспокоить"),style=MaterialTheme.typography.titleLarge)
   Text(t("During quiet hours Telegram waits; tasks remain available.","Во время тишины Telegram ждёт, задания доступны."),style=MaterialTheme.typography.bodySmall)
   Row(Modifier.fillMaxWidth().heightIn(min=48.dp),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.SpaceBetween){Text(t("Quiet hours","Тихие часы"));Switch(quiet,{quiet=it},enabled=!busy,modifier=Modifier.testTag("quiet-enabled").semantics{contentDescription=t("Quiet hours","Тихие часы")})}
   Row(horizontalArrangement=Arrangement.spacedBy(12.dp)){
    OutlinedTextField(start,{start=it},label={Text(t("From · HH:mm","С · ЧЧ:мм"))},enabled=!busy&&quiet,singleLine=true,isError=quiet&&!valid,modifier=Modifier.weight(1f).testTag("quiet-start"))
    OutlinedTextField(end,{end=it},label={Text(t("Until · HH:mm","До · ЧЧ:мм"))},enabled=!busy&&quiet,singleLine=true,isError=quiet&&!valid,modifier=Modifier.weight(1f).testTag("quiet-end"))
   }
   if(quiet&&!valid)Text(t("Enter different start and end times.","Укажите разное время начала и окончания."),color=MaterialTheme.colorScheme.error,style=MaterialTheme.typography.bodySmall)
   Text(t("Profile timezone: ","Часовой пояс профиля: ")+settings.timezone,style=MaterialTheme.typography.bodySmall)
  }}
  if(LocalConfiguration.current.screenWidthDp>=720)Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(32.dp)){Column(Modifier.weight(1.25f)){channelsContent()};Column(Modifier.weight(1f)){quietContent()}}else{channelsContent();quietContent()}
  HorizontalDivider()
  TextButton(onClick={info=!info}){Text(t("Good to know","Важно знать"))}
  if(info)Text(t("Channel selection does not replace personal bot opt-in. Turning a channel back on does not resend cancelled messages.","Выбор канала не заменяет личное включение доставки в боте. Повторное включение канала не возвращает отменённые сообщения."),style=MaterialTheme.typography.bodySmall)
  VowenActionButton(onClick={actions.save(NotificationPatch(channels=channels,expected_version=settings.revision,quiet_enabled=quiet,quiet_start=a?:settings.quiet_start,quiet_end=b?:settings.quiet_end))},enabled=!busy&&valid,modifier=Modifier.fillMaxWidth().testTag("save-notifications")){Text(t("Save changes","Сохранить изменения"))}
 }
}
