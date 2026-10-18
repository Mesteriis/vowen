package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp

data class AdministrationActions(val load:suspend ()->AdministrationView,val change:(String,String,Int)->Unit)

@Composable
fun NativeAdministrationScreen(member:Member,busy:Boolean,completed:Int,actions:AdministrationActions){
 val ru=member.language=="ru"
 var value by remember(member.id){mutableStateOf<AdministrationView?>(null)}
 var error by remember{mutableStateOf(false)}
 var pending by remember{mutableStateOf<Pair<AdministratorMember,String>?>(null)}
 var reload by remember{mutableIntStateOf(0)}
 LaunchedEffect(member.id,member.is_admin,completed,reload){
  value=null;error=false
  if(member.is_admin==true)try{value=actions.load()}catch(e:Exception){if(e is kotlinx.coroutines.CancellationException)throw e;error=true}
 }
 if(member.is_admin!=true){Text(if(ru)"Нужны права администратора." else "Administrator access required.");return}
 Column(verticalArrangement=Arrangement.spacedBy(16.dp)){
  Text(if(ru)"Настройки" else "Settings",style=MaterialTheme.typography.headlineSmall)
  Text(if(ru)"Администраторы" else "Administrators",style=MaterialTheme.typography.titleLarge)
  Text(if(ru)"Назначайте дополнительных администраторов или передайте свои права." else "Appoint more administrators or transfer your role.",style=MaterialTheme.typography.bodySmall)
  TextButton(onClick={reload++},enabled=!busy){Text(if(ru)"Обновить" else "Reload")}
  if(error)Text(if(ru)"Не удалось загрузить участников." else "Could not load members.")
  value?.members?.forEach{person->
   Column(verticalArrangement=Arrangement.spacedBy(8.dp)){
    Text(person.display_name,style=MaterialTheme.typography.titleSmall)
    Text(if(person.is_admin){if(ru)"Администратор" else "Administrator"}else{if(ru)"Участник" else "Member"},style=MaterialTheme.typography.bodySmall)
    if(person.id!=member.id)Row(horizontalArrangement=Arrangement.spacedBy(8.dp)){
     if(!person.is_admin)OutlinedButton(onClick={pending=person to "grant"},enabled=!busy,modifier=Modifier.testTag("admin-grant-${person.id}")){Text(if(ru)"Назначить" else "Appoint")}
     OutlinedButton(onClick={pending=person to "transfer"},enabled=!busy,modifier=Modifier.testTag("admin-transfer-${person.id}")){Text(if(ru)"Передать" else "Transfer")}
    }
    HorizontalDivider()
   }
  }
 }
 pending?.let{(person,action)->AlertDialog(onDismissRequest={if(!busy)pending=null},title={Text(if(action=="transfer"){if(ru)"Передать свои права?" else "Transfer your role?"}else{if(ru)"Назначить администратора?" else "Appoint administrator?"})},text={Column{Text(person.display_name);Text(if(action=="transfer"){if(ru)"Вы потеряете доступ к настройкам пространства." else "You will lose access to space settings."}else{if(ru)"Ваши права администратора сохранятся." else "You will remain an administrator."})}},confirmButton={TextButton(onClick={value?.let{actions.change(person.id,action,it.revision);pending=null}},enabled=!busy){Text(if(ru)"Подтвердить" else "Confirm")}},dismissButton={TextButton(onClick={pending=null},enabled=!busy){Text(if(ru)"Отмена" else "Cancel")}})}
}
