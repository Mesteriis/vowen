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
 data class Screen(val origin:String="",val member:Member?=null,val challenge:Challenge?=null,val busy:Boolean=false,val error:String?=null)
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
  mutable.value=mutable.value.copy(member=api.me(),challenge=null)
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
  mutable.value=mutable.value.copy(member=api.me())
 }
 fun logout()=run { try { api.call("/auth/logout","POST") } finally { clear() } }
 private fun clear() { instance.clear();vault.clear();nonce=null;mutable.value=Screen(origin=instance.origin) }
}
