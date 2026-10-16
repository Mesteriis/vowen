package org.vowen.app

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Surface
import androidx.compose.ui.unit.dp
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test

class RitualDesignTest {
 @get:Rule val compose=createComposeRule()
 @Test fun compactSettingsKeepScheduleRewardsAndPauseAccessible() {
  val member=Member(id="a",display_name="Алекс",paused=false,profile_labels=emptyList(),language="ru",timezone="UTC",profile_version=1)
  val assignment=RitualAssignment(id="ritual",issuer_id="a",recipient_id="b",reviewer_ids=listOf("a"),revision=3,ritual_version_id="rv",approval_required=true,description="Несколько минут внимания к себе.",effective=true,schedule=RitualSchedule(kind="daily",timezone="Europe/Madrid",start_date="2026-10-16",hour=8,minute=30),status="active",title="Утренний ритуал",currency_amount=10)
  var action=""
  val data=WorkspaceState(ritualAssignments=listOf(assignment),participants=listOf(Participant(display_name="Луна",id="b",profile_labels=emptyList())))
  val actions=RitualActions({}, {_,_->}, {_,_->}, {}, {_,_->}, {_,_->}, {_,s->action=s}, {_,_,_,_,_->}, {_,_,_->}, {},rewards={_,_->})
  compose.setContent{VowenTheme{Surface{Column(Modifier.fillMaxSize().safeDrawingPadding().padding(16.dp).verticalScroll(rememberScrollState())){NativeRitualsScreen(member,data,false,0,actions)}}}}
  compose.onNodeWithTag("ritual-assignment-ritual").performScrollTo().performClick()
  val calendar=compose.onNodeWithContentDescription("Изменить расписание")
  calendar.performScrollTo().assertExists()
  compose.onNodeWithContentDescription("Изменить награды ритуала").assertExists()
  compose.onNodeWithContentDescription("Приостановить ритуал").assertExists()
  compose.waitForIdle()
  val inst=InstrumentationRegistry.getInstrumentation()
  android.os.SystemClock.sleep(400) // Let the platform dialog window animation settle before visual capture.
  inst.targetContext.openFileOutput("ritual-design.png",0).use{inst.uiAutomation.takeScreenshot()!!.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)}
  calendar.performClick()
  compose.onNodeWithText("Часовой пояс IANA").assertExists()
  compose.onNodeWithText("Отмена").performScrollTo().performClick()
  // Returning from the editor preserves the chosen assignment.
  compose.onNodeWithTag("ritual-assignment-ritual").performScrollTo().performClick()
  compose.onNodeWithContentDescription("Приостановить ритуал").performScrollTo().performClick()
  assertEquals("pause",action)
 }
}
