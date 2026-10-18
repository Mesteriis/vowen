package org.vowen.app

import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.*
import okhttp3.*
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.*
import org.junit.Test

class ParticipantProfileApiTest {
 @Test fun privateDraftUsesExpectedVersionAndExplicitClear()=runBlocking {
  val requests=mutableListOf<Pair<Request,String>>()
  val response="""{"document":{"identity":{"display_name":"Alex","bio":"Private"}},"version":4,"base_profile_version":0,"base_account_version":1,"step":2,"deferred":false}"""
  val transport=OkHttpClient.Builder().addInterceptor {chain->
   val request=chain.request();requests.add(request to okio.Buffer().also{request.body?.writeTo(it)}.readUtf8())
   Response.Builder().request(request).protocol(Protocol.HTTP_1_1).code(if(request.method=="DELETE")204 else 200).message("Synthetic").body(response.toResponseBody()).build()
  }.build()
  val session=InstanceSession().apply{select("https://instance.example");accessToken="synthetic"}
  val api=Api(session,client=transport)
  assertEquals(2,api.profileDraft().step)
  api.saveProfileDraft(ProfileDraftPatch(expected_version=4,step=3,section="identity",value=mapOf("display_name" to JsonPrimitive("Alex"),"bio" to JsonPrimitive(""),"gender_uid" to JsonNull)))
  val body=Json.parseToJsonElement(requests.last().second).jsonObject
  assertEquals(4,body["expected_version"]!!.jsonPrimitive.int)
  assertEquals(JsonNull,body["value"]!!.jsonObject["gender_uid"])
  assertEquals("",body["value"]!!.jsonObject["bio"]!!.jsonPrimitive.content)
  api.discardProfileDraft(4)
  assertEquals("4",requests.last().first.url.queryParameter("expected_version"))
  assertTrue(requests.all{it.first.header("Authorization")=="Bearer synthetic"})
 }
}
