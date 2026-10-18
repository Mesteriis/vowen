import {ref,onScopeDispose,getCurrentScope} from 'vue'
import type {ProfileApi,ProfileDocument,ProfileDraft,ProfileSection,ProfileView} from './profile-api'
export function useParticipantProfile(api:ProfileApi){
 const published=ref<ProfileView|null>(null),document=ref<ProfileDocument|null>(null),draft=ref<ProfileDraft|null>(null)
 const step=ref(1),loading=ref(false),saving=ref(false),error=ref(''),dirty=ref(false)
 let generation=0
 if(getCurrentScope())onScopeDispose(()=>{generation++;document.value=null;draft.value=null;published.value=null})
 async function load(){const run=++generation;loading.value=true;error.value='';try{
  const own=await api.getOwn();let pending:ProfileDraft|null=null
  if(own.draft_version!==null)pending=await api.getDraft()
  if(run!==generation)return
  published.value=own;draft.value=pending;document.value=JSON.parse(JSON.stringify(pending?.document??own.document));step.value=pending?.step??own.progress.step;dirty.value=false
 }catch(e){if(run===generation)error.value=e instanceof Error?e.message:'NETWORK_ERROR'}finally{if(run===generation)loading.value=false}}
 async function saveSection(section?:ProfileSection,targetStep=step.value,deferred=false){
  if(saving.value||!document.value)return false
  const run=generation;saving.value=true;error.value=''
  try{
   const value=section?JSON.parse(JSON.stringify(document.value[section])):undefined
   const result=await api.saveDraft({expected_version:draft.value?.version??0,step:targetStep,deferred,...(section?{section,value}:{})})
   if(run!==generation)return false
   draft.value=result;step.value=result.step;dirty.value=false;return true
  }catch(e){if(run===generation)error.value=e instanceof Error?e.message:'NETWORK_ERROR';return false}finally{if(run===generation)saving.value=false}
 }
 async function goToStep(next:number,section?:ProfileSection){return saveSection(section,next)}
 async function defer(section?:ProfileSection){return saveSection(section,step.value,true)}
 async function discard(){if(saving.value||!draft.value)return false;const run=generation;saving.value=true;error.value='';try{await api.discard(draft.value.version);if(run!==generation)return false;draft.value=null;document.value=JSON.parse(JSON.stringify(published.value!.document));dirty.value=false;return true}catch(e){error.value=e instanceof Error?e.message:'NETWORK_ERROR';return false}finally{saving.value=false}}
 async function publish(){if(saving.value||!draft.value)return false;const run=generation;saving.value=true;error.value='';try{const result=await api.publish(draft.value.version);if(run!==generation)return false;published.value=result;document.value=JSON.parse(JSON.stringify(result.document));draft.value=null;dirty.value=false;return true}catch(e){if(run===generation)error.value=e instanceof Error?e.message:'NETWORK_ERROR';return false}finally{if(run===generation)saving.value=false}}
 return {published,document,draft,step,loading,saving,error,dirty,load,saveSection,goToStep,defer,discard,publish}
}
