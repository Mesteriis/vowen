import {computed,ref} from 'vue'
import type {WikiApi,WikiDocument,WikiEditView} from './api'
export type WikiEditorApi=Pick<WikiApi,'edit'|'save'|'create'|'publish'|'archive'>
export const emptyDocument=(section=''):WikiDocument=>({section_uid:section,title:'',summary:'',body:'',thumbnail:null,practice_uids:[],pose_uids:[],device_uids:[],sources:[]})
export function useWikiEditor(api:WikiEditorApi){
 const uid=ref(''),document=ref<WikiDocument>(emptyDocument()),version=ref(1),kind=ref<'article'|'encyclopedia'>('article'),mainKind=ref<'practices'|'poses'|'devices'>('practices'),mainUid=ref(''),revisionUid=ref(''),archived=ref(false),error=ref(''),saving=ref(false),forbidden=ref(false)
 const baseline=ref(''),dirty=computed(()=>JSON.stringify(document.value)!==baseline.value)
 function accept(page:WikiEditView){uid.value=page.uid;version.value=page.version;document.value=JSON.parse(JSON.stringify(page.document));baseline.value=JSON.stringify(document.value);revisionUid.value=page.draft_revision_uid??'';archived.value=!!page.archived_at;kind.value=page.kind==='encyclopedia'?'encyclopedia':'article';mainKind.value=page.pose_uid?'poses':page.device_uid?'devices':'practices';mainUid.value=page.practice_uid??page.pose_uid??page.device_uid??''}
 async function attempt(operation:()=>Promise<void>){if(saving.value)return false;saving.value=true;error.value='';try{await operation();return true}catch(e){error.value=e instanceof Error?e.message:'UNAVAILABLE';if(error.value==='ACCESS_DENIED')forbidden.value=true;return false}finally{saving.value=false}}
 async function load(id:string){return attempt(async()=>accept(await api.edit(id)))}
 function initialize(section:string){uid.value='';document.value=emptyDocument(section);baseline.value=JSON.stringify(document.value);kind.value='article';mainUid.value='';version.value=1;revisionUid.value='';archived.value=false;error.value='';forbidden.value=false}
 async function persist(){const command={document:JSON.parse(JSON.stringify(document.value)) as WikiDocument};const page=uid.value?await api.save(uid.value,{...command,expected_version:version.value}):await api.create({...command,kind:kind.value,practice_uid:kind.value==='encyclopedia'&&mainKind.value==='practices'?mainUid.value:null,pose_uid:kind.value==='encyclopedia'&&mainKind.value==='poses'?mainUid.value:null,device_uid:kind.value==='encyclopedia'&&mainKind.value==='devices'?mainUid.value:null});accept(page)}
 const save=()=>attempt(persist)
 const publish=()=>attempt(async()=>{if(dirty.value||!uid.value)await persist();accept(await api.publish(uid.value,{expected_version:version.value,revision_uid:revisionUid.value}))})
 const archive=(value:boolean)=>attempt(async()=>accept(await api.archive(uid.value,{expected_version:version.value,archived:value})))
 function canLeave(confirm:()=>boolean){return !saving.value&&(!dirty.value||confirm())}
 return {uid,document,version,kind,mainKind,mainUid,revisionUid,archived,error,saving,forbidden,dirty,load,initialize,save,publish,archive,reload:()=>load(uid.value),canLeave}
}
