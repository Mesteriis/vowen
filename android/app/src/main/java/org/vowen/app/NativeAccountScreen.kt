package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp

/** All personal preferences are available independently of the administrator role. */
@Composable
fun NativeAccountScreen(member:Member,data:WorkspaceState,currentId:String?,busy:Boolean,completed:Int,actions:WorkspaceActions,notifications:NotificationActions?,initialSection:String="profile") {
 val ru=member.language=="ru"
 var section by remember {mutableStateOf(initialSection)}
 LaunchedEffect(initialSection){section=initialSection}
 val entries=listOf("profile" to if(ru)"Личные данные" else "Personal details","notifications" to if(ru)"Уведомления" else "Notifications","sessions" to if(ru)"Сессии" else "Sessions").filter{it.first!="notifications"||notifications!=null}
 Column(verticalArrangement=Arrangement.spacedBy(24.dp)){
  Text(if(ru)"Профиль" else "Profile",style=MaterialTheme.typography.headlineSmall)
  ScrollableTabRow(selectedTabIndex=entries.indexOfFirst{it.first==section}.coerceAtLeast(0),edgePadding=0.dp,containerColor=MaterialTheme.colorScheme.background){entries.forEach{(id,title)->Tab(selected=section==id,onClick={section=id},text={Text(title)},modifier=Modifier.testTag("personal-$id"))}}
  when(section){
   "profile"->ProfileScreen(member,busy,actions.profile)
   "notifications"->notifications?.let{NativeNotificationScreen(data.notificationSettings,busy,it,ru,onRefresh=actions.refresh)}
   "sessions"->SessionsScreen(member,data.sessions,currentId,busy,completed,actions.revokeSession)
  }
  Row{
   TextButton(onClick=actions.refresh,enabled=!busy,modifier=Modifier.testTag("workspace-refresh")){Text(if(ru)"Обновить" else "Refresh")}
   TextButton(onClick=actions.logout,enabled=!busy){Text(if(ru)"Выйти" else "Sign out")}
  }
 }
}
