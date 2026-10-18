package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

fun changeRequestLabel(kind:String,ru:Boolean):String = when(kind) {
 "ritual_skip" -> if(ru)"Пропуск ритуала" else "Skip request"
 "ritual_pause" -> if(ru)"Пауза ритуала" else "Pause request"
 "rule_add" -> if(ru)"Добавление правила" else "New rule proposal"
 "rule_edit" -> if(ru)"Изменение правила" else "Rule change proposal"
 "rule_delete" -> if(ru)"Удаление правила" else "Rule removal request"
 "pending" -> if(ru)"На согласовании" else "Pending"
 "approved" -> if(ru)"Одобрено" else "Approved"
 "rejected" -> if(ru)"Отклонено" else "Rejected"
 "withdrawn" -> if(ru)"Отозвано" else "Withdrawn"
 else -> kind
}

@Composable fun NativeChangeRequests(member:Member,data:WorkspaceState,domain:String,busy:Boolean,completed:Int,decision:((ChangeRequestView,String,String)->Unit)?,relationId:String?=null) {
 val ru=member.language=="ru"
 var history by remember {mutableStateOf(false)}
 var selected by remember {mutableStateOf<ChangeRequestView?>(null)}
 var comment by remember {mutableStateOf("")}
 LaunchedEffect(completed,relationId){selected=null}
 val rows=data.changeRequests.filter{it.kind.startsWith(domain+"_")&&(relationId==null||it.relation_id==relationId)}
 if(rows.isNotEmpty()) Column(Modifier.widthIn(max=560.dp)) {
  Row {Text(if(ru)"Заявки · ${rows.count{it.status=="pending"}}" else "Requests · ${rows.count{it.status=="pending"}}",style=MaterialTheme.typography.titleMedium);TextButton(onClick={history=!history}){Text(if(ru)"История" else "History")}}
  rows.filter{history||it.status=="pending"}.forEach {row->OutlinedCard(Modifier.fillMaxWidth().padding(vertical=4.dp)) {
   TextButton(onClick={selected=row;comment=""},modifier=Modifier.fillMaxWidth()) {Column(Modifier.fillMaxWidth()){Text(row.title?.takeIf{it.isNotBlank()}?:changeRequestLabel(row.kind,ru));Text((data.participants.find{it.id==row.requester_id}?.display_name?:"—")+" · "+changeRequestLabel(row.status,ru),style=MaterialTheme.typography.bodySmall)}}
  }}
 }
 selected?.let {row->AlertDialog(onDismissRequest={if(!busy)selected=null},title={Text(changeRequestLabel(row.kind,ru))},text={Column(Modifier.verticalScroll(rememberScrollState())){
  Text(changeRequestLabel(row.status,ru));Text(row.reason)
  row.content?.let{Text(it.title);Text(it.description);if(!it.discipline.isNullOrBlank())Text(it.discipline)}
  if(row.comment.isNotBlank())Text(row.comment)
  Text(row.created_at,style=MaterialTheme.typography.bodySmall)
  row.decided_at?.let{Text(it,style=MaterialTheme.typography.bodySmall)}
  if(row.status=="pending")OutlinedTextField(comment,{if(it.length<=10000)comment=it},label={Text(if(ru)"Комментарий" else "Comment")},enabled=!busy)
 }},confirmButton={if(row.status=="pending"&&row.approver_id==member.id&&decision!=null)TextButton(onClick={decision(row,"approve",comment)},enabled=!busy&&!member.paused){Text(if(ru)"Одобрить" else "Approve")}},dismissButton={Row{
  if(row.status=="pending"&&decision!=null)TextButton(onClick={decision(row,if(row.requester_id==member.id)"withdraw" else "reject",comment)},enabled=!busy&&(row.requester_id==member.id||!member.paused)){Text(if(row.requester_id==member.id){if(ru)"Отозвать" else "Withdraw"}else{if(ru)"Отклонить" else "Reject"})}
  TextButton(onClick={selected=null},enabled=!busy){Text(if(ru)"Закрыть" else "Close")}
 }})}
}

@Composable fun NativeChangeRequestEditor(draft:ChangeRequestCreate,busy:Boolean,ru:Boolean,save:(ChangeRequestCreate)->Unit,cancel:()->Unit,punishments:List<DisciplineRecord> = emptyList()) {
 var reason by remember(draft.idempotency_key){mutableStateOf("")}
 var title by remember(draft.idempotency_key){mutableStateOf(draft.content?.title?:"")}
 var description by remember(draft.idempotency_key){mutableStateOf(draft.content?.description?:"")}
 var discipline by remember(draft.idempotency_key){mutableStateOf(draft.content?.discipline?:"")}
 val contentRequired=draft.kind in listOf("rule_add","rule_edit")
 if(contentRequired){RuleTaskDialog(changeRequestLabel(draft.kind,ru),busy,cancel){
  OutlinedTextField(title,{if(it.length<=200)title=it},label={Text(if(ru)"Название" else "Title")},enabled=!busy,modifier=Modifier.fillMaxWidth())
  OutlinedTextField(description,{if(it.length<=10000)description=it},label={Text(if(ru)"Описание" else "Description")},enabled=!busy,modifier=Modifier.fillMaxWidth())
  NativePunishmentPicker(punishments,discipline,busy,ru){discipline=it}
  OutlinedTextField(reason,{if(it.length<=10000)reason=it},label={Text(if(ru)"Причина / предложение" else "Reason")},enabled=!busy,modifier=Modifier.fillMaxWidth())
  Text(if(ru)"До решения доминанта ничего не меняется." else "Nothing changes until your dominant approves.",style=MaterialTheme.typography.bodySmall)
  OutlinedButton(onClick={save(draft.copy(reason=reason,content=RuleContent(title=title,description=description,discipline=discipline)))},enabled=!busy&&reason.isNotBlank()&&title.isNotBlank()&&description.isNotBlank()){Text(if(ru)"Отправить" else "Send")}
 }}else{
 AlertDialog(onDismissRequest={if(!busy)cancel()},title={Text(changeRequestLabel(draft.kind,ru))},text={Column(Modifier.verticalScroll(rememberScrollState())) {
  if(contentRequired){
   OutlinedTextField(title,{if(it.length<=200)title=it},label={Text(if(ru)"Название" else "Title")},enabled=!busy)
   OutlinedTextField(description,{if(it.length<=10000)description=it},label={Text(if(ru)"Описание" else "Description")},enabled=!busy)
   NativePunishmentPicker(punishments,discipline,busy,ru){discipline=it}
  }
  OutlinedTextField(reason,{if(it.length<=10000)reason=it},label={Text(if(ru)"Причина / предложение" else "Reason")},enabled=!busy)
  Text(if(ru)"До решения доминанта ничего не меняется." else "Nothing changes until your dominant approves.",style=MaterialTheme.typography.bodySmall)
 }},confirmButton={TextButton(onClick={save(draft.copy(reason=reason,content=if(contentRequired)RuleContent(title=title,description=description,discipline=discipline) else null))},enabled=!busy&&reason.isNotBlank()&&(!contentRequired||(title.isNotBlank()&&description.isNotBlank()))){Text(if(ru)"Отправить" else "Send")}},dismissButton={TextButton(onClick=cancel,enabled=!busy){Text(if(ru)"Отмена" else "Cancel")}})
 }
}
