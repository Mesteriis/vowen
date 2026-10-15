package org.vowen.app

import android.app.Application
import android.content.Context
import androidx.test.runner.AndroidJUnitRunner
import kotlinx.serialization.json.Json
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody
import okhttp3.MediaType.Companion.toMediaType

/** Test APK only: the release application has no fixture toggle or fake auth provider. */
class VowenTestRunner:AndroidJUnitRunner(){
 override fun newApplication(cl:ClassLoader,className:String,context:Context):Application = super.newApplication(cl,TestApplication::class.java.name,context)
}
class TestApplication:VowenApplication(){
 companion object {var screenshotFixture=false}
 override fun createApi(state:InstanceSession,load:()->String?,save:(String)->Unit,clear:()->Unit):Api {
  if(!screenshotFixture)return super.createApi(state,load,save,clear)
  val json=Json
  val client=OkHttpClient.Builder().addInterceptor{chain->
   val path=chain.request().url.encodedPath.removePrefix("/api/v1")
   val body=when(path){
    "/auth/refresh"->json.encodeToString(Tokens(access_expires_at="2099-01-01T00:00Z",access_token="synthetic-screen-access",refresh_token="synthetic-screen-refresh",session_id="synthetic-session"))
    "/me"->json.encodeToString(Member(display_name="Synthetic QA",id="b",language="en",paused=false,profile_labels=emptyList(),profile_version=1,timezone="UTC"))
    "/ritual-occurrences"->json.encodeToString(listOf(RitualOccurrence(evidence_policy=EvidencePolicy(required=true,allowed_types=listOf("link","photo","video")),approval_required=true,assignment_id="a",can_report=true,can_review=false,description="Take a quiet moment and report.",due_at="2026-10-15T09:00Z",expires_at="2026-10-16T09:00Z",id="o",local_day="2026-10-15",recipient_id="b",reports=emptyList(),revision=1,status="scheduled",title="Morning presence")))
    "/ritual-occurrences/o/evidence"->"[]"
    "/ritual-evidence/proof"->json.encodeToString(EvidenceDownload(id="proof",kind="photo",media_type="image/png",size=3,data_base64="AQID"))
    "/reward-notices"->json.encodeToString(listOf(RewardNotice(id="n",grant_id="g",created_at="2026-10-15T09:00Z")))
    "/rewards"->"[]"
    "/reward-grants"->json.encodeToString(listOf(RewardGrant(id="g",reward_version_id="v",issuer_id="a",recipient_id="b",occurrence_id="o",reward_policy_id="p",revision=1,status="offered",created_at="2026-10-15T09:00Z",title="An evening together",description="Choose a shared activity.",conditions="By agreement",history=listOf(GrantHistory(revision=1,status="offered",actor_id="a",created_at="2026-10-15T09:00Z")))))
    "/participants"->json.encodeToString(listOf(Participant(id="a",display_name="Demo A",profile_labels=emptyList()),Participant(id="b",display_name="Synthetic QA",profile_labels=emptyList())))
    "/me/notifications"->json.encodeToString(NotificationSettings(channels=listOf("in_app","telegram"),quiet_enabled=false,quiet_start=1320,quiet_end=480,revision=1,telegram_connected=false,timezone="UTC"))
    "/survey-schedules","/discipline-records","/journal","/relations","/sessions","/forms","/form-invitations","/form-submissions","/rules","/rule-assignments","/rituals","/ritual-assignments","/ritual-notices"->"[]"
    else->error("Unexpected synthetic screenshot request")
   }
   Response.Builder().request(chain.request()).protocol(Protocol.HTTP_1_1).code(200).message("Synthetic QA").body(body.toResponseBody("application/json".toMediaType())).build()
  }.build()
  return Api(state,load,save,client,clear)
 }
}
