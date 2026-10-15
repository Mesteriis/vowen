package org.vowen.app

import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

class WorkspaceScreenTest {
 @get:Rule val compose=createComposeRule()
 private val member=Member(id="a",display_name="Demo A",paused=false,profile_labels=emptyList(),language="en",timezone="UTC",profile_version=1)
 private val relation=Relation(id="r",dominant_user_id="a",submissive_user_id="b",status="proposed",version=3,relation_version_id="v3",agreement_text="Synthetic exact agreement",scopes=listOf("rules.assign"),consent_user_ids=listOf("b"))
 private val session=DeviceSession(id="s",client="android",device_label="Synthetic device",created_at="2026-10-15T10:00Z",expires_at="2026-11-14T10:00Z",revoked=false)
 private fun actions(onRelation:(Relation,String)->Unit={_,_->},onProfile:(ProfilePatch)->Unit={},onRevoke:(DeviceSession)->Unit={}):WorkspaceActions = WorkspaceActions({}, {}, onRelation, {_,_,_->}, onProfile, onRevoke)

 @Test fun acceptanceShowsExactAgreementAndRequiresExplicitConfirmation() {
  var accepted:Pair<Relation,String>?=null
  compose.setContent {MaterialTheme {WorkspaceScreen(member,WorkspaceState(relations=listOf(relation)),"s",false,0,actions(onRelation={r,a->accepted=r to a}))}}
  compose.onNodeWithTag("accept-r").performClick()
  compose.onNodeWithTag("agreement-review").assertTextContains("Synthetic exact agreement")
  assertNull(accepted)
  compose.onNodeWithTag("confirm-relation").performClick()
  assertEquals("v3",accepted!!.first.relation_version_id)
  assertEquals(3,accepted!!.first.version)
  assertEquals("accept",accepted!!.second)
 }

 @Test fun ownSessionRevocationRequiresTargetConfirmation() {
  var revoked:String?=null
  compose.setContent {MaterialTheme {WorkspaceScreen(member,WorkspaceState(sessions=listOf(session)),"s",false,0,actions(onRevoke={revoked=it.id}))}}
  compose.onNodeWithTag("tab-sessions").performClick()
  compose.onNodeWithText("Current session").assertIsDisplayed()
  compose.onNodeWithTag("revoke-session-s").performClick()
  assertNull(revoked)
  compose.onNodeWithTag("confirm-session-revoke").performClick()
  assertEquals("s",revoked)
 }

 @Test fun profileFormSubmitsVersionAndMetadataOnly() {
  var saved:ProfilePatch?=null
  compose.setContent {MaterialTheme {WorkspaceScreen(member,WorkspaceState(),"s",false,0,actions(onProfile={saved=it}))}}
  compose.onNodeWithTag("tab-profile").performClick()
  compose.onNodeWithTag("profile-name").performTextReplacement("Changed demo")
  compose.onNodeWithTag("profile-timezone").performTextReplacement("Europe/Madrid")
  compose.onNodeWithTag("profile-switch").performClick()
  compose.onNodeWithTag("profile-save").performClick()
  assertEquals(1,saved!!.expected_version)
  assertEquals("Changed demo",saved!!.display_name)
  assertEquals(listOf("switch"),saved!!.profile_labels)
 }
 @Test fun proposalUsesSelectedParticipantAndDoesNotPretendConsent() {
  var proposed:RelationProposal?=null
  val data=WorkspaceState(participants=listOf(Participant(display_name="Other",id="b",profile_labels=emptyList())))
  val callbacks=WorkspaceActions({}, {proposed=it}, {_,_->}, {_,_,_->}, {}, {})
  compose.setContent {MaterialTheme {WorkspaceScreen(member,data,"s",false,0,callbacks)}}
  compose.onNodeWithTag("propose-relation").performClick()
  compose.onNodeWithTag("relation-target").performClick()
  compose.onNodeWithTag("participant-b").performClick()
  compose.onNodeWithTag("relation-agreement").performTextInput("Synthetic proposal")
  compose.onNodeWithTag("submit-relation").performClick()
  assertEquals("a",proposed!!.dominant_user_id)
  assertEquals("b",proposed!!.submissive_user_id)
  assertEquals(listOf("rules.assign"),proposed!!.scopes)
 }

 @Test fun editingAgreementKeepsOriginalVersionForOptimisticConflictCheck() {
  var changed:Triple<Relation,String,List<String>>?=null
  val callbacks=WorkspaceActions({}, {}, {_,_->}, {r,t,s->changed=Triple(r,t,s)}, {}, {})
  compose.setContent {MaterialTheme {WorkspaceScreen(member,WorkspaceState(relations=listOf(relation)),"s",false,0,callbacks)}}
  compose.onNodeWithText("Propose new version").performClick()
  compose.onNodeWithTag("relation-agreement").performTextReplacement("Changed synthetic agreement")
  compose.onNodeWithTag("submit-relation").performClick()
  assertEquals(3,changed!!.first.version)
  assertEquals("Changed synthetic agreement",changed!!.second)
 }
}
