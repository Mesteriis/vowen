package org.vowen.app

import androidx.compose.runtime.mutableStateOf
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.launch
import java.util.Locale

/** Memory-only capability state survives activity recreation, never saved to disk/bundles. */
class GuestViewModel:ViewModel() {
 val visibleState=mutableStateOf(false)
 val linkState=mutableStateOf("")
 val ruState=mutableStateOf(Locale.getDefault().language=="ru")
 val accessState=mutableStateOf<FormAccess?>(null)
 val resultState=mutableStateOf<FormResult?>(null)
 val apiState=mutableStateOf<GuestApi?>(null)
 val apiOriginState=mutableStateOf("")
 val receiptModeState=mutableStateOf(false)
 val receiptLinkState=mutableStateOf<String?>(null)
 val busyState=mutableStateOf(false)
 val messageState=mutableStateOf("")
 val confirmState=mutableStateOf(false)
 val draftState=mutableStateOf<NativeFormDraft?>(null)
 fun runAction(action:suspend ()->Unit) {
  if(busyState.value)return
  busyState.value=true;messageState.value=""
  viewModelScope.launch {
   try {action()}catch(_:Exception){messageState.value=if(ruState.value)"Запрос не подтверждён. Ввод остаётся в этом окне." else "Request not confirmed. Your input remains in this window."}
   finally {busyState.value=false}
  }
 }
 fun close() {
  if(busyState.value)return
  visibleState.value=false;linkState.value="";accessState.value=null;resultState.value=null
  apiState.value=null;apiOriginState.value="";receiptModeState.value=false
  receiptLinkState.value=null;messageState.value="";confirmState.value=false;draftState.value=null
 }
}
