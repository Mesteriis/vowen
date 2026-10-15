package org.vowen.app

import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.*
import okhttp3.*
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.*
import org.junit.Test

class FormApiTest {
 @Test fun submitBindsInvitationAndKeepsIdempotencyAcrossRetry() = runBlocking {
  val captured=mutableListOf<Pair<Request,String>>()
  val transport=OkHttpClient.Builder().addInterceptor {chain->
   val r=chain.request();captured.add(r to okio.Buffer().also {r.body?.writeTo(it)}.readUtf8())
   Response.Builder().request(r).protocol(Protocol.HTTP_1_1).code(200).message("Synthetic").body("""{"id":"s","invitation_id":"i","schema_body":{"title":"T","questions":[]},"readers":[],"status":"submitted","answers":{"q":"secret"}}""".toResponseBody()).build()
  }.build()
  val state=InstanceSession().apply {select("https://instance.example");accessToken="member"}
  val api=Api(state,client=transport)
  val command=FormSubmit(answers=mapOf("q" to JsonPrimitive("secret")),idempotency_key="00000000-0000-0000-0000-000000000001",acknowledged=true)
  api.submitForm("i",command);api.submitForm("i",command)
  assertEquals(captured[0].second,captured[1].second)
  assertTrue(captured.all {it.first.url.encodedPath=="/api/v1/form-invitations/i/submit"&&it.first.header("Authorization")=="Bearer member"})
  val body=Json.parseToJsonElement(captured[0].second).jsonObject
  assertFalse(body.containsKey("reader_ids"))
  assertEquals("secret",body["answers"]!!.jsonObject["q"]!!.jsonPrimitive.content)
 }
 @Test fun guestCapabilityUsesCookieCsrfAndNoMemberBearer() = runBlocking {
  val captured=mutableListOf<Request>()
  val transport=OkHttpClient.Builder().addInterceptor {chain->
   val r=chain.request();captured.add(r)
   Response.Builder().request(r).protocol(Protocol.HTTP_1_1).code(200).message("Synthetic")
    .header("Set-Cookie","__Host-vowen_guest=synthetic-cookie; Secure; HttpOnly; Path=/")
    .body("""{"id":"i","schema_body":{"title":"T","questions":[]},"readers":[],"retention_until":"future","retention_days":90,"expires_at":"future","status":"draft","answers":{},"csrf_token":"synthetic-csrf"}""".toResponseBody()).build()
  }.build()
  val api=GuestApi("https://instance.example",transport)
  api.exchange(GuestExchange(public_id="i",token="a".repeat(43)),false)
  api.save(mapOf("q" to JsonPrimitive("draft")))
  assertEquals("https://instance.example",captured.last().header("Origin"))
  assertEquals("synthetic-csrf",captured.last().header("X-CSRF-Token"))
  assertEquals("__Host-vowen_guest=synthetic-cookie",captured.last().header("Cookie"))
  assertTrue(captured.all {it.header("Authorization")==null})
 }
 @Test fun guestLinkRejectsUnsafeOriginsPathsAndQueries() {
  val id="00000000-0000-0000-0000-000000000001"
  val secret="a".repeat(43)
  assertEquals("https://instance.example",GuestLink.parse("https://instance.example/f/$id#token=$secret").origin)
  for(link in listOf("http://instance.example/f/$id#token=$secret","https://user@instance.example/f/$id#token=$secret","https://instance.example/f/$id?token=$secret","https://instance.example/other/$id#token=$secret")) {
   assertTrue(runCatching {GuestLink.parse(link)}.isFailure)
  }
 }
 @Test fun numericVisibilityMatchesBackendAcrossIntegerAndFloat() {
  val q=FormQuestion(id="q",kind="short_text",label="Q",visibility=FormVisibility(all=listOf(FormCondition(question_id="a",op="equals",value=JsonPrimitive(1)))))
  assertTrue(formVisible(q,mapOf("a" to JsonPrimitive(1.0))))
  assertFalse(formVisible(q,mapOf("a" to JsonPrimitive(true))))
 }
}
