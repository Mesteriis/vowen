package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag

/** Every action is wired to a real member API command by the host ViewModel. */
data class WorkspaceActions(
 val refresh:()->Unit,
 val propose:(RelationProposal)->Unit,
 val relation:(Relation,String)->Unit,
 val change:(Relation,String,List<String>)->Unit,
 val profile:(ProfilePatch)->Unit,
 val revokeSession:(DeviceSession)->Unit
)

@Composable
fun WorkspaceScreen(member:Member,data:WorkspaceState,currentSessionId:String?,busy:Boolean,completed:Int,actions:WorkspaceActions,formActions:FormActions?=null,formLink:String?=null,ruleActions:RuleActions?=null,ritualActions:RitualActions?=null) {
 var tab by remember { mutableIntStateOf(0) }
 val ru=member.language=="ru"
 Column {
  TextButton(onClick=actions.refresh,enabled=!busy,modifier=Modifier.testTag("workspace-refresh")) {Text(if(ru)"Обновить данные" else "Refresh data")}
  Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState())) {
   (listOf("relations" to if(ru)"Отношения" else "Relations","sessions" to if(ru)"Сессии" else "Sessions","profile" to if(ru)"Профиль" else "Profile")+if(formActions!=null)listOf("forms" to if(ru)"Анкеты" else "Forms") else emptyList()) .plus(if(ruleActions!=null)listOf("rules" to if(ru)"Правила" else "Rules") else emptyList()).plus(if(ritualActions!=null)listOf("rituals" to if(ru)"Ритуалы" else "Rituals") else emptyList()).forEachIndexed {index,item->
    TextButton(onClick={tab=index},modifier=Modifier.testTag("tab-${item.first}")) {Text(item.second)}
   }
  }
  when(tab) {
   0 -> RelationsScreen(member,data,busy,completed,actions)
   1 -> SessionsScreen(member,data.sessions,currentSessionId,busy,completed,actions.revokeSession)
   2 -> ProfileScreen(member,busy,actions.profile)
   3 -> if(formActions!=null)NativeFormsScreen(member,data,busy,completed,formLink,formActions) else ruleActions?.let {NativeRulesScreen(member,data,busy,completed,it)}
   4 -> ruleActions?.let {NativeRulesScreen(member,data,busy,completed,it)}
   5 -> ritualActions?.let {NativeRitualsScreen(member,data,busy,completed,it)}
  }
 }
}
