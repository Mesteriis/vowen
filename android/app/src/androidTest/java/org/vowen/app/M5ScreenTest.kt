package org.vowen.app

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

class M5ScreenTest {
 @get:Rule val compose=createComposeRule()
 private val member=Member(id="a",display_name="Demo A",paused=false,profile_labels=emptyList(),language="en",timezone="UTC",profile_version=1)
 private val settings=NotificationSettings(channels=listOf("in_app","telegram"),quiet_enabled=false,quiet_start=1320,quiet_end=480,revision=3,telegram_connected=false,timezone="Europe/Madrid")
 private val schema=FormSchema(title="Reflection",questions=listOf(FormQuestion(id="q",kind="short_text",label="Moment")))
 private val form=FormTemplate(id="f",version_id="v",revision=2,status="published",schema_body=schema)
 private val plan=SurveyPlan(id="s",author_id="a",recipient_id="b",form_version_id="v",idempotency_key="key",owner_paused=false,recipient_paused=false,reader_ids=listOf("a"),revision=2,source_effective=true,title="Reflection")
 private val data=WorkspaceState(forms=listOf(form),participants=listOf(Participant(id="a",display_name="Demo A",profile_labels=emptyList()),Participant(id="b",display_name="Demo B",profile_labels=emptyList())),surveys=listOf(plan))
 @Test fun notificationChannelsQuietBoundariesAndRevision(){
  var saved:NotificationPatch?=null
  compose.setContent{MaterialTheme{Column(Modifier.verticalScroll(rememberScrollState())){NativeNotificationScreen(settings,false,NotificationActions{saved=it},false)}}}
  compose.onNodeWithTag("channel-telegram").performScrollTo().performClick()
  compose.onNodeWithTag("quiet-enabled").performScrollTo().performClick()
  compose.onNodeWithTag("quiet-start").performScrollTo().performTextReplacement("22:15")
  compose.onNodeWithTag("quiet-end").performScrollTo().performTextReplacement("22:15")
  compose.onNodeWithTag("save-notifications").performScrollTo().assertIsNotEnabled()
  compose.onNodeWithTag("quiet-end").performScrollTo().performTextReplacement("08:30")
  compose.onNodeWithTag("save-notifications").performScrollTo().performClick()
  assertEquals(listOf("in_app"),saved!!.channels);assertEquals(3,saved!!.expected_version)
  assertEquals(1335,saved!!.quiet_start);assertEquals(510,saved!!.quiet_end)
  compose.onNodeWithText("Bot not connected").performScrollTo().assertExists()
 }
 @Test fun recipientControlsOwnPauseAndSeesHistoryButCannotSend(){
  var transition:String?=null
  compose.setContent{MaterialTheme{Column(Modifier.verticalScroll(rememberScrollState())){NativeSurveysScreen(member.copy(id="b"),data,false,0,SurveyActions({}, {_,a->transition=a},{_,_,_->},{_,done->done(listOf(SurveyWave(id="w",due_at="2026-10-15",invitation_id="invitation",occurrence_id=null,reason=null,status="created")))}))}}}
  compose.onNodeWithTag("send-survey-s").assertDoesNotExist()
  compose.onNodeWithTag("pause-survey-s").performScrollTo().performClick()
  assertEquals("pause",transition)
  compose.onNodeWithTag("history-survey-s").performScrollTo().performClick()
  compose.onNodeWithText("Invitation: invitation").performScrollTo().assertExists()
 }
 @Test fun failedCreateRetainsEditorAndIdempotencyKey(){
  val submitted=mutableListOf<SurveyCreate>()
  var busy by mutableStateOf(false)
  compose.setContent{MaterialTheme{Column(Modifier.verticalScroll(rememberScrollState())){NativeSurveysScreen(member,data.copy(surveys=emptyList()),busy,0,SurveyActions({submitted.add(it)},{_,_->},{_,_,_->},{_,_->}))}}}
  compose.onNodeWithTag("new-survey").performScrollTo().performClick()
  compose.onNodeWithTag("Published form version").performScrollTo().performClick()
  compose.onNodeWithText("Reflection · v2").performClick()
  compose.onNodeWithTag("Survey recipient").performScrollTo().performClick()
  compose.onNode(hasText("Demo B") and hasAnyAncestor(isPopup())).performClick()
  compose.onNodeWithTag("create-survey").performScrollTo().performClick()
  compose.runOnIdle{busy=true};compose.waitForIdle();compose.runOnIdle{busy=false}
  compose.onNodeWithTag("create-survey").performScrollTo().performClick()
  assertEquals(2,submitted.size);assertEquals(submitted[0].idempotency_key,submitted[1].idempotency_key)
  assertEquals("v",submitted[0].form_version_id);assertEquals("b",submitted[0].recipient_id)
  assertEquals(emptyList<String>(),submitted[0].reader_ids);assertEquals("daily",submitted[0].schedule!!.kind)
 }
 @Test fun anotherParticipantsPauseAndRevokedSourceDisableSending(){
  compose.setContent{MaterialTheme{Column(Modifier.verticalScroll(rememberScrollState())){NativeSurveysScreen(member,data.copy(surveys=listOf(plan.copy(recipient_paused=true,source_effective=false))),false,0,SurveyActions({}, {_,_->},{_,_,_->},{_,_->}))}}}
  compose.onNodeWithTag("send-survey-s").performScrollTo().assertIsNotEnabled()
  compose.onNodeWithTag("pause-survey-s").performScrollTo().assertTextContains("Pause my survey schedule")
 }
 @Test fun approvedRitualFeedbackPinsSourceAndRecipient(){
  var saved:SurveyCreate?=null
  val ritual=RitualAssignment(id="ritual",issuer_id="a",recipient_id="b",reviewer_ids=listOf("a"),revision=1,ritual_version_id="rv",approval_required=true,description="Reflect after approval",effective=true,schedule=RitualSchedule(kind="daily",timezone="UTC",start_date="2026-10-15",hour=10,minute=0),status="active",title="Morning ritual")
  compose.setContent{MaterialTheme{Column(Modifier.verticalScroll(rememberScrollState())){NativeSurveysScreen(member,data.copy(surveys=emptyList(),ritualAssignments=listOf(ritual)),false,0,SurveyActions({saved=it},{_,_->},{_,_,_->},{_,_->}))}}}
  compose.onNodeWithTag("new-survey").performScrollTo().performClick()
  compose.onNodeWithTag("Published form version").performScrollTo().performClick()
  compose.onNodeWithText("Reflection · v2").performClick()
  compose.onNodeWithTag("Survey trigger").performScrollTo().performClick()
  compose.onNodeWithText("After approved ritual").performClick()
  compose.onNodeWithTag("Source ritual assignment").performScrollTo().performClick()
  compose.onNodeWithText("Morning ritual → Demo B").performClick()
  compose.onNodeWithTag("create-survey").performScrollTo().performClick()
  assertNull(saved!!.schedule);assertEquals("ritual",saved!!.ritual_assignment_id)
  assertEquals("b",saved!!.recipient_id);assertEquals("v",saved!!.form_version_id)
 }

}
