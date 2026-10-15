package org.vowen.app

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

class RewardScreenTest {
 @get:Rule val compose=createComposeRule()
 private val member=Member(id="b",display_name="Demo",paused=true,profile_labels=emptyList(),language="en",timezone="UTC",profile_version=1)
 @Test fun earnedRewardCanBeAcceptedDuringPersonalPauseAndKeepsRevision() {
  val grant=RewardGrant(id="g",reward_version_id="v",issuer_id="a",recipient_id="b",occurrence_id="o",reward_policy_id="p",revision=3,status="offered",created_at="2026-10-15T09:00Z",title="Quiet evening",description="Choose together",history=emptyList())
  var result:Pair<Int,String>?=null
  compose.setContent{VowenTheme{NativeRewardsScreen(member,WorkspaceState(rewardGrants=listOf(grant)),false,RewardActions({}, {_,_->}, {}, {g,action->result=g.revision to action}))}}
  compose.onNodeWithText("Accept reward").performClick()
  assertEquals(3 to "accept",result)
  compose.onNodeWithText("Mark delivered").assertDoesNotExist()
 }
}
