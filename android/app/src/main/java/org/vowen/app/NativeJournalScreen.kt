package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import androidx.compose.ui.res.painterResource
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

data class JournalActions(val refresh:()->Unit,val save:(JournalEntry?,JournalContent,Boolean)->Unit,val delete:(JournalEntry)->Unit,val draft:JournalDraftState?=null)

@Composable fun NativeJournalScreen(member:Member,data:WorkspaceState,busy:Boolean,completed:Int,actions:JournalActions){
 val ru=member.language=="ru"
 fun t(en:String,local:String)=if(ru)local else en
 val today=LocalDate.now(ZoneId.of(member.timezone)).toString()
 fun day(date:String)=LocalDate.parse(date).format(DateTimeFormatter.ofPattern("d MMMM",if(ru)Locale.forLanguageTag("ru") else Locale.UK))
 val state=actions.draft?:remember{JournalDraftState()}
 var editing by state.editing;var selected by state.selected;var deleting by remember{mutableStateOf<JournalEntry?>(null)};var expanded by remember{mutableStateOf<String?>(null)};var readingInk by remember{mutableStateOf<JournalEntry?>(null)}
 LaunchedEffect(completed){if(state.observedCompleted!=null&&state.observedCompleted!=completed){editing=false;state.writing.value=false;deleting=null};state.observedCompleted=completed}
 val groups=data.journal.sortedWith(compareByDescending<JournalEntry>{it.date}.thenByDescending{it.created_at}).groupBy{it.date}
 Column(verticalArrangement=Arrangement.spacedBy(12.dp)){
  Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Text(t("Diary","Дневник"),style=MaterialTheme.typography.headlineSmall);OutlinedIconButton(onClick={state.begin(null)},enabled=!busy&&!editing,modifier=Modifier.size(44.dp).testTag("new-journal")){Icon(painterResource(android.R.drawable.ic_input_add),t("New diary entry","Новая запись дневника"))}}
  (groups.keys+today).distinct().sortedDescending().forEach{date->
   Text((if(date==today)t("Today · ","Сегодня · ") else "")+day(date),style=MaterialTheme.typography.labelMedium,color=MaterialTheme.colorScheme.primary)
   if(editing&&(selected?.date?:today)==date)key(selected?.id,selected?.revision){JournalEditor(member,data,selected,busy,actions.save,{editing=false},state)}
   if(groups[date].isNullOrEmpty()&&!(editing&&date==today)){Text(t("No entry for today yet.","Сегодня ещё нет записи."),style=MaterialTheme.typography.bodySmall);TextButton(onClick={state.begin(null)},enabled=!busy&&!editing){Text(t("Write something","Записать мысль"))}}
   groups[date].orEmpty().filter{!editing||it.id!=selected?.id}.forEach{e->
    var menu by remember(e.id){mutableStateOf(false)}
    Row(Modifier.fillMaxWidth()){
     TextButton(onClick={expanded=if(expanded==e.id)null else e.id},modifier=Modifier.weight(1f)){Column(Modifier.fillMaxWidth()){Text(e.title,style=MaterialTheme.typography.titleMedium);if(e.author_id!=member.id)Text(data.participants.find{it.id==e.author_id}?.display_name?:"—",style=MaterialTheme.typography.labelSmall)}}
     if(e.author_id==member.id)Box{IconButton(onClick={menu=true}){Icon(painterResource(android.R.drawable.ic_menu_more),t("Entry actions","Действия записи"))};DropdownMenu(menu,{menu=false}){DropdownMenuItem(text={Text(t("Edit","Изменить"))},onClick={menu=false;state.begin(e)},enabled=!busy&&!editing);DropdownMenuItem(text={Text(t("Delete","Удалить"))},onClick={menu=false;deleting=e},enabled=!busy)}}
    }
    Text(e.text.orEmpty(),style=MaterialTheme.typography.bodyMedium,maxLines=if(expanded==e.id)Int.MAX_VALUE else 2,modifier=Modifier.testTag("journal-text-${e.id}"))
    if(!e.handwriting?.strokes.isNullOrEmpty())TextButton(onClick={readingInk=e}){Text(t("Open handwriting","Открыть рукопись"))}
    HorizontalDivider(color=MaterialTheme.colorScheme.outline.copy(alpha=.3f))
   }
  }
 }
 readingInk?.let{e->NativeJournalInk(e.title,e.date,e.handwriting,busy,ru,true,{}, {},{readingInk=null})}
 deleting?.let{e->AlertDialog(onDismissRequest={if(!busy)deleting=null},title={Text(t("Delete entry?","Удалить запись?"))},text={Text(e.title)},confirmButton={TextButton(onClick={actions.delete(e)},enabled=!busy,modifier=Modifier.testTag("confirm-journal-delete")){Text(t("Delete","Удалить"))}},dismissButton={TextButton(onClick={deleting=null},enabled=!busy){Text(t("Cancel","Отмена"))}})}
}

@Composable private fun JournalEditor(member:Member,data:WorkspaceState,entry:JournalEntry?,busy:Boolean,save:(JournalEntry?,JournalContent,Boolean)->Unit,cancel:()->Unit,state:JournalDraftState){
 val ru=member.language=="ru"
 fun t(en:String,local:String)=if(ru)local else en
 val date=entry?.date?:LocalDate.now(ZoneId.of(member.timezone)).toString()
 var title by state.title;var text by state.text;var ink by state.ink
 var visibility by state.visibility;var readers by state.readers;var published by state.published;var refresh by state.refresh
 val textFocus=remember{FocusRequester()}
 val keyboardController=LocalSoftwareKeyboardController.current
 var requestKeyboard by remember{mutableStateOf(false)}
 var writing by state.writing;var access by remember{mutableStateOf(false)};var discard by remember{mutableStateOf(false)}
 LaunchedEffect(writing,requestKeyboard){if(!writing&&requestKeyboard){textFocus.requestFocus();keyboardController?.show();requestKeyboard=false}}
 val dirty=title!=(entry?.title?:"")||text!=(entry?.text?:"")||ink!=entry?.handwriting||visibility!=(entry?.visibility?:"private")||readers!=(entry?.reader_ids?:emptyList<String>())||published!=(entry?.published?:false)||refresh
 val valid=text.isNotBlank()||!ink?.strokes.isNullOrEmpty()
 fun persist(){if(valid)save(entry,JournalContent(date=date,title=title.ifBlank{t("Entry · ","Запись · ")+date},text=text,handwriting=ink,mood=entry?.mood,tags=entry?.tags?:emptyList(),visibility=visibility,published=published,reader_ids=if(visibility=="private")emptyList()else readers),refresh)}
 OutlinedCard(Modifier.fillMaxWidth()){Column(Modifier.padding(12.dp),verticalArrangement=Arrangement.spacedBy(8.dp)){
  OutlinedTextField(title,{if(it.length<=200)title=it},placeholder={Text(t("Entry title","Название записи"))},enabled=!busy,modifier=Modifier.fillMaxWidth().testTag("journal-title"),singleLine=true)
  OutlinedTextField(text,{if(it.length<=100000)text=it},placeholder={Text(t("What would you like to remember?","Что хочется запомнить?"))},enabled=!busy,modifier=Modifier.focusRequester(textFocus).fillMaxWidth().testTag("journal-text"),minLines=4,maxLines=10)
  Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){OutlinedIconButton(onClick={writing=true},enabled=!busy,modifier=Modifier.size(44.dp)){Icon(painterResource(android.R.drawable.ic_menu_edit),t("Write by hand","Писать от руки"))};TextButton(onClick={access=true},enabled=!busy){Text(if(visibility=="private")t("Only me","Только мне")else t("Readers","Читатели"))};OutlinedIconButton(onClick={persist()},enabled=!busy&&valid,modifier=Modifier.size(44.dp).testTag("save-journal")){Icon(painterResource(android.R.drawable.ic_menu_save),t("Save diary entry","Сохранить запись дневника"))};IconButton(onClick={if(dirty)discard=true else cancel()},enabled=!busy){Icon(painterResource(android.R.drawable.ic_menu_close_clear_cancel),t("Close editor","Закрыть редактор"))}}
  if(!ink?.strokes.isNullOrEmpty())Text(t("Handwriting is included in this entry.","Рукопись сохранится вместе с записью."),style=MaterialTheme.typography.bodySmall)
 }}
 if(writing)NativeJournalInk(title.ifBlank{t("Today’s entry","Запись за сегодня")},date,ink,busy,ru,false,{ink=it},{persist()},{writing=false},keyboard={writing=false;requestKeyboard=true})
 if(discard)AlertDialog(onDismissRequest={discard=false},title={Text(t("Discard changes?","Не сохранять изменения?"))},text={Text(t("Unsaved text and handwriting will be lost.","Несохранённые текст и рукопись будут потеряны."))},confirmButton={TextButton(onClick=cancel){Text(t("Discard","Не сохранять"))}},dismissButton={TextButton(onClick={discard=false}){Text(t("Cancel","Отмена"))}})
 if(access)AlertDialog(onDismissRequest={access=false},title={Text(t("Entry access","Доступ к записи"))},text={Column(Modifier.verticalScroll(rememberScrollState())){
  M4Choice(t("Who can read","Кто может читать"),visibility,listOf("private" to t("Only me","Только мне"),"selected" to t("Selected readers","Выбранные читатели"),"all_current_members" to t("Current members","Текущие участники")),busy){visibility=it}
  val readerOptions=data.participants+readers.filter{id->data.participants.none{it.id==id}}.map{Participant(id=it,display_name=it,profile_labels=emptyList())}
  if(visibility=="selected")readerOptions.filter{it.id!=member.id}.forEach{p->Row{Checkbox(p.id in readers,{checked->readers=if(checked)readers+p.id else readers-p.id},enabled=!busy);Text(p.display_name)}}
  if(visibility!="private")Row{Checkbox(published,{published=it},enabled=!busy,modifier=Modifier.testTag("journal-published"));Text(t("Allow reading after saving","Разрешить чтение после сохранения"))}
  if(visibility=="all_current_members"){Text(t("Future members are not added automatically.","Будущие участники не добавляются автоматически."),style=MaterialTheme.typography.bodySmall);if(entry!=null)Row{Checkbox(refresh,{refresh=it},enabled=!busy);Text(t("Update member list explicitly","Обновить список участников"))}}
 }},confirmButton={TextButton(onClick={access=false}){Text(t("Done","Готово"))}})
}
