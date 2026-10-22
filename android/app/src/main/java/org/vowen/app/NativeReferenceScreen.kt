package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull

data class ReferenceActions(val load:suspend (String)->List<ReferenceEntry>,val add:(PracticeCreate)->Unit,val wikiLinks:(suspend (String)->List<WikiReferenceLink>)?=null)

@Composable
fun NativeSpaceSettingsScreen(member:Member,busy:Boolean,completed:Int,administration:AdministrationActions,references:ReferenceActions?,onWikiPage:((String)->Unit)?=null){
 val ru=member.language=="ru"
 var tab by remember{mutableIntStateOf(0)}
 if(member.is_admin!=true){Text(if(ru)"Нужны права администратора." else "Administrator access required.");return}
 Column(verticalArrangement=Arrangement.spacedBy(24.dp)){
  if(references!=null)TabRow(selectedTabIndex=tab,containerColor=MaterialTheme.colorScheme.background){
   Tab(selected=tab==0,onClick={tab=0},text={Text(if(ru)"Администраторы" else "Administrators")})
   Tab(selected=tab==1,onClick={tab=1},text={Text(if(ru)"Справочники" else "References")},modifier=Modifier.testTag("settings-references"))
  }
  if(tab==1&&references!=null)NativeReferenceScreen(ru,busy,completed,references,onWikiPage) else NativeAdministrationScreen(member,busy,completed,administration)
 }
}

@Composable
fun NativeReferenceScreen(ru:Boolean,busy:Boolean,completed:Int,actions:ReferenceActions,onWikiPage:((String)->Unit)?=null){
 fun t(en:String,r:String)=if(ru)r else en
 val kinds=listOf("biological-sex" to t("Biological sex","Биологический пол"),"genders" to t("Gender","Гендер"),"practices" to t("Practices","Практики"),"practice-categories" to t("Practice categories","Категории практик"),"poses" to t("Poses","Позы"),"pose-categories" to t("Pose categories","Категории поз"),"participant-compositions" to t("Participant composition","Состав участников"),"devices" to t("Devices and accessories","Девайсы и аксессуары"),"body-parts" to t("Body parts","Части тела"),"materials" to t("Materials","Материалы"),"role-scenarios" to t("Role scenarios","Ролевые сценарии"),"interaction-formats" to t("Interaction formats","Форматы взаимодействия"),"venues" to t("Venues","Места проведения"),"health-conditions" to t("Health conditions","Заболевания и состояния"),"allergens" to t("Allergens","Аллергены"),"timezones" to t("Timezones","Часовые пояса"),"relationship-types" to t("Relationship types","Виды отношений"))
 var kind by remember{mutableStateOf("biological-sex")}
 val categorized=kind=="practices"||kind=="poses"
 var query by remember{mutableStateOf("")}
 var filterCategory by remember{mutableStateOf<String?>(null)}
 var filterGroup by remember{mutableStateOf<String?>(null)}
 var groupMenu by remember{mutableStateOf(false)}
 var filterMenu by remember{mutableStateOf(false)}
 var menu by remember{mutableStateOf(false)}
 var wikiLinks by remember{mutableStateOf<Map<String,String>>(emptyMap())}
 var wikiLinksFailed by remember{mutableStateOf(false)}
 var rows by remember{mutableStateOf<List<ReferenceEntry>>(emptyList())}
 var categories by remember{mutableStateOf<List<ReferenceEntry>>(emptyList())}
 var compositions by remember{mutableStateOf<List<ReferenceEntry>>(emptyList())}
 var devices by remember{mutableStateOf<List<ReferenceEntry>>(emptyList())}
 var bodyParts by remember{mutableStateOf<List<ReferenceEntry>>(emptyList())}
 var deviceUids by remember{mutableStateOf<Set<String>>(emptySet())}
 var bodyPartUids by remember{mutableStateOf<Set<String>>(emptySet())}
 var categoryUid by remember{mutableStateOf<String?>(null)}
 var categoryMenu by remember{mutableStateOf(false)}
 var loading by remember{mutableStateOf(false)}
 var failed by remember{mutableStateOf(false)}
 var reload by remember{mutableIntStateOf(0)}
 var limit by remember{mutableIntStateOf(50)}
 var editor by remember{mutableStateOf(false)}
 var name by remember{mutableStateOf("")}
 var description by remember{mutableStateOf("")}
 var icon by remember{mutableStateOf("")}
 var thumbnail by remember{mutableStateOf("")}
 var extra by remember{mutableStateOf("{}")}
 LaunchedEffect(kind,completed,reload){query="";filterCategory=null;filterGroup=null;rows=emptyList();wikiLinks=emptyMap();wikiLinksFailed=false;limit=50;failed=false;loading=true;try{rows=actions.load(kind);categories=when(kind){"practices"->actions.load("practice-categories");"poses"->actions.load("pose-categories");else->emptyList()};devices=if(kind=="practices"||kind=="poses")actions.load("devices") else emptyList();compositions=if(kind=="poses")actions.load("participant-compositions") else emptyList();bodyParts=if(kind=="practices")actions.load("body-parts") else emptyList();actions.wikiLinks?.let{load->try{wikiLinks=load(kind).associate{it.reference_uid to it.page_uid}}catch(e:Exception){if(e is kotlinx.coroutines.CancellationException)throw e;wikiLinksFailed=true}}}catch(e:Exception){if(e is kotlinx.coroutines.CancellationException)throw e;failed=true}finally{loading=false}}
 fun aliases(entry:ReferenceEntry)=(entry.extra?.get("aliases") as? JsonArray)?.mapNotNull{(it as? JsonPrimitive)?.contentOrNull}?:emptyList()
 fun group(entry:ReferenceEntry)=(entry.extra?.get("group") as? JsonPrimitive)?.contentOrNull?.trim().orEmpty()
 val groups=rows.filter{!categorized||filterCategory==null||it.category_uid==filterCategory}.map{group(it)}.filter{it.isNotBlank()}.distinct().sorted()
 LaunchedEffect(filterCategory){filterGroup=null}
 fun normalized(value:String)=value.lowercase(java.util.Locale.ROOT).replace('ё','е').trim()
 val words=normalized(query).split(Regex("\\s+")).filter{it.isNotBlank()}
 val visibleRows=rows.filter{entry->(!categorized||filterCategory==null||entry.category_uid==filterCategory)&&(filterGroup==null||group(entry)==filterGroup)&&words.all{word->normalized(listOf(entry.name,entry.description,group(entry),categories.find{it.uid==entry.category_uid}?.name?:"").plus(aliases(entry)).joinToString(" ")).contains(word)}}
 LaunchedEffect(query,filterCategory,filterGroup){limit=50}
 Column(verticalArrangement=Arrangement.spacedBy(16.dp)){
  Box{
   OutlinedButton(onClick={menu=true},modifier=Modifier.fillMaxWidth().testTag("reference-kind")){Text(kinds.first{it.first==kind}.second)}
   DropdownMenu(expanded=menu,onDismissRequest={menu=false}){kinds.forEach{(id,title)->DropdownMenuItem(text={Text(title)},onClick={kind=id;menu=false},modifier=Modifier.testTag("reference-$id"))}}
  }
  Row(horizontalArrangement=Arrangement.spacedBy(8.dp)){
   TextButton(onClick={reload++},enabled=!loading){Text(t("Reload","Обновить"))}
   if(kind=="practices")OutlinedButton(onClick={deviceUids=emptySet();bodyPartUids=emptySet();categoryUid=null;name="";description="";icon="";thumbnail="";extra="{}";editor=true},enabled=!busy,modifier=Modifier.testTag("new-practice")){Text(t("Add practice","Добавить практику"))}
  }
  OutlinedTextField(query,{query=it},label={Text(t("Search name or alias","Поиск по названию или синониму"))},singleLine=true,modifier=Modifier.fillMaxWidth())
  if(categorized)Box{OutlinedButton(onClick={filterMenu=true}){Text(categories.find{it.uid==filterCategory}?.name?:t("All categories","Все категории"))};DropdownMenu(expanded=filterMenu,onDismissRequest={filterMenu=false}){DropdownMenuItem(text={Text(t("All categories","Все категории"))},onClick={filterCategory=null;filterMenu=false});categories.forEach{category->DropdownMenuItem(text={Text(category.name)},onClick={filterCategory=category.uid;filterMenu=false})}}}
  if(groups.isNotEmpty())Box{OutlinedButton(onClick={groupMenu=true}){Text(filterGroup?:t("All groups","Все группы"))};DropdownMenu(expanded=groupMenu,onDismissRequest={groupMenu=false}){DropdownMenuItem(text={Text(t("All groups","Все группы"))},onClick={filterGroup=null;groupMenu=false});groups.forEach{value->DropdownMenuItem(text={Text(value)},onClick={filterGroup=value;groupMenu=false})}}}
  if(loading)Text(t("Loading…","Загрузка…"))
  if(wikiLinksFailed)Text(t("Could not load article links. Reload the catalogue.","Не удалось загрузить ссылки на статьи. Обновите справочник."))
  if(failed)Text(t("Could not load catalogue.","Не удалось загрузить справочник."))
  Text("${visibleRows.size} / ${rows.size} "+t("entries","записей"),style=MaterialTheme.typography.bodySmall)
  visibleRows.take(limit).forEach{entry->
   var details by remember(entry.uid){mutableStateOf(false)}
   Column(verticalArrangement=Arrangement.spacedBy(8.dp)){
    Text(entry.name,style=MaterialTheme.typography.titleSmall)
    if(aliases(entry).isNotEmpty())Text(aliases(entry).joinToString(", "),style=MaterialTheme.typography.bodySmall)
    if(group(entry).isNotBlank())Text(t("Group: ","Группа: ")+group(entry),style=MaterialTheme.typography.bodySmall)
    if(entry.description.isNotBlank())Text(entry.description,style=MaterialTheme.typography.bodySmall)
    if(categorized)Text(t("Category: ","Категория: ")+(categories.find{it.uid==entry.category_uid}?.name?:t("None","Не выбрана")),style=MaterialTheme.typography.bodySmall)
    wikiLinks[entry.uid]?.let{pageUid->if(onWikiPage!=null)TextButton(onClick={onWikiPage(pageUid)},enabled=!busy,modifier=Modifier.testTag("reference-wiki-${entry.uid}")){Text(t("Article in Wiki","Статья в Wiki"))}}
    TextButton(onClick={details=!details}){Text(t("Details","Подробнее"))}
    if(details){Text("uid: ${entry.uid}",style=MaterialTheme.typography.bodySmall);Text("thumbnail: ${entry.thumbnail?:t("None","Нет")}",style=MaterialTheme.typography.bodySmall);Text("icon: ${entry.icon?:t("None","Нет")}",style=MaterialTheme.typography.bodySmall);Text("url: ${entry.url?:t("None","Нет")}",style=MaterialTheme.typography.bodySmall);Text(t("Devices: ","Девайсы: ")+devices.filter{entry.device_uids?.contains(it.uid)==true}.joinToString{it.name},style=MaterialTheme.typography.bodySmall);if(kind=="practices"){Text(t("Body parts: ","Части тела: ")+bodyParts.filter{entry.body_part_uids?.contains(it.uid)==true}.joinToString{it.name},style=MaterialTheme.typography.bodySmall);};if(kind=="poses"){Text(t("Example compositions: ","Примеры состава участников: ")+compositions.filter{entry.composition_uids?.contains(it.uid)==true}.joinToString{it.name},style=MaterialTheme.typography.bodySmall)};Text("extra: ${entry.extra}",style=MaterialTheme.typography.bodySmall)}
    HorizontalDivider()
   }
  }
  if(visibleRows.size>limit)TextButton(onClick={limit+=50}){Text(t("Show more","Показать ещё"))}
 }
 val parsed=runCatching{Json.parseToJsonElement(extra) as? JsonObject}.getOrNull()
 if(editor)AlertDialog(onDismissRequest={if(!busy)editor=false},title={Text(t("New practice","Новая практика"))},text={Column(Modifier.heightIn(max=460.dp).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(12.dp)){
  OutlinedTextField(name,{if(it.length<=120)name=it},label={Text(t("Name","Название"))},enabled=!busy,modifier=Modifier.fillMaxWidth())
  Box{OutlinedButton(onClick={categoryMenu=true},enabled=!busy){Text(categories.find{it.uid==categoryUid}?.name?:t("Select category","Выбрать категорию"))};DropdownMenu(expanded=categoryMenu,onDismissRequest={categoryMenu=false}){DropdownMenuItem(text={Text(t("None","Не выбрана"))},onClick={categoryUid=null;categoryMenu=false});categories.forEach{category->DropdownMenuItem(text={Text(category.name)},onClick={categoryUid=category.uid;categoryMenu=false})}}}
  OutlinedTextField(description,{if(it.length<=4000)description=it},label={Text(t("Description","Описание"))},enabled=!busy,modifier=Modifier.fillMaxWidth())
  Text(t("Devices","Девайсы"));devices.forEach{item->Row{Checkbox(checked=item.uid in deviceUids,onCheckedChange={checked->deviceUids=if(checked)deviceUids+item.uid else deviceUids-item.uid},enabled=!busy);Text(item.name)}}
  Text(t("Body parts","Части тела"));bodyParts.forEach{item->Row{Checkbox(checked=item.uid in bodyPartUids,onCheckedChange={checked->bodyPartUids=if(checked)bodyPartUids+item.uid else bodyPartUids-item.uid},enabled=!busy);Text(item.name)}}
  OutlinedTextField(thumbnail,{if(it.length<=500)thumbnail=it},label={Text(t("Thumbnail path","Путь к миниатюре"))},enabled=!busy,modifier=Modifier.fillMaxWidth())
  OutlinedTextField(icon,{if(it.length<=500)icon=it},label={Text(t("Icon path","Путь к иконке"))},enabled=!busy,modifier=Modifier.fillMaxWidth())
  OutlinedTextField(extra,{extra=it},label={Text("extra · JSON")},enabled=!busy,isError=parsed==null,modifier=Modifier.fillMaxWidth())
 }},confirmButton={TextButton(onClick={parsed?.let{actions.add(PracticeCreate(device_uids=deviceUids.toList(),body_part_uids=bodyPartUids.toList(),category_uid=categoryUid,name=name,description=description,icon=icon.trim().takeIf{it.isNotEmpty()},thumbnail=thumbnail.trim().takeIf{it.isNotEmpty()},extra=it.toMap()));editor=false}},enabled=!busy&&name.isNotBlank()&&parsed!=null){Text(t("Add","Добавить"))}},dismissButton={TextButton(onClick={editor=false},enabled=!busy){Text(t("Cancel","Отмена"))}})
}
