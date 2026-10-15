<script setup lang="ts">
import {onMounted,ref,watch,computed} from 'vue'
import type {components} from '../../shared/api'
import type {SessionClient} from '../auth/session'
import {useWorkspaceView} from '../workspace/context'
type RecordView=components['schemas']['DisciplineView']
type Assignment=components['schemas']['RuleAssignmentView']
type Occurrence=components['schemas']['OccurrenceView']
const props=defineProps<{client:SessionClient;ru:boolean;me:components['schemas']['MemberView'];participants:components['schemas']['ParticipantView'][]}>()
const view=useWorkspaceView()
const rows=ref<RecordView[]>([]),rules=ref<Assignment[]>([]),occurrences=ref<Occurrence[]>([])
const recipients=computed(()=>props.participants.filter(p=>view.recipients('discipline.propose').includes(p.id)))
const visibleRows=computed(()=>rows.value.filter(r=>view.pair(r.author_id,r.recipient_id)||!!view.selected.value&&r.recipient_id===(view.selected.value.dominant_user_id===props.me.id?view.selected.value.submissive_user_id:view.selected.value.dominant_user_id)&&r.reviewer_ids.includes(props.me.id)))
const busy=ref(false),error=ref(''),editing=ref(false),selected=ref<RecordView|null>(null),review=ref<RecordView|null>(null),history=ref('')
const recipient=ref(''),reviewers=ref<string[]>([]),description=ref(''),conditions=ref(''),deadline=ref(''),rule=ref(''),occurrence=ref(''),comment=ref(''),key=ref('')
const t=(en:string,ru:string)=>props.ru?ru:en
const name=(id:string)=>props.participants.find(p=>p.id===id)?.display_name??id
const current=(r:RecordView)=>r.versions.find(v=>v.id===r.version_id)!
async function load(){rows.value=await props.client.get<RecordView[]>('/discipline-records');rules.value=await props.client.get<Assignment[]>('/rule-assignments');occurrences.value=await props.client.get<Occurrence[]>('/ritual-occurrences')}
async function run(fn:()=>Promise<void>){busy.value=true;error.value='';try{await fn()}catch(e){error.value=e instanceof Error?e.message:'NETWORK_ERROR';rows.value=[]}finally{busy.value=false}}
onMounted(()=>run(load))
watch(view.revision,()=>{recipient.value='';void run(load)})
watch(()=>props.me.paused,()=>{rows.value=rows.value.filter(r=>r.recipient_id===props.me.id);review.value=null;void run(load)})
function edit(r:RecordView|null){const v=r?current(r):null;selected.value=r;recipient.value=r?.recipient_id??'';reviewers.value=r?.reviewer_ids??[];description.value=v?.description??'';conditions.value=v?.conditions??'';deadline.value=v?.deadline??'';rule.value=v?.rule_version_id??'';occurrence.value=v?.occurrence_id??'';key.value=crypto.randomUUID();editing.value=true}
async function save(){await run(async()=>{
 const r=selected.value,body={description:description.value,conditions:conditions.value,deadline:deadline.value||null,rule_version_id:rule.value||null,occurrence_id:occurrence.value||null}
 if(r)await props.client.post(`/discipline-records/${r.id}/versions`,{...body,expected_version:r.revision})
 else await props.client.post('/discipline-records',{...body,recipient_id:recipient.value,reviewer_ids:reviewers.value,idempotency_key:key.value})
 editing.value=false;await load()
})}
async function act(r:RecordView,action:string){await run(async()=>{await props.client.post(`/discipline-records/${r.id}/transitions`,{expected_version:r.revision,version_id:r.version_id,action,comment:comment.value});review.value=null;comment.value='';await load()})}
</script>
<template>
<section id="discipline" aria-labelledby="discipline-heading">
 <h2 id="discipline-heading">{{t('Discipline','Дисциплина')}}</h2>
 <p>{{t('A proposal describes an alleged event, not an agreed fact. Acceptance is personal and can be withdrawn.','Предложение описывает предполагаемое событие, а не установленный факт. Согласие личное и может быть отозвано.')}}</p>
 <button :disabled="busy" @click="run(load)">{{t('Refresh discipline','Обновить дисциплину')}}</button>
 <button :disabled="busy||me.paused" v-if="recipients.length" @click="edit(null)">{{t('New discipline proposal','Новое дисциплинарное предложение')}}</button>
 <p v-if="error" role="alert">{{error}}</p>
 <form v-if="editing" @submit.prevent="save">
  <label>{{t('Discipline recipient','Адресат записи')}}<select :aria-label="t('Discipline recipient','Адресат записи')" v-model="recipient" required :disabled="!!selected||busy" @change="rule='';occurrence='';reviewers=reviewers.filter(id=>id!==recipient)"><option value="" disabled>—</option><option v-for="p in recipients" :key="p.id" :value="p.id">{{p.display_name}}</option></select></label>
  <label>{{t('Description of alleged event','Описание предполагаемого события')}}<textarea v-model="description" required maxlength="10000" /></label>
  <label>{{t('Proposed conditions','Предлагаемые условия')}}<textarea v-model="conditions" required maxlength="10000" /></label>
  <label>{{t('Deadline (ISO 8601 with timezone, optional)','Срок (ISO 8601 с часовым поясом, необязательно)')}}<input v-model="deadline" placeholder="2026-11-01T18:00:00+01:00"></label>
  <label>{{t('Exact rule version (optional)','Точная версия правила (необязательно)')}}<select v-model="rule"><option value="">—</option><option v-if="selected&&current(selected).rule_version_id" :value="current(selected).rule_version_id!">{{current(selected).rule_title}} · {{current(selected).rule_version_id}}</option><option v-for="a in rules.filter(a=>a.recipient_id===recipient&&a.accepted_at)" :key="a.id" :value="a.rule_version_id">{{a.title}} · {{a.rule_version_id}}</option></select></label>
  <label>{{t('Related ritual occurrence (optional)','Связанное выполнение ритуала (необязательно)')}}<select v-model="occurrence"><option value="">—</option><option v-if="selected&&current(selected).occurrence_id" :value="current(selected).occurrence_id!">{{current(selected).occurrence_id}}</option><option v-for="o in occurrences.filter(o=>o.recipient_id===recipient)" :key="o.id" :value="o.id">{{o.title}} · {{o.local_day}}</option></select></label>
  <fieldset :disabled="!!selected||busy"><legend>{{t('Explicit reviewers','Назначенные проверяющие')}}</legend><label v-for="p in participants.filter(p=>p.id!==recipient)" :key="p.id"><input v-model="reviewers" type="checkbox" :value="p.id">{{t('Reviewer: ','Проверяющий: ')}}{{p.display_name}}</label></fieldset>
  <p>{{t('Each revision needs fresh recipient acceptance. Participants and reviewers cannot be replaced.','Каждая новая версия требует согласия адресата. Автор, адресат и проверяющие не заменяются.')}}</p>
  <button :disabled="busy||me.paused||!reviewers.length">{{t('Send discipline proposal','Отправить дисциплинарное предложение')}}</button><button type="button" :disabled="busy" @click="editing=false">{{t('Cancel','Отмена')}}</button>
 </form>
 <p v-if="!rows.length">{{t('No visible discipline records','Нет доступных дисциплинарных записей')}}</p>
 <label>{{t('Transition comment (optional)','Комментарий к действию (необязательно)')}}<textarea v-model="comment" maxlength="5000" /></label>
 <article v-for="r in visibleRows" :key="r.id">
  <h3>{{name(r.author_id)}} → {{name(r.recipient_id)}}</h3><p>{{current(r).description}}</p><p>{{current(r).conditions}}</p><p>{{r.status}}</p>
  <p>{{t('Reviewers','Проверяющие')}}: {{r.reviewer_ids.map(name).join(', ')}}</p>
  <p>{{t('Exact version','Точная версия')}}: {{r.version_id}}</p>
  <p v-if="current(r).rule_version_id">{{current(r).rule_title}} · {{current(r).rule_version_id}}</p>
  <p v-if="current(r).deadline">{{current(r).deadline}}</p>
  <p v-if="!r.effective&&['accepted','in_progress','completed'].includes(r.status)">{{t('Execution suspended: current authority is required.','Выполнение приостановлено: нужны актуальные полномочия.')}}</p>
  <template v-if="r.recipient_id===me.id">
   <button v-if="r.status==='proposed'" :disabled="busy||me.paused" @click="review=r">{{t('Accept proposal','Принять предложение')}}</button>
   <button v-if="r.status==='proposed'" :disabled="busy" @click="act(r,'decline')">{{t('Decline proposal','Отклонить предложение')}}</button>
   <button v-if="r.status==='accepted'" :disabled="busy||me.paused||!r.effective" @click="act(r,'start')">{{t('Start action','Начать выполнение')}}</button>
   <button v-if="r.status==='in_progress'" :disabled="busy||me.paused||!r.effective" @click="act(r,'complete')">{{t('Mark completed','Отметить выполнение')}}</button>
   <button v-if="['proposed','accepted','in_progress','completed'].includes(r.status)" :disabled="busy" @click="act(r,'dispute')">{{t('Dispute proposal','Оспорить предложение')}}</button>
  </template>
  <button v-if="r.status==='completed'&&r.reviewer_ids.includes(me.id)" :disabled="busy||me.paused||!r.effective" @click="act(r,'confirm')">{{t('Confirm completion','Подтвердить выполнение')}}</button>
  <button v-if="r.author_id===me.id&&!['confirmed','declined','cancelled'].includes(r.status)" :disabled="busy||me.paused" @click="edit(r)">{{t('Revise conditions','Изменить условия')}}</button>
  <button v-if="!['confirmed','declined','cancelled'].includes(r.status)" :disabled="busy" @click="act(r,'cancel')">{{t('Withdraw / cancel','Отозвать / отменить')}}</button>
  <button :disabled="busy" @click="history=history===r.id?'':r.id">{{t('Show discipline history','Показать историю дисциплины')}}</button>
  <section v-if="history===r.id" role="region" :aria-label="t('Discipline history','История дисциплины')"><h4>{{t('Immutable versions and history','Неизменяемые версии и история')}}</h4><article v-for="v in r.versions" :key="v.id"><p>{{v.id}} · {{v.created_at}}</p><p>{{v.description}}</p><p>{{v.conditions}}</p><p>{{v.rule_title}} {{v.rule_version_id}}</p></article><p v-for="h in r.history" :key="h.revision">{{h.revision}} · {{h.status}} · {{name(h.actor_id)}} · {{h.created_at}} · {{h.version_id}} · {{h.comment}}</p></section>
 </article>
 <div v-if="review" role="dialog" aria-modal="true" :aria-label="t('Review discipline version','Подтверждение версии дисциплины')"><h3>{{t('Review exact conditions','Проверьте точные условия')}}</h3><p>{{current(review).description}}</p><p>{{current(review).conditions}}</p><p>{{review.version_id}}</p><p>{{current(review).rule_title}} {{current(review).rule_version_id}}</p><p>{{current(review).deadline}}</p><p>{{t('You may decline, dispute or withdraw consent.','Вы можете отклонить, оспорить или отозвать согласие.')}}</p><button :disabled="busy||me.paused" @click="act(review,'accept')">{{t('Confirm exact version','Подтверждаю точную версию')}}</button><button :disabled="busy" @click="review=null">{{t('Cancel','Отмена')}}</button></div>
</section>
</template>
