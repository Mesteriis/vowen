package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import java.util.UUID
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

data class RewardActions(val refresh:()->Unit,val save:(RewardDefinition?,RewardContent)->Unit,val grant:(GrantCommand)->Unit,val transition:(RewardGrant,String)->Unit)

@Composable fun NativeRewardsScreen(member:Member,data:WorkspaceState,busy:Boolean,actions:RewardActions){
 val ru=member.language=="ru"
 fun t(en:String,r:String)=if(ru)r else en
 fun label(s:String)=if(ru)mapOf("offered" to "Предложено","accepted" to "Принято","declined" to "Отклонено","delivered" to "Вручено","cancelled" to "Отменено")[s]?:s else mapOf("offered" to "Offered","accepted" to "Accepted","declined" to "Declined","delivered" to "Delivered","cancelled" to "Cancelled")[s]?:s
 var editing by remember{mutableStateOf(false)};var selected by remember{mutableStateOf<RewardDefinition?>(null)}
 var offering by remember{mutableStateOf<RewardDefinition?>(null)};var recipient by remember{mutableStateOf("")};var expanded by remember{mutableStateOf(false)}
 var requestKey by remember{mutableStateOf(UUID.randomUUID().toString())}
 Column(verticalArrangement=Arrangement.spacedBy(8.dp)){
  Text(t("Rewards","Награды"),style=MaterialTheme.typography.headlineMedium)
  Row{TextButton(onClick=actions.refresh,enabled=!busy){Text(t("Refresh rewards","Обновить награды"))};Button(onClick={selected=null;editing=true},enabled=!busy&&!member.paused){Text(t("New reward","Новая награда"))}}
  if(editing)key(selected?.id,selected?.revision){
   var title by remember{mutableStateOf(selected?.title?:"")};var description by remember{mutableStateOf(selected?.description?:"")};var conditions by remember{mutableStateOf(selected?.conditions?:"")}
   OutlinedTextField(title,{if(it.length<=200)title=it},label={Text(t("Reward title","Название награды"))},enabled=!busy)
   OutlinedTextField(description,{if(it.length<=10000)description=it},label={Text(t("Reward description","Описание награды"))},enabled=!busy)
   OutlinedTextField(conditions,{if(it.length<=10000)conditions=it},label={Text(t("Reward conditions","Условия награды"))},enabled=!busy)
   Button(onClick={actions.save(selected,RewardContent(title=title,description=description,conditions=conditions))},enabled=!busy&&!member.paused&&title.isNotBlank()&&description.isNotBlank()){Text(t("Save reward","Сохранить награду"))}
   TextButton(onClick={editing=false},enabled=!busy){Text(t("Close editor","Закрыть редактор"))}
  }
  Text(t("Your grants","Ваши выдачи"),style=MaterialTheme.typography.titleLarge)
  if(data.rewardGrants.isEmpty())Text(t("No reward offers yet.","Пока нет предложенных наград."))
  data.rewardGrants.forEach{g->Card(Modifier.fillMaxWidth()){Column(Modifier.padding(16.dp),verticalArrangement=Arrangement.spacedBy(8.dp)){
   Text(g.title,style=MaterialTheme.typography.titleLarge);Text(label(g.status),color=MaterialTheme.colorScheme.primary);Text(g.description);Text(g.conditions?:"")
   Text(if(g.occurrence_id==null)t("Manual offer","Ручное предложение") else t("Approved ritual","Одобренный ритуал"))
   if(g.recipient_id==member.id&&g.status=="offered"){TextButton(onClick={actions.transition(g,"accept")},enabled=!busy){Text(t("Accept reward","Принять награду"))};TextButton(onClick={actions.transition(g,"decline")},enabled=!busy){Text(t("Decline reward","Отклонить награду"))}}
   if(g.issuer_id==member.id&&g.status=="accepted")TextButton(onClick={actions.transition(g,"deliver")},enabled=!busy&&!member.paused){Text(t("Mark delivered","Отметить вручение"))}
   if(g.issuer_id==member.id&&g.status in listOf("offered","accepted"))TextButton(onClick={actions.transition(g,"cancel")},enabled=!busy&&!member.paused){Text(t("Cancel reward","Отменить награду"))}
   Text(t("Grant history","История выдачи"),style=MaterialTheme.typography.titleMedium)
   g.history.forEach{h->Text(label(h.status)+" · "+OffsetDateTime.parse(h.created_at).atZoneSameInstant(ZoneId.of(member.timezone)).format(DateTimeFormatter.ofPattern("d MMM uuuu, HH:mm VV",if(ru)Locale.forLanguageTag("ru") else Locale.UK)),style=MaterialTheme.typography.bodySmall)}
  }}}
  Text(t("Your catalogue","Ваш каталог"),style=MaterialTheme.typography.titleLarge)
  if(data.rewards.isEmpty())Text(t("Create a reward before offering it or adding it to an assignment.","Создайте награду перед выдачей или добавлением к назначению."))
  data.rewards.forEach{r->Text(r.title,style=MaterialTheme.typography.titleLarge);Text(r.description);Text(r.conditions?:"")
   Row{TextButton(onClick={offering=r;recipient="";requestKey=UUID.randomUUID().toString()},enabled=!busy&&!member.paused){Text(t("Offer reward","Предложить награду"))};TextButton(onClick={selected=r;editing=true},enabled=!busy&&!member.paused){Text(t("New reward version","Новая версия награды"))}}
  }
  offering?.let{r->Text(r.title);Box{TextButton(onClick={expanded=true},enabled=!busy){Text(data.participants.find{it.id==recipient}?.display_name?:t("Reward recipient","Получатель награды"))};DropdownMenu(expanded,{expanded=false}){data.participants.filter{it.id!=member.id}.forEach{p->DropdownMenuItem(text={Text(p.display_name)},onClick={recipient=p.id;requestKey=UUID.randomUUID().toString();expanded=false})}}}
   Button(onClick={actions.grant(GrantCommand(reward_version_id=r.version_id,recipient_id=recipient,idempotency_key=requestKey))},enabled=!busy&&!member.paused&&recipient.isNotEmpty()){Text(t("Confirm reward offer","Подтвердить предложение награды"))};TextButton(onClick={offering=null},enabled=!busy){Text(t("Close offer","Закрыть предложение"))}
  }

 }
}
