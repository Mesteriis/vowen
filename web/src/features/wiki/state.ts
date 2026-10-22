import {ref} from 'vue'
import type {WikiApi,WikiPageView,WikiTreeView,WikiSearchView} from './api'
export type WikiReaderApi=Pick<WikiApi,'tree'|'page'|'search'>
export function useWikiState(api:WikiReaderApi){
 const pageUid=ref(''),sectionUid=ref(''),query=ref(''),tree=ref<WikiTreeView|null>(null),page=ref<WikiPageView|null>(null),results=ref<WikiSearchView|null>(null),error=ref(''),loading=ref(false)
 let generation=0,searchGeneration=0
 async function loadTree(){try{tree.value=await api.tree()}catch(e){error.value=e instanceof Error?e.message:'UNAVAILABLE'}}
 async function openPage(uid:string){const id=++generation;searchGeneration++;loading.value=true;error.value='';try{const p=await api.page(uid);if(id===generation){page.value=p;pageUid.value=uid;sectionUid.value=p.document.section_uid;results.value=null;query.value=''}}catch(e){if(id===generation)error.value=e instanceof Error?e.message:'UNAVAILABLE'}finally{if(id===generation)loading.value=false}}
 function openSection(uid:string){generation++;searchGeneration++;page.value=null;pageUid.value='';sectionUid.value=uid;results.value=null;query.value='';loading.value=false;error.value=''}
 async function search(q:string,offset=0){generation++;loading.value=false;const id=++searchGeneration;query.value=q;error.value='';try{const r=await api.search(q,sectionUid.value,offset);if(id===searchGeneration)results.value=r}catch(e){if(id===searchGeneration)error.value=e instanceof Error?e.message:'UNAVAILABLE'}}
 async function restore(location:string){
  const id=++generation;searchGeneration++;loading.value=true;error.value=''
  const params=new URLSearchParams(location.split('?')[1]??'');const uid=params.get('page')??'',section=params.get('section')??'',q=params.get('q')??''
  try{
   const destination=uid?await api.page(uid):null
   if(id!==generation)return
   const destinationSection=destination?.document.section_uid??section
   const found=q?await api.search(q,destinationSection,0):null
   if(id!==generation)return
   page.value=destination;pageUid.value=uid;sectionUid.value=destinationSection;query.value=q;results.value=found
  }catch(e){if(id===generation)error.value=e instanceof Error?e.message:'UNAVAILABLE'}finally{if(id===generation)loading.value=false}
 }
 function invalidate(){generation++;searchGeneration++;loading.value=false}
 return {pageUid,sectionUid,query,tree,page,results,error,loading,loadTree,openPage,openSection,search,restore,invalidate}
}
