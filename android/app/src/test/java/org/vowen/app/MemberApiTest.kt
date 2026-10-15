package org.vowen.app

import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.*
import okhttp3.*
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.*
import org.junit.Test

class MemberApiTest {
 @Test fun memberCommandsUseTypedBodiesExactVersionsAndBearer() = runBlocking {
  val requests=mutableListOf<Pair<Request,String>>()
  val member="""{"id":"a","display_name":"Demo","paused":false,"profile_labels":[],"language":"en","timezone":"UTC","profile_version":1}"""
  val relation="""{"id":"r","dominant_user_id":"a","submissive_user_id":"b","status":"proposed","version":2,"relation_version_id":"v","scopes":["rules.assign"],"agreement_text":"Synthetic","consent_user_ids":["a"]}"""
  val transport=OkHttpClient.Builder().addInterceptor { chain ->
   val request=chain.request()
   val body=okio.Buffer().also {request.body?.writeTo(it)}.readUtf8()
   requests.add(request to body)
   val path=request.url.encodedPath
   val response=when {
    path.endsWith("/participants") -> """[{"id":"b","display_name":"Other","profile_labels":[]}]"""
    path.endsWith("/sessions") -> """[{"id":"s","client":"android","device_label":"Demo","created_at":"2026-10-15T10:00:00Z","expires_at":"2026-11-14T10:00:00Z","revoked":false}]"""
    path.endsWith("/preferences") -> member
    path.endsWith("/relations") && request.method=="GET" -> "[$relation]"
    else -> relation
   }
   Response.Builder().request(request).protocol(Protocol.HTTP_1_1).code(if(request.method=="DELETE")204 else 200).message("Synthetic").body(response.toResponseBody()).build()
  }.build()
  val state=InstanceSession().apply {select("https://instance.example");accessToken="synthetic"}
  val api=Api(state,client=transport)
  assertEquals("b",api.participants().single().id)
  assertEquals("r",api.relations().single().id)
  assertEquals("s",api.sessions().single().id)
  api.propose(RelationProposal(dominant_user_id="a",agreement_text="Synthetic",scopes=listOf("rules.assign"),submissive_user_id="b"))
  val row=api.relations().single()
  api.transition(row,"accept")
  val accepted=Json.parseToJsonElement(requests.last().second).jsonObject
  assertEquals(2,accepted["expected_version"]!!.jsonPrimitive.int)
  assertEquals("v",accepted["relation_version_id"]!!.jsonPrimitive.content)
  api.transition(row,"pause")
  assertEquals(setOf("expected_version"),Json.parseToJsonElement(requests.last().second).jsonObject.keys)
  api.change(row,RelationChange("Updated",2,listOf("rules.assign","rewards.grant")))
  api.updateProfile(ProfilePatch(display_name="New",expected_version=1,language="ru"))
  val patch=Json.parseToJsonElement(requests.last().second).jsonObject
  assertEquals("PATCH",requests.last().first.method)
  assertFalse(patch.containsKey("timezone"))
  api.revokeSession("s")
  assertEquals("DELETE",requests.last().first.method)
  assertTrue(requests.all {it.first.header("Authorization")=="Bearer synthetic"})
 }
 @Test fun challengeProofKeepsNonceAndPollSecretInTheirOwnFields() = runBlocking {
  var body=""
  val transport=OkHttpClient.Builder().addInterceptor { chain ->
   val request=chain.request()
   body=okio.Buffer().also {request.body?.writeTo(it)}.readUtf8()
   Response.Builder().request(request).protocol(Protocol.HTTP_1_1).code(200).message("Synthetic").body("""{"status":"pending"}""".toResponseBody()).build()
  }.build()
  val state=InstanceSession().apply {select("https://instance.example")}
  val api=Api(state,client=transport)
  api.status(Challenge(bot_url="https://t.me/example",challenge_id="c",display_code="123456",expires_at="future",poll_secret="poll-secret"),"client-nonce")
  val proof=Json.parseToJsonElement(body).jsonObject
  assertEquals("client-nonce",proof["client_nonce"]!!.jsonPrimitive.content)
  assertEquals("poll-secret",proof["poll_secret"]!!.jsonPrimitive.content)
 }
}
