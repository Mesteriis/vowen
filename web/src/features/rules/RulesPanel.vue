<script setup lang="ts">
import {onMounted,ref,watch,computed} from 'vue'
import type {components} from '../../shared/api'
import type {SessionClient} from '../auth/session'
import {useWorkspaceView} from '../workspace/context'
type Rule=components['schemas']['RuleView']
type Assignment=components['schemas']['RuleAssignmentView']
const props=defineProps<{client:SessionClient;ru:boolean;me:components['schemas']['MemberView'];participants:components['schemas']['ParticipantView'][]}>()
const view=useWorkspaceView()
const templates=ref<Rule[]>([]),assignments=ref<Assignment[]>([]),busy=ref(false),error=ref('')
const recipients=computed(()=>props.participants.filter(p=>view.recipients('rules.assign').includes(p.id)))
const visibleAssignments=computed(()=>assignments.value.filter(view.rule))
const history=ref<Rule[]>([]),historyFor=ref('')
const editor=ref(false),selected=ref<Rule|null>(null),title=ref(''),description=ref(''),discipline=ref('')
const assigning=ref<Rule|null>(null),recipient=ref(''),managers=ref<string[]>([]),review=ref<Assignment|null>(null)
const t=(en:string,ru:string)=>props.ru?ru:en
const name=(id:string)=>props.participants.find(p=>p.id===id)?.display_name??id
async function load(){
 templates.value=await props.client.get<Rule[]>('/rules')
 assignments.value=await props.client.get<Assignment[]>('/rule-assignments')
}
async function run(fn:()=>Promise<void>){busy.value=true;error.value='';try{await fn()}catch(e){error.value=e instanceof Error?e.message:'NETWORK_ERROR'}finally{busy.value=false}}
onMounted(()=>run(load))
watch(view.revision,()=>{recipient.value='';void run(load)})
watch(recipient,id=>{managers.value=managers.value.filter(manager=>manager!==id)})
watch(()=>props.me.paused,()=>{
 assignments.value=assignments.value.filter(a=>!props.me.paused||a.recipient_id===props.me.id)
 void run(load)
})
function edit(rule:Rule|null){selected.value=rule;title.value=rule?.title??'';description.value=rule?.description??'';discipline.value=rule?.discipline??'';editor.value=true;assigning.value=null}
async function showHistory(rule:Rule){await run(async()=>{history.value=await props.client.get<Rule[]>(`/rules/${rule.id}/versions`);historyFor.value=rule.id})}
async function save(){await run(async()=>{
 const r=selected.value,body={title:title.value,description:description.value,discipline:discipline.value}
 if(!r)await props.client.post('/rules',body)
 else if(r.status==='draft')await props.client.patch(`/rules/${r.id}`,{...body,expected_version:r.revision})
 else await props.client.post(`/rules/${r.id}/versions`,{...body,expected_version:r.revision})
 editor.value=false;await load()
})}
async function transition(r:Rule,action:'publish'|'archive'){await run(async()=>{await props.client.post(`/rules/${r.id}/${action}`,{expected_version:r.revision});await load()})}
function startAssign(r:Rule){assigning.value=r;recipient.value='';managers.value=[];editor.value=false}
async function assign(){await run(async()=>{const r=assigning.value;if(!r)return
 await props.client.post(`/rules/${r.id}/assignments`,{rule_version_id:r.version_id,recipient_id:recipient.value,manager_ids:managers.value.filter(id=>id!==recipient.value)})
 assigning.value=null;await load()
})}
async function decide(a:Assignment,action:string){await run(async()=>{
 await props.client.post(`/rule-assignments/${a.id}/${action}`,{expected_version:a.revision,rule_version_id:a.rule_version_id})
 review.value=null;await load()
})}
</script>
<template>
 <section id="rules" aria-labelledby="rules-heading">
  <h2 id="rules-heading">{{t('Rules','Правила')}}</h2>
  <button :disabled="busy" @click="run(load)">{{t('Refresh rules','Обновить правила')}}</button>
  <button :disabled="busy||me.paused" @click="edit(null)">{{t('New rule','Новое правило')}}</button>
  <p v-if="error" role="alert">{{error}}</p>
  <form v-if="editor" @submit.prevent="save">
   <label>{{t('Rule title','Название правила')}}<input v-model="title" required maxlength="200"></label>
   <label>{{t('Rule description','Описание правила')}}<textarea v-model="description" required maxlength="10000" rows="5" /></label>
   <p v-if="selected?.status!=='draft'&&selected">{{t('A new version requires new consent. The accepted version continues until replacement.','Новая версия требует нового согласия. Принятая действует до замены.')}}</p>
   <label>{{t('Rule discipline','Дисциплина по правилу')}}<textarea v-model="discipline" maxlength="10000" rows="3" /></label><button :disabled="busy||me.paused">{{t('Save rule','Сохранить правило')}}</button>
   <button type="button" :disabled="busy" @click="editor=false">{{t('Cancel','Отмена')}}</button>
  </form>
  <article v-for="rule in templates" :key="rule.id">
   <h3>{{rule.title}}</h3><p>{{rule.description}}</p><p class="muted">{{rule.status==='draft'?t('Draft','Черновик'):rule.status==='published'?t('Published','Опубликовано'):t('Archived','В архиве')}} · {{t('Version','Версия')}} {{rule.revision}}</p>
   <button :disabled="busy||me.paused" @click="edit(rule)">{{rule.status==='draft'?t('Edit rule draft','Изменить черновик правила'):t('New rule version','Новая версия правила')}}</button>
   <button v-if="rule.status==='draft'" :disabled="busy||me.paused" @click="transition(rule,'publish')">{{t('Publish rule','Опубликовать правило')}}</button>
   <button v-if="rule.status==='published'&&recipients.length" :disabled="busy||me.paused" @click="startAssign(rule)">{{t('Assign rule','Назначить правило')}}</button>
   <button :disabled="busy" @click="showHistory(rule)">{{t('Rule version history','История версий правила')}}</button>
   <button v-if="rule.status!=='archived'" :disabled="busy" @click="transition(rule,'archive')">{{t('Archive rule','Архивировать правило')}}</button>
  </article>
  <section v-if="historyFor" role="region" :aria-label="t('Rule version history','История версий правила')">
   <h3>{{t('Version history','История версий')}}</h3>
   <article v-for="v in history" :key="v.version_id"><h4>{{v.title}}</h4><p>{{v.description}}</p><p>{{v.status}} · {{v.version_id}}</p></article>
   <button :disabled="busy" @click="historyFor='';history=[]">{{t('Close history','Закрыть историю')}}</button>
  </section>
  <form v-if="assigning" @submit.prevent="assign">
   <h3>{{assigning.title}}</h3>
   <label>{{t('Rule recipient','Адресат правила')}}<select v-model="recipient" required><option value="" disabled>—</option><option v-for="p in recipients" :key="p.id" :value="p.id">{{p.display_name}}</option></select></label>
   <fieldset><legend>{{t('Explicit managers','Управляющие')}}</legend><label v-for="p in participants.filter(p=>p.id!==recipient)" :key="p.id"><input v-model="managers" type="checkbox" :value="p.id">{{t('Manager: ','Управляющий: ')}}{{p.display_name}}</label></fieldset>
   <p>{{t('Only managers with current rules authority can act. Each recipient decides separately.','Требуются актуальные полномочия управляющих. Каждый адресат решает отдельно.')}}</p>
   <button :disabled="busy||me.paused">{{t('Send rule proposal','Предложить правило')}}</button>
   <button type="button" :disabled="busy" @click="assigning=null">{{t('Cancel','Отмена')}}</button>
  </form>
  <h3>{{t('Assignments and history','Назначения и история')}}</h3>
  <p v-if="!assignments.length">{{t('No visible assignments','Нет доступных назначений')}}</p>
  <article v-for="a in visibleAssignments" :key="a.id">
   <h4>{{a.title}} · {{name(a.recipient_id)}}</h4><p>{{a.description}}</p><p v-if="a.discipline">{{t('Discipline: ','Дисциплина: ')}}{{a.discipline}}</p>
   <p>{{a.status}} · {{a.effective&&!(me.paused&&a.recipient_id===me.id)?'effective':'inactive'}}</p>
   <p>{{t('Version','Версия')}}: {{a.rule_version_id}}</p>
   <p>{{t('Managers','Управляющие')}}: {{a.manager_ids.map(name).join(', ')||'—'}}</p>
   <p v-if="a.accepted_at">{{t('Accepted','Принято')}}: {{a.accepted_at}}</p>
   <template v-if="a.status==='pending_acceptance'&&a.recipient_id===me.id">
    <button :disabled="busy||me.paused" @click="review=a">{{t('Accept rule','Принять правило')}}</button>
    <button :disabled="busy" @click="decide(a,'decline')">{{t('Decline rule','Отклонить правило')}}</button>
   </template>
   <button v-if="['active','pending_acceptance'].includes(a.status)" :disabled="busy" @click="decide(a,'pause')">{{t('Pause rule','Приостановить правило')}}</button>
   <button v-if="a.status!=='revoked'" :disabled="busy" @click="decide(a,'revoke')">{{t('Revoke rule','Отозвать правило')}}</button>
  </article>
  <div v-if="review" role="dialog" aria-modal="true" :aria-label="t('Review exact rule version','Подтверждение точной версии правила')">
   <h3>{{review.title}}</h3><p>{{review.description}}</p><p v-if="review.discipline">{{t('Discipline: ','Дисциплина: ')}}{{review.discipline}}</p><p>{{review.rule_version_id}}</p>
   <p>{{t('Accepting replaces the previously active version of this rule.','Принятие заменит ранее действовавшую версию этого правила.')}}</p>
   <button :disabled="busy||me.paused" @click="decide(review,'accept')">{{t('Confirm rule acceptance','Подтверждаю принятие правила')}}</button>
   <button :disabled="busy" @click="review=null">{{t('Cancel','Отмена')}}</button>
  </div>
 </section>
</template>
