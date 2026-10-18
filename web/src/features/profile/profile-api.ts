import type {components} from '../../shared/api'
import type {SessionClient} from '../auth/session'
export type ProfileDocument=components['schemas']['ProfileDocument']
export type ProfileSection='identity'|'dynamics'|'preferences'|'boundaries'|'health'|'visibility'
export type ProfileView=components['schemas']['ProfileView']
export type ProfileDraft=components['schemas']['ProfileDraftView']
export type ProfileDraftPatch=components['schemas']['ProfileDraftPatch']
export function createProfileApi(client:SessionClient){return {
 getOwn:()=>client.get<ProfileView>('/me/profile'),
 getDraft:()=>client.get<ProfileDraft>('/me/profile/draft'),
 saveDraft:(patch:ProfileDraftPatch)=>client.put<ProfileDraft>('/me/profile/draft',patch),
 publish:(version:number)=>client.post<ProfileView>('/me/profile/publish',{expected_draft_version:version}),
 discard:(version:number)=>client.delete('/me/profile/draft?expected_version='+version),
 getShared:(ownerId:string)=>client.get<components['schemas']['SharedProfileView']>('/participants/'+encodeURIComponent(ownerId)+'/profile')
}}
export type ProfileApi=ReturnType<typeof createProfileApi>
