package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.foundation.text.KeyboardOptions
import kotlinx.serialization.json.*
import java.util.UUID

fun formVisible(q:FormQuestion,answers:Map<String,JsonElement>):Boolean {
 fun equal(a:JsonElement?,b:JsonElement?):Boolean {
  val left=(a as? JsonPrimitive)?.takeUnless {it.isString}?.doubleOrNull
  val right=(b as? JsonPrimitive)?.takeUnless {it.isString}?.doubleOrNull
  return if(left!=null&&right!=null)left==right else (a?:JsonNull)==(b?:JsonNull)
 }
 fun matches(c:FormCondition):Boolean {
  val v=answers[c.question_id]
  return when(c.op) {
   "answered" -> v!=null&&v!=JsonNull&&v!=JsonPrimitive("")&&v!=JsonArray(emptyList())
   "equals" -> equal(v,c.value)
   "not_equals" -> !equal(v,c.value)
   "contains" -> if(v is JsonArray)v.contains(c.value) else v is JsonPrimitive&&v.isString&&c.value is JsonPrimitive&&c.value.isString&&v.content.contains(c.value.content)
   else -> false
  }
 }
 val visibility=q.visibility?:return true
 return (visibility.all?:emptyList()).all(::matches)&&((visibility.any?:emptyList()).isEmpty()||(visibility.any?:emptyList()).any(::matches))
}

class NativeFormDraft(initial:Map<String,JsonElement>) {
 val answersState=mutableStateOf(initial)
 val reviewState=mutableStateOf(false)
 val acknowledgedState=mutableStateOf(false)
 val key=UUID.randomUUID().toString()
}

@Composable
fun NativeFormRunner(schema:FormSchema,initial:Map<String,JsonElement>,ru:Boolean,busy:Boolean,guest:Boolean,onSave:(Map<String,JsonElement>)->Unit,onSubmit:(FormSubmit)->Unit,state:NativeFormDraft?=null) {
 val draft=state?:remember(schema) {NativeFormDraft(initial)}
 var answers by draft.answersState
 var review by draft.reviewState
 var acknowledged by draft.acknowledgedState
 val key=draft.key
 val clean=mutableMapOf<String,JsonElement>()
 val questions=schema.questions.filter {q->if(formVisible(q,clean)){answers[q.id]?.let {clean[q.id]=it};true}else false}
 fun update(id:String,value:JsonElement){answers=answers+(id to value)}
 Column {
  Text(schema.description?:"")
  if(!review) {
   questions.forEach {q->
    Text(q.label+if(q.required==true)" *" else "")
    when(q.kind) {
     "boolean" -> Row {
      RadioButton(selected=answers[q.id]==JsonPrimitive(true),onClick={update(q.id,JsonPrimitive(true))},enabled=!busy,modifier=Modifier.testTag("form-answer-${q.id}").semantics {contentDescription=q.label+": Yes"});Text(if(ru)"Да" else "Yes")
      RadioButton(selected=answers[q.id]==JsonPrimitive(false),onClick={update(q.id,JsonPrimitive(false))},enabled=!busy,modifier=Modifier.semantics {contentDescription=q.label+": No"});Text(if(ru)"Нет" else "No")
     }
     "acknowledgement" -> Row {
      Checkbox(checked=(answers[q.id] as? JsonPrimitive)?.booleanOrNull==true,onCheckedChange={update(q.id,JsonPrimitive(it))},enabled=!busy,modifier=Modifier.testTag("form-answer-${q.id}").semantics {contentDescription=q.label});Text(q.label)
     }
     "single_choice" -> (q.options?:emptyList()).forEach {o->Row {
      RadioButton(selected=answers[q.id]==JsonPrimitive(o.id),onClick={update(q.id,JsonPrimitive(o.id))},enabled=!busy,modifier=Modifier.semantics {contentDescription=o.label});Text(o.label)
     }}
     "multiple_choice" -> (q.options?:emptyList()).forEach {o->Row {
      val selected=(answers[q.id] as? JsonArray)?.toList()?:emptyList()
      Checkbox(checked=selected.contains(JsonPrimitive(o.id)),onCheckedChange={checked->update(q.id,JsonArray(if(checked)selected+JsonPrimitive(o.id) else selected-JsonPrimitive(o.id)))},enabled=!busy,modifier=Modifier.semantics {contentDescription=o.label});Text(o.label)
     }}
     else -> {
      var text by remember(schema,q.id) {mutableStateOf((answers[q.id] as? JsonPrimitive)?.content?:"")}
      val numeric=q.kind in listOf("number","scale","rating")
      OutlinedTextField(value=text,onValueChange={text=it;update(q.id,if(numeric)it.toDoubleOrNull()?.let(::JsonPrimitive)?:JsonPrimitive(it) else JsonPrimitive(it))},label={Text(q.label+if(q.kind=="date")" (YYYY-MM-DD)" else "")},enabled=!busy,singleLine=q.kind!="long_text",keyboardOptions=KeyboardOptions(keyboardType=if(numeric)KeyboardType.Decimal else KeyboardType.Text),modifier=Modifier.fillMaxWidth().testTag("form-answer-${q.id}"))
      if(q.kind in listOf("scale","rating"))Text("${q.minimum?:1.0} – ${q.maximum?:5.0}")
     }
    }
   }
   Text(if(ru)"При ошибке ввод остаётся в этом окне; сохранение требует ответа сервера." else "Failed requests keep input in this window; saving requires server confirmation.")
   Button(onClick={onSave(answers)},enabled=!busy) {Text(if(ru)"Сохранить черновик" else "Save draft")}
   Row {
    Checkbox(checked=acknowledged,onCheckedChange={acknowledged=it},enabled=!busy,modifier=Modifier.testTag("form-ack"))
    Text(if(ru) if(guest)"Мне 18 лет или больше; я ознакомился с читателями и хранением" else "Я ознакомился с читателями и хранением" else if(guest)"I am 18 or older and have reviewed readers and retention" else "I have reviewed readers and retention")
   }
   Button(onClick={review=true},enabled=!busy&&acknowledged,modifier=Modifier.testTag("form-review")) {Text(if(ru)"Проверить ответы" else "Review answers")}
  } else {
   Text(if(ru)"Проверьте ответы перед отправкой" else "Review before sending")
   questions.forEach {q->Text(q.label+": "+(answers[q.id]?.toString()?:"—"))}
   Button(onClick={review=false},enabled=!busy) {Text(if(ru)"Изменить" else "Edit answers")}
   Button(onClick={onSubmit(FormSubmit(answers=answers,idempotency_key=key,acknowledged=true))},enabled=!busy,modifier=Modifier.testTag("form-send")) {Text(if(ru)"Отправить ответы" else "Send answers")}
  }
 }
}
