package org.vowen.app

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.MediaType.Companion.toMediaType
import java.util.concurrent.TimeUnit


class Api(private val state: InstanceSession,
 private val loadRefresh:()->String? = {null}, private val saveRefresh:(String)->Unit = {},
 private val client:OkHttpClient=OkHttpClient.Builder().followRedirects(false).followSslRedirects(false)
  .callTimeout(20,TimeUnit.SECONDS).build(), private val clearRefresh:()->Unit = {}) {
 private val refreshMutex=Mutex()
 private val json=Json { ignoreUnknownKeys=true; encodeDefaults=false; explicitNulls=false }
 suspend fun call(path:String,method:String="GET",body:String?=null,authenticated:Boolean=true,allowRefresh:Boolean=true):String = withContext(Dispatchers.IO) {
  require(path.startsWith("/") && !path.startsWith("//"))
  val usedOrigin=state.origin
  val usedAccess=state.accessToken
  val builder=Request.Builder().url(usedOrigin+"/api/v1"+path)
  if(authenticated) usedAccess?.let { builder.header("Authorization","Bearer $it") }
  if(method!="GET") builder.method(method,(body?:"{}").toRequestBody("application/json".toMediaType()))
  client.newCall(builder.build()).execute().use { response ->
   if(response.code==401 && authenticated && allowRefresh && usedAccess!=null) {
    response.close()
    refreshMutex.withLock {
     check(state.origin==usedOrigin)
     if(state.accessToken==usedAccess) {
      try {
       val refreshToken=loadRefresh()?:throw IllegalStateException("Sign in again")
       val rotated=refresh(refreshToken)
       check(state.origin==usedOrigin)
       saveRefresh(rotated.refresh_token)
       state.accessToken=rotated.access_token
      } catch(error:Exception) {state.clear();clearRefresh();throw error}
     }
    }
    return@withContext call(path,method,body,authenticated,false)
   }
   if(!response.isSuccessful) throw IllegalStateException("HTTP ${response.code}")
   response.body?.string()?:""
  }
 }
 suspend fun challenge(nonce:String):Challenge = json.decodeFromString(call("/auth/android/challenges","POST",json.encodeToString(ChallengeRequest(client_nonce=nonce,device_label="Android")),false))
 suspend fun status(challenge:Challenge,nonce:String):ChallengeStatus = json.decodeFromString(call("/auth/android/challenges/${challenge.challenge_id}/status","POST",json.encodeToString(Proof(poll_secret=challenge.poll_secret,client_nonce=nonce)),false))
 suspend fun consume(challenge:Challenge,nonce:String):Tokens = json.decodeFromString(call("/auth/android/challenges/${challenge.challenge_id}/consume","POST",json.encodeToString(Proof(poll_secret=challenge.poll_secret,client_nonce=nonce)),false))
 suspend fun refresh(token:String):Tokens = json.decodeFromString(call("/auth/refresh","POST",json.encodeToString(RefreshRequest(token)),false))
 suspend fun me():Member = json.decodeFromString(call("/me"))
 suspend fun participants():List<Participant> = json.decodeFromString(call("/participants"))
 suspend fun relations():List<Relation> = json.decodeFromString(call("/relations"))
 suspend fun sessions():List<DeviceSession> = json.decodeFromString(call("/sessions"))
 suspend fun propose(proposal:RelationProposal):Relation = json.decodeFromString(call("/relations","POST",json.encodeToString(proposal)))
 suspend fun transition(relation:Relation,action:String):Relation {
  require(action in listOf("accept","pause","resume","revoke"))
  val body=if(action=="accept") json.encodeToString(RelationAcceptance(expected_version=relation.version,relation_version_id=relation.relation_version_id)) else json.encodeToString(ExpectedVersion(expected_version=relation.version))
  return json.decodeFromString(call("/relations/${relation.id}/$action","POST",body))
 }
 suspend fun change(relation:Relation,change:RelationChange):Relation = json.decodeFromString(call("/relations/${relation.id}/versions","POST",json.encodeToString(change)))
 suspend fun updateProfile(patch:ProfilePatch):Member = json.decodeFromString(call("/me/preferences","PATCH",json.encodeToString(patch)))
 suspend fun revokeSession(id:String) {call("/sessions/$id","DELETE")}
}
