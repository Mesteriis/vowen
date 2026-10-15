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
 val delete:(String)->Unit,
 val archive:((FormTemplate)->Unit)?=null,
 val management:((FormTemplate,(List<FormInvitation>)->Unit)->Unit)?=null,
 val revoke:((FormInvitation)->Unit)?=null,
 val removeReader:((FormInvitation,String)->Unit)?=null
)

@Composable
fun NativeFormsScreen(member:Member,data:WorkspaceState,busy:Boolean,completed:Int,link:String?,actions:FormActions) {
 val ru=member.language=="ru"
 var editor by remember {mutableStateOf(false)}
 var editing by remember {mutableStateOf<FormTemplate?>(null)}
 var inviting by remember {mutableStateOf<FormTemplate?>(null)}
 var filling by remember {mutableStateOf<FormAccess?>(null)}
 var deleting by remember {mutableStateOf<FormResult?>(null)}
 var managed by remember {mutableStateOf<FormTemplate?>(null)}
 var invitations by remember {mutableStateOf(emptyList<FormInvitation>())}
 var days by remember {mutableStateOf("7")}
 var retention by remember {mutableStateOf("90")}
 var deliver by remember {mutableStateOf(false)}
 var contact by remember {mutableStateOf("")}
 var recipient by remember {mutableStateOf<String?>(null)}
 var readers by remember {mutableStateOf<List<String>>(emptyList())}
 val clipboard=LocalClipboardManager.current
 LaunchedEffect(completed){editor=false;editing=null;filling=null;deleting=null}
 Column {
  Text(if(ru)"Анкеты" else "Forms",style=MaterialTheme.typography.headlineMedium)
  VowenActionButton(onClick={editor=true;editing=null}) {Text(if(ru)"Новая анкета" else "New form")}
  TextButton(onClick=actions.refresh,enabled=!busy) {Text(if(ru)"Обновить анкеты" else "Refresh forms")}
  if(editor)NativeFormEditor(editing?.schema_body,ru,busy,{actions.save(editing,it)},{editor=false},identity=editing?.version_id?:"new")
  LaunchedEffect(completed){managed?.let{f->actions.management?.invoke(f){invitations=it}}}
  data.forms.forEach {f->
   Text(f.schema_body.title+" · "+f.status)
   TextButton(onClick={editing=f;editor=true}) {Text(if(f.status=="draft")if(ru)"Редактировать" else "Edit" else if(ru)"Новая версия" else "New version")}
   if(f.status=="draft")VowenActionButton(onClick={actions.publish(f)},enabled=!busy) {Text(if(ru)"Опубликовать" else "Publish")}
   if(f.status!="archived")actions.archive?.let{archive->TextButton(onClick={archive(f)},enabled=!busy){Text(if(ru)"Архивировать анкету" else "Archive form")}}
   actions.management?.let{load->TextButton(onClick={load(f){invitations=it;managed=f}},enabled=!busy){Text(if(ru)"Управлять приглашениями" else "Manage invitations")}}
   if(f.status=="published")VowenActionButton(onClick={inviting=f;recipient=null;readers=emptyList()},enabled=!busy) {Text(if(ru)"Пригласить" else "Invite")}
  }
  inviting?.let {f->
   Text(if(ru)"Адресат и читатели" else "Recipient and readers")
   TextButton(onClick={recipient=null}){Text((if(recipient==null)"✓ " else "")+if(ru)"Внешний гость" else "External guest")}
   data.participants.forEach {p->
    TextButton(onClick={recipient=p.id}){Text((if(recipient==p.id)"✓ " else "")+p.display_name)}
    Row {Checkbox(checked=p.id in readers,onCheckedChange={checked->readers=if(checked)readers+p.id else readers-p.id});Text((if(ru)"Читатель: " else "Reader: ")+p.display_name)}
   }
   OutlinedTextField(days,{days=it},label={Text(if(ru)"Срок приглашения, дней" else "Invitation days")},enabled=!busy)
   OutlinedTextField(retention,{retention=it},label={Text(if(ru)"Хранение ответа, дней" else "Retention days")},enabled=!busy)
   Row{Checkbox(deliver,{deliver=it},enabled=!busy);Text(if(ru)"Попробовать доставку в Telegram" else "Try Telegram delivery")}
   if(deliver&&recipient==null)OutlinedTextField(contact,{contact=it},label={Text("Telegram contact ID")},enabled=!busy)
   Text(if(ru)"Ссылка секретная; первый обладатель может активировать её. Это не подтверждение личности." else "The link is secret; its first holder can activate it. It does not verify identity.")
   VowenActionButton(onClick={actions.invite(f,FormInvitationCreate(reader_ids=readers,recipient_user_id=recipient,ttl_days=days.toInt(),retention_days=retention.toInt(),deliver=deliver,contact_telegram_id=if(deliver&&recipient==null)contact.toLongOrNull() else null))},enabled=!busy&&days.toIntOrNull() in 1..7&&retention.toIntOrNull() in 1..365&&(!deliver||recipient!=null||contact.toLongOrNull()?.let{it>0}==true)) {Text(if(ru)"Создать приглашение" else "Create invitation")}
  }
  managed?.let {f->
   Text(f.schema_body.title+" · "+if(ru)"Приглашения" else "Invitations")
   if(invitations.isEmpty())Text(if(ru)"Нет приглашений" else "No invitations")
   invitations.forEach{i->
    Text("${i.id} · ${i.delivery_status} · ${i.expires_at}")
    actions.revoke?.let{revoke->TextButton(onClick={revoke(i)},enabled=!busy&&!i.revoked){Text(if(ru)"Отозвать приглашение" else "Revoke invitation")}}
    actions.removeReader?.let{remove->M4Choice(if(ru)"Удалить читателя" else "Remove reader","",data.participants.map{it.id to it.display_name},busy){remove(i,it)}}
   }
  }
  link?.let {
   OutlinedTextField(value=it,onValueChange={},readOnly=true,label={Text(if(ru)"Ссылка приглашения" else "Invitation link")},modifier=Modifier.fillMaxWidth())
   TextButton(onClick={clipboard.setText(AnnotatedString(it))}){Text(if(ru)"Копировать секретную ссылку" else "Copy secret link")}
  }
  Text(if(ru)"Мне назначены" else "Assigned to me")
  data.formInvitations.forEach {a->Text(a.schema_body.title+" · "+a.status);if(a.status=="draft")VowenActionButton(onClick={filling=a}){Text(if(ru)"Заполнить" else "Fill form")}}
  filling?.let {a->
   Text(a.schema_body.title)
   Text((if(ru)"Читатели: " else "Results readers: ")+a.readers.joinToString {it.display_name})
   Text((if(ru)"Хранение до: " else "Retained until: ")+(a.retention_until?:"${a.retention_days} "+if(ru)"дней после отправки" else "days after submission"))
   key(a.id){NativeFormRunner(a.schema_body,a.answers,ru,busy,false,{actions.draft(a.id,it)},{actions.submit(a.id,it)})}
  }
  Text(if(ru)"Доступные ответы" else "Available responses")
  data.formResults.forEach {r->
   Text(r.schema_body.title)
   r.schema_body.questions.filter {r.answers.containsKey(it.id)}.forEach {q->Text(q.label+": "+r.answers[q.id])}
   if(r.can_delete==true)TextButton(onClick={deleting=r}){Text(if(ru)"Удалить свой ответ" else "Delete own response")}
  }
 }
 deleting?.let {r->AlertDialog(onDismissRequest={deleting=null},title={Text(if(ru)"Удалить ответ?" else "Delete response?")},text={Text(if(ru)"Тело ответа будет удалено, доступ читателей отозван." else "The body will be deleted and reader access revoked.")},confirmButton={VowenActionButton(onClick={actions.delete(r.id)},enabled=!busy){Text(if(ru)"Подтвердить удаление" else "Confirm deletion")}},dismissButton={TextButton(onClick={deleting=null}){Text(if(ru)"Отмена" else "Cancel")}})}
}
