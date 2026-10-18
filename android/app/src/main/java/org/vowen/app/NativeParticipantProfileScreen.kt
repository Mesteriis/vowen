package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import kotlinx.serialization.json.*

@Composable
fun NativeParticipantProfileScreen(member:Member,data:WorkspaceState,actions:ParticipantProfileActions){
 val state=remember(member.id){ParticipantProfileState(actions)}
 val scope=rememberCoroutineScope();val ru=member.language=="ru"
 var wizard by remember(member.id){mutableStateOf(false)}
 var editing by remember(member.id){mutableStateOf<String?>(null)}
 LaunchedEffect(member.id){state.load()}
 val section=if(wizard)profileChapters[state.step-1] else editing
 fun move(next:Int){scope.launch{if(state.save(section,next))Unit}}
 Column(verticalArrangement=Arrangement.spacedBy(24.dp)) {
  state.error?.let {Text(if(it.contains("409")){if(ru)"Профиль изменён. Текст сохранён в форме. Обновите или удалите черновик." else "Profile changed. Your text remains in this form. Reload or discard the draft."}else{if(ru)"Не удалось сохранить. Изменения остаются в форме." else "Could not save. Changes remain in the form."},color=MaterialTheme.colorScheme.error)
   TextButton(onClick={scope.launch{state.load()}},enabled=!state.busy){Text(if(ru)"Обновить данные" else "Reload")}
   if(state.draftVersion>0)TextButton(onClick={scope.launch{if(state.discard()){editing=null;wizard=false}}},enabled=!state.busy){Text(if(ru)"Удалить черновик" else "Discard draft")}
  }
  val profile=state.profile
  if(profile==null){if(state.busy)CircularProgressIndicator()}else if(wizard){
   NativeProfileWizard(state.step,state.busy,ru,{move(it)},{scope.launch{if(state.save(section,defer=true))wizard=false}},{scope.launch{if(state.save("visibility")&&state.publish()){wizard=false;editing=null}}}){
    NativeProfileSection(state,profileChapters[state.step-1],member,data,ru)
   }
  }else{
   Text(profile.document.identity.display_name,style=MaterialTheme.typography.headlineLarge)
   Text((profile.document.dynamics?.profile_labels?:member.profile_labels).joinToString(" / "),color=MaterialTheme.colorScheme.primary)
   Text(profile.document.identity.bio?.takeIf{it.isNotBlank()}?:if(ru)"Расскажите о себе и о том, что для вас важно." else "Share what matters to you.")
   VowenActionButton(onClick={editing="identity"},enabled=!state.busy){Text(if(ru)"Редактировать профиль" else "Edit profile")}
   if(!profile.progress.completed||state.draftVersion>0){
    Text(if(ru)"Дополним ваш профиль?" else "Build your profile?",style=MaterialTheme.typography.headlineSmall)
    Text(if(ru)"Можно по шагам и в удобное время." else "One step at a time, whenever you like.")
   }
   TextButton(onClick={scope.launch{if(section==null||state.save(section,profileChapters.indexOf(section)+1))wizard=true}},enabled=!state.busy){Text(if(state.draftVersion>0){if(ru)"Продолжить заполнение" else "Continue setup"}else{if(ru)"Заполнить по шагам" else "Start guided setup"})}
   Row(Modifier.horizontalScroll(rememberScrollState())){profileChapters.forEach{key->TextButton(onClick={scope.launch{if(section==null||state.save(section))editing=key}},enabled=!state.busy){Text(profileChapter(key,ru))}}}
   if(section!=null){
    Text(if(ru)"Черновик · только я" else "Draft · only me",style=MaterialTheme.typography.labelLarge)
    NativeProfileSection(state,section,member,data,ru)
    VowenActionButton(onClick={scope.launch{if(state.save(section)&&state.publish())editing=null}},enabled=!state.busy,modifier=Modifier.testTag("profile-publish")){Text(if(ru)"Сохранить профиль" else "Save profile")}
   }else{
    Text(if(ru)"Что мне нравится" else "What I like",style=MaterialTheme.typography.headlineSmall)
    val liked=profile.document.preferences?.practices.orEmpty().filter{it.attitude in listOf("like","want_to_try")}
    liked.forEach{row->Text(state.catalogues["practices"]?.find{it.uid==row.practice_uid}?.name?:"—")}
    if(liked.isEmpty())Text(if(ru)"Предпочтения пока не указаны" else "Preferences not specified")
    Text(if(ru)"Мои границы" else "My boundaries",style=MaterialTheme.typography.headlineSmall)
    profile.document.preferences?.practices.orEmpty().filter{it.attitude in listOf("taboo","conditional")}.forEach{row->Text((state.catalogues["practices"]?.find{it.uid==row.practice_uid}?.name?:"—")+" · "+(if(row.attitude=="taboo")"Табу" else "При условиях"))}
    Text(if(ru)"Здоровье и забота · личный раздел" else "Health & care · personal section")
   }
  }
 }
}

private fun JsonObject.text(key:String)=this[key]?.jsonPrimitive?.contentOrNull.orEmpty()
private fun JsonObject.ids(key:String)=this[key]?.jsonArray?.map{it.jsonPrimitive.content}.orEmpty()
private fun strings(values:List<String>)=JsonArray(values.map(::JsonPrimitive))

@Composable
private fun NativeProfileSelect(title:String,value:String,options:List<Pair<String,String>>,enabled:Boolean=true,onChange:(String)->Unit){
 var expanded by remember{mutableStateOf(false)}
 Column{Text(title,style=MaterialTheme.typography.labelLarge);Box{
  OutlinedButton(onClick={expanded=true},enabled=enabled,modifier=Modifier.fillMaxWidth().heightIn(min=48.dp)){Text(options.find{it.first==value}?.second?:"—")}
  DropdownMenu(expanded=expanded,onDismissRequest={expanded=false}){options.forEach{(id,label)->DropdownMenuItem(text={Text(label)},onClick={expanded=false;onChange(id)})}}
 }}
}

@Composable
private fun NativeProfilePicker(title:String,items:List<ReferenceEntry>,selected:List<String>,enabled:Boolean,onChange:(List<String>)->Unit){
 var search by remember(title){mutableStateOf("")};var limit by remember(title){mutableIntStateOf(15)}
 Column(verticalArrangement=Arrangement.spacedBy(8.dp)){
  Text(title,style=MaterialTheme.typography.titleMedium)
  OutlinedTextField(search,{search=it;limit=15},label={Text(title)},modifier=Modifier.fillMaxWidth(),enabled=enabled)
  val filtered=items.filter{it.name.contains(search,ignoreCase=true)}
  filtered.take(limit).forEach{item->Row(Modifier.fillMaxWidth().heightIn(min=48.dp)){
   Checkbox(item.uid in selected,{checked->onChange(if(checked)selected+item.uid else selected-item.uid)},enabled=enabled)
   Text(item.name,modifier=Modifier.weight(1f).padding(top=12.dp))
  }}
  if(filtered.size>limit)TextButton(onClick={limit+=20}){Text("+20")}
 }
}

@Composable
private fun NativeProfileSection(state:ParticipantProfileState,section:String,member:Member,data:WorkspaceState,ru:Boolean){
 val content=state.section(section)
 fun put(key:String,value:JsonElement)=state.update(section,key,value)
 val unspecified=if(ru)"Не указано" else "Not specified"
 val attitudes=listOf("not_specified" to unspecified,"like" to if(ru)"Нравится" else "Like","want_to_try" to if(ru)"Хочу попробовать" else "Want to try","conditional" to if(ru)"При условиях" else "Conditional","taboo" to if(ru)"Табу" else "Taboo")
 @Composable fun field(key:String,title:String,max:Int=4000){OutlinedTextField(content.text(key),{if(it.length<=max)put(key,JsonPrimitive(it))},label={Text(title)},enabled=!state.busy,modifier=Modifier.fillMaxWidth())}
 @Composable fun picker(key:String,kind:String,title:String){NativeProfilePicker(title,state.catalogues[kind].orEmpty(),content.ids(key),!state.busy){put(key,strings(it))}}
 when(section){
  "identity"->{field("display_name",if(ru)"Имя" else "Display name",100);field("bio",if(ru)"О себе" else "About me",2000)
   listOf("biological_sex_uid" to "biological-sex","gender_uid" to "genders").forEach{(key,kind)->NativeProfileSelect(if(key=="gender_uid"){if(ru)"Гендер" else "Gender"}else{if(ru)"Биологический пол" else "Biological sex"},content.text(key),listOf("" to unspecified)+state.catalogues[kind].orEmpty().map{it.uid to it.name},!state.busy){put(key,if(it.isEmpty())JsonNull else JsonPrimitive(it))}}
  }
  "dynamics"->{listOf("dominant","submissive","switch").forEach{role->Row{Checkbox(role in content.ids("profile_labels"),{checked->put("profile_labels",strings(if(checked)content.ids("profile_labels")+role else content.ids("profile_labels")-role))},enabled=!state.busy);Text(role)}}
   picker("relationship_type_uids","relationship-types",if(ru)"Виды отношений" else "Relationship types")
   picker("composition_uids","participant-compositions",if(ru)"Состав участников" else "Participant compositions")
   picker("interaction_format_uids","interaction-formats",if(ru)"Форматы" else "Formats")
   listOf("sex_preference" to "biological-sex","gender_preference" to "genders").forEach{(key,kind)->
    val pref=content[key]?.jsonObject?:JsonObject(emptyMap());val title=if(key=="sex_preference"){if(ru)"Предпочтения по полу" else "Sex preferences"}else{if(ru)"Предпочтения по гендеру" else "Gender preferences"}
    NativeProfileSelect(title,pref.text("mode").ifEmpty{"not_specified"},listOf("not_specified" to unspecified,"any" to if(ru)"Любые" else "Any","selected" to if(ru)"Выбранные" else "Selected"),!state.busy){put(key,buildJsonObject{put("mode",it);put("uids",JsonArray(emptyList()))})}
    if(pref.text("mode")=="selected")NativeProfilePicker(title,state.catalogues[kind].orEmpty(),pref.ids("uids"),!state.busy){put(key,JsonObject(pref+("uids" to strings(it))))}
   }
  }
  "preferences"->{
   var selected by remember{mutableStateOf("")};var category by remember{mutableStateOf("")}
   val rows=content["practices"]?.jsonArray.orEmpty().map{it.jsonObject}
   val current=rows.find{it.text("practice_uid")==selected}?:buildJsonObject{put("practice_uid",selected);put("attitude","not_specified");put("experience","not_specified");put("participation","not_specified");put("conditions","")}
   fun change(key:String,value:String){put("practices",JsonArray(rows.filter{it.text("practice_uid")!=selected}+JsonObject(current+(key to JsonPrimitive(value)))))}
   NativeProfileSelect(if(ru)"Категория" else "Category",category,listOf("" to if(ru)"Все" else "All")+state.catalogues["practice-categories"].orEmpty().map{it.uid to it.name}){category=it}
   NativeProfilePicker(if(ru)"Практики" else "Practices",state.catalogues["practices"].orEmpty().filter{category.isEmpty()||it.category_uid==category},listOfNotNull(selected.takeIf{it.isNotEmpty()}),!state.busy){selected=it.lastOrNull().orEmpty()}
   if(selected.isNotEmpty()){
    Text(state.catalogues["practices"]?.find{it.uid==selected}?.name?:"—",style=MaterialTheme.typography.titleLarge)
    NativeProfileSelect(if(ru)"Моё отношение" else "My preference",current.text("attitude"),attitudes,!state.busy){change("attitude",it)}
    NativeProfileSelect(if(ru)"Опыт" else "Experience",current.text("experience"),listOf("not_specified" to unspecified,"none" to if(ru)"Без опыта" else "No experience","tried" to if(ru)"Пробовал(а)" else "Tried","experienced" to if(ru)"Есть опыт" else "Experienced"),!state.busy){change("experience",it)}
    NativeProfileSelect(if(ru)"Участие" else "Participation",current.text("participation"),listOf("not_specified" to unspecified,"give" to if(ru)"Делать" else "Give","receive" to if(ru)"Получать" else "Receive","both" to if(ru)"Оба" else "Both"),!state.busy){change("participation",it)}
    OutlinedTextField(current.text("conditions"),{if(it.length<=2000)change("conditions",it)},label={Text(if(ru)"Условия" else "Conditions")},modifier=Modifier.fillMaxWidth(),enabled=!state.busy)
   }
   listOf("devices" to "Девайсы","body_parts" to "Части тела","materials" to "Материалы","role_scenarios" to "Сценарии","venues" to "Места").forEach{(key,title)->
    val choices=content[key]?.jsonArray.orEmpty().map{it.jsonObject}
    NativeProfilePicker(if(ru)title else key,state.catalogues[key.replace('_','-')].orEmpty(),choices.map{it.text("uid")},!state.busy){ids->put(key,JsonArray(ids.map{uid->choices.find{it.text("uid")==uid}?:buildJsonObject{put("uid",uid);put("attitude","not_specified");put("conditions","")}}))}
    choices.forEach{choice->val uid=choice.text("uid");fun alter(field:String,value:String){put(key,JsonArray(choices.map{if(it.text("uid")==uid)JsonObject(it+(field to JsonPrimitive(value)))else it}))}
     Text(state.catalogues[key.replace('_','-')]?.find{it.uid==uid}?.name?:"—")
     NativeProfileSelect(if(ru)"Отношение" else "Preference",choice.text("attitude"),attitudes,!state.busy){alter("attitude",it)}
     OutlinedTextField(choice.text("conditions"),{if(it.length<=2000)alter("conditions",it)},label={Text(if(ru)"Условия" else "Conditions")},modifier=Modifier.fillMaxWidth(),enabled=!state.busy)
    }
   }
  }
  "boundaries"->{state.section("preferences")["practices"]?.jsonArray.orEmpty().map{it.jsonObject}.filter{it.text("attitude") in listOf("taboo","conditional")}.forEach{Text((state.catalogues["practices"]?.find{p->p.uid==it.text("practice_uid")}?.name?:"—")+" · "+(attitudes.find{a->a.first==it.text("attitude")}?.second?:unspecified))};field("notes",if(ru)"Что важно учитывать" else "What matters to me")}
  "health"->{Text(if(ru)"По умолчанию только я" else "Private by default");picker("condition_uids","health-conditions",if(ru)"Состояния здоровья" else "Health conditions");picker("allergen_uids","allergens",if(ru)"Аллергены" else "Allergens");picker("care_practice_uids","practices",if(ru)"Восстановление и забота" else "Recovery & care");field("notes",if(ru)"Личные пожелания" else "Personal notes")}
  "visibility"->{val grants=content["sections"]?.jsonArray.orEmpty().map{it.jsonObject}
   val partnerIds=data.relations.filter{it.status=="active"&&(it.dominant_user_id==member.id||it.submissive_user_id==member.id)}.map{if(it.dominant_user_id==member.id)it.submissive_user_id else it.dominant_user_id}
   Text(if(ru)"Только выбранные прямые партнёры. Черновик всегда приватный." else "Only selected direct partners. Drafts are always private.")
   profileChapters.take(5).forEach{key->val current=grants.find{it.text("section")==key};val readers=current?.ids("reader_ids").orEmpty();Text(profileChapter(key,ru),style=MaterialTheme.typography.titleMedium)
    Text(if(readers.isEmpty()){if(ru)"Только я" else "Only me"}else{if(ru)"Выбранные партнёры" else "Selected partners"})
    (partnerIds+readers).distinct().forEach{id->Row{Checkbox(id in readers,{checked->val updated=if(checked)readers+id else readers-id;put("sections",JsonArray(grants.filter{it.text("section")!=key}+buildJsonObject{put("section",key);put("reader_ids",strings(updated))}))},enabled=!state.busy);Text(data.participants.find{it.id==id}?.display_name?:if(ru)"Недействующий доступ" else "Inactive access")}}
   }
  }
 }
}
