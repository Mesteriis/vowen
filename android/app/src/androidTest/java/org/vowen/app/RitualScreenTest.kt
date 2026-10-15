package org.vowen.app

import androidx.compose.material3.MaterialTheme
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.verticalScroll
import androidx.compose.ui.unit.dp
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

class RitualScreenTest {
 @get:Rule val compose=createComposeRule()
 private val member=Member(id="b",display_name="Demo",paused=false,profile_labels=emptyList(),language="en",timezone="UTC",profile_version=1)
 private val o=RitualOccurrence(approval_required=true,assignment_id="a",can_report=true,can_review=false,description="Synthetic ritual",due_at="2026-10-15T09:00Z",expires_at="2026-10-16T09:00Z",id="o",local_day="2026-10-15",recipient_id="b",reports=emptyList(),revision=7,status="needs_changes",title="Presence")
 private fun actions(report:(RitualOccurrence,String,String)->Unit={_,_,_->},review:(RitualOccurrence,String,String)->Unit={_,_,_->})=RitualActions({}, {_,_->}, {_,_->}, {}, {_,_->}, {_,_->}, {_,_->}, report,review,{})
 @Test fun reportCarriesOccurrenceRevisionAndStableRequestIdentity() {
  var sent:Triple<RitualOccurrence,String,String>?=null
  compose.setContent{MaterialTheme{NativeRitualsScreen(member,WorkspaceState(ritualOccurrences=listOf(o)),false,0,actions(report={a,b,c->sent=Triple(a,b,c)}))}}
  compose.onNodeWithTag("report-o").performClick()
  compose.onNodeWithTag("ritual-report-text").performTextInput("Synthetic revised report")
  compose.onNodeWithTag("submit-ritual-report").performClick()
  val first=sent!!
  compose.onNodeWithTag("submit-ritual-report").performClick()
  assertEquals(first.third,sent!!.third)
  assertEquals(7,sent!!.first.revision)
  assertEquals("Synthetic revised report",sent!!.second)
 }
 @Test fun reviewerDecisionsAreExplicitAndKeepExpectedRevision() {
  var result:String?=null
  compose.setContent{MaterialTheme{NativeRitualsScreen(member,WorkspaceState(ritualOccurrences=listOf(o.copy(can_report=false,can_review=true,status="submitted"))),false,0,actions(review={a,s,_->assertEquals(7,a.revision);result=s}))}}
  compose.onNodeWithTag("report-o").assertDoesNotExist()
  compose.onNodeWithTag("review-o").performClick()
  assertNull(result)
  compose.onNodeWithTag("ritual-request-changes").performClick()
  assertEquals("needs_changes",result)
 }
 @Test fun startupUsesSuppliedVelvetArtworkAndThenReleasesContent() {
  var loading by androidx.compose.runtime.mutableStateOf(true)
  compose.setContent{VowenTheme{StartupGate(loading){androidx.compose.material3.Text("Ready workspace")}}}
  compose.onNodeWithTag("vowen-startup").assertExists()
  compose.runOnIdle{loading=false}
  compose.onNodeWithText("Ready workspace").assertExists()
  compose.onNodeWithTag("vowen-startup").assertDoesNotExist()
 }
 @Test fun renderReferenceThemeWithRealNativeRitualComponents() {
  compose.setContent{VowenTheme{androidx.compose.material3.Surface{androidx.compose.foundation.layout.Column(androidx.compose.ui.Modifier.fillMaxSize().verticalScroll(androidx.compose.foundation.rememberScrollState()).padding(16.dp)){
   androidx.compose.foundation.layout.Row(verticalAlignment=androidx.compose.ui.Alignment.CenterVertically){androidx.compose.foundation.Image(androidx.compose.ui.res.painterResource(R.drawable.vowen_crest),null,androidx.compose.ui.Modifier.size(48.dp));androidx.compose.material3.Text("Vowen",style=androidx.compose.material3.MaterialTheme.typography.headlineLarge,color=androidx.compose.material3.MaterialTheme.colorScheme.primary)}
   NativeRitualsScreen(member,WorkspaceState(ritualOccurrences=listOf(o.copy(status="scheduled"))),false,0,actions())
  }}}}
  compose.waitForIdle()
  val context=androidx.test.platform.app.InstrumentationRegistry.getInstrumentation().targetContext
  val width=context.resources.configuration.screenWidthDp
  val values=android.content.ContentValues().apply{put(android.provider.MediaStore.Images.Media.DISPLAY_NAME,if(width>=600)"rituals-final-tablet.png" else "rituals-final-phone.png");put(android.provider.MediaStore.Images.Media.MIME_TYPE,"image/png");put(android.provider.MediaStore.Images.Media.RELATIVE_PATH,"Pictures/VowenQA")}
  val uri=context.contentResolver.insert(android.provider.MediaStore.Images.Media.EXTERNAL_CONTENT_URI,values)!!
  context.contentResolver.openOutputStream(uri)!!.use{compose.onRoot().captureToImage().asAndroidBitmap().compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)}
 }

}
