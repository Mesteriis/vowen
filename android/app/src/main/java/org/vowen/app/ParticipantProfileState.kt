package org.vowen.app

import androidx.compose.runtime.*
import kotlinx.coroutines.CancellationException
import kotlinx.serialization.json.*

/** Transport callbacks retain the host's authenticated session and never cache private data on disk. */
data class ParticipantProfileActions(
 val load:suspend ()->ProfileView,
 val draft:suspend ()->ProfileDraftView,
 val save:suspend (ProfileDraftPatch)->ProfileDraftView,
 val publish:suspend (Int)->ProfileView,
 val discard:suspend (Int)->Unit,
 val references:suspend (String)->List<ReferenceEntry>
)

class ParticipantProfileState(private val actions:ParticipantProfileActions) {
 private val json=Json {ignoreUnknownKeys=true;encodeDefaults=true;explicitNulls=true}
 var profile by mutableStateOf<ProfileView?>(null);private set
 var document by mutableStateOf(JsonObject(emptyMap()));private set
 var draftVersion by mutableStateOf(0);private set
 var step by mutableIntStateOf(1);private set
 var busy by mutableStateOf(false);private set
 var error by mutableStateOf<String?>(null);private set
 var catalogues by mutableStateOf<Map<String,List<ReferenceEntry>>>(emptyMap());private set
 suspend fun load()=perform {
  val result=actions.load()
  val pending=if(result.draft_version!=null)actions.draft() else null
  val refs=listOf("biological-sex","genders","practices","practice-categories","participant-compositions","devices","body-parts","materials","role-scenarios","interaction-formats","venues","health-conditions","allergens","relationship-types").associateWith{actions.references(it)}
  profile=result;document=json.encodeToJsonElement(pending?.document?:result.document).jsonObject
  draftVersion=pending?.version?:0;step=pending?.step?:result.progress.step;catalogues=refs
 }
 fun section(name:String)=document[name]?.jsonObject?:JsonObject(emptyMap())
 fun update(sectionName:String,key:String,value:JsonElement){document=JsonObject(document+ (sectionName to JsonObject(section(sectionName)+(key to value))))}
 suspend fun save(section:String?,next:Int=step,defer:Boolean=false):Boolean=perform {
  val result=actions.save(ProfileDraftPatch(expected_version=draftVersion,section=section,value=section?.let{this.section(it)},step=next,deferred=defer))
  draftVersion=result.version;step=result.step
 }
 suspend fun publish():Boolean=perform {
  val result=actions.publish(draftVersion);profile=result;document=json.encodeToJsonElement(result.document).jsonObject;draftVersion=0
 }
 suspend fun discard():Boolean=perform {actions.discard(draftVersion);draftVersion=0;profile?.let{document=json.encodeToJsonElement(it.document).jsonObject}}
 private suspend fun perform(block:suspend ()->Unit):Boolean {
  if(busy)return false
  busy=true;error=null
  return try{block();true}catch(e:CancellationException){throw e}catch(e:Exception){error=e.message?:"NETWORK_ERROR";false}finally{busy=false}
 }
}
