package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.contentDescription

@Composable
fun ProfileScreen(member:Member,busy:Boolean,onSave:(ProfilePatch)->Unit,general:Boolean?=null) {
 var name by remember(member.id,member.profile_version) {mutableStateOf(member.display_name)}
 var language by remember(member.id,member.profile_version) {mutableStateOf(member.language)}
 var timezone by remember(member.id,member.profile_version) {mutableStateOf(member.timezone)}
 var labels by remember(member.id,member.profile_version) {mutableStateOf(member.profile_labels)}
 val ru=member.language=="ru"
 Column(verticalArrangement=Arrangement.spacedBy(12.dp)) {
  if(general!=true) OutlinedTextField(name,{if(it.length<=100)name=it},label={Text(if(ru)"Отображаемое имя" else "Display name")},enabled=!busy,modifier=Modifier.fillMaxWidth().testTag("profile-name"))
  if(general!=false){
  Text(if(ru)"Язык" else "Language")
  Row {listOf("en" to "English","ru" to "Русский").forEach {(code,title)->
   Row {RadioButton(selected=language==code,onClick={language=code},enabled=!busy);Text(title)}
  }}
  OutlinedTextField(timezone,{if(it.length<=64)timezone=it},label={Text(if(ru)"Часовой пояс IANA" else "IANA timezone")},enabled=!busy,modifier=Modifier.fillMaxWidth().testTag("profile-timezone"))
  }
  if(general!=true){
  Text(if(ru)"Метки профиля не предоставляют полномочий." else "Profile labels do not grant permissions.")
  listOf("dominant","submissive","switch").forEach {label->
   Row {Checkbox(label in labels,{checked->labels=if(checked)labels+label else labels-label},enabled=!busy,modifier=Modifier.testTag("profile-$label").semantics {contentDescription=label});Text(label)}
  }
  }
  VowenActionButton(onClick={onSave(ProfilePatch(expected_version=member.profile_version,display_name=if(general==true)member.display_name else name,language=if(general!=false)language else member.language,timezone=if(general!=false)timezone else member.timezone,profile_labels=if(general==true)member.profile_labels else labels))},enabled=!busy&&name.isNotBlank()&&timezone.isNotBlank(),modifier=Modifier.testTag("profile-save")) {Text(if(ru)"Сохранить изменения" else "Save changes")}
 }
}
