package org.vowen.app

import android.app.Application
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
 data class Screen(val origin:String="",val member:Member?=null,val challenge:Challenge?=null,val busy:Boolean=false,val error:String?=null,val workspace:WorkspaceState=WorkspaceState(),val sessionId:String?=null,val completed:Int=0,val formLink:String?=null)
 private val mutable=MutableStateFlow(Screen())
 val screen=mutable.asStateFlow()
 private val instance=InstanceSession()
 private val vault=TokenVault(application)
 private val api=Api(instance,{vault.load(instance.origin)},{vault.save(instance.origin,it)},clearRefresh={vault.clear()})
 private val preferences=application.getSharedPreferences("instance",0)
 private val mutex=Mutex()
 private var nonce:String?=null
 init {
  preferences.getString("origin",null)?.let { savedOrigin ->
   try {
    instance.select(savedOrigin)
    mutable.value=Screen(origin=instance.origin)
    run { vault.load(instance.origin)?.let { tokens(api.refresh(it)) } }
   } catch (_: IllegalArgumentException) { vault.clear(); preferences.edit().clear().apply() }
  }
 }
 private fun run(action:suspend ()->Unit) { viewModelScope.launch { mutex.withLock {
  mutable.value=mutable.value.copy(busy=true,error=null)
  try { action() } catch(_:Exception) { if(instance.accessToken==null && mutable.value.member!=null) clear(); mutable.value=mutable.value.copy(error="Request failed. Retry or sign in again. / Ошибка запроса. Повторите вход.") }
  finally { mutable.value=mutable.value.copy(busy=false) }
 } } }
 fun select(origin:String)=run {
  if(instance.select(origin)) {vault.clear();nonce=null;mutable.value=Screen(origin=instance.origin)}
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
 fun logout()=run { try { api.call("/auth/logout","POST") } finally { clear() } }
 private fun clear() { instance.clear();vault.clear();nonce=null;mutable.value=Screen(origin=instance.origin) }
}
