package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString

/** Commands use authenticated server services; reader selections never become local ACLs. */
data class FormActions(
 val refresh:()->Unit,
 val save:(FormTemplate?,FormSchema)->Unit,
 val publish:(FormTemplate)->Unit,
 val invite:(FormTemplate,FormInvitationCreate)->Unit,
 val draft:(String,Map<String,kotlinx.serialization.json.JsonElement>)->Unit,
 val submit:(String,FormSubmit)->Unit,
 val delete:(String)->Unit
)

@Composable
fun NativeFormsScreen(member:Member,data:WorkspaceState,busy:Boolean,completed:Int,link:String?,actions:FormActions) {
 val ru=member.language=="ru"
 var editor by remember {mutableStateOf(false)}
 var editing by remember {mutableStateOf<FormTemplate?>(null)}
 var inviting by remember {mutableStateOf<FormTemplate?>(null)}
 var filling by remember {mutableStateOf<FormAccess?>(null)}
 var deleting by remember {mutableStateOf<FormResult?>(null)}
 var recipient by remember {mutableStateOf<String?>(null)}
 var readers by remember {mutableStateOf<List<String>>(emptyList())}
 val clipboard=LocalClipboardManager.current
 LaunchedEffect(completed){editor=false;editing=null;filling=null;deleting=null}
 Column {
  Text(if(ru)"Анкеты" else "Forms",style=MaterialTheme.typography.headlineMedium)
  Button(onClick={editor=true;editing=null}) {Text(if(ru)"Новая анкета" else "New form")}
  TextButton(onClick=actions.refresh,enabled=!busy) {Text(if(ru)"Обновить анкеты" else "Refresh forms")}
  if(editor)NativeFormEditor(editing?.schema_body,ru,busy,{actions.save(editing,it)},{editor=false})
  data.forms.forEach {f->
   Text(f.schema_body.title+" · "+f.status)
   TextButton(onClick={editing=f;editor=true}) {Text(if(f.status=="draft")if(ru)"Редактировать" else "Edit" else if(ru)"Новая версия" else "New version")}
   if(f.status=="draft")Button(onClick={actions.publish(f)},enabled=!busy) {Text(if(ru)"Опубликовать" else "Publish")}
   if(f.status=="published")Button(onClick={inviting=f;recipient=null;readers=emptyList()},enabled=!busy) {Text(if(ru)"Пригласить" else "Invite")}
  }
  inviting?.let {f->
   Text(if(ru)"Адресат и читатели" else "Recipient and readers")
   TextButton(onClick={recipient=null}){Text((if(recipient==null)"✓ " else "")+if(ru)"Внешний гость" else "External guest")}
   data.participants.forEach {p->
    TextButton(onClick={recipient=p.id}){Text((if(recipient==p.id)"✓ " else "")+p.display_name)}
    Row {Checkbox(checked=p.id in readers,onCheckedChange={checked->readers=if(checked)readers+p.id else readers-p.id});Text((if(ru)"Читатель: " else "Reader: ")+p.display_name)}
   }
   Text(if(ru)"Приглашение: 7 дней. Хранение: 30 дней. Ссылка секретная." else "Invitation: 7 days. Retention: 30 days. The link is secret.")
   Button(onClick={actions.invite(f,FormInvitationCreate(reader_ids=readers,recipient_user_id=recipient))},enabled=!busy) {Text(if(ru)"Создать приглашение" else "Create invitation")}
  }
  link?.let {
   OutlinedTextField(value=it,onValueChange={},readOnly=true,label={Text(if(ru)"Ссылка приглашения" else "Invitation link")},modifier=Modifier.fillMaxWidth())
   TextButton(onClick={clipboard.setText(AnnotatedString(it))}){Text(if(ru)"Копировать секретную ссылку" else "Copy secret link")}
  }
  Text(if(ru)"Мне назначены" else "Assigned to me")
  data.formInvitations.forEach {a->Text(a.schema_body.title+" · "+a.status);if(a.status=="draft")Button(onClick={filling=a}){Text(if(ru)"Заполнить" else "Fill form")}}
  filling?.let {a->
   Text(a.schema_body.title)
   Text((if(ru)"Читатели: " else "Results readers: ")+a.readers.joinToString {it.display_name})
   Text((if(ru)"Хранение до: " else "Retained until: ")+a.retention_until)
   key(a.id){NativeFormRunner(a.schema_body,a.answers,ru,busy,false,{actions.draft(a.id,it)},{actions.submit(a.id,it)})}
  }
  Text(if(ru)"Доступные ответы" else "Available responses")
  data.formResults.forEach {r->
   Text(r.schema_body.title)
   r.schema_body.questions.filter {r.answers.containsKey(it.id)}.forEach {q->Text(q.label+": "+r.answers[q.id])}
   if(r.can_delete==true)TextButton(onClick={deleting=r}){Text(if(ru)"Удалить свой ответ" else "Delete own response")}
  }
 }
 deleting?.let {r->AlertDialog(onDismissRequest={deleting=null},title={Text(if(ru)"Удалить ответ?" else "Delete response?")},text={Text(if(ru)"Тело ответа будет удалено, доступ читателей отозван." else "The body will be deleted and reader access revoked.")},confirmButton={Button(onClick={actions.delete(r.id)},enabled=!busy){Text(if(ru)"Подтвердить удаление" else "Confirm deletion")}},dismissButton={TextButton(onClick={deleting=null}){Text(if(ru)"Отмена" else "Cancel")}})}
}
