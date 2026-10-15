package org.vowen.app

import android.net.Uri
import androidx.lifecycle.ViewModelProvider
import androidx.test.core.app.ActivityScenario
import androidx.test.platform.app.InstrumentationRegistry
import androidx.compose.ui.test.junit4.createEmptyComposeRule
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

class EvidenceSaveLifecycleTest {
 @get:Rule val compose=createEmptyComposeRule()
 private fun setup():android.content.Context {
  val context=InstrumentationRegistry.getInstrumentation().targetContext
  TestApplication.screenshotFixture=true
  context.getSharedPreferences("instance",0).edit().putString("origin","https://qa.vowen.invalid").commit()
  TokenVault(context).save("https://qa.vowen.invalid","synthetic-refresh")
  return context
 }
 private fun clear(context:android.content.Context){TokenVault(context).clear();context.getSharedPreferences("instance",0).edit().clear().commit();TestApplication.screenshotFixture=false}
 @Test fun pendingSaveRefetchesExactBytesAfterActivityRecreation() {
  val context=setup();val file=java.io.File(context.cacheDir,"synthetic-save.png");file.delete()
  try{ActivityScenario.launch(MainActivity::class.java).use{scenario->
   lateinit var model:AuthViewModel
   scenario.onActivity{model=ViewModelProvider(it)[AuthViewModel::class.java]}
   compose.waitUntil(10000){model.screen.value.member!=null&&!model.screen.value.busy}
   var prepared=false
   scenario.onActivity{model.prepareEvidenceSave(EvidenceView(id="proof",kind="photo",media_type="image/png",size=3)){prepared=true}}
   compose.waitUntil(10000){prepared&&!model.screen.value.busy}
   scenario.recreate()
   scenario.onActivity{model=ViewModelProvider(it)[AuthViewModel::class.java];model.completeEvidenceSave(Uri.fromFile(file))}
   compose.waitUntil(10000){file.exists()&&file.length()==3L&&!model.screen.value.busy}
   assertArrayEquals(byteArrayOf(1,2,3),file.readBytes())
  }}finally{file.delete();clear(context)}
 }
 @Test fun switchingInstanceCancelsPendingSaveBeforeNetworkOrWriting() {
  val context=setup();val file=java.io.File(context.cacheDir,"synthetic-cancelled-save.png");file.delete()
  try{ActivityScenario.launch(MainActivity::class.java).use{scenario->
   lateinit var model:AuthViewModel
   scenario.onActivity{model=ViewModelProvider(it)[AuthViewModel::class.java]}
   compose.waitUntil(10000){model.screen.value.member!=null&&!model.screen.value.busy}
   var prepared=false
   scenario.onActivity{model.prepareEvidenceSave(EvidenceView(id="proof",kind="photo",media_type="image/png",size=3)){prepared=true}}
   compose.waitUntil(10000){prepared&&!model.screen.value.busy}
   scenario.onActivity{model.select("https://other.vowen.invalid")}
   compose.waitUntil(10000){model.screen.value.origin=="https://other.vowen.invalid"&&!model.screen.value.busy}
   scenario.onActivity{model.completeEvidenceSave(Uri.fromFile(file))}
   compose.waitUntil(10000){model.screen.value.error!=null&&!model.screen.value.busy}
   assertFalse(file.exists())
  }}finally{file.delete();clear(context)}
 }
}
