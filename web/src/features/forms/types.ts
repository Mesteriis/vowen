import type {components} from '../../shared/api'
export type Schema=components['schemas']['FormSchema']
export type Question=components['schemas']['Question']
export type Form=components['schemas']['FormView']
export type Access=components['schemas']['FormAccess']
export type Result=components['schemas']['SubmissionView']
export type Invitation=components['schemas']['InvitationView']
export type AnswerMap=Record<string,components['schemas']['JsonValue']>
export function isVisible(q:Question,answers:AnswerMap):boolean {
 const check=(c:NonNullable<Question['visibility']>['all'] extends (infer T)[]|undefined?T:never)=>{
  const v=answers[c.question_id]
  switch(c.op){
   case 'equals':return JSON.stringify(v??null)===JSON.stringify(c.value??null)
   case 'not_equals':return JSON.stringify(v??null)!==JSON.stringify(c.value??null)
   case 'answered':return v!=null && v!=='' && (!Array.isArray(v)||v.length>0)
   case 'contains':return Array.isArray(v)?v.includes(c.value):typeof v==='string'&&typeof c.value==='string'&&v.includes(c.value)
  }
 }
 return !q.visibility||((q.visibility.all??[]).every(check)&&(!(q.visibility.any?.length)||q.visibility.any.some(check)))
}
