import {ref} from 'vue'
import type {components} from '../../shared/api'
import type {SessionClient} from '../auth/session'

type WikiReferenceLink=components['schemas']['WikiReferenceLink']

/** Keep catalogue failures separate from optional article navigation and reject stale responses. */
export function useReferenceWikiLinks(client:Pick<SessionClient,'get'>){
 const links=ref<Record<string,string>>({})
 const failed=ref(false)
 let request=0
 function reset(){request++;links.value={};failed.value=false}
 async function load(kind:string){
  const token=++request
  links.value={};failed.value=false
  try{
   const rows=await client.get<WikiReferenceLink[]>('/wiki/reference-links/'+encodeURIComponent(kind))
   if(token===request)links.value=Object.fromEntries(rows.map(row=>[row.reference_uid,row.page_uid]))
  }catch{if(token===request)failed.value=true}
 }
 return {links,failed,load,reset}
}
