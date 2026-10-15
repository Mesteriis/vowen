package org.vowen.app

import java.net.URI
import java.util.UUID
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

data class GuestLink(val origin:String,val proof:GuestExchange,val receipt:Boolean) {
 companion object {
  fun parse(value:String):GuestLink {
   val uri=URI(value.trim())
   require(uri.scheme=="https"&&uri.userInfo==null&&uri.query==null&&uri.host!=null)
   val parts=uri.path.split('/')
   require(parts.size==3&&parts[1] in listOf("f","r"))
   UUID.fromString(parts[2])
   val fragment=uri.rawFragment?:error("Missing secret")
   require(fragment.startsWith("token="))
   val token=fragment.removePrefix("token=")
   require(token.matches(Regex("[A-Za-z0-9_-]{40,100}")))
   val state=InstanceSession().apply {select("https://${uri.rawAuthority}")}
   return GuestLink(state.origin,GuestExchange(public_id=parts[2],token=token),parts[1]=="r")
  }
 }
}

/** Capability-only transport. Never shares member tokens or follows redirects. */
class GuestApi(origin:String,private val client:OkHttpClient=OkHttpClient.Builder().followRedirects(false).followSslRedirects(false).callTimeout(20,TimeUnit.SECONDS).build()) {
 private val origin=InstanceSession().apply {select(origin)}.origin
 private val json=Json {ignoreUnknownKeys=true;explicitNulls=false}
 private var cookie:String?=null
 private var csrf:String?=null
 private var context:String?=null
 private suspend fun call(path:String,method:String="GET",body:String?=null):String = withContext(Dispatchers.IO) {
  require(path.startsWith('/')&&!path.startsWith("//"))
  val request=Request.Builder().url(origin+"/api/v1/guest"+path).header("Origin",origin)
  cookie?.let {request.header("Cookie",it)}
  csrf?.let {request.header("X-CSRF-Token",it)}
  context?.let {request.header("X-Guest-Context",it)}
  if(method!="GET")request.method(method,(body?:"{}").toRequestBody("application/json".toMediaType()))
  client.newCall(request.build()).execute().use {response->
   if(!response.isSuccessful)throw IllegalStateException("HTTP ${response.code}")
   response.headers("Set-Cookie").firstOrNull {it.startsWith("__Host-vowen_guest=")}?.let {cookie=it.substringBefore(';')}
   response.body?.string()?:""
  }
 }
 suspend fun exchange(proof:GuestExchange,receipt:Boolean):FormAccess {
  val access:FormAccess=json.decodeFromString(call(if(receipt)"/receipts/exchange" else "/invitations/exchange","POST",json.encodeToString(proof)))
  csrf=access.csrf_token
  context=proof.public_id
  return access
 }
 suspend fun save(answers:Map<String,JsonElement>):FormAccess = json.decodeFromString(call("/draft","PUT",json.encodeToString(FormAnswers(answers))))
 suspend fun submit(command:FormSubmit):FormResult = json.decodeFromString(call("/submit","POST",json.encodeToString(command)))
 suspend fun result():FormResult = json.decodeFromString(call("/submission"))
 suspend fun receipt():String {
  val proof:GuestExchange=json.decodeFromString(call("/receipt","POST"))
  return "$origin/r/${proof.public_id}#token=${proof.token}"
 }
 suspend fun delete() {call("/submission","DELETE")}
}
