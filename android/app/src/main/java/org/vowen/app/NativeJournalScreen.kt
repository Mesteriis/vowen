package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import java.time.LocalDate

data class JournalActions(val refresh:()->Unit,val save:(JournalEntry?,JournalContent,Boolean)->Unit,val delete:(JournalEntry)->Unit)

@Composable
fun NativeJournalScreen(member:Member,data:WorkspaceState,busy:Boolean,completed:Int,actions:JournalActions){
 val ru=member.language=="ru"
 fun t(en:String,local:String)=if(ru)local else en
 fun name(id:String)=data.participants.find{it.id==id}?.display_name?:id
 var editing by remember {mutableStateOf(false)}
 var selected by remember {mutableStateOf<JournalEntry?>(null)}
 var deleting by remember {mutableStateOf<JournalEntry?>(null)}
 var search by remember {mutableStateOf("")}
 var tag by remember {mutableStateOf("")}
 LaunchedEffect(completed){editing=false;deleting=null}
 Column(verticalArrangement=Arrangement.spacedBy(8.dp)){
  Text(t("Diary","Дневник"),style=MaterialTheme.typography.headlineSmall)
  Text(t("Private by default. Relationships do not grant diary access.","По умолчанию приватный. Отношения не открывают доступ к дневнику."))
  TextButton(onClick=actions.refresh,enabled=!busy){Text(t("Refresh diary","Обновить дневник"))}
  Button(onClick={selected=null;editing=true},enabled=!busy,modifier=Modifier.testTag("new-journal")){Text(t("New diary entry","Новая запись дневника"))}
  OutlinedTextField(search,{search=it},label={Text(t("Search accessible entries","Поиск доступных записей"))},modifier=Modifier.testTag("journal-search"))
  OutlinedTextField(tag,{tag=it},label={Text(t("Filter by tag","Фильтр по тегу"))})
  if(editing)key(selected?.id,selected?.revision){JournalEditor(member,data,selected,busy,actions.save,{editing=false})}
  val visible=data.journal.filter{(it.title+"\n"+it.text).contains(search,ignoreCase=true)&&(tag.isBlank()||tag in (it.tags?:emptyList()))}
  if(visible.isEmpty())Text(t("No accessible entries","Нет доступных записей"))
  visible.forEach{e->Card(Modifier.fillMaxWidth()){Column(Modifier.padding(16.dp),verticalArrangement=Arrangement.spacedBy(8.dp)){
   Text(e.title,style=MaterialTheme.typography.titleMedium);Text("${e.date} · ${name(e.author_id)} · ${e.visibility} · ${if(e.published==true)t("Published","Опубликовано") else t("Draft","Черновик")}")
   Text(e.text,Modifier.testTag("journal-text-${e.id}"));e.mood?.let{Text(it)};Text(e.tags?.joinToString()?:"")
   Text(t("Readers: ","Читатели: ")+(e.reader_ids?:emptyList()).joinToString{ name(it) })
   if(e.author_id==member.id){
    TextButton(onClick={selected=e;editing=true},enabled=!busy,modifier=Modifier.testTag("edit-journal-${e.id}")){Text(t("Edit diary entry","Изменить запись дневника"))}
    TextButton(onClick={deleting=e},enabled=!busy,modifier=Modifier.testTag("delete-journal-${e.id}")){Text(t("Delete diary entry","Удалить запись дневника"))}
   }
  }}}
 }
 deleting?.let{e->AlertDialog(onDismissRequest={if(!busy)deleting=null},title={Text(t("Delete diary entry","Удаление записи дневника"))},text={Text(t("Delete this entry and revoke all readers?","Удалить запись и доступ всех читателей?")+"\n"+e.title)},confirmButton={TextButton(onClick={actions.delete(e)},enabled=!busy,modifier=Modifier.testTag("confirm-journal-delete")){Text(t("Confirm diary deletion","Подтвердить удаление записи"))}},dismissButton={TextButton(onClick={deleting=null},enabled=!busy){Text(t("Cancel","Отмена"))}})}
}

@Composable
private fun JournalEditor(member:Member,data:WorkspaceState,entry:JournalEntry?,busy:Boolean,save:(JournalEntry?,JournalContent,Boolean)->Unit,cancel:()->Unit){
 val ru=member.language=="ru"
 fun t(en:String,local:String)=if(ru)local else en
 var date by remember{mutableStateOf(entry?.date?:LocalDate.now().toString())}
 var title by remember{mutableStateOf(entry?.title?:"")}
 var text by remember{mutableStateOf(entry?.text?:"")}
 var mood by remember{mutableStateOf(entry?.mood?:"")}
 var tags by remember{mutableStateOf(entry?.tags?.joinToString(", ")?:"")}
 var visibility by remember{mutableStateOf(entry?.visibility?:"private")}
 var readers by remember{mutableStateOf(entry?.reader_ids?:emptyList())}
 var published by remember{mutableStateOf(entry?.published?:false)}
 var refresh by remember{mutableStateOf(false)}
 Column(verticalArrangement=Arrangement.spacedBy(8.dp)){
  OutlinedTextField(date,{date=it},label={Text(t("Entry date (YYYY-MM-DD)","Дата записи (ГГГГ-ММ-ДД)"))},enabled=!busy)
  OutlinedTextField(title,{if(it.length<=200)title=it},label={Text(t("Entry title","Заголовок записи"))},enabled=!busy,modifier=Modifier.testTag("journal-title"))
  OutlinedTextField(text,{if(it.length<=100000)text=it},label={Text(t("Entry text","Текст записи"))},enabled=!busy,modifier=Modifier.testTag("journal-text"))
  OutlinedTextField(mood,{if(it.length<=100)mood=it},label={Text(t("Mood","Настроение"))},enabled=!busy)
  OutlinedTextField(tags,{tags=it},label={Text(t("Tags (comma separated)","Теги (через запятую)"))},enabled=!busy)
  Row{Checkbox(published,{published=it},enabled=!busy,modifier=Modifier.testTag("journal-published"));Text(t("Published entry; drafts are visible only to you","Опубликованная запись; черновики видны только вам"))}
  M4Choice(t("Entry visibility","Видимость записи"),visibility,listOf("private" to t("Private","Только мне"),"selected" to t("Selected readers","Выбранные читатели"),"all_current_members" to t("Current members snapshot; future members excluded","Текущие участники; будущие не добавляются")),busy){visibility=it}
  val readerOptions=data.participants+readers.filter{id->data.participants.none{it.id==id}}.map{Participant(id=it,display_name=it,profile_labels=emptyList())}
  if(visibility=="selected")readerOptions.filter{it.id!=member.id}.forEach{p->Row{Checkbox(p.id in readers,{checked->readers=if(checked)readers+p.id else readers-p.id},enabled=!busy,modifier=Modifier.testTag("journal-reader-${p.id}"));Text(p.display_name)}}
  if(visibility=="all_current_members"){
   Text(t("Editing text never expands the readership snapshot.","Редактирование текста не расширяет список читателей."))
   if(entry!=null)Row{Checkbox(refresh,{refresh=it},enabled=!busy);Text(t("Explicitly refresh current member snapshot","Явно обновить список текущих участников"))}
  }
  Button(onClick={save(entry,JournalContent(date=date,title=title,text=text,mood=mood.ifBlank{null},tags=tags.split(',').map{it.trim()}.filter{it.isNotEmpty()},published=published,visibility=visibility,reader_ids=if(visibility=="private")emptyList() else readers),refresh)},enabled=!busy&&title.isNotBlank()&&text.isNotBlank()&&runCatching{LocalDate.parse(date)}.isSuccess,modifier=Modifier.testTag("save-journal")){Text(t("Save diary entry","Сохранить запись дневника"))}
  TextButton(onClick=cancel,enabled=!busy){Text(t("Cancel","Отмена"))}
 }
}
