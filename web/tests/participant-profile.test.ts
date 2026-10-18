import {describe,it,expect} from 'vitest'
import {useParticipantProfile} from '../src/features/profile/useParticipantProfile'
import type {ProfileApi} from '../src/features/profile/profile-api'

const document={identity:{display_name:'Alex',bio:''},dynamics:{},preferences:{practices:[]},boundaries:{notes:''},health:{notes:''},visibility:{sections:[]}}
function api(){return {
 getOwn:async()=>({document,version:0,account_version:1,progress:{step:1,deferred:false,completed:false},draft_version:null}),
 getDraft:async()=>{throw Error('NOT_FOUND')},
 saveDraft:async()=>{throw Error('NETWORK_ERROR')},publish:async()=>{throw Error('CONFLICT')},discard:async()=>{},getShared:async()=>({owner_id:'x',sections:{}})
} as unknown as ProfileApi}
describe('participant profile draft',()=>{
 it('failed save retains edits and does not advance step',async()=>{
  const state=useParticipantProfile(api());await state.load();state.document.value!.identity.bio='Unsaved text'
  expect(await state.goToStep(2,'identity')).toBe(false)
  expect(state.step.value).toBe(1);expect(state.document.value!.identity.bio).toBe('Unsaved text');expect(state.error.value).toBe('NETWORK_ERROR')
 })
 it('resumes the server draft and skips without clearing answers',async()=>{
  const service=api();const own=service.getOwn;service.getOwn=async()=>({...await own(),draft_version:4});service.getDraft=async()=>({document:{...document,identity:{display_name:'Alex',bio:'Saved draft'}},version:4,base_profile_version:0,base_account_version:1,step:3,deferred:false}) as Awaited<ReturnType<ProfileApi['getDraft']>>
  service.saveDraft=async patch=>({...(await service.getDraft()),version:5,step:patch.step})
  const state=useParticipantProfile(service);await state.load();expect(state.step.value).toBe(3)
  expect(state.document.value?.identity.bio).toBe('Saved draft');expect(await state.goToStep(4)).toBe(true)
  expect(state.document.value?.identity.bio).toBe('Saved draft')
 })
 it('conflict does not retry or replace entered values',async()=>{
  const service=api();service.saveDraft=async()=>{throw Error('CONFLICT')}
  const state=useParticipantProfile(service);await state.load();state.document.value!.identity.bio='Keep me'
  expect(await state.saveSection('identity')).toBe(false);expect(state.error.value).toBe('CONFLICT');expect(state.document.value?.identity.bio).toBe('Keep me')
 })
})
