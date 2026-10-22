package org.vowen.app

import androidx.compose.runtime.*
import kotlinx.coroutines.CancellationException

private data class WikiLocation(val section:String,val pageUid:String?,val query:String,val searchOffset:Int?)

class WikiState(val api:WikiApi) {
 var tree by mutableStateOf<WikiTreeView?>(null)
 var page by mutableStateOf<WikiPageView?>(null)
 var section by mutableStateOf("")
 var query by mutableStateOf("")
 var results by mutableStateOf<WikiSearchView?>(null)
 var error by mutableStateOf<String?>(null)
 var notice by mutableStateOf<String?>(null)
 var busy by mutableStateOf(false)
 var editing by mutableStateOf(false)
 var draft by mutableStateOf(WikiDocument(section_uid="",title="",body=""))
 var saved by mutableStateOf<WikiEditView?>(null)
 var baseline by mutableStateOf(draft)
 var kind by mutableStateOf("article")
 var mainKind by mutableStateOf("practices")
 var mainUid by mutableStateOf<String?>(null)
 var mode by mutableStateOf("published")
 var adminRows by mutableStateOf<List<WikiEditView>>(emptyList())
 var adminOffset by mutableIntStateOf(0)
 private var request=0
 private var searchRequest=0
 private val backStack=mutableListOf<WikiLocation>()
 private fun location()=WikiLocation(section,page?.uid,query,results?.offset)
 val dirty get()=editing&&draft!=baseline
 suspend fun action(block:suspend ()->Unit):Boolean {if(busy)return false;busy=true;error=null;return try{block();true}catch(e:CancellationException){throw e}catch(e:Exception){error=e.message;false}finally{busy=false}}
 suspend fun refresh(){tree=api.tree()}
 suspend fun openPage(uid:String,push:Boolean=true){val token=++request;searchRequest++;try{val loaded=api.page(uid);if(token==request){if(push)backStack.add(location());mode="published";page=loaded;section=loaded.document.section_uid;results=null;query="";error=null}}catch(e:CancellationException){throw e}catch(e:Exception){if(token==request)error=e.message}}
 fun openSection(uid:String,push:Boolean=true){if(push)backStack.add(location());request++;searchRequest++;mode="published";section=uid;page=null;results=null;query=""}
 suspend fun back(){if(backStack.isNotEmpty()){
  val target=backStack.removeAt(backStack.lastIndex)
  if(target.searchOffset!=null){val token=++request;val searchToken=++searchRequest;try{val found=api.search(target.query,target.section,target.searchOffset);if(token==request&&searchToken==searchRequest){section=target.section;query=target.query;results=found;page=null;mode="published";error=null}}catch(e:CancellationException){throw e}catch(e:Exception){if(token==request){error=e.message;backStack.add(target)}}}
  else if(target.pageUid!=null)openPage(target.pageUid,false)else openSection(target.section,false)
 }}
 val hasBack get()=backStack.isNotEmpty()
 suspend fun search(offset:Int=0){request++;val token=++searchRequest;val q=query;val sectionUid=section;try{val found=api.search(q,sectionUid,offset);if(token==searchRequest){mode="published";results=found;error=null}}catch(e:CancellationException){throw e}catch(e:Exception){if(token==searchRequest)error=e.message}}
 suspend fun edit(uid:String?){action{if(uid==null){saved=null;draft=WikiDocument(section_uid=section.ifBlank{tree?.sections?.firstOrNull()?.uid?:""},title="",body="");kind="article";mainUid=null}else{val record=api.edit(uid);saved=record;draft=record.document;kind=record.kind;mainKind=if(record.pose_uid!=null)"poses" else if(record.device_uid!=null)"devices" else "practices";mainUid=record.practice_uid?:record.pose_uid?:record.device_uid};baseline=draft;editing=true}}
 private suspend fun persist(){val existing=saved;val record=if(existing!=null)api.save(existing.uid,WikiPageSave(document=draft,expected_version=existing.version))else api.create(WikiPageCreate(document=draft,kind=kind,practice_uid=if(kind=="encyclopedia"&&mainKind=="practices")mainUid else null,pose_uid=if(kind=="encyclopedia"&&mainKind=="poses")mainUid else null,device_uid=if(kind=="encyclopedia"&&mainKind=="devices")mainUid else null));saved=record;draft=record.document;baseline=draft}
 suspend fun save(publish:Boolean=false){action{if(!publish||dirty||saved==null)persist();if(publish){val record=saved?:error("Missing saved revision");saved=api.publish(record.uid,WikiPublish(record.version,record.draft_revision_uid?:error("Missing revision")))};refresh();notice="Saved"}}
 suspend fun archive(){action{val record=saved?:return@action;saved=api.archive(record.uid,WikiArchive(record.archived_at==null,record.version));refresh()}}
 fun discardDraft(){editing=false;saved=null;draft=WikiDocument(section_uid="",title="",body="");baseline=draft}
 suspend fun list(mode:String,offset:Int=0){action{this.mode=mode;adminOffset=offset;adminRows=if(mode=="published")emptyList()else api.list(mode,offset)}}
}
