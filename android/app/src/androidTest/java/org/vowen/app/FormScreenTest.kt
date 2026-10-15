package org.vowen.app

import androidx.compose.material3.MaterialTheme
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.ui.Modifier
import androidx.test.core.app.ActivityScenario
import androidx.lifecycle.ViewModelProvider
import androidx.compose.runtime.*
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import kotlinx.serialization.json.*
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

class FormScreenTest {
 @get:Rule val compose=createComposeRule()
 private val schema=FormSchema(title="Synthetic form",questions=listOf(FormQuestion(id="q",kind="short_text",label="Answer",required=true)))
 @Test fun submissionRequiresReadersAcknowledgementAndExplicitReview() {
  var submitted:FormSubmit?=null
  compose.setContent {MaterialTheme {NativeFormRunner(schema,emptyMap(),false,false,true,{}, {submitted=it})}}
  compose.onNodeWithTag("form-answer-q").performTextInput("Native answer")
  compose.onNodeWithTag("form-review").assertIsNotEnabled()
  compose.onNodeWithTag("form-ack").performClick()
  compose.onNodeWithTag("form-review").performClick()
  assertNull(submitted)
  compose.onNodeWithTag("form-send").performClick()
  assertEquals("Native answer",submitted!!.answers["q"]!!.jsonPrimitive.content)
  assertTrue(submitted!!.acknowledged)
 }
 @Test fun hiddenRequiredQuestionIsNotRenderedButReappearsWithCondition() {
  val conditional=FormSchema(title="Conditional",questions=listOf(
   FormQuestion(id="first",kind="boolean",label="First"),
   FormQuestion(id="second",kind="long_text",label="Second",required=true,visibility=FormVisibility(all=listOf(FormCondition(question_id="first",op="equals",value=JsonPrimitive(true)))))))
  compose.setContent {MaterialTheme {NativeFormRunner(conditional,emptyMap(),false,false,false,{}, {})}}
  compose.onNodeWithTag("form-answer-second").assertDoesNotExist()
  compose.onNodeWithTag("form-answer-first").performClick()
  compose.onNodeWithTag("form-answer-second").assertExists()
 }
 @Test fun nativeEditorCreatesTemplateWithoutJson() {
  var saved:FormSchema?=null
  compose.setContent {MaterialTheme {Column(Modifier.verticalScroll(rememberScrollState())) {NativeFormEditor(null,false,false,{saved=it},{})}}}
  compose.onNodeWithTag("native-form-title").performTextInput("Native template")
  compose.onNodeWithTag("native-question-0").performTextInput("Native question")
  compose.onNodeWithTag("native-form-save").performScrollTo().performClick()
  assertEquals("Native template",saved!!.title)
  assertEquals("Native question",saved!!.questions.single().label)
  assertEquals("short_text",saved!!.questions.single().kind)
 }
 @Test fun nativeGuestRejectsNonHttpsLinkBeforeNetwork() {
  val guestModel=GuestViewModel()
  compose.setContent {MaterialTheme {Column(Modifier.verticalScroll(rememberScrollState())) {NativeGuestScreen(guestModel) {}}}}
  compose.onNodeWithText("Secret form or receipt link").performTextInput("http://unsafe.example/f/id#token=secret")
  compose.onNodeWithText("Open form / receipt").performScrollTo().performClick()
  compose.onNodeWithText("Request not confirmed. Your input remains in this window.").assertExists()
 }
 @Test fun switchingTemplateResetsUnsavedEditorBeforeSavingNewTarget() {
  var initial by mutableStateOf(FormSchema(title="Template A",questions=listOf(FormQuestion(id="a",kind="short_text",label="Question A"))))
  var saved:FormSchema?=null
  compose.setContent {MaterialTheme {Column(Modifier.verticalScroll(rememberScrollState())) {NativeFormEditor(initial,false,false,{saved=it},{})}}}
  compose.onNodeWithTag("native-form-title").performTextReplacement("Unsaved A")
  compose.runOnIdle {initial=FormSchema(title="Template B",questions=listOf(FormQuestion(id="b",kind="short_text",label="Question B")))}
  compose.onNodeWithTag("native-form-title").assertTextContains("Template B")
  compose.onNodeWithTag("native-form-save").performScrollTo().performClick()
  assertEquals("b",saved!!.questions.single().id)
 }
 @Test fun activityRecreationKeepsGuestCookieRouteAndUnsavedInputInMemory() {
  val scenario=ActivityScenario.launch(MainActivity::class.java)
  var transport:GuestApi?=null
  var key:String?=null
  try {
   compose.onNodeWithText("Guest form / Гостевая анкета").performClick()
   scenario.onActivity {activity->
    val m=ViewModelProvider(activity)[GuestViewModel::class.java]
    transport=GuestApi("https://instance.example")
    m.apiState.value=transport
    m.accessState.value=FormAccess(id="i",schema_body=schema,readers=emptyList(),answers=emptyMap(),status="draft",retention_until=null,retention_days=90,expires_at="future")
    m.draftState.value=NativeFormDraft(mapOf("q" to JsonPrimitive("Unsaved before rotation")))
    key=m.draftState.value!!.key
   }
   compose.onNodeWithTag("form-answer-q").assertTextContains("Unsaved before rotation")
   scenario.recreate()
   compose.onNodeWithTag("form-answer-q").assertTextContains("Unsaved before rotation")
   scenario.onActivity {activity->
    val m=ViewModelProvider(activity)[GuestViewModel::class.java]
    assertTrue(m.visibleState.value)
    assertSame(transport,m.apiState.value)
    assertEquals(key,m.draftState.value!!.key)
   }
  } finally {scenario.close()}
 }
}
