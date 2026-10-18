package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp

val profileChapters=listOf("identity","dynamics","preferences","boundaries","health","visibility")
fun profileChapter(key:String,ru:Boolean)=if(ru) mapOf("identity" to "О себе","dynamics" to "Динамика","preferences" to "Предпочтения","boundaries" to "Границы","health" to "Здоровье и забота","visibility" to "Видимость")[key]?:key else mapOf("identity" to "About me","dynamics" to "Dynamics","preferences" to "Preferences","boundaries" to "Boundaries","health" to "Health & care","visibility" to "Visibility")[key]?:key

@Composable
fun NativeProfileWizard(step:Int,busy:Boolean,ru:Boolean,onStep:(Int)->Unit,onExit:()->Unit,onPublish:()->Unit,content:@Composable ()->Unit){
 Column(Modifier.fillMaxWidth().imePadding().navigationBarsPadding(),verticalArrangement=Arrangement.spacedBy(20.dp)) {
  Text(if(ru)"Пошаговое заполнение · $step из 6" else "Guided profile · $step of 6",style=MaterialTheme.typography.labelLarge)
  Text(profileChapter(profileChapters[step-1],ru),style=MaterialTheme.typography.headlineMedium)
  Row(Modifier.horizontalScroll(rememberScrollState()),horizontalArrangement=Arrangement.spacedBy(8.dp)) {profileChapters.forEachIndexed{index,key->TextButton(onClick={onStep(index+1)},enabled=!busy){Text("${index+1}. ${profileChapter(key,ru)}")}}}
  content()
  Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)) {
   TextButton(onClick={onStep(step-1)},enabled=!busy&&step>1){Text(if(ru)"Назад" else "Back")}
   VowenActionButton(onClick={if(step==6)onPublish() else onStep(step+1)},enabled=!busy,modifier=Modifier.weight(1f).testTag(if(step==6)"profile-publish" else "profile-wizard-next")){Text(if(step==6){if(ru)"Сохранить профиль" else "Publish profile"}else{if(ru)"Сохранить и далее" else "Save & continue"})}
  }
  if(step<6)TextButton(onClick={onStep(step+1)},enabled=!busy,modifier=Modifier.testTag("profile-wizard-skip")){Text(if(ru)"Пропустить" else "Skip")}
  TextButton(onClick=onExit,enabled=!busy){Text(if(ru)"Сохранить и выйти" else "Save & exit")}
 }
}
