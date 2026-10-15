package org.vowen.app

import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.*
import okhttp3.*
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.*
import org.junit.Test

class M4ApiTest {
 @Test fun disciplineDecisionBindsExactVersionAndJournalEditPreservesAudience() = runBlocking {
  val captured=mutableListOf<Pair<Request,String>>()
  val transport=OkHttpClient.Builder().addInterceptor {chain->
   val r=chain.request();captured.add(r to okio.Buffer().also {r.body?.writeTo(it)}.readUtf8())
   val response=if(r.url.encodedPath.contains("discipline")) """{"id":"d","author_id":"a","recipient_id":"b","reviewer_ids":["a"],"version_id":"v","revision":7,"status":"accepted","effective":true,"versions":[],"history":[]}""" else """{"id":"j","author_id":"b","revision":3,"date":"2026-10-15","title":"Diary","text":"Private","visibility":"all_current_members","reader_ids":["a"],"published":true,"created_at":"now","updated_at":"now"}"""
   Response.Builder().request(r).protocol(Protocol.HTTP_1_1).code(200).message("Synthetic").body(response.toResponseBody()).build()
  }.build()
  val state=InstanceSession().apply {select("https://instance.example");accessToken="synthetic"}
  val api=Api(state,client=transport)
  val r=DisciplineRecord(id="d",author_id="a",recipient_id="b",reviewer_ids=listOf("a"),version_id="v",revision=6,status="proposed",effective=false,versions=emptyList(),history=emptyList())
  api.decideDiscipline(r,"accept","Personal acceptance")
  val decision=Json.parseToJsonElement(captured.last().second).jsonObject
  assertEquals("v",decision["version_id"]!!.jsonPrimitive.content)
  assertEquals(6,decision["expected_version"]!!.jsonPrimitive.int)
  assertEquals("accept",decision["action"]!!.jsonPrimitive.content)
  val entry=JournalEntry(id="j",author_id="b",revision=2,date="2026-10-15",title="Diary",text="Private",created_at="now",updated_at="now",visibility="all_current_members",published=true,reader_ids=listOf("a"))
  api.saveJournal(entry,JournalContent(date=entry.date,title=entry.title,text="Updated",visibility=entry.visibility,published=true,reader_ids=entry.reader_ids),false)
  val edit=Json.parseToJsonElement(captured.last().second).jsonObject
  assertEquals("PATCH",captured.last().first.method)
  assertEquals(2,edit["expected_version"]!!.jsonPrimitive.int)
  assertEquals(false,edit["refresh_audience"]!!.jsonPrimitive.boolean)
  assertEquals(listOf("a"),edit["reader_ids"]!!.jsonArray.map {it.jsonPrimitive.content})
  assertTrue(captured.all {it.first.header("Authorization")=="Bearer synthetic"})
 }
}
