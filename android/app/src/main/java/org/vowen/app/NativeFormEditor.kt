package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import java.util.UUID

@Composable
fun NativeFormEditor(initial:FormSchema?,ru:Boolean,busy:Boolean,onSave:(FormSchema)->Unit,onCancel:()->Unit,identity:String?=null) {
 fun question()=FormQuestion(id="q_"+UUID.randomUUID().toString().replace("-",""),kind="short_text",label="",required=false,options=emptyList())
 var schema by remember(initial,identity) {mutableStateOf(initial?:FormSchema(title="",questions=listOf(question())))}
 var kindIndex by remember {mutableStateOf<Int?>(null)}
 val kinds=listOf("short_text","long_text","number","date","boolean","single_choice","multiple_choice","scale","rating","acknowledgement")
 fun update(index:Int,q:FormQuestion){schema=schema.copy(questions=schema.questions.mapIndexed {i,old->if(i==index)q else old})}
 Column {
  OutlinedTextField(schema.title,{schema=schema.copy(title=it)},label={Text(if(ru)"Название анкеты" else "Form title")},modifier=Modifier.testTag("native-form-title"))
  OutlinedTextField(schema.description?:"",{schema=schema.copy(description=it)},label={Text(if(ru)"Описание" else "Description")})
  Row {Switch(checked=schema.kind=="survey",onCheckedChange={schema=schema.copy(kind=if(it)"survey" else "questionnaire")});Text("Survey / Опрос")}
  schema.questions.forEachIndexed {i,q->
   OutlinedTextField(q.label,{update(i,q.copy(label=it))},label={Text("${if(ru)"Вопрос" else "Question"} ${i+1}")},modifier=Modifier.testTag("native-question-$i"))
   TextButton(onClick={kindIndex=i}) {Text(q.kind)}
   Row {Checkbox(checked=q.required==true,onCheckedChange={update(i,q.copy(required=it))});Text(if(ru)"Обязательный" else "Required")}
   if(q.kind.contains("choice"))OutlinedTextField(q.options?.joinToString("\n"){it.label}?:"",{text->update(i,q.copy(options=text.split('\n').mapIndexed {n,label->FormOption(id=q.options?.getOrNull(n)?.id?:"o$n",label=label)}))},label={Text(if(ru)"Варианты: один на строку" else "Options: one per line")})
   if(q.kind in listOf("scale","rating")) {
    OutlinedTextField((q.minimum?:1.0).toString(),{it.toDoubleOrNull()?.let {n->update(i,q.copy(minimum=n))}},label={Text("Min")})
    OutlinedTextField((q.maximum?:5.0).toString(),{it.toDoubleOrNull()?.let {n->update(i,q.copy(maximum=n))}},label={Text("Max")})
   }
   if(q.visibility!=null)Text(if(ru)"Условия сохранены. Изменяйте их в Mini App." else "Existing conditions are preserved. Edit conditions in Mini App.")
   TextButton(onClick={schema=schema.copy(questions=schema.questions.filterIndexed {j,_->i!=j})},enabled=schema.questions.size>1) {Text(if(ru)"Удалить вопрос" else "Remove question")}
  }
  VowenActionButton(onClick={schema=schema.copy(questions=schema.questions+question())},enabled=schema.questions.size<100) {Text(if(ru)"Добавить вопрос" else "Add question")}
  VowenActionButton(onClick={onSave(schema)},enabled=!busy,modifier=Modifier.testTag("native-form-save")) {Text(if(ru)"Сохранить анкету" else "Save form")}
  TextButton(onClick=onCancel) {Text(if(ru)"Отмена" else "Cancel")}
 }
 kindIndex?.let {index->AlertDialog(onDismissRequest={kindIndex=null},title={Text("Question type / Тип вопроса")},text={Column {kinds.forEach {kind->TextButton(onClick={val q=schema.questions[index];update(index,q.copy(kind=kind,options=if(kind.contains("choice"))listOf(FormOption("o1","Option 1"),FormOption("o2","Option 2")) else emptyList()));kindIndex=null}){Text(kind)}}}},confirmButton={})}
}
