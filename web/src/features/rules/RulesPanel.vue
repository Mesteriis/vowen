<script setup lang="ts">
import {onMounted,ref,watch,computed,nextTick} from 'vue'
import type {components} from '../../shared/api'
import type {SessionClient} from '../auth/session'
import {IconPlus,IconChevronDown,IconShieldCheck,IconLink,IconUser,IconPencil,IconPlayerPause,IconHistory,IconArchive,IconCheck,IconX,IconUserPlus,IconTrash,IconDots} from '@tabler/icons-vue'
import {statusLabel} from '../workspace/context'
import AssignPunishment from '../discipline/AssignPunishment.vue'
import PunishmentPicker from './PunishmentPicker.vue'
import ChangeRequests from '../change-requests/ChangeRequests.vue'
import {useWorkspaceView} from '../workspace/context'
type Rule=components['schemas']['RuleView']
type Assignment=components['schemas']['RuleAssignmentView']
const props=defineProps<{client:SessionClient;ru:boolean;active:boolean;me:components['schemas']['MemberView'];participants:components['schemas']['ParticipantView'][]}>()
const tab=ref<'active'|'requests'|'templates'>('active'),requestCount=ref(0),expanded=ref(''),more=ref('')
const dialog=ref<HTMLDialogElement|null>(null),confirmation=ref<{assignment?:Assignment;rule?:Rule;action:string;label:string}|null>(null)
const requests=ref<InstanceType<typeof ChangeRequests>|null>(null)
const view=useWorkspaceView()
const subordinate=computed(()=>view.selected.value?.submissive_user_id===props.me.id&&view.selected.value?.status==='active'&&view.selected.value?.scopes.includes('rules.assign'))
const templates=ref<Rule[]>([]),assignments=ref<Assignment[]>([]),busy=ref(false),error=ref('')
const recipients=computed(()=>props.participants.filter(p=>view.recipients('rules.assign').includes(p.id)))
const visibleAssignments=computed(()=>assignments.value.filter(view.rule))
const history=ref<Rule[]>([]),historyFor=ref('')
const punishmentRule=ref<Assignment|null>(null)
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
watch(()=>props.active,active=>{if(active)void run(load)})
watch(view.revision,()=>{punishmentRule.value=null;tab.value='active';recipient.value='';editor.value=false;assigning.value=null;review.value=null;historyFor.value='';confirmation.value=null;expanded.value='';void run(load)})
watch(recipient,id=>{managers.value=managers.value.filter(manager=>manager!==id)})
watch(()=>props.me.paused,()=>{
 assignments.value=assignments.value.filter(a=>!props.me.paused||a.recipient_id===props.me.id)
 void run(load)
})
const dialogOpen=computed(()=>editor.value||!!assigning.value||!!review.value||!!historyFor.value||!!confirmation.value)
watch(dialogOpen,async open=>{await nextTick();if(open&&!dialog.value?.open)dialog.value?.showModal();else if(!open)dialog.value?.close()})
function close(){if(busy.value)return;editor.value=false;assigning.value=null;review.value=null;historyFor.value='';confirmation.value=null}
function create(){if(subordinate.value)void requests.value?.start({kind:'rule_add',relation_id:view.selected.value!.id});else edit(null)}
function ask(a:Assignment,action:string,label:string){confirmation.value={assignment:a,action,label};more.value=''}
async function confirm(){const c=confirmation.value;if(!c)return;if(c.assignment)await decide(c.assignment,c.action);else if(c.rule)await transition(c.rule,'archive');if(!error.value)confirmation.value=null}
function edit(rule:Rule|null){selected.value=rule;title.value=rule?.title??'';description.value=rule?.description??'';discipline.value=rule?.discipline??'';editor.value=true;assigning.value=null}
async function showHistory(rule:Rule){await run(async()=>{history.value=await props.client.get<Rule[]>(`/rules/${rule.id}/versions`);historyFor.value=rule.id})}
async function save(){await run(async()=>{
 const r=selected.value,body={title:title.value,description:description.value,discipline:discipline.value}
 const saved=!r?await props.client.post<Rule>('/rules',body):r.status==='draft'?await props.client.patch<Rule>(`/rules/${r.id}`,{...body,expected_version:r.revision}):await props.client.post<Rule>(`/rules/${r.id}/versions`,{...body,expected_version:r.revision})
 editor.value=false;tab.value='templates';expanded.value=saved.id;await load()
})}
async function transition(r:Rule,action:'publish'|'archive'){await run(async()=>{await props.client.post(`/rules/${r.id}/${action}`,{expected_version:r.revision});await load()})}
function startAssign(r:Rule){assigning.value=r;recipient.value=recipients.value.length===1?recipients.value[0]!.id:'';managers.value=[props.me.id];editor.value=false}
async function assign(){await run(async()=>{const r=assigning.value;if(!r)return
 await props.client.post(`/rules/${r.id}/assignments`,{rule_version_id:r.version_id,recipient_id:recipient.value,manager_ids:managers.value.filter(id=>id!==recipient.value)})
 assigning.value=null;tab.value='active';await load()
})}
async function propose(a:Assignment,kind:'rule_edit'|'rule_delete'){await requests.value?.start({kind,assignment_id:a.id,expected_version:a.revision,content:kind==='rule_edit'?{title:a.title,description:a.description,discipline:a.discipline??''}:null})}
async function decide(a:Assignment,action:string){await run(async()=>{
 await props.client.post(`/rule-assignments/${a.id}/${action}`,{expected_version:a.revision,rule_version_id:a.rule_version_id})
 review.value=null;await load()
})}
</script>
<template>
 <section id="rules" class="rules-panel" :aria-label="t('Rules','Правила')">
  <div class="rules-controls">
   <nav class="rules-tabs" :aria-label="t('Rule sections','Разделы правил')">
    <button :aria-pressed="tab==='active'" @click="tab='active'">{{t('Rules','Правила')}}</button>
    <button :aria-pressed="tab==='requests'" @click="tab='requests'">{{t('Requests','Заявки')}}<small v-if="requestCount">{{requestCount}}</small></button>
    <button v-if="!subordinate" :aria-pressed="tab==='templates'" @click="tab='templates'">{{t('Templates','Шаблоны')}}</button>
   </nav>
   <button class="rule-icon rule-create" :disabled="busy||me.paused" :aria-label="subordinate?t('Propose rule','Предложить правило'):t('New rule','Новое правило')" :title="subordinate?t('Propose rule','Предложить правило'):t('New rule','Новое правило')" @click="create"><IconPlus :size="21" /></button>
  </div>
  <p v-if="error&&!dialogOpen" role="alert">{{error}}</p>
  <ChangeRequests ref="requests" :show-list="tab==='requests'" :active="active" :client="client" :ru="ru" :me="me" :participants="participants" domain="rule" @count="requestCount=$event" @changed="run(load)" />
  <p v-if="tab==='requests'&&!requestCount" class="rules-empty">{{t('No pending requests. Previous decisions are in history.','Нет ожидающих заявок. Предыдущие решения — в истории.')}}</p>
  <div v-if="tab==='active'" class="rule-list">
   <p v-if="!visibleAssignments.length" class="rules-empty">{{busy?t('Loading…','Загрузка…'):t('No rules in this relationship yet.','В этих отношениях пока нет правил.')}}</p>
   <article v-for="a in visibleAssignments" :key="a.id" class="rule-card" :class="{'is-open':expanded===a.id}">
    <button class="rule-card-toggle" :aria-expanded="expanded===a.id" :aria-controls="'rule-'+a.id" @click="expanded=expanded===a.id?'':a.id;more=''">
     <IconShieldCheck class="rule-leading" :size="20" /><span><strong>{{a.title}}</strong><small>{{name(a.recipient_id)}}</small></span><span class="rule-status" :data-status="a.status">{{statusLabel(a.status,ru)}}</span><IconChevronDown class="rule-chevron" :size="18" />
    </button>
    <div v-if="expanded===a.id" :id="'rule-'+a.id" class="rule-card-body">
     <p class="rule-description">{{a.description}}</p>
     <button v-if="view.selected.value?.dominant_user_id===me.id&&view.selected.value?.submissive_user_id===a.recipient_id&&a.accepted_at" class="quiet-button" :disabled="busy||me.paused" @click="punishmentRule=a">{{t('Assign punishment for violation','Назначить наказание за нарушение')}}</button>
     <div v-if="a.discipline" class="rule-fact"><IconLink :size="19" /><div><small>{{t('Punishment','Наказание')}}</small><p>{{a.discipline}}</p></div></div>
     <div class="rule-fact"><IconUser :size="19" /><div><small>{{t('For','Для')}}</small><p>{{name(a.recipient_id)}}</p><small v-if="a.manager_ids.length">{{t('Managers: ','Управляющие: ')}}{{a.manager_ids.map(name).join(', ')}}</small></div></div>
     <div class="rule-card-actions">
      <template v-if="a.status==='pending_acceptance'&&a.recipient_id===me.id"><button :disabled="busy||me.paused" @click="review=a"><IconCheck :size="18" />{{t('Review & accept','Прочитать и принять')}}</button><button class="rule-icon" :disabled="busy" :aria-label="t('Decline rule','Отклонить правило')" :title="t('Decline rule','Отклонить правило')" @click="ask(a,'decline',t('Decline this rule?','Отклонить это правило?'))"><IconX :size="18" /></button></template>
      <button v-if="a.recipient_id===me.id&&a.status!=='revoked'" class="rule-icon" :disabled="busy||me.paused" :aria-label="t('Propose changes','Предложить изменения')" :title="t('Propose changes','Предложить изменения')" @click="propose(a,'rule_edit')"><IconPencil :size="19" /></button>
      <button v-if="['active','pending_acceptance'].includes(a.status)" class="rule-icon" :disabled="busy" :aria-label="t('Pause rule','Пауза правила')" :title="t('Pause rule','Пауза правила')" @click="ask(a,'pause',t('Pause this rule?','Поставить правило на паузу?'))"><IconPlayerPause :size="19" /></button>
      <details class="rule-meta"><summary>{{t('Version & consent','Версия и согласие')}}</summary><small>{{a.rule_version_id}}</small><p v-if="a.accepted_at">{{t('Accepted: ','Принято: ')}}{{new Date(a.accepted_at).toLocaleString(ru?'ru':'en')}}</p><p>{{a.effective&&!(me.paused&&a.recipient_id===me.id)?t('Effective','Действует'):t('Inactive','Не действует')}}</p></details>
      <div v-if="a.status!=='revoked'" class="rule-overflow"><button class="rule-icon" :aria-expanded="more===a.id" :aria-label="t('More actions','Другие действия')" @click="more=more===a.id?'':a.id"><IconDots :size="19" /></button><div v-if="more===a.id" class="rule-menu"><button v-if="a.recipient_id===me.id" :disabled="busy||me.paused" @click="propose(a,'rule_delete');more=''"><IconTrash :size="17" />{{t('Request removal','Запросить удаление')}}</button><button :disabled="busy" @click="ask(a,'revoke',a.recipient_id===me.id?t('Withdraw consent?','Отозвать согласие?'):t('Revoke rule?','Отозвать правило?'))"><IconX :size="17" />{{a.recipient_id===me.id?t('Withdraw consent','Отозвать согласие'):t('Revoke rule','Отозвать правило')}}</button></div></div>
     </div>
    </div>
   </article>
  </div>
  <div v-if="tab==='templates'&&!subordinate" class="rule-list">
   <p v-if="!templates.length" class="rules-empty">{{t('Create a rule, then assign it to a participant.','Создайте правило и назначьте его участнику.')}}</p>
   <article v-for="rule in templates" :key="rule.id" class="rule-card">
    <button class="rule-card-toggle" :aria-expanded="expanded===rule.id" @click="expanded=expanded===rule.id?'':rule.id"><IconShieldCheck :size="20" /><span><strong>{{rule.title}}</strong><small>{{t('Version','Версия')}} {{rule.revision}}</small></span><span class="rule-status">{{statusLabel(rule.status,ru)}}</span><IconChevronDown class="rule-chevron" :size="18" /></button>
    <div v-if="expanded===rule.id" class="rule-card-body"><p class="rule-description">{{rule.description}}</p><div v-if="rule.discipline" class="rule-fact"><IconLink :size="19" /><div><small>{{t('Punishment','Наказание')}}</small><p>{{rule.discipline}}</p></div></div>
     <div class="rule-card-actions">
      <button class="rule-icon" :disabled="busy||me.paused" :aria-label="rule.status==='draft'?t('Edit rule draft','Изменить черновик правила'):t('New rule version','Новая версия правила')" :title="t('Edit','Редактировать')" @click="edit(rule)"><IconPencil :size="19" /></button>
      <button v-if="rule.status==='draft'" :disabled="busy||me.paused" @click="transition(rule,'publish')"><IconCheck :size="18" />{{t('Publish','Опубликовать')}}</button>
      <button v-if="rule.status==='published'&&recipients.length" :disabled="busy||me.paused" @click="startAssign(rule)"><IconUserPlus :size="18" />{{t('Assign','Назначить')}}</button>
      <button class="rule-icon" :disabled="busy" :aria-label="t('Rule version history','История версий правила')" :title="t('Version history','История версий')" @click="showHistory(rule)"><IconHistory :size="19" /></button>
      <button v-if="rule.status!=='archived'" class="rule-icon" :disabled="busy" :aria-label="t('Archive rule','Архивировать правило')" :title="t('Archive','В архив')" @click="confirmation={rule,action:'archive',label:t('Archive this rule?','Архивировать правило?')}"><IconArchive :size="19" /></button>
     </div>
    </div>
   </article>
  </div>
  <dialog ref="dialog" class="rule-dialog" :class="{'rule-editor-dialog':editor||!!assigning}" :aria-label="editor?t('Rule editor','Редактор правила'):assigning?t('Assign rule','Назначить правило'):review?t('Review rule','Принятие правила'):historyFor?t('Version history','История версий'):t('Confirm action','Подтверждение действия')" @cancel.prevent="close">
   <header><h3>{{editor?(selected?t('Edit rule','Редактирование правила'):t('New rule','Новое правило')):assigning?t('Assign rule','Назначить правило'):review?t('Accept rule','Принять правило'):historyFor?t('Version history','История версий'):t('Confirm action','Подтверждение')}}</h3><button class="rule-icon" :disabled="busy" :aria-label="t('Close','Закрыть')" @click="close"><IconX :size="20" /></button></header>
   <p v-if="error" role="alert">{{error}}</p>
   <form v-if="editor" @submit.prevent="save">
    <label>{{t('Title','Название')}}<input v-model="title" required maxlength="200" autofocus></label>
    <label>{{t('Description','Описание')}}<textarea v-model="description" required maxlength="10000" rows="4" /></label>
    <PunishmentPicker v-model="discipline" :client="client" :ru="ru" />
    <p v-if="selected&&selected.status!=='draft'" class="muted">{{t('A new version requires new consent. The accepted version continues until replacement.','Новая версия требует нового согласия. Принятая действует до замены.')}}</p>
    <footer><button :disabled="busy||me.paused||!title.trim()||!description.trim()"><IconCheck :size="18" />{{t('Save rule','Сохранить правило')}}</button><button type="button" :disabled="busy" @click="close">{{t('Cancel','Отмена')}}</button></footer>
   </form>
   <form v-else-if="assigning" @submit.prevent="assign"><p>{{assigning.title}}</p><label>{{t('Recipient','Адресат')}}<select v-model="recipient" required><option value="" disabled>{{t('Choose participant','Выберите участника')}}</option><option v-for="p in recipients" :key="p.id" :value="p.id">{{p.display_name}}</option></select></label><details class="rule-managers"><summary>{{t('Managers','Управляющие')}} · {{managers.map(name).join(', ')||'—'}}</summary><fieldset><legend>{{t('Explicit managers','Управляющие')}}</legend><label v-for="p in participants.filter(p=>p.id!==recipient)" :key="p.id"><input v-model="managers" type="checkbox" :value="p.id">{{p.display_name}}</label></fieldset></details><p class="muted">{{t('Managers need current authority. The recipient accepts this exact version separately.','Управляющим нужны актуальные полномочия. Адресат отдельно принимает эту версию.')}}</p><footer><button :disabled="busy||me.paused||!recipient">{{t('Send rule proposal','Предложить правило')}}</button></footer></form>
   <template v-else-if="review"><h4>{{review.title}}</h4><p class="rule-description">{{review.description}}</p><div v-if="review.discipline" class="rule-fact"><IconLink :size="19" /><div><small>{{t('Punishment','Наказание')}}</small><p>{{review.discipline}}</p></div></div><small class="rule-version">{{review.rule_version_id}}</small><p class="muted">{{t('Accepting replaces the previously active version of this rule.','Принятие заменит ранее действовавшую версию этого правила.')}}</p><footer><button :disabled="busy||me.paused" @click="decide(review,'accept')">{{t('Confirm rule acceptance','Подтверждаю принятие правила')}}</button></footer></template>
   <template v-else-if="historyFor"><article v-for="v in history" :key="v.version_id"><h4>{{v.title}}</h4><p class="rule-description">{{v.description}}</p><p v-if="v.discipline">{{v.discipline}}</p><small class="rule-version">{{statusLabel(v.status,ru)}} · {{v.version_id}}</small></article></template>
   <template v-else-if="confirmation"><p>{{confirmation.label}}</p><p class="muted">{{confirmation.assignment?.title??confirmation.rule?.title}}</p><footer><button :disabled="busy" @click="confirm">{{t('Confirm','Подтвердить')}}</button><button :disabled="busy" @click="close">{{t('Cancel','Отмена')}}</button></footer></template>
  </dialog>
 <AssignPunishment v-if="punishmentRule&&view.selected.value" :key="punishmentRule.id+view.selected.value.id" :client="client" :ru="ru" :relation-id="view.selected.value.id" :recipient-name="participants.find(p=>p.id===punishmentRule?.recipient_id)?.display_name??''" :rule-version-id="punishmentRule.rule_version_id" :initial-conditions="punishmentRule.discipline" @close="punishmentRule=null"/>
 </section>
</template>
