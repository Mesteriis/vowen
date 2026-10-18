package org.vowen.app

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

class M4ScreenTest {
 @get:Rule val compose=createComposeRule()
 private val member=Member(id="b",display_name="Demo B",paused=false,profile_labels=emptyList(),language="en",timezone="UTC",profile_version=1)
 private val version=DisciplineVersionView(id="exact-v1",description="Alleged event",conditions="Voluntary reflection",created_at="2026-10-15T10:00Z",rule_title="Agreed rule",rule_version_id="rule-v1")
 private val record=DisciplineRecord(id="d",author_id="a",recipient_id="b",reviewer_ids=listOf("a"),version_id="exact-v1",revision=4,status="planned",effective=true,versions=listOf(version),history=emptyList())
 private val entry=JournalEntry(id="j",author_id="b",revision=2,date="2026-10-15",title="Reflection",text="<script>private</script>",created_at="now",updated_at="now",visibility="private",published=true,reader_ids=emptyList())
 @Test fun recipientStartsWithoutAcceptanceAndCannotReviseConditions(){
  var decision:Triple<DisciplineRecord,String,String>?=null
  compose.setContent{MaterialTheme{Column(Modifier.verticalScroll(rememberScrollState())){NativeDisciplineScreen(member,WorkspaceState(discipline=listOf(record)),false,0,DisciplineActions({}, {}, {_,_->}, {r,a,c->decision=Triple(r,a,c)}))}}}
  compose.onNodeWithText("Assigned").performClick()
  compose.onNodeWithTag("revise-discipline-d").assertDoesNotExist()
  compose.onNodeWithTag("accept-discipline-d").assertDoesNotExist()
  compose.onNodeWithText("Start action").performScrollTo().performClick()
  assertEquals("exact-v1",decision!!.first.version_id)
  assertEquals(4,decision!!.first.revision)
  assertEquals("start",decision!!.second)
 }
 @Test fun pausedRecipientCannotStartAndHasNoConsentWorkflow(){
  var action:String?=null
  compose.setContent{MaterialTheme{Column(Modifier.verticalScroll(rememberScrollState())){NativeDisciplineScreen(member.copy(paused=true),WorkspaceState(discipline=listOf(record.copy(status="accepted",effective=false))),false,0,DisciplineActions({}, {}, {_,_->}, {_,a,_->action=a}))}}}
  compose.onNodeWithText("Assigned").performClick()
  compose.onNodeWithText("Start action").performScrollTo().assertIsNotEnabled()
  compose.onNodeWithTag("cancel-discipline-d").assertDoesNotExist()
  assertNull(action)
 }
 @Test fun diaryEditorDefaultsPrivateAndDraft(){
  var saved:JournalContent?=null
  compose.setContent{MaterialTheme{Column(Modifier.verticalScroll(rememberScrollState())){NativeJournalScreen(member,WorkspaceState(),false,0,JournalActions({}, {_,body,_->saved=body}, {}))}}}
  compose.onNodeWithTag("new-journal").performScrollTo().performClick()
  compose.onNodeWithTag("journal-title").performScrollTo().performTextInput("Private reflection")
  compose.onNodeWithTag("journal-text").performScrollTo().performTextInput("Private body")
  compose.onNodeWithTag("save-journal").performScrollTo().performClick()
  assertEquals("private",saved!!.visibility)
  assertEquals(false,saved!!.published)
  assertEquals(emptyList<String>(),saved!!.reader_ids)
 }
 @Test fun readerSeesPlainTextButCannotEditOrDelete(){
  compose.setContent{MaterialTheme{Column(Modifier.verticalScroll(rememberScrollState())){NativeJournalScreen(member.copy(id="a"),WorkspaceState(journal=listOf(entry)),false,0,JournalActions({}, {_,_,_->}, {}))}}}
  compose.onNodeWithTag("journal-text-j").performScrollTo().assertTextEquals("<script>private</script>")
  compose.onNodeWithTag("edit-journal-j").assertDoesNotExist()
  compose.onNodeWithTag("delete-journal-j").assertDoesNotExist()
 }
 @Test fun authorDeletionRequiresConfirmation(){
  var deleted:String?=null
  compose.setContent{MaterialTheme{Column(Modifier.verticalScroll(rememberScrollState())){NativeJournalScreen(member,WorkspaceState(journal=listOf(entry)),false,0,JournalActions({}, {_,_,_->}, {deleted=it.id}))}}}
  compose.onNodeWithTag("delete-journal-j").performScrollTo().performClick()
  assertNull(deleted)
  compose.onNodeWithTag("confirm-journal-delete").performClick()
  assertEquals("j",deleted)
 }
 @Test fun authorCanRemoveReaderMissingFromActiveParticipantList(){
  var saved:JournalContent?=null
  val shared=entry.copy(visibility="selected",reader_ids=listOf("disabled-reader"))
  compose.setContent{MaterialTheme{Column(Modifier.verticalScroll(rememberScrollState())){NativeJournalScreen(member,WorkspaceState(journal=listOf(shared)),false,0,JournalActions({}, {_,body,_->saved=body}, {}))}}}
  compose.onNodeWithTag("edit-journal-j").performScrollTo().performClick()
  compose.onNodeWithTag("journal-reader-disabled-reader").performScrollTo().assertIsOn().performClick()
  compose.onNodeWithTag("save-journal").performScrollTo().performClick()
  assertEquals(emptyList<String>(),saved!!.reader_ids)
 }

}
