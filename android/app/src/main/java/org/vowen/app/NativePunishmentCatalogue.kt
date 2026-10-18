package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import java.util.UUID

@Composable fun NativePunishmentCatalogue(member:Member,data:WorkspaceState,busy:Boolean,actions:DisciplineActions){
 val ru=member.language=="ru";fun t(en:String,r:String)=if(ru)r else en
 val relations=data.relations.filter{it.status=="active"&&"discipline.propose" in it.scopes&&it.consent_user_ids.size==2}
 var rid by remember{mutableStateOf(relations.singleOrNull()?.id?:"")}
 val relation=relations.find{it.id==rid};val upper=relation?.dominant_user_id==member.id&&!member.paused
 var templates by remember(rid){mutableStateOf(emptyList<PunishmentTemplateView>())}
 var category by remember(rid){mutableStateOf<String?>(null)};var selected by remember(rid){mutableStateOf<PunishmentTemplateView?>(null)}
 var editing by remember(rid){mutableStateOf(false)};var editItem by remember(rid){mutableStateOf<PunishmentTemplateView?>(null)};var assigning by remember(rid){mutableStateOf<PunishmentTemplateView?>(null)}
 val currentRid by rememberUpdatedState(rid)
 fun reload(){if(rid.isNotBlank()){val id=rid;actions.templates(id){if(currentRid==id)templates=it}}}
 LaunchedEffect(rid){reload()}
 M4Choice(t("Relationship","Отношения"),rid,relations.map{r->r.id to (data.participants.find{it.id==if(r.dominant_user_id==member.id)r.submissive_user_id else r.dominant_user_id}?.display_name?:t("Participant","Участник"))},busy){rid=it}
 if(relation==null){Text(t("Choose a relationship.","Выберите отношения."));return}
 val categories=listOf("physical" to t("Physical punishments","Телесные наказания"),"ban" to t("Bans","Запреты"),"other" to t("Other","Другое"))
 BoxWithConstraints(Modifier.fillMaxWidth()){
  val wide=maxWidth>=700.dp
  Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(20.dp)){
   if(wide||category==null)Column(if(wide)Modifier.width(160.dp) else Modifier.fillMaxWidth()){
    categories.forEach{(id,label)->TextButton(onClick={category=id;selected=null},modifier=Modifier.fillMaxWidth()){Text(label)}}
   }
   if(wide||category!=null)Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(8.dp)){
    if(!wide)TextButton(onClick={category=null}){Text(t("Back to catalogues","К каталогам"))}
    Row{Text(categories.find{it.first==(category?:"physical")}!!.second,style=MaterialTheme.typography.titleMedium);if(upper)TextButton(onClick={editItem=null;editing=true},enabled=!busy){Text("+")}}
    val items=templates.filter{it.punishment_type==(category?:"physical")}
    if(items.isEmpty())Text(t("No saved variants yet.","Пока нет сохранённых вариантов."),style=MaterialTheme.typography.bodySmall)
    items.forEach{item->Row(Modifier.fillMaxWidth()){
     TextButton(onClick={selected=item;if(upper)assigning=item},modifier=Modifier.weight(1f)){Column{Text(item.title);Text(item.description,style=MaterialTheme.typography.bodySmall)}}
     if(upper&&item.can_edit)TextButton(onClick={editItem=item;editing=true},enabled=!busy){Text(t("Edit","Изменить"))}
    };HorizontalDivider()}
   }
   if(wide&&selected!=null)Column(Modifier.weight(1f)){val item=selected!!;Text(item.title,style=MaterialTheme.typography.titleMedium);Text(item.description);item.device?.let{Text(it)};item.body_part?.let{Text(it)};item.strike_count?.let{Text(t("Strike count: ","Количество ударов: ")+it)};if(item.punishment_type=="physical")Text(t("Intensity is set on assignment","Сила задаётся при назначении"));if(upper)OutlinedButton(onClick={assigning=item}){Text(t("Assign","Назначить"))}}
  }
 }
 if(editing)NativePunishmentTemplateEditor(rid,editItem,category?:"physical",ru,busy,actions,{editing=false;reload()},{editing=false})
 assigning?.let{item->NativePunishmentAssign(item,data.participants.find{it.id==relation.submissive_user_id}?.display_name?:"",ru,busy,actions,null,{assigning=null})}
}

@Composable internal fun NativePunishmentAssign(item:PunishmentTemplateView,recipient:String,ru:Boolean,busy:Boolean,actions:DisciplineActions,ruleVersion:String?=null,close:()->Unit){
 var comment by remember(item.id){mutableStateOf("")};var intensity by remember(item.id){mutableFloatStateOf(1f)}
 val key=remember(item.id,comment,intensity){UUID.randomUUID().toString()}
 AlertDialog(onDismissRequest={if(!busy)close()},title={Text(if(ru)"Назначить наказание" else "Assign punishment")},text={Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){
  Text(item.title);Text((if(ru)"Кому: " else "To: ")+recipient)
  if(ruleVersion!=null)Text(if(ru)"За нарушение правила" else "For a rule violation")
  if(item.punishment_type=="physical"){Text((if(ru)"Сила воздействия: " else "Intensity: ")+intensity.toInt()+" / 10");Slider(value=intensity,onValueChange={intensity=it},valueRange=1f..10f,steps=8,enabled=!busy)}
  NativeVoiceText(comment,{comment=it},ru,busy)
 }},confirmButton={TextButton(onClick={actions.assignTemplate(item,PunishmentAssign(expected_version=item.revision,idempotency_key=key,comment=comment,intensity=if(item.punishment_type=="physical")intensity.toInt() else null,rule_version_id=ruleVersion),close)},enabled=!busy){Text(if(ru)"Назначить" else "Assign")}},dismissButton={TextButton(onClick=close,enabled=!busy){Text(if(ru)"Отмена" else "Cancel")}})
}

@Composable private fun NativePunishmentTemplateEditor(rid:String,item:PunishmentTemplateView?,initialType:String,ru:Boolean,busy:Boolean,actions:DisciplineActions,saved:()->Unit,close:()->Unit){
 fun t(en:String,r:String)=if(ru)r else en
 var title by remember{mutableStateOf(item?.title?:"")};var description by remember{mutableStateOf(item?.description?:"")};var conditions by remember{mutableStateOf(item?.conditions?:"")};var type by remember{mutableStateOf(item?.punishment_type?:initialType)}
 var device by remember{mutableStateOf(item?.device?:"")};var part by remember{mutableStateOf(item?.body_part?:"")};var count by remember{mutableStateOf(item?.strike_count?.toString()?:"")};var days by remember{mutableStateOf(item?.ban_days?.toString()?:"")}
 var devices by remember{mutableStateOf(emptyList<String>())};var parts by remember{mutableStateOf(emptyList<String>())};var newDevice by remember{mutableStateOf("")};var newPart by remember{mutableStateOf("")};var archiving by remember{mutableStateOf(false)}
 LaunchedEffect(rid){actions.dictionary(rid,"device",null){devices=it};actions.dictionary(rid,"body_part",null){parts=it}}
 val valid=title.isNotBlank()&&description.isNotBlank()&&when(type){"physical"->device in devices&&part in parts&&(count.toIntOrNull()?:0) in 1..1000000;"ban"->(days.toIntOrNull()?:0) in 1..36500;else->true}
 AlertDialog(onDismissRequest={if(!busy)close()},title={Text(if(item==null)t("New variant","Новый вариант") else t("Edit variant","Редактировать вариант"))},text={Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(8.dp)){
  OutlinedTextField(title,{title=it.take(200)},label={Text(t("Title","Название"))},enabled=!busy)
  OutlinedTextField(description,{description=it.take(10000)},label={Text(t("Description","Описание"))},enabled=!busy)
  M4Choice(t("Type","Тип"),type,listOf("physical" to t("Physical","Физическое"),"ban" to t("Bans","Запреты"),"other" to t("Other","Другое")),busy){type=it}
  if(type=="physical"){
   M4Choice(t("Device","Девайс"),device,devices.map{it to it},busy){device=it}
   OutlinedTextField(newDevice,{newDevice=it.take(100)},label={Text(t("New device","Новый девайс"))},enabled=!busy)
   TextButton(onClick={actions.dictionary(rid,"device",newDevice){devices=it;device=it.firstOrNull{v->v.equals(newDevice.trim(),true)}?:device;newDevice=""}},enabled=!busy&&newDevice.isNotBlank()){Text(t("Add device","Добавить девайс"))}
   M4Choice(t("Body part","Часть тела"),part,parts.map{it to it},busy){part=it}
   OutlinedTextField(newPart,{newPart=it.take(100)},label={Text(t("New body part","Новая часть тела"))},enabled=!busy)
   TextButton(onClick={actions.dictionary(rid,"body_part",newPart){parts=it;part=it.firstOrNull{v->v.equals(newPart.trim(),true)}?:part;newPart=""}},enabled=!busy&&newPart.isNotBlank()){Text(t("Add body part","Добавить часть тела"))}
   OutlinedTextField(count,{count=it},label={Text(t("Strike count","Количество ударов"))},keyboardOptions=androidx.compose.foundation.text.KeyboardOptions(keyboardType=androidx.compose.ui.text.input.KeyboardType.Number),enabled=!busy)
  }
  if(type=="ban")OutlinedTextField(days,{days=it},label={Text(t("Days","Дни"))},keyboardOptions=androidx.compose.foundation.text.KeyboardOptions(keyboardType=androidx.compose.ui.text.input.KeyboardType.Number),enabled=!busy)
  OutlinedTextField(conditions,{conditions=it.take(10000)},label={Text(t("Conditions (optional)","Условия (необязательно)"))},enabled=!busy)
  if(item!=null)TextButton(onClick={archiving=true},enabled=!busy){Text(t("Archive variant","Убрать из каталога"))}
  if(archiving){Text(t("Existing assignments remain.","Назначения сохранятся."));TextButton(onClick={actions.archiveTemplate(item!!,saved)},enabled=!busy){Text(t("Confirm archive","Подтвердить удаление из каталога"))}}
 }},confirmButton={TextButton(onClick={actions.saveTemplate(item,PunishmentTemplateCreate(relation_id=rid,title=title,description=description,conditions=conditions,punishment_type=type,device=if(type=="physical")device else null,body_part=if(type=="physical")part else null,strike_count=if(type=="physical")count.toIntOrNull() else null,ban_days=if(type=="ban")days.toIntOrNull() else null),saved)},enabled=!busy&&valid){Text(t("Save variant","Сохранить вариант"))}},dismissButton={TextButton(onClick=close,enabled=!busy){Text(t("Cancel","Отмена"))}})
}
