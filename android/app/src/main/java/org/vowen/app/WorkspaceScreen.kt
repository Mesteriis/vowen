package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp

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
fun WorkspaceScreen(member:Member,data:WorkspaceState,currentSessionId:String?,busy:Boolean,completed:Int,actions:WorkspaceActions,formActions:FormActions?=null,formLink:String?=null,ruleActions:RuleActions?=null,ritualActions:RitualActions?=null,rewardActions:RewardActions?=null) {
 var tab by remember {mutableIntStateOf(0)}
 val ru=member.language=="ru"
 val tabs=listOf("relations","sessions","profile")+(if(formActions!=null)listOf("forms") else emptyList())+(if(ruleActions!=null)listOf("rules") else emptyList())+(if(ritualActions!=null)listOf("rituals") else emptyList())+(if(rewardActions!=null)listOf("rewards") else emptyList())
 val labels=if(ru)mapOf("relations" to "Отношения","sessions" to "Сессии","profile" to "Профиль","forms" to "Анкеты","rules" to "Правила","rituals" to "Ритуалы","rewards" to "Награды") else mapOf("relations" to "Relations","sessions" to "Sessions","profile" to "Profile","forms" to "Forms","rules" to "Rules","rituals" to "Rituals","rewards" to "Rewards")
 val content:@Composable ()->Unit={
  if(tabs.getOrNull(tab) !in listOf("rituals","rewards"))TextButton(onClick=actions.refresh,enabled=!busy,modifier=Modifier.testTag("workspace-refresh")){Text(if(ru)"Обновить данные" else "Refresh data")}
  when(tabs.getOrNull(tab)){
   "relations"->RelationsScreen(member,data,busy,completed,actions)
   "sessions"->SessionsScreen(member,data.sessions,currentSessionId,busy,completed,actions.revokeSession)
   "profile"->ProfileScreen(member,busy,actions.profile)
   "forms"->formActions?.let{NativeFormsScreen(member,data,busy,completed,formLink,it)}
   "rules"->ruleActions?.let{NativeRulesScreen(member,data,busy,completed,it)}
   "rewards"->rewardActions?.let{NativeRewardsScreen(member,data,busy,it)}
   "rituals"->ritualActions?.let{NativeRitualsScreen(member,data,busy,completed,it)}
  }
 }
 if(LocalConfiguration.current.screenWidthDp>=720){
  Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(24.dp)){
   Column(Modifier.width(156.dp).testTag("expanded-navigation"),verticalArrangement=Arrangement.spacedBy(4.dp)){
    tabs.forEachIndexed{index,name->NavigationDrawerItem(label={Text(labels.getValue(name))},selected=tab==index,onClick={tab=index},modifier=Modifier.testTag("tab-$name"))}
   }
   Column(Modifier.weight(1f)){content()}
  }
 }else{
  Column{
   ScrollableTabRow(selectedTabIndex=tab,edgePadding=0.dp,containerColor=MaterialTheme.colorScheme.background,divider={}){
    tabs.forEachIndexed{index,name->Tab(selected=tab==index,onClick={tab=index},modifier=Modifier.testTag("tab-$name"),text={Text(labels.getValue(name))})}
   }
   content()
  }
 }
}
