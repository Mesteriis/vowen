package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.serialization.json.jsonPrimitive

fun ritualScheduleSummary(s:RitualSchedule,ru:Boolean):String {
 val days=if(ru)listOf("Пн","Вт","Ср","Чт","Пт","Сб","Вс") else listOf("Mon","Tue","Wed","Thu","Fri","Sat","Sun")
 val cadence=when(s.kind){"daily"->if(ru)"Ежедневно" else "Daily";"weekly"->s.weekdays.orEmpty().mapNotNull{days.getOrNull(it)}.joinToString(" ");else->s.start_date}
 return cadence+" · "+s.hour.toString().padStart(2,'0')+":"+s.minute.toString().padStart(2,'0')
}
@Composable fun NativeRitualDetails(a:RitualAssignment,member:Member,recipient:String,busy:Boolean,schedule:()->Unit,rewards:(()->Unit)?,transition:(String)->Unit) {
 val ru=member.language=="ru"
 fun t(en:String,r:String)=if(ru)r else en
 Column(verticalArrangement=Arrangement.spacedBy(12.dp)){
  Text(a.title,style=MaterialTheme.typography.headlineSmall,fontSize=23.sp)
  Text(ritualStateLabel(a.status,ru),color=MaterialTheme.colorScheme.primary,style=MaterialTheme.typography.bodySmall)
  Text(a.description,style=MaterialTheme.typography.bodyMedium)
  var more by remember(a.id){mutableStateOf(false)}
  val evidence=a.evidence_policy?.allowed_types?:listOf("link","photo","video")
  val facts=listOf(t("Participant","Участник") to recipient,t("Schedule","Расписание") to ritualScheduleSummary(a.schedule,ru),t("Timezone","Часовой пояс") to a.schedule.timezone,t("Review","Проверка") to if(a.approval_required)t("Required","Обязательна") else t("Not required","Не требуется"),t("Evidence","Доказательство") to ((if(a.evidence_policy?.required==true)t("Required","Обязательно") else t("Optional","Необязательно"))+" · "+evidence.joinToString(", "){when(it){"link"->t("Link","Ссылка");"photo"->t("Photo","Фото");else->t("Video","Видео")}}),t("Rewards","Награды") to (listOfNotNull(a.currency_amount?.takeIf{it>0}?.let{"+$it "+t("coins","монет")})+a.reward_version_ids.orEmpty().map{a.reward_titles?.get(it)?.jsonPrimitive?.content?:t("Saved reward","Сохранённая награда")}).joinToString("\n").ifBlank{t("None","Без награды")})
  facts.forEach{(label,value)->HorizontalDivider(color=MaterialTheme.colorScheme.outline.copy(alpha=.3f));Column(verticalArrangement=Arrangement.spacedBy(4.dp)){Text(label,style=MaterialTheme.typography.labelSmall,color=MaterialTheme.colorScheme.onSurfaceVariant);Text(value,style=MaterialTheme.typography.bodyMedium)}}
  Row(horizontalArrangement=Arrangement.spacedBy(8.dp)){
   if(a.issuer_id==member.id&&a.effective){OutlinedIconButton(onClick=schedule,enabled=!busy&&!member.paused,modifier=Modifier.size(44.dp)){Icon(painterResource(android.R.drawable.ic_menu_my_calendar),contentDescription=t("Change schedule","Изменить расписание"),modifier=Modifier.size(20.dp))};rewards?.let{OutlinedIconButton(onClick=it,enabled=!busy&&!member.paused,modifier=Modifier.size(44.dp)){Icon(painterResource(android.R.drawable.star_big_off),contentDescription=t("Change ritual rewards","Изменить награды ритуала"),modifier=Modifier.size(20.dp))}}}
   if(a.status=="active"&&(a.issuer_id==member.id||a.recipient_id==member.id))OutlinedIconButton(onClick={transition("pause")},enabled=!busy,modifier=Modifier.size(44.dp)){Icon(painterResource(android.R.drawable.ic_media_pause),contentDescription=t("Pause ritual","Приостановить ритуал"),modifier=Modifier.size(20.dp))}
   if(a.status=="paused"&&a.recipient_id==member.id)OutlinedIconButton(onClick={transition("resume")},enabled=!busy&&!member.paused,modifier=Modifier.size(44.dp)){Icon(painterResource(android.R.drawable.ic_media_play),contentDescription=t("Resume ritual","Возобновить ритуал"),modifier=Modifier.size(20.dp))}
   if(a.status!="revoked"&&(a.issuer_id==member.id||a.recipient_id==member.id))Box{OutlinedIconButton(onClick={more=true},modifier=Modifier.size(44.dp)){Icon(painterResource(android.R.drawable.ic_menu_more),contentDescription=t("More actions","Другие действия"),modifier=Modifier.size(20.dp))};DropdownMenu(more,{more=false}){DropdownMenuItem(text={Text(t("Revoke ritual","Отозвать ритуал"))},enabled=!busy,onClick={more=false;transition("revoke")})}}
  }

 }
}

@Composable fun NativeRitualRewardEditor(a:RitualAssignment,rewards:List<RewardDefinition>,busy:Boolean,ru:Boolean,save:(RewardBundleEdit)->Unit,cancel:()->Unit){
 var ids by androidx.compose.runtime.remember(a.id){androidx.compose.runtime.mutableStateOf(a.reward_version_ids.orEmpty())}
 var coins by androidx.compose.runtime.remember(a.id){androidx.compose.runtime.mutableStateOf((a.currency_amount?:0).toString())}
 val options=rewards.map{it.version_id to it.title}+ids.filter{id->rewards.none{it.version_id==id}}.map{it to (a.reward_titles?.get(it)?.jsonPrimitive?.content?:if(ru)"Сохранённая награда" else "Saved reward")}
 Column(verticalArrangement=Arrangement.spacedBy(12.dp)){
  Text(a.title,style=MaterialTheme.typography.headlineSmall)
  options.forEach{(id,title)->Row{Checkbox(id in ids,{ids=if(it)ids+id else ids-id},enabled=!busy);Text(title,style=MaterialTheme.typography.bodyMedium)}}
  OutlinedTextField(coins,{coins=it},label={Text(if(ru)"Монет за выполнение" else "Coins per completion")},enabled=!busy)
  Text(if(ru)"Изменения действуют только для будущих выполнений." else "Changes apply to future occurrences only.",style=MaterialTheme.typography.bodySmall)
  OutlinedButton(onClick={save(RewardBundleEdit(expected_version=a.revision,reward_version_ids=ids,currency_amount=coins.toInt()))},enabled=!busy&&coins.toIntOrNull() in 0..1000000000){Text(if(ru)"Сохранить награды ритуала" else "Save ritual rewards")}
  TextButton(onClick=cancel,enabled=!busy){Text(if(ru)"Отмена" else "Cancel")}
 }
}
