package org.vowen.app

import android.app.Application
import android.net.Uri
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import android.util.Base64
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.security.SecureRandom

/** One serialized auth lane: switching instances cannot race an old network response. */
class AuthViewModel(application:Application):AndroidViewModel(application) {
 data class Screen(val origin:String="",val member:Member?=null,val challenge:Challenge?=null,val busy:Boolean=false,val error:String?=null,val workspace:WorkspaceState=WorkspaceState(),val sessionId:String?=null,val completed:Int=0,val formLink:String?=null,val booting:Boolean=true)
 private val mutable=MutableStateFlow(Screen())
 val screen=mutable.asStateFlow()
 private val instance=InstanceSession()
 private val vault=TokenVault(application)
 private val api=(application as VowenApplication).createApi(instance,{vault.load(instance.origin)},{vault.save(instance.origin,it)},{vault.clear()})
 private val preferences=application.getSharedPreferences("instance",0)
 private val mutex=Mutex()
 private var nonce:String?=null
 private data class EvidenceSave(val evidence:EvidenceView,val origin:String,val sessionId:String,val memberId:String)
 private var pendingEvidenceSave:EvidenceSave?=null
 init {
  var restoring=false
  preferences.getString("origin",null)?.let { savedOrigin ->
   try {
    instance.select(savedOrigin)
    mutable.value=Screen(origin=instance.origin)
    restoring=true
    run { vault.load(instance.origin)?.let { tokens(api.refresh(it)) } }
   } catch (_: IllegalArgumentException) { vault.clear(); preferences.edit().clear().apply() }
  }
  if(!restoring)mutable.value=mutable.value.copy(booting=false)
 }
 private fun run(action:suspend ()->Unit) { viewModelScope.launch { mutex.withLock {
  mutable.value=mutable.value.copy(busy=true,error=null)
  try { action() } catch(_:Exception) { if(instance.accessToken==null && mutable.value.member!=null) clear(); mutable.value=mutable.value.copy(error="Request failed. Retry or sign in again. / Ошибка запроса. Повторите вход.") }
  finally { mutable.value=mutable.value.copy(busy=false,booting=false) }
 } } }
 fun select(origin:String)=run {
  if(instance.select(origin)) {pendingEvidenceSave=null;vault.clear();nonce=null;mutable.value=Screen(origin=instance.origin)}
  preferences.edit().putString("origin",instance.origin).apply()
  val saved=vault.load(instance.origin)
  if(saved!=null) {
   try { tokens(api.refresh(saved)) } catch(_:Exception) { clear() }
  }
 }
 private suspend fun tokens(tokens:Tokens) {
  vault.save(instance.origin,tokens.refresh_token)
  instance.accessToken=tokens.access_token
  mutable.value=mutable.value.copy(member=api.me(),challenge=null,workspace=api.workspace(),sessionId=tokens.session_id)
  nonce=null
 }
 fun begin()=run {
  require(instance.origin.isNotBlank())
  nonce=Base64.encodeToString(ByteArray(32).also { SecureRandom().nextBytes(it) },Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING)
  mutable.value=mutable.value.copy(challenge=api.challenge(nonce!!))
 }
 fun poll()=run {
  val challenge=mutable.value.challenge?:return@run
  val currentNonce=nonce?:return@run
  when(api.status(challenge,currentNonce).status) {
   "approved" -> tokens(api.consume(challenge,currentNonce))
   "pending" -> Unit
   else -> { nonce=null;mutable.value=mutable.value.copy(challenge=null,error="Login rejected / Вход отклонён") }
  }
 }
 fun pause()=run {
  api.call(if(mutable.value.member?.paused==true) "/me/resume" else "/me/pause","POST")
  loadWorkspace()
 }
 private suspend fun loadWorkspace(changed:Boolean=false) {
  val member=api.me()
  val workspace=api.workspace()
  mutable.value=mutable.value.copy(member=member,workspace=workspace,completed=mutable.value.completed+if(changed)1 else 0)
 }
 fun refreshWorkspace()=run {loadWorkspace()}
 fun propose(proposal:RelationProposal)=run {api.propose(proposal);loadWorkspace(true)}
 fun relationAction(relation:Relation,action:String)=run {api.transition(relation,action);loadWorkspace(true)}
 fun changeRelation(relation:Relation,agreement:String,scopes:List<String>)=run {
  api.change(relation,RelationChange(agreement_text=agreement,expected_version=relation.version,scopes=scopes));loadWorkspace(true)
 }
 val wikiApi by lazy { WikiApi(api) }
 suspend fun referenceEntries(kind:String):List<ReferenceEntry> = api.referenceEntries(kind)
 fun addPractice(command:PracticeCreate)=run {api.addPractice(command);loadWorkspace(true)}
 suspend fun administration():AdministrationView=api.administration()
 fun changeAdministrator(id:String,action:String,revision:Int)=run {api.changeAdministrator(id,action,revision);loadWorkspace(true)}
 suspend fun participantProfile():ProfileView = api.participantProfile()
 suspend fun profileDraft():ProfileDraftView = api.profileDraft()
 suspend fun saveProfileDraft(patch:ProfileDraftPatch):ProfileDraftView = api.saveProfileDraft(patch)
 suspend fun publishProfileDraft(version:Int):ProfileView {val result=api.publishProfileDraft(version);loadWorkspace(true);return result}
 suspend fun discardProfileDraft(version:Int) = api.discardProfileDraft(version)
 fun saveProfile(patch:ProfilePatch)=run {api.updateProfile(patch);loadWorkspace(true)}
 fun revokeSession(session:DeviceSession)=run {
  api.revokeSession(session.id)
  if(session.id==mutable.value.sessionId) clear() else loadWorkspace(true)
 }
 fun saveForm(template:FormTemplate?,schema:FormSchema)=run {api.saveForm(template?.id,schema,template?.revision?:1,template?.status=="draft"||template==null);loadWorkspace(true)}
 fun publishForm(template:FormTemplate)=run {api.publishForm(template);loadWorkspace(true)}
 fun inviteForm(template:FormTemplate,command:FormInvitationCreate)=run {
  val invitation=api.inviteForm(template.id,command)
  mutable.value=mutable.value.copy(formLink=invitation.link,error=invitation.delivery_status)
  loadWorkspace(true)
 }
 fun saveFormDraft(id:String,answers:Map<String,kotlinx.serialization.json.JsonElement>)=run {api.saveFormDraft(id,answers);loadWorkspace(true)}
 fun submitForm(id:String,command:FormSubmit)=run {api.submitForm(id,command);loadWorkspace(true)}
 fun deleteFormResult(id:String)=run {api.deleteFormResult(id);loadWorkspace(true)}
 fun ruleHistory(rule:RuleTemplate)=run {val history=api.ruleHistory(rule);mutable.value=mutable.value.copy(workspace=mutable.value.workspace.copy(ruleHistory=history))}
 fun saveRule(rule:RuleTemplate?,body:RuleContent)=run {api.saveRule(rule,body);loadWorkspace(true)}
 fun ruleTemplate(rule:RuleTemplate,action:String)=run {api.ruleTemplate(rule,action);loadWorkspace(true)}
 fun assignRule(rule:RuleTemplate,body:RuleAssign)=run {api.assignRule(rule,body);loadWorkspace(true)}
 fun decideRule(assignment:RuleAssignment,action:String)=run {api.decideRule(assignment,action);loadWorkspace(true)}
 fun punishmentTemplates(rid:String,done:(List<PunishmentTemplateView>)->Unit)=run{done(api.punishmentTemplates(rid))}
 fun savePunishmentTemplate(item:PunishmentTemplateView?,body:PunishmentTemplateCreate,done:()->Unit)=run{api.savePunishmentTemplate(item,body);done()}
 fun archivePunishmentTemplate(item:PunishmentTemplateView,done:()->Unit)=run{api.archivePunishmentTemplate(item);done()}
 fun assignPunishment(item:PunishmentTemplateView,body:PunishmentAssign,done:()->Unit)=run{api.assignPunishment(item,body);loadWorkspace(true);done()}
 fun disciplineDictionary(rid:String,kind:String,name:String?,done:(List<String>)->Unit)=run{done(api.disciplineDictionary(rid,kind,name))}
 fun createDiscipline(body:DisciplineCreate)=run{api.createDiscipline(body);loadWorkspace(true)}
 fun reviseDiscipline(r:DisciplineRecord,body:DisciplineEdit)=run{api.reviseDiscipline(r,body);loadWorkspace(true)}
 fun decideDiscipline(r:DisciplineRecord,action:String,comment:String)=run{api.decideDiscipline(r,action,comment);loadWorkspace(true)}
 fun saveJournal(e:JournalEntry?,body:JournalContent,refresh:Boolean)=run{api.saveJournal(e,body,refresh);loadWorkspace(true)}
 fun deleteJournal(e:JournalEntry)=run{api.deleteJournal(e);loadWorkspace(true)}
 fun createRitualToAssign(body:RitualContent,ready:(RitualTemplate)->Unit)=run{val draft=api.saveRitual(null,body);val published=api.ritualTemplate(draft,"publish");loadWorkspace();ready(published)}
 fun ritualRewards(a:RitualAssignment,body:RewardBundleEdit)=run{api.ritualRewards(a,body);loadWorkspace(true)}
 fun saveRitual(r:RitualTemplate?,body:RitualContent)=run{api.saveRitual(r,body);loadWorkspace(true)}
 fun ritualTemplate(r:RitualTemplate,action:String)=run{api.ritualTemplate(r,action);loadWorkspace(true)}
 fun ritualHistory(r:RitualTemplate)=run{val history=api.ritualHistory(r);mutable.value=mutable.value.copy(workspace=mutable.value.workspace.copy(ritualHistory=history))}
 fun assignRitual(r:RitualTemplate,body:RitualAssign)=run{api.assignRitual(r,body);loadWorkspace(true)}
 fun scheduleRitual(a:RitualAssignment,s:RitualSchedule)=run{api.scheduleRitual(a,s);loadWorkspace(true)}
 fun ritualAssignment(a:RitualAssignment,action:String)=run{api.ritualAssignment(a,action);loadWorkspace(true)}
 fun reportRitual(o:RitualOccurrence,text:String,key:String,links:List<String>,evidenceIds:List<String>)=run{api.reportRitual(o,text,key,links,evidenceIds);loadWorkspace(true)}
 fun reviewRitual(o:RitualOccurrence,decision:String,comment:String)=run{api.reviewRitual(o,decision,comment);loadWorkspace(true)}
 fun createChangeRequest(body:ChangeRequestCreate)=run{api.createChangeRequest(body);loadWorkspace(true)}
 fun decideChangeRequest(row:ChangeRequestView,action:String,comment:String)=run{api.decideChangeRequest(row,action,comment);loadWorkspace(true)}
 fun skipRitual(o:RitualOccurrence)=run{api.skipRitual(o);loadWorkspace(true)}

 fun stagedEvidence(o:RitualOccurrence,done:(List<EvidenceView>)->Unit)=run{done(api.stagedEvidence(o))}
 fun uploadEvidence(o:RitualOccurrence,body:EvidenceUpload,done:(EvidenceView)->Unit)=run{done(api.uploadEvidence(o,body))}
 fun prepareEvidenceSave(e:EvidenceView,ready:()->Unit)=run {
  val screen=mutable.value
  pendingEvidenceSave=EvidenceSave(e,instance.origin,screen.sessionId?:error("Sign in again"),screen.member?.id?:error("Sign in again"))
  ready()
 }
 fun completeEvidenceSave(destination:Uri?)=run {
  val pending=pendingEvidenceSave;pendingEvidenceSave=null
  if(destination==null)return@run
  check(pending!=null){"Save request expired"}
  fun sameSession()=instance.origin==pending.origin&&mutable.value.sessionId==pending.sessionId&&mutable.value.member?.id==pending.memberId
  check(sameSession()){"Save request expired"}
  val media=withContext(Dispatchers.IO){api.downloadEvidence(pending.evidence)}
  check(sameSession()){"Save request expired"}
  withContext(Dispatchers.IO){
   val bytes=Base64.decode(media.data_base64,Base64.DEFAULT)
   getApplication<Application>().contentResolver.openOutputStream(destination)?.use{it.write(bytes)}?:error("Cannot save file")
  }
 }
 fun discardEvidence(e:EvidenceView,done:()->Unit)=run{api.discardEvidence(e);done()}
 private suspend fun economyLoaded(rid:String?){val relationId=rid.orEmpty();val wallet=if(relationId.isEmpty())null else api.wallet(relationId);val shop=api.shop(relationId);mutable.value=mutable.value.copy(workspace=mutable.value.workspace.copy(economyRelationId=rid,wallet=wallet,shop=shop))}
 fun loadEconomy(rid:String)=run{economyLoaded(rid)}
 fun creditCoins(rid:String,body:CreditCommand)=run{api.creditCoins(rid,body);loadWorkspace(true);economyLoaded(rid)}
 fun listingAudience(version:String,done:(List<ShopListing>)->Unit)=run{done(api.listingAudience(version))}
 fun setListingAudience(rid:String,body:AvailabilityCommand)=run{api.setListingAudience(body);loadWorkspace(true);economyLoaded(rid)}
 fun createListing(rid:String,body:ListingCommand)=run{api.createListing(rid,body);loadWorkspace(true);economyLoaded(rid)}
 fun purchase(s:ShopListing,key:String)=run{api.purchase(s,key);loadWorkspace(true);economyLoaded(s.purchase_relation_id?:s.relation_id.orEmpty())}
 fun editListing(s:ShopListing)=run{api.editListing(s);loadWorkspace(true);economyLoaded(s.purchase_relation_id?:s.relation_id.orEmpty())}
 fun saveReward(r:RewardDefinition?,body:RewardContent)=run{api.saveReward(r,body);loadWorkspace(true)}
 fun grantReward(body:GrantCommand)=run{api.grantReward(body);loadWorkspace(true)}
 fun transitionReward(g:RewardGrant,action:String)=run{val rid=mutable.value.workspace.economyRelationId;api.transitionReward(g,action);loadWorkspace(true);economyLoaded(rid)}
 fun formManagement(f:FormTemplate,done:(List<FormInvitation>)->Unit)=run{done(api.formManagement(f))}
 fun archiveForm(f:FormTemplate)=run{api.archiveForm(f);loadWorkspace(true)}
 fun revokeFormInvitation(i:FormInvitation)=run{api.revokeFormInvitation(i);loadWorkspace(true)}
 fun removeFormReader(i:FormInvitation,uid:String)=run{api.removeFormReader(i,uid);loadWorkspace(true)}
 fun createSurvey(body:SurveyCreate)=run{api.createSurvey(body);loadWorkspace(true)}
 fun transitionSurvey(p:SurveyPlan,action:String)=run{api.transitionSurvey(p,action);loadWorkspace(true)}
 fun sendSurvey(p:SurveyPlan,key:String,done:()->Unit)=run{api.sendSurvey(p,key);done();loadWorkspace(true)}
 fun surveyWaves(p:SurveyPlan,done:(List<SurveyWave>)->Unit)=run{done(api.surveyWaves(p))}
 fun updateNotifications(body:NotificationPatch)=run{api.updateNotifications(body);loadWorkspace(true)}
 fun logout()=run { try { api.call("/auth/logout","POST") } finally { clear() } }
 private fun clear() { pendingEvidenceSave=null;instance.clear();vault.clear();nonce=null;mutable.value=Screen(origin=instance.origin,booting=false) }

 fun createShopProduct(body:ShopProductContent)=run{val rid=mutable.value.workspace.economyRelationId;api.createShopProduct(body);loadWorkspace(true);economyLoaded(rid)}
 fun editShopProduct(item:ShopListing,body:ShopProductEdit)=run{val rid=mutable.value.workspace.economyRelationId;api.editShopProduct(item,body);loadWorkspace(true);economyLoaded(rid)}
 fun removeShopProduct(item:ShopListing)=run{val rid=mutable.value.workspace.economyRelationId;api.removeShopProduct(item);loadWorkspace(true);economyLoaded(rid)}
 fun toggleShopRelation(item:ShopListing)=run{val rid=mutable.value.workspace.economyRelationId;api.toggleShopRelation(item);loadWorkspace(true);economyLoaded(rid)}
}
