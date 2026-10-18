import {describe,it,expect} from 'vitest'
import {accountDestination,mainNavigation} from '../src/features/profile/navigation'
import {preferencePatch} from '../src/features/profile/preferences'
import type {components} from '../src/shared/api'
const member={display_name:'Alex',language:'ru',timezone:'Europe/Madrid',profile_labels:['switch'],profile_version:7} as components['schemas']['MemberView']
const draft={name:'New name',language:'en',timezone:'UTC',labels:['dominant']}
describe('account settings migration',()=>{
 it('keeps legacy links directed to the corresponding settings section',()=>{
  expect(accountDestination('notifications')).toEqual({section:'profile',personal:'notifications'})
  expect(accountDestination('sessions')).toEqual({section:'profile',personal:'sessions'})
  expect(accountDestination('rules')).toBeNull()
 })
 it('removes only notifications and sessions from main navigation',()=>{
  expect(mainNavigation(['home','notifications','profile','sessions','rules'])).toEqual(['home','rules'])
 })
 it('keeps profile and settings out of the main list',()=>{expect(mainNavigation(['profile','settings','home'])).toEqual(['home'])})
 it('saves all personal preferences together',()=>{expect(preferencePatch(member,'all',draft)).toEqual({expected_version:7,display_name:'New name',language:'en',timezone:'UTC',profile_labels:['dominant']})})
 it('saves general settings without changing name or self-description',()=>{
  expect(preferencePatch(member,'general',draft)).toEqual({expected_version:7,display_name:'Alex',language:'en',timezone:'UTC',profile_labels:['switch']})
 })
 it('saves personal fields without overwriting general settings',()=>{
  expect(preferencePatch(member,'profile',draft)).toEqual({expected_version:7,display_name:'New name',language:'ru',timezone:'Europe/Madrid',profile_labels:['dominant']})
 })
})
