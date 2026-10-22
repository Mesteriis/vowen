import type {components} from '../../shared/api'
import type {SessionClient} from '../auth/session'
export type WikiDocument=components['schemas']['WikiDocument']
export type WikiPageView=components['schemas']['WikiPageView']
export type WikiEditView=components['schemas']['WikiEditView']
export type WikiTreeView=components['schemas']['WikiTreeView']
export type WikiSectionView=components['schemas']['WikiSectionView']
export type WikiPageSummary=components['schemas']['WikiPageSummary']
export type WikiSearchView=components['schemas']['WikiSearchView']
export type WikiRevisionView=components['schemas']['WikiRevisionView']
export type Reference=components['schemas']['ReferenceView']
const root='/wiki'
export function createWikiApi(client:SessionClient){return {
 tree:()=>client.get<WikiTreeView>(root+'/tree'),
 page:(uid:string)=>client.get<WikiPageView>(root+'/pages/'+uid),
 search:(q:string,sectionUid='',offset=0)=>client.get<WikiSearchView>(root+'/search?'+new URLSearchParams({q,offset:String(offset),...(sectionUid?{section_uid:sectionUid}:{})})),
 edit:(uid:string)=>client.get<WikiEditView>(root+'/admin/pages/'+uid),
 list:(state:'drafts'|'published'|'archived',offset=0)=>client.get<WikiEditView[]>(root+'/admin/pages?'+new URLSearchParams({state,offset:String(offset)})),
 create:(command:components['schemas']['WikiPageCreate'])=>client.post<WikiEditView>(root+'/admin/pages',command),
 save:(uid:string,command:components['schemas']['WikiPageSave'])=>client.patch<WikiEditView>(root+'/admin/pages/'+uid,command),
 publish:(uid:string,command:components['schemas']['WikiPublish'])=>client.post<WikiEditView>(root+'/admin/pages/'+uid+'/publish',command),
 archive:(uid:string,command:components['schemas']['WikiArchive'])=>client.post<WikiEditView>(root+'/admin/pages/'+uid+'/archive',command),
 history:(uid:string,offset=0)=>client.get<WikiRevisionView[]>(root+'/admin/pages/'+uid+'/revisions?offset='+offset),
 saveSection:(uid:string|null,command:components['schemas']['WikiSectionSave'])=>uid?client.patch<WikiTreeView>(root+'/admin/sections/'+uid,command):client.post<WikiTreeView>(root+'/admin/sections',command),
 deleteSection:async(uid:string,version:number,treeVersion:number)=>{await client.delete(root+'/admin/sections/'+uid+'?'+new URLSearchParams({expected_version:String(version),expected_tree_version:String(treeVersion)}))},
 seed:()=>client.post<components['schemas']['WikiSeedResult']>(root+'/admin/seed-references'),
 references:(kind:string)=>client.get<Reference[]>('/references/'+kind),
}}
export type WikiApi=ReturnType<typeof createWikiApi>
