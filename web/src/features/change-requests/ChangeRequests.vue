<script setup lang="ts">
import {ref,computed,onMounted,onUnmounted,watch,nextTick} from 'vue'
import {IconCheck,IconX,IconInfoCircle} from '@tabler/icons-vue'
import type {components} from '../../shared/api'
import type {SessionClient} from '../auth/session'
import PunishmentPicker from '../rules/PunishmentPicker.vue'
import {useWorkspaceView} from '../workspace/context'
type Row=components['schemas']['ChangeRequestView']
type Command=components['schemas']['ChangeRequestCreate']
const props=defineProps<{client:SessionClient;ru:boolean;me:components['schemas']['MemberView'];domain:'ritual'|'rule';active:boolean;participants:components['schemas']['ParticipantView'][];showList?:boolean}>()
const emit=defineEmits<{changed:[];count:[number]}>()
const context=useWorkspaceView(),rows=ref<Row[]>([]),busy=ref(false),error=ref(''),dialog=ref<HTMLDialogElement|null>(null)
const draft=ref<Partial<Command>|null>(null),selected=ref<Row|null>(null),reason=ref(''),comment=ref(''),title=ref(''),description=ref(''),discipline=ref(''),history=ref(false)
const t=(en:string,ru:string)=>props.ru?ru:en
const name=(id:string)=>props.participants.find(p=>p.id===id)?.display_name??'—'
const labels:Record<string,[string,string]>={ritual_skip:['Skip request','Пропуск ритуала'],ritual_pause:['Pause request','Пауза ритуала'],rule_add:['New rule proposal','Добавление правила'],rule_edit:['Rule change proposal','Изменение правила'],rule_delete:['Rule removal request','Удаление правила'],pending:['Pending','На согласовании'],approved:['Approved','Одобрено'],rejected:['Rejected','Отклонено'],withdrawn:['Withdrawn','Отозвано']}
const label=(key:string)=>labels[key]?.[props.ru?1:0]??key
const visible=computed(()=>rows.value.filter(r=>r.kind.startsWith(props.domain+'_')&&(!context.selected.value||r.relation_id===context.selected.value.id)))
const pending=computed(()=>visible.value.filter(r=>r.status==='pending'))
watch(pending,rows=>emit('count',rows.length),{immediate:true})
async function load(){rows.value=await props.client.get<Row[]>('/change-requests')}
async function run(fn:()=>Promise<void>){busy.value=true;error.value='';try{await fn()}catch(e){error.value=e instanceof Error?e.message:'NETWORK_ERROR'}finally{busy.value=false}}
function focus(){if(props.active&&document.visibilityState==='visible'&&!busy.value)void run(load)}
onMounted(()=>{window.addEventListener('focus',focus);document.addEventListener('visibilitychange',focus);if(props.active)void run(load)});onUnmounted(()=>{window.removeEventListener('focus',focus);document.removeEventListener('visibilitychange',focus)});watch(()=>props.active,active=>{if(active)void run(load)});watch(context.revision,()=>{dialog.value?.close();void run(load)})
watch(()=>props.me.paused,()=>run(load))
async function start(command:Partial<Command>){draft.value={...command,idempotency_key:crypto.randomUUID()};selected.value=null;reason.value='';title.value=command.content?.title??'';description.value=command.content?.description??'';discipline.value=command.content?.discipline??'';error.value='';await nextTick();dialog.value?.showModal()}
async function open(row:Row){selected.value=row;draft.value=null;comment.value='';error.value='';await nextTick();dialog.value?.showModal()}
async function send(){await run(async()=>{if(!draft.value)return;const content=['rule_add','rule_edit'].includes(draft.value.kind??'')?{title:title.value,description:description.value,discipline:discipline.value}:null;await props.client.post('/change-requests',{...draft.value,reason:reason.value,content});draft.value=null;dialog.value?.close();await load();emit('changed')})}
async function decide(action:'approve'|'reject'|'withdraw'){await run(async()=>{if(!selected.value)return;await props.client.post(`/change-requests/${selected.value.id}/${action}`,{expected_version:selected.value.revision,comment:comment.value});dialog.value?.close();selected.value=null;await load();emit('changed')})}
defineExpose({start,load})
</script>
<template>
<section v-if="visible.length&&showList!==false" class="change-requests" :aria-label="t('Change requests','Заявки на согласование')">
 <div class="change-request-heading"><h3>{{t('Requests','Заявки')}} <small>{{pending.length}}</small></h3><button class="quiet-button" @click="history=!history">{{history?t('Pending','Ожидающие'):t('History','История')}}</button></div>
 <p v-if="error&&!dialog?.open" role="alert">{{error}}</p>
 <article v-for="row in history?visible:pending" :key="row.id" class="change-request-row">
  <div><strong>{{row.title||label(row.kind)}}</strong><small>{{label(row.kind)}} · {{name(row.requester_id)}} → {{name(row.approver_id)}} · {{label(row.status)}}</small></div>
  <button class="ritual-icon-action" :aria-label="t('Open request','Открыть заявку')" @click="open(row)"><IconInfoCircle :size="18" /></button>
 </article>
</section>
<dialog ref="dialog" class="change-request-dialog" :aria-label="t('Change request','Заявка на согласование')" @cancel="draft=null;selected=null">
 <header><h3>{{label(draft?.kind??selected?.kind??'pending')}}</h3><button class="quiet-button" :aria-label="t('Close','Закрыть')" @click="dialog?.close()"><IconX :size="20" /></button></header>
 <p v-if="error" role="alert">{{error}}</p>
 <form v-if="draft" @submit.prevent="send">
  <template v-if="draft.kind==='rule_add'||draft.kind==='rule_edit'"><label>{{t('Title','Название')}}<input v-model="title" required maxlength="200"></label><label>{{t('Description','Описание')}}<textarea v-model="description" required maxlength="10000" rows="3" /></label><PunishmentPicker v-model="discipline" :client="client" :ru="ru" /></template>
  <label>{{t('Reason','Причина / предложение')}}<textarea v-model="reason" required maxlength="10000" rows="3" /></label>
  <p class="muted">{{t('Nothing changes until your dominant approves.','До решения доминанта ничего не меняется.')}}</p>
  <button :disabled="busy||me.paused">{{t('Send request','Отправить заявку')}}</button>
 </form>
 <template v-if="selected"><p>{{name(selected.requester_id)}} → {{name(selected.approver_id)}} · {{label(selected.status)}}</p><h4 v-if="selected.title">{{selected.title}}</h4><p class="request-text">{{selected.reason}}</p><template v-if="selected.content"><h4>{{selected.content.title}}</h4><p class="request-text">{{selected.content.description}}</p><p v-if="selected.content.discipline" class="request-text">{{selected.content.discipline}}</p></template><p v-if="selected.comment" class="request-text">{{t('Decision comment: ','Комментарий к решению: ')}}{{selected.comment}}</p><small>{{new Date(selected.created_at).toLocaleString(ru?'ru':'en')}}<template v-if="selected.decided_at"> · {{new Date(selected.decided_at).toLocaleString(ru?'ru':'en')}}</template></small>
  <template v-if="selected.status==='pending'"><label>{{t('Comment','Комментарий')}}<textarea v-model="comment" maxlength="10000" rows="2" /></label><div class="row-actions"><template v-if="selected.approver_id===me.id"><button :disabled="busy||me.paused" @click="decide('approve')"><IconCheck :size="18" /> {{t('Approve','Одобрить')}}</button><button :disabled="busy||me.paused" @click="decide('reject')"><IconX :size="18" /> {{t('Reject','Отклонить')}}</button></template><button v-if="selected.requester_id===me.id" :disabled="busy" @click="decide('withdraw')">{{t('Withdraw request','Отозвать заявку')}}</button></div></template>
 </template>
</dialog>
</template>
