import type {components} from '../../shared/api'
type Member=components['schemas']['MemberView']
export function preferencePatch(member:Member,mode:'profile'|'general'|'all',draft:{name:string;language:string;timezone:string;labels:string[]}){
 return {expected_version:member.profile_version,display_name:mode==='general'?member.display_name:draft.name,language:mode!=='profile'?draft.language:member.language,timezone:mode!=='profile'?draft.timezone:member.timezone,profile_labels:mode==='general'?member.profile_labels:draft.labels}
}
