package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch

@Composable fun NativeWikiSections(state:WikiState,ru:Boolean,onClose:()->Unit){
 val scope=rememberCoroutineScope();var uid by remember{mutableStateOf<String?>(null)};var title by remember{mutableStateOf("")};var description by remember{mutableStateOf("")};var parent by remember{mutableStateOf<String?>(null)};var order by remember{mutableStateOf("0")};var version by remember{mutableStateOf<Int?>(null)};val treeVersion=remember{state.tree?.version?:1};var error by remember{mutableStateOf(false)}
 AlertDialog(onDismissRequest={if(!state.busy)onClose()},title={Text(if(ru)"Разделы библиотеки" else "Library sections")},text={Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(12.dp)){
  WikiNativeSelect(if(ru)"Раздел" else "Section",uid?:"",listOf("" to if(ru)"Новый раздел" else "New section")+state.tree?.sections.orEmpty().map{it.uid to it.title},!state.busy){id->val s=state.tree?.sections?.find{it.uid==id};uid=s?.uid;title=s?.title?:"";description=s?.description?:"";parent=s?.parent_uid;version=s?.version;order=(s?.sort_order?:0).toString()}
  OutlinedTextField(title,{title=it.take(160)},label={Text(if(ru)"Название" else "Title")},enabled=!state.busy)
  OutlinedTextField(description,{description=it.take(600)},label={Text(if(ru)"Описание" else "Description")},enabled=!state.busy)
  WikiNativeSelect(if(ru)"Родитель" else "Parent",parent?:"",listOf("" to if(ru)"В корне" else "Root")+state.tree?.sections.orEmpty().filter{it.uid!=uid}.map{it.uid to it.title},!state.busy){parent=it.ifBlank{null}}
  OutlinedTextField(order,{order=it.filter(Char::isDigit).take(7)},label={Text(if(ru)"Порядок" else "Order")},enabled=!state.busy)
  if(error)Text(if(ru)"Не удалось изменить раздел. Проверьте версию, вложенность и содержимое." else "Could not update section. Check version, nesting and contents.",color=MaterialTheme.colorScheme.error)
  if(uid!=null)TextButton(onClick={scope.launch{val ok=state.action{state.api.deleteSection(uid!!,version!!,treeVersion);state.refresh()};if(ok)onClose()else error=true}},enabled=!state.busy){Text(if(ru)"Удалить пустой раздел" else "Delete empty section")}
 }},confirmButton={TextButton(onClick={scope.launch{val ok=state.action{state.tree=state.api.saveSection(uid,WikiSectionSave(title=title,description=description,parent_uid=parent,sort_order=order.toIntOrNull()?:0,expected_version=version,expected_tree_version=treeVersion))};if(ok)onClose()else error=true}},enabled=!state.busy&&title.isNotBlank()&&(order.toIntOrNull()?:-1) in 0..1000000){Text(if(ru)"Сохранить" else "Save")}},dismissButton={TextButton(onClick=onClose,enabled=!state.busy){Text(if(ru)"Закрыть" else "Close")}})
}
