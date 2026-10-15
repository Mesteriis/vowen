package org.vowen.app

import androidx.compose.ui.test.*
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
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
  compose.setContent{VowenTheme{NativeRewardsScreen(member,WorkspaceState(rewardGrants=listOf(grant),rewardNotices=listOf(RewardNotice(id="n",grant_id="g",created_at="2026-10-15T09:00Z")),participants=listOf(Participant(id="a",display_name="Alice",profile_labels=emptyList()))),false,RewardActions({}, {_,_->}, {}, {g,action->result=g.revision to action}))}}
  compose.onNodeWithText("Alice → Demo").assertExists()
  compose.onNodeWithText("You have an update in the app").assertExists()
  compose.onNodeWithText("Accept reward").performClick()
  assertEquals(3 to "accept",result)
  compose.onNodeWithText("Mark delivered").assertDoesNotExist()
 }
 @Test fun successfulRewardSavesCloseEditorAndUseTheLatestCatalogueVersion() {
  var data by androidx.compose.runtime.mutableStateOf(WorkspaceState())
  var completed by androidx.compose.runtime.mutableIntStateOf(0)
  val revisions=mutableListOf<Int?>()
  val actions=RewardActions({}, {old,body->revisions.add(old?.revision);data=data.copy(rewards=listOf(RewardDefinition(id="r",version_id="v${completed+1}",revision=completed+1,title=body.title,description=body.description,conditions=body.conditions)));completed++}, {}, {_,_->})
  val workspaceActions=WorkspaceActions({}, {}, {_,_->}, {_,_,_->}, {}, {})
  compose.setContent{VowenTheme{WorkspaceScreen(member.copy(paused=false),data,null,false,completed,workspaceActions,rewardActions=actions)}}
  compose.onNodeWithTag("tab-rewards").performScrollTo().performClick()
  compose.onNodeWithText("New reward").performClick()
  compose.onNodeWithText("Reward title").performTextInput("Local reward")
  compose.onNodeWithText("Reward description").performTextInput("First version")
  compose.onNodeWithText("Save reward").performClick()
  compose.onNodeWithText("Save reward").assertDoesNotExist()
  compose.onNodeWithText("New reward version").performClick()
  compose.onNodeWithText("Reward description").performTextClearance()
  compose.onNodeWithText("Reward description").performTextInput("Second version")
  compose.onNodeWithText("Save reward").performClick()
  compose.onNodeWithText("Save reward").assertDoesNotExist()
  assertEquals(listOf(null,1),revisions)
 }

}
