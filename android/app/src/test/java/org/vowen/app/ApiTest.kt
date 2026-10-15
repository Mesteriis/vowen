package org.vowen.app

import kotlinx.coroutines.runBlocking
import okhttp3.OkHttpClient
import okhttp3.Response
import okhttp3.Protocol
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.*
import org.junit.Test

class ApiTest {
 @Test fun expiredAccessRotatesRefreshAndRetriesThenInstanceSwitchSendsNoOldBearer() = runBlocking {
  val state=InstanceSession().apply {select("https://first.example");accessToken="old"}
  var refresh="initial-refresh"
  var refreshCount=0
  var secondHostBearer:String?="unobserved"
  val transport=OkHttpClient.Builder().addInterceptor { chain ->
   val request=chain.request()
   val isRefresh=request.url.encodedPath.endsWith("/refresh")
   val code=if(request.url.host=="second.example") {secondHostBearer=request.header("Authorization");200}
    else if(isRefresh) 200 else if(request.header("Authorization")=="Bearer new") 200 else 401
   val body=if(isRefresh) {
    refreshCount++
    """{"access_token":"new","refresh_token":"rotated","access_expires_at":"2026-10-15T10:15:00Z","session_id":"demo"}"""
   } else """{"id":"demo","display_name":"Demo","paused":false}"""
   Response.Builder().request(request).protocol(Protocol.HTTP_1_1).code(code).message("Synthetic").body(body.toResponseBody()).build()
  }.build()
  val api=Api(state,{refresh},{refresh=it},transport)
  assertEquals("Demo",api.me().display_name)
  assertEquals(1,refreshCount)
  assertEquals("rotated",refresh)
  state.select("https://second.example")
  api.me()
  assertNull(secondHostBearer)
 }
 @Test fun revokedRefreshClearsAccessAndStoredRefreshWithoutRetryLoop() = runBlocking {
  val state=InstanceSession().apply {select("https://first.example");accessToken="old"}
  var saved:String?="revoked-refresh"
  var requests=0
  val transport=OkHttpClient.Builder().addInterceptor { chain ->
   requests++
   Response.Builder().request(chain.request()).protocol(Protocol.HTTP_1_1).code(401).message("Synthetic").body("{}".toResponseBody()).build()
  }.build()
  val api=Api(state,{saved},{saved=it},transport,clearRefresh={saved=null})
  try {api.me();fail("Revoked refresh must fail")} catch (_: IllegalStateException) { }
  assertNull(state.accessToken)
  assertNull(saved)
  assertEquals(2,requests)
 }
}
