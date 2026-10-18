package org.vowen.app

import androidx.compose.material3.MaterialTheme
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

class RuleScreenTest {
 @get:Rule val compose=createComposeRule()
 private val member=Member(id="b",display_name="Demo B",paused=false,profile_labels=emptyList(),language="en",timezone="UTC",profile_version=1)
 private val assigned=RuleAssignment(id="assignment",rule_id="rule",rule_version_id="exact-v1",recipient_id="b",manager_ids=listOf("a"),revision=4,status="pending_acceptance",accepted_at=null,decided_at=null,effective=false,title="Daily check-in",description="Exact synthetic rule text")
 private fun actions(onDecision:(RuleAssignment,String)->Unit={_,_->},onSave:(RuleTemplate?,RuleContent)->Unit={_,_->}):RuleActions = RuleActions({},onSave,{_,_->},{_,_->},onDecision)
 @Test fun consentRequiresReviewAndCarriesExactVersion() {
  var result:Pair<RuleAssignment,String>?=null
  compose.setContent {MaterialTheme {NativeRulesScreen(member,WorkspaceState(ruleAssignments=listOf(assigned)),false,0,actions(onDecision={a,s->result=a to s}))}}
  compose.onNodeWithText("Daily check-in").performClick()
  compose.onNodeWithTag("accept-rule-assignment").performClick()
  assertNull(result)
  compose.onNodeWithTag("rule-review").assertTextContains("Exact synthetic rule text")
  compose.onNodeWithTag("confirm-rule-acceptance").performClick()
  assertEquals("exact-v1",result!!.first.rule_version_id)
  assertEquals(4,result!!.first.revision)
  assertEquals("accept",result!!.second)
 }
 @Test fun pausedRecipientCanWithdrawButCannotAccept() {
  var result:String?=null
  compose.setContent {MaterialTheme {NativeRulesScreen(member.copy(paused=true),WorkspaceState(ruleAssignments=listOf(assigned.copy(status="active",effective=true))),false,0,actions(onDecision={_,s->result=s}))}}
  compose.onNodeWithText("Daily check-in").performClick()
  compose.onNodeWithText("active · inactive").assertExists()
  compose.onNodeWithTag("pause-rule-assignment").performClick()
  assertEquals("pause",result)
  compose.onNodeWithTag("accept-rule-assignment").assertDoesNotExist()
 }
 @Test fun editorSubmitsRealContentWithoutAssigningConsent() {
  var saved:RuleContent?=null
  compose.setContent {MaterialTheme {NativeRulesScreen(member,WorkspaceState(),false,0,actions(onSave={_,s->saved=s}))}}
  compose.onNodeWithTag("new-rule").performClick()
  compose.onNodeWithTag("rule-title").performTextInput("Synthetic title")
  compose.onNodeWithTag("rule-description").performTextInput("Synthetic description")
  compose.onNodeWithTag("save-rule").performClick()
  assertEquals("Synthetic title",saved!!.title)
  assertEquals("Synthetic description",saved!!.description)
 }
 @Test fun authorCanReadOlderPublishedTextAfterStartingReplacementDraft() {
  val old=RuleTemplate(author_id="b",description="Old published text",id="rule",revision=3,status="published",title="Rule",version_id="v1")
  val draft=old.copy(description="Replacement draft text",status="draft",version_id="v2")
  var requested:String?=null
  compose.setContent {MaterialTheme {NativeRulesScreen(member,WorkspaceState(rules=listOf(draft),ruleHistory=listOf(old,draft)),false,0,actions().copy(history={requested=it.id}))}}
  compose.onNodeWithText("Templates").performClick()
  compose.onNodeWithText("Rule").performClick()
  compose.onNodeWithTag("rule-history-rule").performClick()
  assertEquals("rule",requested)
  compose.onNodeWithText("Old published text").assertExists()
 }
 @Test fun longConsentTextCanBeScrolledToItsEnd() {
  val long=assigned.copy(description=(1..150).joinToString("\n"){"Synthetic line $it"}+"\nEND OF EXACT RULE")
  compose.setContent {MaterialTheme {Column(Modifier.verticalScroll(rememberScrollState())) {NativeRulesScreen(member,WorkspaceState(ruleAssignments=listOf(long)),false,0,actions())}}}
  compose.onNodeWithText("Daily check-in").performClick()
  compose.onNodeWithTag("accept-rule-assignment").performScrollTo().performClick()
  compose.onNodeWithTag("rule-review-end").performScrollTo().assertIsDisplayed()
 }

}
