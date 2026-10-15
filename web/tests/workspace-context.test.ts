import {expect,it} from 'vitest'
import {eligibleRecipients,relationRole,matchesContext,contextRule,contextOccurrence} from '../src/features/workspace/context'
import type {components} from '../src/shared/api'
type Relation=components['schemas']['RelationView']
const outgoing:Relation={id:'ab',dominant_user_id:'a',submissive_user_id:'b',status:'active',version:1,relation_version_id:'v1',agreement_text:'fixture',scopes:['rituals.assign'],consent_user_ids:['a','b']}
const incoming:Relation={...outgoing,id:'ca',dominant_user_id:'c',submissive_user_id:'a',consent_user_ids:['c','a']}
it('derives roles per relationship, never from profile labels',()=>{
 expect(relationRole(outgoing,'a')).toBe('dominant')
 expect(relationRole(incoming,'a')).toBe('submissive')
 expect(relationRole(outgoing,'outsider')).toBe(null)
})
it('requires both exact-version consents, scope, active state and no personal pause',()=>{
 expect(eligibleRecipients([outgoing,incoming],'a',false,'rituals.assign',null)).toEqual(['b'])
 for(const r of [{...outgoing,status:'paused'},{...outgoing,consent_user_ids:['a']},{...outgoing,scopes:['rules.assign']}])expect(eligibleRecipients([r],'a',false,'rituals.assign',null)).toEqual([])
 expect(eligibleRecipients([outgoing],'a',true,'rituals.assign',null)).toEqual([])
})
it('selected incoming context cannot borrow outgoing authority or transitively access another person',()=>{
 expect(eligibleRecipients([outgoing,incoming],'a',false,'rituals.assign',incoming)).toEqual([])
 expect(matchesContext('b','c',outgoing,'a')).toBe(false)
 expect(matchesContext('a','b',outgoing,'a')).toBe(true)
 expect(matchesContext('c','a',incoming,'a')).toBe(true)
})
it('rule managers are explicit: receiving rules from another relationship is not enough',()=>{
 expect(contextRule({recipient_id:'a',manager_ids:['c']},outgoing,'a')).toBe(false)
 expect(contextRule({recipient_id:'a',manager_ids:['b']},outgoing,'a')).toBe(true)
})
it('occurrences require a matching visible assignment; unrelated reviewer data cannot enter a context',()=>{
 const assignments=[{id:'one',issuer_id:'a',recipient_id:'b',reviewer_ids:['a']},{id:'two',issuer_id:'c',recipient_id:'a',reviewer_ids:['c']}]
 expect(contextOccurrence({assignment_id:'one',recipient_id:'b',can_review:true},assignments,outgoing,'a')).toBe(true)
 expect(contextOccurrence({assignment_id:'two',recipient_id:'a',can_review:false},assignments,outgoing,'a')).toBe(false)
 expect(contextOccurrence({assignment_id:'missing',recipient_id:'a',can_review:false},assignments,outgoing,'a')).toBe(false)
})
it('keeps explicitly delegated review in partner context without inventing assignment authority',()=>{
 const assignments=[{id:'delegated',issuer_id:'c',recipient_id:'b',reviewer_ids:['a']}]
 expect(contextOccurrence({assignment_id:'delegated',recipient_id:'b',can_review:true},assignments,outgoing,'a')).toBe(true)
 expect(eligibleRecipients([{...outgoing,scopes:['rituals.review']}],'a',false,'rituals.assign',null)).toEqual([])
})
