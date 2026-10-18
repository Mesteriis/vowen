package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier

/** Copy exact visible conditions into the rule's consented version; never trigger execution. */
@Composable fun NativePunishmentPicker(records:List<DisciplineRecord>,value:String,busy:Boolean,ru:Boolean,change:(String)->Unit){
 var open by remember{mutableStateOf(false)}
 val choices=records.mapNotNull{record->record.versions.find{it.id==record.version_id}}
 val selected=choices.find{it.conditions==value}
 Column{
  Text(if(ru)"Наказание" else "Punishment",style=MaterialTheme.typography.labelMedium)
  Box{
   OutlinedButton(onClick={open=true},enabled=!busy,modifier=Modifier.fillMaxWidth()){Text(selected?.description?:if(value.isBlank()){if(ru)"Без наказания" else "No punishment"}else{if(ru)"Сохранённые условия наказания" else "Saved punishment conditions"})}
   DropdownMenu(open,{open=false}){
    DropdownMenuItem(text={Text(if(ru)"Без наказания" else "No punishment")},onClick={change("");open=false})
    choices.forEach{item->DropdownMenuItem(text={Text(item.description)},onClick={change(item.conditions);open=false})}
   }
  }
  if(value.isNotBlank())Text(value,style=MaterialTheme.typography.bodySmall)
  if(choices.isEmpty())Text(if(ru)"Создайте запись в разделе «Наказания»." else "Create a record in Punishments.",style=MaterialTheme.typography.bodySmall)
  Text(if(ru)"Выбор сохраняет условия и не запускает наказание." else "Selection saves conditions and does not start a punishment.",style=MaterialTheme.typography.labelSmall)
 }
}
