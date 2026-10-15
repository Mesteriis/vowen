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
 suspend fun forms():List<FormTemplate> = json.decodeFromString(call("/forms"))
 suspend fun formInvitations():List<FormAccess> = json.decodeFromString(call("/form-invitations"))
 suspend fun formResults():List<FormResult> = json.decodeFromString(call("/form-submissions"))
 suspend fun saveForm(id:String?,schema:FormSchema,revision:Int=1,draft:Boolean=true):FormTemplate {
  val path=if(id==null) "/forms" else "/forms/$id"+if(draft) "" else "/versions"
  val body=if(id==null) json.encodeToString(schema) else json.encodeToString(FormEdit(expected_version=revision,schema_body=schema))
  return json.decodeFromString(call(path,if(id!=null&&draft) "PATCH" else "POST",body))
 }
 suspend fun publishForm(form:FormTemplate):FormTemplate = json.decodeFromString(call("/forms/${form.id}/publish","POST",json.encodeToString(ExpectedVersion(form.revision))))
 suspend fun inviteForm(formId:String,command:FormInvitationCreate):FormInvitation = json.decodeFromString(call("/forms/$formId/invitations","POST",json.encodeToString(command)))
 suspend fun saveFormDraft(id:String,answers:Map<String,kotlinx.serialization.json.JsonElement>):FormAccess = json.decodeFromString(call("/form-invitations/$id/draft","PUT",json.encodeToString(FormAnswers(answers))))
 suspend fun submitForm(id:String,command:FormSubmit):FormResult = json.decodeFromString(call("/form-invitations/$id/submit","POST",json.encodeToString(command)))
 suspend fun deleteFormResult(id:String) {call("/form-submissions/$id","DELETE")}
 suspend fun rules():List<RuleTemplate> = json.decodeFromString(call("/rules"))
 suspend fun ruleHistory(rule:RuleTemplate):List<RuleTemplate> = json.decodeFromString(call("/rules/${rule.id}/versions"))
 suspend fun ruleAssignments():List<RuleAssignment> = json.decodeFromString(call("/rule-assignments"))
 suspend fun saveRule(rule:RuleTemplate?,body:RuleContent):RuleTemplate {
  if(rule==null)return json.decodeFromString(call("/rules","POST",json.encodeToString(body)))
  val path="/rules/${rule.id}"+if(rule.status=="draft")"" else "/versions"
  return json.decodeFromString(call(path,if(rule.status=="draft")"PATCH" else "POST",json.encodeToString(RuleEdit(title=body.title,description=body.description,expected_version=rule.revision))))
 }
 suspend fun ruleTemplate(rule:RuleTemplate,action:String):RuleTemplate {
  require(action in listOf("publish","archive"))
  return json.decodeFromString(call("/rules/${rule.id}/$action","POST",json.encodeToString(ExpectedVersion(rule.revision))))
 }
 suspend fun assignRule(rule:RuleTemplate,body:RuleAssign):RuleAssignment = json.decodeFromString(call("/rules/${rule.id}/assignments","POST",json.encodeToString(body)))
 suspend fun decideRule(assignment:RuleAssignment,action:String):RuleAssignment {
  require(action in listOf("accept","decline","pause","revoke"))
  return json.decodeFromString(call("/rule-assignments/${assignment.id}/$action","POST",json.encodeToString(RuleDecision(assignment.revision,assignment.rule_version_id))))
 }

 suspend fun rituals():List<RitualTemplate> = json.decodeFromString(call("/rituals"))
 suspend fun ritualAssignments():List<RitualAssignment> = json.decodeFromString(call("/ritual-assignments"))
 suspend fun ritualOccurrences():List<RitualOccurrence> = json.decodeFromString(call("/ritual-occurrences"))
 suspend fun ritualNotices():List<RitualNotice> = json.decodeFromString(call("/ritual-notices"))
 suspend fun ritualHistory(r:RitualTemplate):List<RitualTemplate> = json.decodeFromString(call("/rituals/${r.id}/versions"))
 suspend fun saveRitual(r:RitualTemplate?,body:RitualContent):RitualTemplate {
  if(r==null)return json.decodeFromString(call("/rituals","POST",json.encodeToString(body)))
  return json.decodeFromString(call("/rituals/${r.id}"+if(r.status=="draft")"" else "/versions",if(r.status=="draft")"PATCH" else "POST",json.encodeToString(RitualEdit(description=body.description,title=body.title,expected_version=r.revision))))
 }
 suspend fun ritualTemplate(r:RitualTemplate,action:String):RitualTemplate {require(action in listOf("publish","archive"));return json.decodeFromString(call("/rituals/${r.id}/$action","POST",json.encodeToString(ExpectedVersion(r.revision))))}
 suspend fun assignRitual(r:RitualTemplate,body:RitualAssign):RitualAssignment = json.decodeFromString(call("/rituals/${r.id}/assignments","POST",json.encodeToString(body)))
 suspend fun scheduleRitual(a:RitualAssignment,s:RitualSchedule):RitualAssignment = json.decodeFromString(call("/ritual-assignments/${a.id}/schedule","PUT",json.encodeToString(RitualScheduleEdit(expected_version=a.revision,schedule=s))))
 suspend fun ritualAssignment(a:RitualAssignment,action:String):RitualAssignment {require(action in listOf("pause","resume","revoke"));return json.decodeFromString(call("/ritual-assignments/${a.id}/$action","POST",json.encodeToString(ExpectedVersion(a.revision))))}
 suspend fun reportRitual(o:RitualOccurrence,text:String,key:String,links:List<String>,evidenceIds:List<String>):RitualOccurrence = json.decodeFromString(call("/ritual-occurrences/${o.id}/report","POST",json.encodeToString(RitualReportCommand(expected_version=o.revision,idempotency_key=key,text=text,links=links,evidence_ids=evidenceIds))))
 suspend fun reviewRitual(o:RitualOccurrence,decision:String,comment:String):RitualOccurrence {require(decision in listOf("approved","needs_changes"));return json.decodeFromString(call("/ritual-occurrences/${o.id}/review","POST",json.encodeToString(RitualReviewCommand(expected_version=o.revision,decision=decision,comment=comment))))}
 suspend fun skipRitual(o:RitualOccurrence):RitualOccurrence = json.decodeFromString(call("/ritual-occurrences/${o.id}/skip","POST",json.encodeToString(ExpectedVersion(o.revision))))

 suspend fun stagedEvidence(o:RitualOccurrence):List<EvidenceView> = json.decodeFromString(call("/ritual-occurrences/${o.id}/evidence"))
 suspend fun uploadEvidence(o:RitualOccurrence,body:EvidenceUpload):EvidenceView=json.decodeFromString(call("/ritual-occurrences/${o.id}/evidence","POST",json.encodeToString(body)))
 suspend fun downloadEvidence(e:EvidenceView):EvidenceDownload=json.decodeFromString(call("/ritual-evidence/${e.id}"))
 suspend fun discardEvidence(e:EvidenceView){call("/ritual-evidence/${e.id}","DELETE")}
 suspend fun rewards():List<RewardDefinition> = json.decodeFromString(call("/rewards"))
 suspend fun rewardGrants():List<RewardGrant> = json.decodeFromString(call("/reward-grants"))
 suspend fun saveReward(r:RewardDefinition?,body:RewardContent):RewardDefinition = json.decodeFromString(call(if(r==null)"/rewards" else "/rewards/${r.id}/versions","POST",if(r==null)json.encodeToString(body) else json.encodeToString(RewardEdit(title=body.title,description=body.description,conditions=body.conditions,expected_version=r.revision))))
 suspend fun grantReward(body:GrantCommand):RewardGrant=json.decodeFromString(call("/reward-grants","POST",json.encodeToString(body)))
 suspend fun transitionReward(g:RewardGrant,action:String):RewardGrant=json.decodeFromString(call("/reward-grants/${g.id}/transitions","POST",json.encodeToString(GrantTransitionCommand(expected_version=g.revision,action=action))))

}
