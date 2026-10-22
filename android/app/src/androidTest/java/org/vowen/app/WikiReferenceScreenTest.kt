package org.vowen.app

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.test.platform.app.InstrumentationRegistry
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import kotlinx.serialization.json.Json
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Rule
import org.junit.Test

/** Real Compose screens/state/JSON transport; only network delivery is synthetic. */
class WikiReferenceScreenTest {
 @get:Rule val compose=createComposeRule()
 private val json=Json{encodeDefaults=true}
 private val reference="11111111-2222-4333-8444-555555555555"
 private val page="aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
 private val related="bbbbbbbb-cccc-4ddd-8eee-ffffffffffff"
 private fun summary(uid:String,title:String)=WikiPageSummary(kind="article",published_at=null,section_uid="section",summary="",thumbnail=null,title=title,uid=uid)
 private fun api():WikiApi {
  val session=InstanceSession().apply{select("https://wiki-fixture.invalid")}
  val client=OkHttpClient.Builder().addInterceptor{chain->
   val path=chain.request().url.encodedPath
   val body=when(path){
    "/api/v1/wiki/reference-links/biological-sex"->json.encodeToString(listOf(WikiReferenceLink(page_uid=page,reference_uid=reference)))
    "/api/v1/wiki/tree"->json.encodeToString(WikiTreeView(pages=listOf(summary(page,"Исходная статья"),summary(related,"Связанный материал")),sections=emptyList(),version=1))
    "/api/v1/wiki/pages/$page","/api/v1/wiki/pages/$related"->{val first=path.endsWith(page);json.encodeToString(WikiPageView(author_id="author",created_at="2026-10-22",device_uid=null,document=WikiDocument(section_uid="section",title=if(first)"Исходная статья" else "Связанный материал",body="## Описание\n\nРусское описание из справочника.\n\n[Открыть связанную статью](#wiki?page=$related)"),kind="article",pose_uid=null,practice_uid=null,published_at=null,related_pages=if(first)listOf(summary(related,"Связанный материал"))else emptyList(),revision_uid=if(first)"r1" else "r2",uid=if(first)page else related))}
    else->error("Unexpected Wiki request: $path")
   }
   Response.Builder().request(chain.request()).protocol(Protocol.HTTP_1_1).code(200).message("fixture").body(body.toResponseBody()).build()
  }.build()
  return WikiApi(Api(session,client=client))
 }
 private fun screenshot(){
  val context=InstrumentationRegistry.getInstrumentation().targetContext
  java.io.File(context.filesDir,"wiki-reference-article.png").outputStream().use{compose.onRoot().captureToImage().asAndroidBitmap().compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)}
 }
 @Test fun catalogueOpensServerResolvedArticleAndRelatedMaterial(){
  val wiki=api()
  val member=Member(id="admin",display_name="Тест",is_admin=true,language="ru",paused=false,profile_labels=emptyList(),profile_version=1,timezone="UTC")
  val references=ReferenceActions({listOf(ReferenceEntry(uid=reference,name="Запись справочника",description="Русское описание"))},{},wiki::referenceLinks)
  compose.setContent{MaterialTheme{androidx.compose.foundation.layout.Box(Modifier.fillMaxSize()){WorkspaceScreen(member,WorkspaceState(),null,false,0,WorkspaceActions({},{},{_,_->},{_,_,_->},{},{}),administrationActions=AdministrationActions({AdministrationView(emptyList(),1)},{_,_,_->}),referenceActions=references,wikiApi=wiki)}}}
  // Compact navigation uses More; expanded navigation exposes the settings item directly.
  if(compose.onAllNodesWithTag("tab-settings").fetchSemanticsNodes().isEmpty())compose.onNodeWithText("Ещё").performClick()
  compose.onNodeWithTag("tab-settings").performClick()
  compose.onNodeWithTag("settings-references").performClick()
  compose.waitUntil(10000){compose.onAllNodesWithTag("reference-wiki-$reference").fetchSemanticsNodes().isNotEmpty()}
  compose.onNodeWithTag("reference-wiki-$reference").performScrollTo().performClick()
  compose.waitUntil(10000){compose.onAllNodesWithText("Исходная статья").fetchSemanticsNodes().isNotEmpty()}
  compose.onNodeWithText("Исходная статья").performScrollTo().assertIsDisplayed()
  screenshot()
  compose.onNodeWithText("Открыть связанную статью").performScrollTo().performClick()
  compose.waitUntil(10000){compose.onAllNodesWithText("Связанный материал").fetchSemanticsNodes().isNotEmpty()&&compose.onAllNodesWithText("Исходная статья").fetchSemanticsNodes().isEmpty()}
  compose.onNodeWithText("Связанный материал").performScrollTo().assertIsDisplayed()
 }
 @Test fun failedLinkLookupKeepsCatalogueReadable(){
  val references=ReferenceActions({listOf(ReferenceEntry(uid=reference,name="Запись справочника",description="Описание остаётся доступным"))},{},{error("offline")})
  compose.setContent{MaterialTheme{NativeReferenceScreen(true,false,0,references,{})}}
  compose.waitUntil(10000){compose.onAllNodesWithText("Описание остаётся доступным").fetchSemanticsNodes().isNotEmpty()}
  compose.onNodeWithText("Описание остаётся доступным").assertExists()
  compose.onNodeWithText("Не удалось загрузить ссылки на статьи. Обновите справочник.").assertExists()
  compose.onNodeWithTag("reference-wiki-$reference").assertDoesNotExist()
 }
}
