package org.vowen.app

import androidx.compose.material3.MaterialTheme
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
  compose.setContent {MaterialTheme {NativeRulesScreen(member.copy(paused=true),WorkspaceState(ruleAssignments=listOf(assigned.copy(status="active",effective=false))),false,0,actions(onDecision={_,s->result=s}))}}
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
}
