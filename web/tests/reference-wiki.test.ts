import {expect,it} from 'vitest'
import {useReferenceWikiLinks} from '../src/features/profile/reference-wiki'
import type {SessionClient} from '../src/features/auth/session'
function client(get:(path:string)=>Promise<unknown>){return {get} as Pick<SessionClient,'get'>}
it('uses server-provided page ids and leaves entries without publications unlinked',async()=>{
 const state=useReferenceWikiLinks(client(async path=>{
  expect(path).toBe('/wiki/reference-links/devices')
  return [{reference_uid:'custom-reference',page_uid:'custom-publication'}]
 }))
 await state.load('devices')
 expect(state.links.value).toEqual({'custom-reference':'custom-publication'})
 expect(state.links.value.missing).toBeUndefined()
 expect(state.failed.value).toBe(false)
})
it('does not attach the previous catalogue result after switching catalogues',async()=>{
 let finish:(value:unknown)=>void=()=>{}
 const state=useReferenceWikiLinks(client(path=>path.endsWith('devices')?new Promise(resolve=>{finish=resolve}):Promise.resolve([{reference_uid:'pose',page_uid:'pose-page'}])))
 const old=state.load('devices')
 await state.load('poses')
 finish([{reference_uid:'tool',page_uid:'old-page'}]);await old
 expect(state.links.value).toEqual({pose:'pose-page'})
})
it('reports article-link failures without inventing links and ignores obsolete failures',async()=>{
 let rejectOld:(reason:Error)=>void=()=>{}
 const state=useReferenceWikiLinks(client(path=>path.endsWith('devices')?new Promise((_resolve,reject)=>{rejectOld=reject}):Promise.resolve([])))
 const old=state.load('devices');await state.load('poses');rejectOld(Error('offline'));await old
 expect(state.failed.value).toBe(false)
 const failed=useReferenceWikiLinks(client(async()=>{throw Error('offline')}))
 await failed.load('devices');expect(failed.failed.value).toBe(true);expect(failed.links.value).toEqual({})
})
it('invalidates pending loads when the catalogue view is left',async()=>{
 let finish:(value:unknown)=>void=()=>{}
 const state=useReferenceWikiLinks(client(()=>new Promise(resolve=>{finish=resolve})))
 const loading=state.load('devices');state.reset()
 finish([{reference_uid:'tool',page_uid:'page'}]);await loading
 expect(state.links.value).toEqual({});expect(state.failed.value).toBe(false)
})
