package org.vowen.app

import org.junit.Assert.*
import org.junit.Test
import okhttp3.ResponseBody.Companion.toResponseBody
import kotlinx.coroutines.async

/** Markdown and navigation regressions; executed by testDebugUnitTest. */
class WikiStateTest {
 @Test fun refusesUnsafeUrls(){
  assertNull(wikiSafeUrl("javascript:alert(1)"))
  assertNull(wikiSafeUrl("https://a:b@example.org"))
  assertNull(wikiSafeUrl("file:///tmp/x"))
  assertEquals("https://example.org",wikiSafeUrl("https://example.org"))
 }
 @Test fun internalWikiLinksUseOnlyExactPageRoutes(){
  val uid="11111111-2222-4333-8444-555555555555"
  assertEquals(uid,wikiLinkedPage("#wiki?page=$uid"))
  assertEquals("#wiki?page=$uid",wikiSafeUrl("#wiki?page=$uid"))
  assertNull(wikiSafeUrl("#wiki?page=$uid&admin=1"))
  assertNull(wikiSafeUrl("#wiki?page=bad"))
  assertNull(wikiSafeUrl("#settings?admin=1"))
  val blocks=parseWikiMarkdown("[Material](#wiki?page=$uid)")
  assertEquals("#wiki?page=$uid",blocks.flatMap{it.spans}.single().url)
 }
 @Test fun onlyLocalReferenceThumbnails(){
  assertFalse(wikiLocalThumbnail("https://example.org/x.png"))
  assertFalse(wikiLocalThumbnail("/references/../api/private.png"))
  assertTrue(wikiLocalThumbnail("/references/devices/sample.webp"))
 }
 @Test fun repeatedHeadingsGetDifferentAnchors(){
  val blocks=parseWikiMarkdown("# Same\n\n## Same")
  assertEquals(listOf("heading-1","heading-2"),blocks.filter{it.level>0}.map{it.anchor})
 }
 @Test fun htmlAndImagesBecomeText(){
  val blocks=parseWikiMarkdown("<script>alert(1)</script>\n\n![x](https://example.org/image.png)")
  assertTrue(blocks.flatMap{it.spans}.none{it.url!=null})
 }
}

/** Real state and JSON/transport; interceptor replaces only external network delivery. */
class WikiNavigationStateTest {
 private val json=kotlinx.serialization.json.Json{encodeDefaults=true}
 private fun state(respond:(okhttp3.Request)->Pair<Int,String>):WikiState {
  val session=InstanceSession().apply{select("https://wiki-fixture.invalid")}
  val client=okhttp3.OkHttpClient.Builder().addInterceptor{chain->val (code,body)=respond(chain.request());okhttp3.Response.Builder().request(chain.request()).protocol(okhttp3.Protocol.HTTP_1_1).code(code).message("fixture").body(body.toResponseBody()).build()}.build()
  return WikiState(WikiApi(Api(session,client=client)))
 }
 private fun search(title:String,offset:Int=0)=json.encodeToString(WikiSearchView(items=listOf(WikiPageSummary(kind="article",published_at=null,section_uid="s",summary="",thumbnail=null,title=title,uid="p")),limit=50,offset=offset,total=100))
 private fun page()=json.encodeToString(WikiPageView(author_id="u",created_at="2026-10-21",device_uid=null,document=WikiDocument(section_uid="s",title="Page",body="Body"),kind="article",pose_uid=null,practice_uid=null,published_at=null,related_pages=emptyList(),revision_uid="r",uid="p"))
 @Test fun backRestoresQueryAndPagination()=kotlinx.coroutines.runBlocking {
  val state=state{request->200 to if(request.url.encodedPath.endsWith("/search"))search(request.url.queryParameter("q")?:"",request.url.queryParameter("offset")?.toInt()?:0)else page()}
  state.query="remember";state.section="s";state.search(50);state.openPage("p");state.back()
  assertEquals("remember",state.query);assertEquals(50,state.results?.offset);assertEquals("published",state.mode)
 }
 @Test fun readerNavigationLeavesAdminLists()=kotlinx.coroutines.runBlocking {
  val state=state{request->200 to if(request.url.encodedPath.endsWith("/search"))search("Found")else page()}
  state.mode="drafts";state.openPage("p");assertEquals("published",state.mode)
  state.mode="archived";state.search();assertEquals("published",state.mode)
 }
 @Test fun failedSaveRetainsDraft()=kotlinx.coroutines.runBlocking {
  val state=state{500 to "{}"};state.editing=true;state.draft=WikiDocument(section_uid="s",title="Keep me",body="Draft")
  state.save();assertEquals("Keep me",state.draft.title);assertTrue(state.dirty);assertNotNull(state.error)
 }
 @Test fun lateSearchCannotReplaceNewResults()=kotlinx.coroutines.runBlocking {
  val started=java.util.concurrent.CountDownLatch(1);val release=java.util.concurrent.CountDownLatch(1)
  val state=state{request->val q=request.url.queryParameter("q")?:"";if(q=="old"){started.countDown();check(release.await(5,java.util.concurrent.TimeUnit.SECONDS))};200 to search(q)}
  val first=kotlinx.coroutines.CoroutineScope(kotlinx.coroutines.Dispatchers.Default).async{state.query="old";state.search()}
  check(started.await(5,java.util.concurrent.TimeUnit.SECONDS));state.query="new";state.search();release.countDown();first.await()
  assertEquals("new",state.results?.items?.first()?.title)
 }
}
