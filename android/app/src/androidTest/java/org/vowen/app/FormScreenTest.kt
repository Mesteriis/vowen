package org.vowen.app

import androidx.compose.material3.MaterialTheme
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.ui.Modifier
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
  compose.setContent {MaterialTheme {Column(Modifier.verticalScroll(rememberScrollState())) {NativeGuestScreen {}}}}
  compose.onNodeWithText("Secret form or receipt link").performTextInput("http://unsafe.example/f/id#token=secret")
  compose.onNodeWithText("Open form / receipt").performScrollTo().performClick()
  compose.onNodeWithText("Request not confirmed. Your input remains in this window.").assertExists()
 }
}
