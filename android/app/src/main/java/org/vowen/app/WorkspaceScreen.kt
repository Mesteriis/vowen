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
import kotlinx.coroutines.launch

/** Every action is wired to a real member API command by the host ViewModel. */
data class WorkspaceActions(
 val refresh:()->Unit,
 val propose:(RelationProposal)->Unit,
 val relation:(Relation,String)->Unit,
 val change:(Relation,String,List<String>)->Unit,
 val profile:(ProfilePatch)->Unit,
 val revokeSession:(DeviceSession)->Unit,
 val logout:()->Unit={},
 val participantProfile:ParticipantProfileActions?=null
)

@Composable
fun WorkspaceScreen(member:Member,data:WorkspaceState,currentSessionId:String?,busy:Boolean,completed:Int,actions:WorkspaceActions,formActions:FormActions?=null,formLink:String?=null,ruleActions:RuleActions?=null,ritualActions:RitualActions?=null,rewardActions:RewardActions?=null,error:String?=null,disciplineActions:DisciplineActions?=null,journalActions:JournalActions?=null,surveyActions:SurveyActions?=null,notificationActions:NotificationActions?=null,administrationActions:AdministrationActions?=null,referenceActions:ReferenceActions?=null,onHomeChanged:(Boolean)->Unit={},wikiApi:WikiApi?=null) {
 var tab by remember {mutableIntStateOf(0)}
 val ru=member.language=="ru"
 val wikiScope=rememberCoroutineScope()
 val wikiState=remember(member.id,wikiApi){wikiApi?.let{WikiState(it)}}
 var pendingWikiTab by remember{mutableStateOf<Int?>(null)}
 fun selectTab(target:Int){if(wikiState?.editing==true&&wikiState.busy)return;if(wikiState?.dirty==true){pendingWikiTab=target}else{tab=target}}
 pendingWikiTab?.let{target->AlertDialog(onDismissRequest={pendingWikiTab=null},title={Text(if(ru)"Несохранённые изменения" else "Unsaved changes")},text={Text(if(ru)"Уйти без сохранения?" else "Discard unsaved changes?")},confirmButton={TextButton(onClick={wikiState?.discardDraft();pendingWikiTab=null;tab=target}){Text(if(ru)"Уйти" else "Leave")}},dismissButton={TextButton(onClick={pendingWikiTab=null}){Text(if(ru)"Остаться" else "Stay")}})}
 var accountSection by remember {mutableStateOf("profile")}
 var homeTarget by remember {mutableStateOf<String?>(null)}
 val tabs=(if(ritualActions!=null)listOf("home") else emptyList())+listOf("relations","profile")+(if(formActions!=null)listOf("forms") else emptyList())+(if(ruleActions!=null)listOf("rules") else emptyList())+(if(ritualActions!=null)listOf("rituals") else emptyList())+(if(rewardActions!=null)listOf("rewards") else emptyList())
 val allTabs=tabs+(if(wikiApi!=null)listOf("wiki") else emptyList())+(if(surveyActions!=null)listOf("surveys") else emptyList())+(if(disciplineActions!=null)listOf("discipline") else emptyList())+(if(journalActions!=null)listOf("journal") else emptyList())+(if(member.is_admin==true&&administrationActions!=null)listOf("settings") else emptyList())
 val navigationTabs=allTabs.filter{it!="profile"}
 fun openReferenceWiki(uid:String){val state=wikiState?:return;if(state.dirty||(state.editing&&state.busy))return;state.discardDraft();selectTab(allTabs.indexOf("wiki"));wikiScope.launch{state.openPage(uid)}}
 LaunchedEffect(member.is_admin){if(allTabs.getOrNull(tab)==null)selectTab(allTabs.indexOf("profile"))}
 val labels=if(ru)mapOf("wiki" to "Wiki","settings" to "Настройки","home" to "Главная","surveys" to "Повторные анкеты","notifications" to "Уведомления","relations" to "Отношения","sessions" to "Сессии","profile" to "Профиль","forms" to "Анкеты","rules" to "Правила","rituals" to "Ритуалы","rewards" to "Награды","discipline" to "Наказания","journal" to "Дневник") else mapOf("wiki" to "Wiki","settings" to "Settings","home" to "Home","surveys" to "Recurring surveys","notifications" to "Notifications","relations" to "Relations","sessions" to "Sessions","profile" to "Profile","forms" to "Forms","rules" to "Rules","rituals" to "Rituals","rewards" to "Rewards","discipline" to "Punishments","journal" to "Diary")
 LaunchedEffect(tab){onHomeChanged(allTabs.getOrNull(tab) in listOf("home","rituals","rules","rewards","relations","notifications","profile","settings","wiki"))}
 val content:@Composable ()->Unit={
  if(allTabs.getOrNull(tab) !in listOf("home","rituals","rules","rewards","relations","notifications","profile","settings","wiki"))TextButton(onClick=actions.refresh,enabled=!busy,modifier=Modifier.testTag("workspace-refresh")){Text(if(ru)"Обновить данные" else "Refresh data")}
  if(allTabs.getOrNull(tab)!="home")Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.End){TextButton(onClick={accountSection="profile";selectTab(allTabs.indexOf("profile"))},modifier=Modifier.testTag("profile-avatar")){Text(member.display_name.take(1))}}
  when(allTabs.getOrNull(tab)){
   "wiki"->wikiState?.let{NativeWikiScreen(it,member.is_admin==true,ru)}
   "settings"->administrationActions?.let{NativeSpaceSettingsScreen(member,busy,completed,it,referenceActions,if(wikiState!=null)::openReferenceWiki else null)}
   "home"->NativeHomeScreen(member,data,busy,error,actions.refresh,{o->homeTarget=o.id;selectTab(allTabs.indexOf("rituals"))},{name->val target=if(name in listOf("notifications","sessions")){accountSection=name;"profile"}else name;allTabs.indexOf(target).takeIf{it>=0}?.let{selectTab(it)}})
   "surveys"->surveyActions?.let{NativeSurveysScreen(member,data,busy,completed,it)}
   "notifications"->notificationActions?.let{NativeNotificationScreen(data.notificationSettings,busy,it,ru,member.display_name,actions.refresh)}
   "discipline"->disciplineActions?.let{NativeDisciplineScreen(member,data,busy,completed,it)}
   "journal"->journalActions?.let{NativeJournalScreen(member,data,busy,completed,it)}
   "relations"->RelationsScreen(member,data,busy,completed,actions)
   "sessions"->SessionsScreen(member,data.sessions,currentSessionId,busy,completed,actions.revokeSession)
   "profile"->NativeAccountScreen(member,data,currentSessionId,busy,completed,actions,notificationActions,accountSection)
   "forms"->formActions?.let{NativeFormsScreen(member,data,busy,completed,formLink,it)}
   "rules"->ruleActions?.let{NativeRulesScreen(member,data,busy,completed,it,disciplineActions)}
   "rewards"->rewardActions?.let{NativeRewardsScreen(member,data,busy,it,completed)}
   "rituals"->ritualActions?.let{NativeRitualsScreen(member,data,busy,completed,it,error,homeTarget)}
  }
 }
 if(LocalConfiguration.current.screenWidthDp>=720){
  Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(24.dp)){
   Column(Modifier.width(112.dp).fillMaxHeight().testTag("expanded-navigation"),verticalArrangement=Arrangement.spacedBy(4.dp)){
    navigationTabs.filter{it!="settings"}.forEach{name->val index=allTabs.indexOf(name);NavigationDrawerItem(label={Text(labels.getValue(name))},selected=tab==index,onClick={selectTab(index)},modifier=Modifier.testTag("tab-$name"))}
    if("settings" in navigationTabs){Spacer(Modifier.weight(1f));NavigationDrawerItem(label={Text(labels.getValue("settings"))},selected=allTabs.getOrNull(tab)=="settings",onClick={selectTab(allTabs.indexOf("settings"))},modifier=Modifier.testTag("tab-settings"))}
   }
   Column(Modifier.weight(1f).then(if(allTabs.getOrNull(tab) in listOf("home","rituals","rules","rewards","relations","notifications","profile","settings","wiki"))Modifier.verticalScroll(rememberScrollState()) else Modifier)){content()}
  }
 }else if(allTabs.getOrNull(tab) in listOf("home","rituals","rules","rewards","relations","notifications","profile","settings","wiki")){
  var more by remember{mutableStateOf(false)}
  Column(Modifier.fillMaxSize()){
   Column(Modifier.weight(1f).verticalScroll(rememberScrollState())){content()}
   NavigationBar(containerColor=MaterialTheme.colorScheme.background){
    listOf("home","rituals","rules","journal").forEach{name->val index=allTabs.indexOf(name);if(index>=0)NavigationBarItem(selected=allTabs.getOrNull(tab)==name,onClick={homeTarget=null;selectTab(index)},icon={Icon(painterResource(when(name){"home"->android.R.drawable.ic_menu_view;"rituals"->android.R.drawable.ic_menu_agenda;"rules"->android.R.drawable.ic_menu_info_details;else->android.R.drawable.ic_menu_edit}),contentDescription=null,modifier=Modifier.size(20.dp))},label={Text(labels.getValue(name))},modifier=Modifier.testTag("tab-$name"))}
    Box(Modifier.testTag("tab-more")){Row{NavigationBarItem(selected=false,onClick={more=true},icon={Icon(painterResource(android.R.drawable.ic_menu_more),contentDescription=null,modifier=Modifier.size(20.dp))},label={Text(if(ru)"Ещё" else "More")})};DropdownMenu(more,{more=false}){navigationTabs.filter{it !in listOf("home","rituals","rules","journal")}.forEach{name->DropdownMenuItem(text={Text(labels.getValue(name))},onClick={selectTab(allTabs.indexOf(name));more=false},modifier=Modifier.testTag("tab-$name"))}}}
   }
  }
 }else{
  Column{
   ScrollableTabRow(selectedTabIndex=navigationTabs.indexOf(allTabs.getOrNull(tab)).coerceAtLeast(0),edgePadding=0.dp,containerColor=MaterialTheme.colorScheme.background,divider={}){
    navigationTabs.forEach{name->val index=allTabs.indexOf(name);Tab(selected=tab==index,onClick={selectTab(index)},modifier=Modifier.testTag("tab-$name"),text={Text(labels.getValue(name))})}
   }
   content()
  }
 }
}
