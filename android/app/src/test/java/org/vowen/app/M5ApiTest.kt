package org.vowen.app

import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.*
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.*
import org.junit.Test

class M5ApiTest {
 @Test fun settingsAndSurveyCommandsUseTypedContractAndStableRetryKeys()=runBlocking{
  val requests=mutableListOf<Triple<String,String,JsonObject>>()
  val state=InstanceSession().apply{select("https://test.example");accessToken="synthetic"}
  val plan=SurveyPlan(id="p",author_id="a",recipient_id="b",form_version_id="v",idempotency_key="create-key",owner_paused=false,recipient_paused=false,reader_ids=listOf("a"),revision=4,source_effective=true,title="Fixed version")
  val transport=OkHttpClient.Builder().addInterceptor{chain->
   val r=chain.request();val sink=okio.Buffer();r.body?.writeTo(sink)
   requests.add(Triple(r.url.encodedPath,r.method,if(r.body==null)buildJsonObject{} else Json.parseToJsonElement(sink.readUtf8()).jsonObject))
   assertEquals("Bearer synthetic",r.header("Authorization"))
   val body=when{
    r.url.encodedPath.endsWith("/notifications")->Json.encodeToString(NotificationSettings(channels=listOf("in_app"),quiet_enabled=true,quiet_start=1320,quiet_end=480,revision=5,telegram_connected=false,timezone="UTC"))
    r.url.encodedPath.endsWith("/send-now")->Json.encodeToString(SurveyWave(id="w",due_at="now",invitation_id="i",occurrence_id=null,reason=null,status="created"))
    else->Json.encodeToString(plan)
   }
   Response.Builder().request(r).protocol(Protocol.HTTP_1_1).code(200).message("Synthetic").body(body.toResponseBody()).build()
  }.build()
  val api=Api(state,client=transport)
  assertEquals(5,api.updateNotifications(NotificationPatch(channels=listOf("in_app"),expected_version=4,quiet_enabled=true,quiet_start=1320,quiet_end=480)).revision)
  assertEquals("PATCH",requests[0].second)
  api.createSurvey(SurveyCreate(form_version_id="v",recipient_id="b",reader_ids=listOf("a"),ritual_assignment_id="ritual",idempotency_key="create-key"))
  assertEquals("v",requests[1].third["form_version_id"]!!.jsonPrimitive.content)
  api.sendSurvey(plan,"retry-key");api.sendSurvey(plan,"retry-key")
  assertEquals(requests[2],requests[3]);assertEquals(4,requests[2].third["expected_version"]!!.jsonPrimitive.int)
  api.transitionSurvey(plan,"pause");assertEquals("/api/v1/survey-schedules/p/pause",requests.last().first)
 }
 @Test fun guestContactRetainsBigIntIdentity(){
  val body=FormInvitationCreate(reader_ids=emptyList(),contact_telegram_id=100000000009L,deliver=true)
  val encoded=Json.encodeToString(body)
  assertEquals(100000000009L,Json.parseToJsonElement(encoded).jsonObject["contact_telegram_id"]!!.jsonPrimitive.long)
 }
}
