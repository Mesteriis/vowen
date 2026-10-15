package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import kotlinx.coroutines.launch

@Composable
fun NativeGuestScreen(model:GuestViewModel,onClose:()->Unit) {
 var link by model.linkState
 var ru by model.ruState
 var access by model.accessState
 var result by model.resultState
 var api by model.apiState
 var apiOrigin by model.apiOriginState
 var receiptMode by model.receiptModeState
 var receiptLink by model.receiptLinkState
 var busy by model.busyState
 var message by model.messageState
 var confirm by model.confirmState
 val clipboard=LocalClipboardManager.current
 fun run(action:suspend ()->Unit)=model.runAction(action)
 Column {
  Text(if(ru)"Гостевая анкета" else "Guest form",style=MaterialTheme.typography.headlineMedium)
  TextButton(onClick={ru=!ru}){Text(if(ru)"EN" else "RU")}
  Text(if(ru)"Telegram не требуется. Аккаунт не создаётся. Ответ не анонимный; оператор сервера имеет технический доступ." else "No Telegram or account is required. Responses are not anonymous; the server operator has technical access.")
  Text(if(ru)"Гостевой сеанс хранится только в памяти. До закрытия сохраните квитанцию; потерянный черновик открывается через новое приглашение." else "The guest session stays in memory. Save your receipt before closing; a lost draft session requires a new invitation.")
  if(access==null) {
   OutlinedTextField(link,{link=it},label={Text(if(ru)"Секретная ссылка анкеты или квитанции" else "Secret form or receipt link")},enabled=!busy,modifier=Modifier.fillMaxWidth())
   VowenActionButton(onClick={run {
    val parsed=GuestLink.parse(link)
    val transport=api?.takeIf {apiOrigin==parsed.origin}?:GuestApi(parsed.origin).also {api=it;apiOrigin=parsed.origin}
    receiptMode=parsed.receipt
    val a=transport.exchange(parsed.proof,parsed.receipt)
    access=a;link="";model.draftState.value=NativeFormDraft(a.answers)
    if(a.status=="submitted")result=transport.result()
   }},enabled=!busy){Text(if(ru)"Открыть анкету / квитанцию" else "Open form / receipt")}
  }
  Text(message)
  access?.let {a->
   Text(a.schema_body.title)
   Text((if(ru)"Читатели результатов: " else "Results readers: ")+a.readers.joinToString {it.display_name})
   Text((if(ru)"Хранение до: " else "Retained until: ")+(a.retention_until?:"${a.retention_days} "+if(ru)"дней после отправки" else "days after submission"))
   Text(if(ru)"Можно удалить ответ. Резервные копии удаляются по политике хранения. Возраст подтверждается только вами." else "You can delete your response. Backups expire by retention policy. Age is self-confirmed only.")
   if(result==null&&!receiptMode&&a.status=="draft")NativeFormRunner(a.schema_body,a.answers,ru,busy,true,{answers->run {access=api!!.save(answers);message=if(ru)"Черновик сохранён" else "Draft saved"}},{command->run {result=api!!.submit(command)}},state=model.draftState.value)
   result?.let {r->
    Text(if(ru)"Ответ отправлен" else "Response submitted")
    r.schema_body.questions.filter {r.answers.containsKey(it.id)}.forEach {q->Text(q.label+": "+r.answers[q.id])}
    if(!receiptMode)VowenActionButton(onClick={run {receiptLink=api!!.receipt()}},enabled=!busy){Text(if(ru)"Создать квитанцию" else "Create receipt")}
    receiptLink?.let {value->OutlinedTextField(value,{},readOnly=true,label={Text(if(ru)"Ссылка квитанции" else "Receipt link")});TextButton(onClick={clipboard.setText(AnnotatedString(value))}){Text(if(ru)"Копировать квитанцию" else "Copy receipt")}}
    VowenActionButton(onClick={confirm=true},enabled=!busy){Text(if(ru)"Удалить ответ" else "Delete response")}
   }
  }
  TextButton(onClick=onClose,enabled=!busy){Text(if(ru)"Закрыть гостевой сеанс" else "Close guest session")}
 }
 if(confirm)AlertDialog(onDismissRequest={confirm=false},title={Text(if(ru)"Удалить ответ?" else "Delete response?")},confirmButton={VowenActionButton(onClick={run {api!!.delete();access=null;result=null;receiptLink=null;confirm=false;api=null;message=if(ru)"Ответ удалён" else "Response deleted"}},enabled=!busy){Text(if(ru)"Подтвердить удаление" else "Confirm deletion")}},dismissButton={TextButton(onClick={confirm=false}){Text(if(ru)"Отмена" else "Cancel")}})
}
