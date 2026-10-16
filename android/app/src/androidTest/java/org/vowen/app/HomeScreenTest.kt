package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.Image
import androidx.compose.ui.res.painterResource
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.unit.dp
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Rule
import org.junit.Test
import org.junit.Assert.*
import java.time.LocalDate

class HomeScreenTest {
 @get:Rule val compose=createComposeRule()
 @Test fun contextualDayAndReportNavigation(){
  val day=LocalDate.now().toString()
  val m=Member("Алекс","a","ru",false,listOf("switch"),1,"UTC")
  val r=Relation("Синтетическое соглашение",listOf("a","b"),"a","r","v",listOf("rituals.assign","rituals.review"),"active","b",1)
  val schedule=RitualSchedule(8,"daily",0,day,"UTC")
  val a=RitualAssignment(true,description="demo",effective=true,id="assignment",issuer_id="a",recipient_id="b",reviewer_ids=listOf("a"),revision=1,ritual_version_id="v",schedule=schedule,status="active",title="Утренний ритуал")
  val o=RitualOccurrence(true,"assignment",false,true,"demo",day+"T08:00:00Z",null,day+"T23:59:00Z","o",day,"b",emptyList(),1,"submitted","Утренний ритуал")
  var opened:String?=null
  compose.setContent{VowenTheme{Surface{Box{Image(painterResource(R.drawable.vowen_velvet_texture),null,contentScale=androidx.compose.ui.layout.ContentScale.Crop,alpha=.22f,modifier=Modifier.fillMaxSize());Column(Modifier.fillMaxSize().safeDrawingPadding().padding(16.dp).verticalScroll(rememberScrollState())){NativeHomeScreen(m,WorkspaceState(relations=listOf(r),participants=listOf(Participant("Луна","b",emptyList())),ritualAssignments=listOf(a),ritualOccurrences=listOf(o)),false,null,{}, {opened=it.id},{})}}}}}
  compose.onNodeWithTag("home-context").performScrollTo().performClick()
  compose.onNodeWithText("Луна · Вы доминант").performClick()
  compose.onNodeWithTag("home-occurrence-o").performScrollTo().assertExists()
  compose.onNodeWithTag("home-review").performScrollTo().performClick()
  assertEquals("o",opened)
  val inst=InstrumentationRegistry.getInstrumentation()
  val context=inst.targetContext
  java.io.File(context.cacheDir,"home-qa.png").outputStream().use{inst.uiAutomation.takeScreenshot()!!.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)}
 }
}
