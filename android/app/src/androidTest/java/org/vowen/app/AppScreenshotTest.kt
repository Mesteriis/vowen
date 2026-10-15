package org.vowen.app

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createEmptyComposeRule
import androidx.test.core.app.ActivityScenario
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Rule
import org.junit.Test

/** Real shipped MainActivity/navigation/insets, synthetic test-only transport. No live-auth claim. */
class AppScreenshotTest {
 @get:Rule val compose=createEmptyComposeRule()
 @Test fun actualMainActivityM4Navigation(){
  val inst=InstrumentationRegistry.getInstrumentation()
  val context=inst.targetContext
  val preferences=context.getSharedPreferences("instance",0)
  context.getSharedPreferences("appearance",0).edit().putString("theme","light").commit()
  TestApplication.screenshotFixture=true
  preferences.edit().putString("origin","https://qa.vowen.invalid").commit()
  TokenVault(context).save("https://qa.vowen.invalid","synthetic-screen-refresh")
  try {
   ActivityScenario.launch(MainActivity::class.java).use{
    compose.waitUntil(10000){compose.onAllNodesWithTag("tab-discipline").fetchSemanticsNodes().isNotEmpty()}
    compose.onNodeWithTag("tab-surveys").performScrollTo().performClick()
    compose.onNodeWithTag("new-survey").performScrollTo().assertExists()
    compose.onNodeWithTag("tab-notifications").performScrollTo().performClick()
    compose.onNodeWithTag("save-notifications").performScrollTo().assertExists()
    java.io.File(context.cacheDir,"m5-app-notifications.png").outputStream().use{out->inst.uiAutomation.takeScreenshot()!!.compress(android.graphics.Bitmap.CompressFormat.PNG,100,out)}
    compose.onNodeWithTag("Appearance").assertDoesNotExist()
    it.onActivity{activity->org.junit.Assert.assertFalse(androidx.core.view.WindowCompat.getInsetsController(activity.window,activity.window.decorView).isAppearanceLightStatusBars)}
    compose.onNodeWithTag("tab-discipline").performScrollTo().performClick()
    compose.onNodeWithTag("new-discipline").performScrollTo().assertExists()
    java.io.File(context.cacheDir,"m4-app-discipline.png").outputStream().use{out->inst.uiAutomation.takeScreenshot()!!.compress(android.graphics.Bitmap.CompressFormat.PNG,100,out)}
    compose.onNodeWithTag("tab-journal").performScrollTo().performClick()
    compose.onNodeWithTag("new-journal").performScrollTo().performClick()
    compose.onNodeWithTag("journal-title").performScrollTo().performTextInput("Synthetic private reflection")
    compose.onNodeWithTag("journal-text").performScrollTo().performTextInput("This is synthetic QA content.")
    compose.onNodeWithTag("journal-published").performScrollTo().assertIsOff()
    java.io.File(context.cacheDir,"m4-app-journal.png").outputStream().use{out->inst.uiAutomation.takeScreenshot()!!.compress(android.graphics.Bitmap.CompressFormat.PNG,100,out)}
   }
  } finally {TokenVault(context).clear();preferences.edit().clear().commit();TestApplication.screenshotFixture=false}
 }
 @Test fun actualMainActivityRitualViewport(){
  val inst=InstrumentationRegistry.getInstrumentation()
  val context=inst.targetContext
  val preferences=context.getSharedPreferences("instance",0)
  TestApplication.screenshotFixture=true
  preferences.edit().putString("origin","https://qa.vowen.invalid").commit()
  TokenVault(context).save("https://qa.vowen.invalid","synthetic-screen-refresh")
  try {
   ActivityScenario.launch(MainActivity::class.java).use{
    compose.waitUntil(10000){compose.onAllNodesWithTag("tab-rituals").fetchSemanticsNodes().isNotEmpty()}
    compose.onNodeWithTag("tab-rituals").performScrollTo().performClick()
    compose.onNodeWithText("Vowen",useUnmergedTree=true).performScrollTo()
    compose.waitForIdle()
    val bitmap=inst.uiAutomation.takeScreenshot()!!
    val width=context.resources.configuration.screenWidthDp
    if(width>=720)compose.onNodeWithTag("expanded-navigation").assertExists()
    val values=android.content.ContentValues().apply{put(android.provider.MediaStore.Images.Media.DISPLAY_NAME,if(width>=600)"rituals-app-reviewed-tablet.png" else "rituals-app-reviewed-phone.png");put(android.provider.MediaStore.Images.Media.MIME_TYPE,"image/png");put(android.provider.MediaStore.Images.Media.RELATIVE_PATH,"Pictures/VowenQA")}
    val uri=context.contentResolver.insert(android.provider.MediaStore.Images.Media.EXTERNAL_CONTENT_URI,values)!!
    context.contentResolver.openOutputStream(uri)!!.use{bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)}
    fun capture(name:String){val picture=inst.uiAutomation.takeScreenshot()!!;val meta=android.content.ContentValues().apply{put(android.provider.MediaStore.Images.Media.DISPLAY_NAME,name);put(android.provider.MediaStore.Images.Media.MIME_TYPE,"image/png");put(android.provider.MediaStore.Images.Media.RELATIVE_PATH,"Pictures/VowenQA")};val target=context.contentResolver.insert(android.provider.MediaStore.Images.Media.EXTERNAL_CONTENT_URI,meta)!!;context.contentResolver.openOutputStream(target)!!.use{picture.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)}}
    compose.onNodeWithTag("report-o").performScrollTo().performClick()
    compose.onNodeWithTag("ritual-evidence-links").assertExists()
    compose.waitForIdle();capture(if(width>=720)"evidence-app-tablet.png" else "evidence-app-phone.png")
    compose.onNodeWithText("Cancel").performClick()
    compose.onNodeWithTag("tab-rewards").performScrollTo().performClick()
    compose.onNodeWithText("Vowen",useUnmergedTree=true).performScrollTo()
    compose.waitForIdle();capture(if(width>=720)"rewards-app-tablet.png" else "rewards-app-phone.png")

   }
  } finally {TokenVault(context).clear();preferences.edit().clear().commit();TestApplication.screenshotFixture=false}
 }
}
