package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties

@Composable fun NativeJournalInk(title:String,date:String,ink:InkDocument?,busy:Boolean,ru:Boolean,readOnly:Boolean=false,change:(InkDocument)->Unit,save:()->Unit,close:()->Unit,keyboard:(()->Unit)?=null){
 var tool by remember{mutableStateOf("pen")};var finger by remember{mutableStateOf(false)};var nib by remember{mutableStateOf(.003)}
 var undo by remember{mutableStateOf(emptyList<InkDocument?>())};var redo by remember{mutableStateOf(emptyList<InkDocument?>())};var limit by remember{mutableStateOf(false)}
 fun update(value:InkDocument){undo=(undo+listOf(ink)).takeLast(40);redo=emptyList();change(value)}
 Dialog(onDismissRequest=close,properties=DialogProperties(usePlatformDefaultWidth=false,decorFitsSystemWindows=false)){
  Surface(Modifier.fillMaxSize()){BoxWithConstraints(Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.safeDrawing)){
   val phone=maxWidth<600.dp
   Column(Modifier.fillMaxSize().padding(horizontal=if(phone)16.dp else 24.dp,vertical=8.dp),verticalArrangement=Arrangement.spacedBy(8.dp)){
    Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){TextButton(onClick=close,enabled=!busy){Icon(painterResource(android.R.drawable.ic_media_previous),if(ru)"Назад" else "Back");Text(if(ru)"Дневник" else "Diary")};Text(date,style=MaterialTheme.typography.labelSmall,modifier=Modifier.padding(top=14.dp));if(!readOnly)OutlinedIconButton(onClick=save,enabled=!busy,modifier=Modifier.size(44.dp)){Icon(painterResource(android.R.drawable.ic_menu_save),if(ru)"Сохранить запись" else "Save entry")}}
    Text(title,style=MaterialTheme.typography.headlineSmall)
    Row(Modifier.fillMaxWidth().weight(1f),horizontalArrangement=Arrangement.spacedBy(8.dp)){
     BoxWithConstraints(Modifier.weight(1f).fillMaxHeight().verticalScroll(rememberScrollState())){AndroidView(factory={JournalInkView(it)},modifier=Modifier.fillMaxWidth().height(maxWidth*1.4f),update={view->view.document=ink;view.tool=tool;view.nib=nib;view.finger=finger;view.readOnly=readOnly||busy;view.changed={update(it)};view.limit={limit=true};view.contentDescription=if(ru)"Рукописная страница. Можно вернуться к текстовому вводу." else "Handwriting page. Text input is also available.";view.invalidate()})}
     if(!phone&&!readOnly)Column{InkTools(tool,{tool=it},undo.isNotEmpty(),redo.isNotEmpty(),{val last=undo.last();undo=undo.dropLast(1);redo=redo+listOf(ink);change(last?:InkDocument(version=1,strokes=emptyList()))},{val last=redo.last();redo=redo.dropLast(1);undo=undo+listOf(ink);change(last?:InkDocument(version=1,strokes=emptyList()))},keyboard?:close,busy,ru)}
    }
    if(phone&&!readOnly)Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.Center){InkTools(tool,{tool=it},undo.isNotEmpty(),redo.isNotEmpty(),{val last=undo.last();undo=undo.dropLast(1);redo=redo+listOf(ink);change(last?:InkDocument(version=1,strokes=emptyList()))},{val last=redo.last();redo=redo.dropLast(1);undo=undo+listOf(ink);change(last?:InkDocument(version=1,strokes=emptyList()))},keyboard?:close,busy,ru)}
    if(!readOnly)Row{Checkbox(finger,{finger=it},enabled=!busy);Text(if(ru)"Писать пальцем" else "Draw with finger",style=MaterialTheme.typography.labelSmall,modifier=Modifier.padding(top=16.dp));TextButton(onClick={nib=if(nib==.003).006 else if(nib==.006).002 else .003},enabled=!busy){Text(if(ru)"Толщина" else "Width")}}
    if(limit)Text(if(ru)"Лист заполнен. Сохраните запись и начните новую." else "Page is full. Save and start another entry.",style=MaterialTheme.typography.bodySmall)
   }
  }}
 }
}
@Composable private fun InkTools(tool:String,select:(String)->Unit,canUndo:Boolean,canRedo:Boolean,undo:()->Unit,redo:()->Unit,keyboard:()->Unit,busy:Boolean,ru:Boolean){
 OutlinedIconButton(onClick={select("pen")},enabled=!busy,modifier=Modifier.size(44.dp)){Icon(painterResource(android.R.drawable.ic_menu_edit),if(ru)"Перо" else "Pen",tint=if(tool=="pen")MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface)}
 OutlinedIconButton(onClick={select("eraser")},enabled=!busy,modifier=Modifier.size(44.dp)){Icon(painterResource(android.R.drawable.ic_menu_close_clear_cancel),if(ru)"Ластик" else "Eraser",tint=if(tool=="eraser")MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface)}
 OutlinedIconButton(onClick=undo,enabled=canUndo&&!busy,modifier=Modifier.size(44.dp)){Icon(painterResource(android.R.drawable.ic_media_rew),if(ru)"Отменить штрих" else "Undo")}
 OutlinedIconButton(onClick=redo,enabled=canRedo&&!busy,modifier=Modifier.size(44.dp)){Icon(painterResource(android.R.drawable.ic_media_ff),if(ru)"Вернуть штрих" else "Redo")}
 OutlinedIconButton(onClick=keyboard,enabled=!busy,modifier=Modifier.size(44.dp)){Icon(painterResource(android.R.drawable.ic_menu_revert),if(ru)"К тексту" else "Back to text")}
}
