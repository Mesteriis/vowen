package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.ui.res.painterResource
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
fun WorkspaceScreen(member:Member,data:WorkspaceState,currentSessionId:String?,busy:Boolean,completed:Int,actions:WorkspaceActions,formActions:FormActions?=null,formLink:String?=null,ruleActions:RuleActions?=null,ritualActions:RitualActions?=null,rewardActions:RewardActions?=null,error:String?=null,disciplineActions:DisciplineActions?=null,journalActions:JournalActions?=null,surveyActions:SurveyActions?=null,notificationActions:NotificationActions?=null,onHomeChanged:(Boolean)->Unit={}) {
 var tab by remember {mutableIntStateOf(0)}
 val ru=member.language=="ru"
 var homeTarget by remember {mutableStateOf<String?>(null)}
 val tabs=(if(ritualActions!=null)listOf("home") else emptyList())+listOf("relations","sessions","profile")+(if(formActions!=null)listOf("forms") else emptyList())+(if(ruleActions!=null)listOf("rules") else emptyList())+(if(ritualActions!=null)listOf("rituals") else emptyList())+(if(rewardActions!=null)listOf("rewards") else emptyList())
 val allTabs=tabs+(if(surveyActions!=null)listOf("surveys") else emptyList())+(if(notificationActions!=null)listOf("notifications") else emptyList())+(if(disciplineActions!=null)listOf("discipline") else emptyList())+(if(journalActions!=null)listOf("journal") else emptyList())
 val labels=if(ru)mapOf("home" to "Главная","surveys" to "Повторные анкеты","notifications" to "Уведомления","relations" to "Отношения","sessions" to "Сессии","profile" to "Профиль","forms" to "Анкеты","rules" to "Правила","rituals" to "Ритуалы","rewards" to "Награды","discipline" to "Дисциплина","journal" to "Дневник") else mapOf("home" to "Home","surveys" to "Recurring surveys","notifications" to "Notifications","relations" to "Relations","sessions" to "Sessions","profile" to "Profile","forms" to "Forms","rules" to "Rules","rituals" to "Rituals","rewards" to "Rewards","discipline" to "Discipline","journal" to "Diary")
 LaunchedEffect(tab){onHomeChanged(allTabs.getOrNull(tab) in listOf("home","rituals"))}
 val content:@Composable ()->Unit={
  if(allTabs.getOrNull(tab) !in listOf("home","rituals","rewards"))TextButton(onClick=actions.refresh,enabled=!busy,modifier=Modifier.testTag("workspace-refresh")){Text(if(ru)"Обновить данные" else "Refresh data")}
  when(allTabs.getOrNull(tab)){
   "home"->NativeHomeScreen(member,data,busy,error,actions.refresh,{o->homeTarget=o.id;tab=allTabs.indexOf("rituals")},{name->allTabs.indexOf(name).takeIf{it>=0}?.let{tab=it}})
   "surveys"->surveyActions?.let{NativeSurveysScreen(member,data,busy,completed,it)}
   "notifications"->notificationActions?.let{NativeNotificationScreen(data.notificationSettings,busy,it,ru)}
   "discipline"->disciplineActions?.let{NativeDisciplineScreen(member,data,busy,completed,it)}
   "journal"->journalActions?.let{NativeJournalScreen(member,data,busy,completed,it)}
   "relations"->RelationsScreen(member,data,busy,completed,actions)
   "sessions"->SessionsScreen(member,data.sessions,currentSessionId,busy,completed,actions.revokeSession)
   "profile"->ProfileScreen(member,busy,actions.profile)
   "forms"->formActions?.let{NativeFormsScreen(member,data,busy,completed,formLink,it)}
   "rules"->ruleActions?.let{NativeRulesScreen(member,data,busy,completed,it)}
   "rewards"->rewardActions?.let{NativeRewardsScreen(member,data,busy,it,completed)}
   "rituals"->ritualActions?.let{NativeRitualsScreen(member,data,busy,completed,it,error,homeTarget)}
  }
 }
 if(LocalConfiguration.current.screenWidthDp>=720){
  Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(24.dp)){
   Column(Modifier.width(112.dp).testTag("expanded-navigation"),verticalArrangement=Arrangement.spacedBy(4.dp)){
    allTabs.forEachIndexed{index,name->NavigationDrawerItem(label={Text(labels.getValue(name))},selected=tab==index,onClick={tab=index},modifier=Modifier.testTag("tab-$name"))}
   }
   Column(Modifier.weight(1f).then(if(allTabs.getOrNull(tab) in listOf("home","rituals"))Modifier.verticalScroll(rememberScrollState()) else Modifier)){content()}
  }
 }else if(allTabs.getOrNull(tab) in listOf("home","rituals")){
  var more by remember{mutableStateOf(false)}
  Column(Modifier.fillMaxSize()){
   Column(Modifier.weight(1f).verticalScroll(rememberScrollState())){content()}
   NavigationBar(containerColor=MaterialTheme.colorScheme.background){
    listOf("home","rituals","rules","journal").forEach{name->val index=allTabs.indexOf(name);if(index>=0)NavigationBarItem(selected=allTabs.getOrNull(tab)==name,onClick={homeTarget=null;tab=index},icon={Icon(painterResource(when(name){"home"->android.R.drawable.ic_menu_view;"rituals"->android.R.drawable.ic_menu_agenda;"rules"->android.R.drawable.ic_menu_info_details;else->android.R.drawable.ic_menu_edit}),contentDescription=null,modifier=Modifier.size(20.dp))},label={Text(labels.getValue(name))},modifier=Modifier.testTag("tab-$name"))}
    Box(Modifier.testTag("tab-more")){Row{NavigationBarItem(selected=false,onClick={more=true},icon={Icon(painterResource(android.R.drawable.ic_menu_more),contentDescription=null,modifier=Modifier.size(20.dp))},label={Text(if(ru)"Ещё" else "More")})};DropdownMenu(more,{more=false}){allTabs.filter{it !in listOf("home","rituals","rules","journal")}.forEach{name->DropdownMenuItem(text={Text(labels.getValue(name))},onClick={tab=allTabs.indexOf(name);more=false},modifier=Modifier.testTag("tab-$name"))}}}
   }
  }
 }else{
  Column{
   ScrollableTabRow(selectedTabIndex=tab,edgePadding=0.dp,containerColor=MaterialTheme.colorScheme.background,divider={}){
    allTabs.forEachIndexed{index,name->Tab(selected=tab==index,onClick={tab=index},modifier=Modifier.testTag("tab-$name"),text={Text(labels.getValue(name))})}
   }
   content()
  }
 }
}
