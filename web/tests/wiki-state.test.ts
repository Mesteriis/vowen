import {it,expect} from 'vitest'
import {useWikiState,type WikiReaderApi} from '../src/features/wiki/state'
import type {WikiPageView,WikiSearchView} from '../src/features/wiki/api'
function deferred<T>(){let resolve!:(v:T)=>void;const promise=new Promise<T>(r=>resolve=r);return {promise,resolve}}
const result=(title:string):WikiSearchView=>({items:[{uid:title,kind:'article',title,summary:'',section_uid:'s',thumbnail:null,published_at:null}],total:1,offset:0,limit:50})
it('ignores old search responses',async()=>{
 const first=deferred<WikiSearchView>(),last=deferred<WikiSearchView>()
 const api:WikiReaderApi={tree:async()=>({version:1,sections:[],pages:[]}),page:async()=>{throw Error('offline')},search:q=>q==='old'?first.promise:last.promise}
 const s=useWikiState(api)
 const a=s.search('old'),b=s.search('new')
 last.resolve(result('New'));await b;first.resolve(result('Old'));await a
 expect(s.results.value?.items[0].title).toBe('New')
 expect(s.query.value).toBe('new')
})
it('preserves reading on failure and restores navigation',async()=>{
 const p:WikiPageView={uid:'first',kind:'article',practice_uid:null,pose_uid:null,device_uid:null,revision_uid:'r',document:{section_uid:'s',title:'First',summary:'',body:'Body'},author_id:'u',created_at:'2026-10-21',published_at:null,related_pages:[]}
 const api:WikiReaderApi={tree:async()=>({version:1,sections:[],pages:[]}),page:async uid=>{if(uid==='first')return p;throw Error('offline')},search:async()=>result('Found')}
 const s=useWikiState(api)
 await s.openPage('first');await s.openPage('other')
 expect(s.page.value?.uid).toBe('first');expect(s.error.value).toBeTruthy()
 await s.restore('#wiki?section=s&q=hello')
 expect(s.sectionUid.value).toBe('s');expect(s.query.value).toBe('hello')
})
it('preserves the readable page when actual hash navigation fails',async()=>{
 const page={uid:'a',kind:'article',practice_uid:null,pose_uid:null,device_uid:null,revision_uid:'r',document:{section_uid:'s',title:'A',body:'Body',summary:''},author_id:'u',created_at:'2026-10-21T00:00:00Z',published_at:null,related_pages:[]} satisfies WikiPageView
 const s=useWikiState({tree:async()=>({version:1,sections:[],pages:[]}),page:async uid=>{if(uid==='a')return page;throw Error('offline')},search:async()=>result('Found')})
 await s.restore('#wiki?page=a');await s.restore('#wiki?page=b')
 expect(s.page.value?.uid).toBe('a');expect(s.pageUid.value).toBe('a');expect(s.sectionUid.value).toBe('s')
})
it('ignores the continuation of an old hash navigation after a newer search',async()=>{
 const slow=deferred<WikiPageView>()
 const s=useWikiState({tree:async()=>({version:1,sections:[],pages:[]}),page:()=>slow.promise,search:async q=>result(q)})
 const old=s.restore('#wiki?page=slow&q=old')
 await s.restore('#wiki?section=new&q=new')
 slow.resolve({uid:'slow',kind:'article',practice_uid:null,pose_uid:null,device_uid:null,revision_uid:'r',document:{section_uid:'old',title:'Old',summary:'',body:'Old'},author_id:'u',created_at:'now',published_at:null,related_pages:[]});await old
 expect(s.sectionUid.value).toBe('new');expect(s.query.value).toBe('new');expect(s.results.value?.items[0].title).toBe('new')
})
