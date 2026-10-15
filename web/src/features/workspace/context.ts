/** Presentation context only. The server still authorizes every operation. */
import {computed,inject,type ComputedRef,type InjectionKey} from 'vue'
import type {components} from '../../shared/api'
export type Relation=components['schemas']['RelationView']
export type Member=components['schemas']['MemberView']
export type Section='home'|'rituals'|'rewards'|'discipline'|'journal'|'rules'|'forms'|'relations'|'notifications'|'profile'|'sessions'
export function relationRole(relation:Relation,memberId:string):'dominant'|'submissive'|null {
 if(relation.dominant_user_id===memberId)return 'dominant'
 if(relation.submissive_user_id===memberId)return 'submissive'
 return null
}
export function partnerId(relation:Relation,memberId:string):string|null {
 const role=relationRole(relation,memberId)
 return role==='dominant'?relation.submissive_user_id:role==='submissive'?relation.dominant_user_id:null
}
export function eligibleRecipients(relations:Relation[],memberId:string,paused:boolean,scope:string,selected:Relation|null):string[] {
 if(paused)return []
 return [...new Set(relations.filter(r=>(!selected||selected.id===r.id)&&r.dominant_user_id===memberId&&r.status==='active'&&r.scopes.includes(scope)&&r.consent_user_ids.includes(r.dominant_user_id)&&r.consent_user_ids.includes(r.submissive_user_id)).map(r=>r.submissive_user_id))]
}
export function matchesContext(author:string,recipient:string,selected:Relation|null,memberId:string):boolean {
 if(!selected)return true
 const partner=partnerId(selected,memberId)
 return partner!==null&&((author===memberId&&recipient===partner)||(author===partner&&recipient===memberId))
}
export function contextRule(row:{recipient_id:string;manager_ids:string[]},selected:Relation|null,memberId:string):boolean {
 if(!selected)return true
 const partner=partnerId(selected,memberId)
 return partner!==null&&((row.recipient_id===memberId&&row.manager_ids.includes(partner))||(row.recipient_id===partner&&row.manager_ids.includes(memberId)))
}
export function contextAssignment(row:{issuer_id:string;recipient_id:string;reviewer_ids:string[]},selected:Relation|null,memberId:string):boolean {
 return matchesContext(row.issuer_id,row.recipient_id,selected,memberId)||!!selected&&(row.recipient_id===partnerId(selected,memberId)&&row.reviewer_ids.includes(memberId))
}
export function contextOccurrence(row:{assignment_id:string;recipient_id:string;can_review:boolean},assignments:{id:string;issuer_id:string;recipient_id:string;reviewer_ids:string[]}[],selected:Relation|null,memberId:string):boolean {
 if(!selected)return true
 const assignment=assignments.find(a=>a.id===row.assignment_id)
 return !!assignment&&contextAssignment(assignment,selected,memberId)
}
export type WorkspaceView={selected:ComputedRef<Relation|null>;member:ComputedRef<Member|null>;relations:ComputedRef<Relation[]>;revision:ComputedRef<string>;navigate:(section:Section)=>void}
export const workspaceKey:InjectionKey<WorkspaceView>=Symbol('workspace-view')
export function useWorkspaceView(){
 const workspace=inject(workspaceKey,null)
 const selected=computed(()=>workspace?.selected.value??null)
 const memberId=computed(()=>workspace?.member.value?.id??'')
 function recipients(scope:string):string[]{return workspace?.member.value?eligibleRecipients(workspace.relations.value,memberId.value,workspace.member.value.paused,scope,selected.value):[]}
 return {selected,memberId,revision:computed(()=>workspace?.revision.value??''),recipients,
 pair:(author:string,recipient:string)=>matchesContext(author,recipient,selected.value,memberId.value),
 rule:(row:{recipient_id:string;manager_ids:string[]})=>contextRule(row,selected.value,memberId.value),
 assignment:(row:{issuer_id:string;recipient_id:string;reviewer_ids:string[]})=>contextAssignment(row,selected.value,memberId.value),
 occurrence:(row:{assignment_id:string;recipient_id:string;can_review:boolean},assignments:{id:string;issuer_id:string;recipient_id:string;reviewer_ids:string[]}[])=>contextOccurrence(row,assignments,selected.value,memberId.value)}
}
export function statusLabel(status:string,ru:boolean):string {
 const labels:Record<string,[string,string]>={active:['Active','Действуют'],proposed:['Awaiting consent','Ожидают согласия'],paused:['Paused','На паузе'],revoked:['Revoked','Отозваны'],scheduled:['Planned','Запланировано'],submitted:['Awaiting review','Ждёт проверки'],needs_changes:['Needs changes','На доработке'],approved:['Approved','Одобрено'],missed:['Missed','Пропущено'],skipped:['Skipped','Пропущено добровольно'],cancelled:['Cancelled','Отменено'],offered:['Offered','Предложено'],accepted:['Accepted','Принято'],delivered:['Delivered','Вручено'],declined:['Declined','Отклонено'],pending_acceptance:['Awaiting acceptance','Ожидает согласия'],draft:['Draft','Черновик'],published:['Published','Опубликовано'],archived:['Archived','В архиве']}
 return labels[status]?.[ru?1:0]??(ru?'Недоступно':'Unavailable')
}
export function scopeLabel(scope:string,ru:boolean):string {
 const labels:Record<string,[string,string]>={'rules.assign':['Propose rules','Предлагать правила'],'rituals.assign':['Assign rituals','Назначать ритуалы'],'rituals.review':['Review reports','Проверять отчёты'],'discipline.propose':['Propose discipline','Предлагать дисциплину'],'discipline.review':['Review discipline','Подтверждать выполнение'],'rewards.grant':['Offer rewards','Предлагать награды']}
 return labels[scope]?.[ru?1:0]??(ru?'Полномочие':'Permission')
}
