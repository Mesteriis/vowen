package org.vowen.app

import androidx.compose.runtime.mutableStateOf
import androidx.lifecycle.ViewModel

/** Transient app-memory draft survives rotation/folding; never serialized to disk or logs. */
class JournalDraftState {
 val editing=mutableStateOf(false)
 val selected=mutableStateOf<JournalEntry?>(null)
 val title=mutableStateOf("")
 val text=mutableStateOf("")
 val ink=mutableStateOf<InkDocument?>(null)
 val visibility=mutableStateOf("private")
 val readers=mutableStateOf(emptyList<String>())
 val published=mutableStateOf(false)
 val refresh=mutableStateOf(false)
 val writing=mutableStateOf(false)
 var observedCompleted:Int?=null
 fun begin(entry:JournalEntry?){
  selected.value=entry;title.value=entry?.title?:"";text.value=entry?.text?:""
  ink.value=entry?.handwriting;visibility.value=entry?.visibility?:"private"
  readers.value=entry?.reader_ids?:emptyList();published.value=entry?.published?:false
  refresh.value=false;writing.value=false;editing.value=true
 }
}
class JournalDraftViewModel:ViewModel(){
 private var sessionId:String?=null
 private var state=JournalDraftState()
 fun bind(id:String?):JournalDraftState{
  if(id!=sessionId){sessionId=id;state=JournalDraftState()}
  return state
 }
}
