package org.vowen.app

import android.content.ContentValues
import android.net.Uri
import android.provider.MediaStore
import androidx.activity.result.ActivityResultRegistry
import androidx.activity.result.ActivityResultRegistryOwner
import androidx.activity.result.contract.ActivityResultContract
import androidx.activity.compose.LocalActivityResultRegistryOwner
import androidx.core.app.ActivityOptionsCompat
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

class EvidenceRecoveryTest {
 @get:Rule val compose=createComposeRule()
 @Test fun rejectedUploadCanBeReplacedWithoutLosingReportDraft() {
  val context=InstrumentationRegistry.getInstrumentation().targetContext
  val values=ContentValues().apply{put(MediaStore.Images.Media.DISPLAY_NAME,"synthetic-recovery.png");put(MediaStore.Images.Media.MIME_TYPE,"image/png");put(MediaStore.Images.Media.RELATIVE_PATH,"Pictures/VowenQA")}
  val uri=context.contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI,values)!!
  context.contentResolver.openOutputStream(uri)!!.use{it.write(byteArrayOf(1,2,3))}
  val registry=object:ActivityResultRegistry(){override fun <I,O> onLaunch(requestCode:Int,contract:ActivityResultContract<I,O>,input:I,options:ActivityOptionsCompat?){dispatchResult(requestCode,uri)}}
  val owner=object:ActivityResultRegistryOwner{override val activityResultRegistry=registry}
  val member=Member(id="b",display_name="Demo",paused=false,profile_labels=emptyList(),language="en",timezone="UTC",profile_version=1)
  val o=RitualOccurrence(approval_required=true,assignment_id="a",can_report=true,can_review=false,description="Synthetic",due_at="2026-10-15T09:00Z",expires_at="2026-10-16T09:00Z",evidence_policy=EvidencePolicy(required=true,allowed_types=listOf("link","photo")),id="o",local_day="2026-10-15",recipient_id="b",reports=emptyList(),revision=7,status="scheduled",title="Presence")
  var attempts=0;var sent:Triple<String,List<String>,List<String>>?=null
  val actions=RitualActions({}, {_,_->}, {_,_->}, {}, {_,_->}, {_,_->}, {_,_->}, {_,text,_,links,ids->sent=Triple(text,links,ids)}, {_,_,_->}, {}, upload={_,_,done->attempts++;if(attempts==1)throw IllegalStateException("HTTP 422") else done(EvidenceView(id="proof",kind="photo",media_type="image/png",size=3))})
  try{
   compose.setContent{CompositionLocalProvider(LocalActivityResultRegistryOwner provides owner){VowenTheme{NativeRitualsScreen(member,WorkspaceState(ritualOccurrences=listOf(o)),false,0,actions)}}}
   compose.onNodeWithTag("report-o").performClick()
   compose.onNodeWithTag("ritual-report-text").performTextInput("Keep this report")
   compose.onNodeWithTag("ritual-evidence-links").performTextInput("https://example.org/proof")
   compose.onNodeWithText("Choose photo or video").performClick()
   compose.waitUntil(10000){attempts==1}
   compose.onNodeWithText("HTTP 422").assertExists()
   compose.onNodeWithText("Replace pending file").performClick()
   compose.onNodeWithText("Choose photo or video").assertIsEnabled().performClick()
   compose.waitUntil(10000){attempts==2}
   compose.onNodeWithTag("submit-ritual-report").performClick()
   assertEquals(Triple("Keep this report",listOf("https://example.org/proof"),listOf("proof")),sent)
  }finally{context.contentResolver.delete(uri,null,null)}
 }
}
