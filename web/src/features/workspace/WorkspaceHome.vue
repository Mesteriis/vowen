<script setup lang="ts">
import {computed,onMounted,onUnmounted,ref,watch} from 'vue'
import {IconCalendar,IconCircleCheck,IconClipboardCheck,IconNotebook,IconChevronRight} from '@tabler/icons-vue'
import type {components} from '../../shared/api'
import type {SessionClient} from '../auth/session'
import {statusLabel,useWorkspaceView,type Section} from './context'
import {dayAgenda} from './day'
type S=components['schemas']
const props=defineProps<{client:SessionClient;me:S['MemberView'];participants:S['ParticipantView'][];relations:S['RelationView'][];ru:boolean;active:boolean}>()
const emit=defineEmits<{navigate:[Section];open:[S['OccurrenceView']]}>()
const view=useWorkspaceView(),occurrences=ref<S['OccurrenceView'][]>([]),assignments=ref<S['RitualAssignmentView'][]>([])
const busy=ref(false),error=ref(false),now=ref(new Date())
let loadId=0
const t=(en:string,ru:string)=>props.ru?ru:en
async function load(){
 const id=++loadId;busy.value=true;error.value=false
 try{const [o,a]=await Promise.all([props.client.get<S['OccurrenceView'][]>('/ritual-occurrences'),props.client.get<S['RitualAssignmentView'][]>('/ritual-assignments')]);if(id===loadId){occurrences.value=o;assignments.value=a}}
 catch{if(id===loadId){error.value=true;occurrences.value=[];assignments.value=[]}}
 finally{if(id===loadId)busy.value=false}
}
onMounted(load)
const timer=setInterval(()=>now.value=new Date(),60000)
onUnmounted(()=>clearInterval(timer))
watch(()=>props.active,active=>{if(active)void load()})
watch(view.revision,()=>{occurrences.value=[];void load()})
const visible=computed(()=>occurrences.value.filter(o=>view.occurrence(o,assignments.value)))
const buckets=computed(()=>dayAgenda(visible.value,props.me.timezone,now.value))
const reviews=computed(()=>props.me.paused?[]:buckets.value.reviews)
const preview=computed(()=>reviews.value[0])
function name(id:string){return props.participants.find(p=>p.id===id)?.display_name??t('Participant','Участник')}
function time(value:string){return new Intl.DateTimeFormat(props.ru?'ru-RU':'en-GB',{timeZone:props.me.timezone,hour:'2-digit',minute:'2-digit'}).format(new Date(value))}
function date(value:Date|string){return new Intl.DateTimeFormat(props.ru?'ru-RU':'en-GB',{timeZone:props.me.timezone,day:'numeric',month:'long',weekday:'long'}).format(new Date(value))}
</script>
<template>
<div class="quiet-home" :aria-busy="busy">
 <section class="quiet-agenda">
  <div class="quiet-heading"><h2>{{t('Today','Сегодня')}}</h2><time>{{date(now)}}</time></div>
  <p v-if="busy" role="status">{{t('Bringing your day together…','Собираем ваш день…')}}</p>
  <div v-else-if="error" role="alert"><p>{{t('Your day could not be loaded. Try refreshing.','Не удалось загрузить ваш день. Попробуйте обновить.')}}</p><button @click="load">{{t('Try again','Повторить')}}</button></div>
  <template v-else>
   <div v-if="reviews.length" class="quiet-attention"><IconClipboardCheck :size="22" /><span>{{ru?`Ждут проверки: ${reviews.length}`:`Reports to review: ${reviews.length}`}}</span><button @click="emit('open',reviews[0]!)">{{t('Review','Проверить')}}</button></div>
   <p v-if="!buckets.today.length" class="quiet-empty">{{t('No rituals scheduled for today.','На сегодня ритуалов нет.')}}</p>
   <a v-for="o in buckets.today" :key="o.id" href="#rituals" class="quiet-day-row" :data-status="o.status" @click.prevent="emit('open',o)">
    <time>{{time(o.due_at)}}</time><span class="quiet-status"><IconClipboardCheck v-if="o.can_review" :size="22" /><IconCircleCheck v-else-if="o.status==='approved'" :size="22" /><IconCalendar v-else :size="22" /></span><span class="quiet-task"><strong>{{o.title}}</strong><small>{{name(o.recipient_id)}}</small><small class="quiet-state">{{o.can_review?t('Awaiting your review','Ждёт вашей проверки'):statusLabel(o.status,ru)}}</small></span><IconChevronRight :size="17" />
   </a>
  </template>
  <a href="#journal" class="quiet-diary" @click.prevent="emit('navigate','journal')"><IconNotebook :size="22" /><span>{{t('My diary','Мой дневник')}}</span><IconChevronRight :size="17" /></a>
 </section>
 <aside v-if="!busy&&!error" class="quiet-aside">
  <section v-if="preview" class="quiet-review"><img src="/brand/vowen-trust.webp" alt=""><div><h2>{{t('Awaiting your attention','Ожидает вашего внимания')}}</h2><small>{{t('Report','Отчёт')}} · {{name(preview.recipient_id)}}</small><h3>{{preview.title}}</h3><p>{{preview.reports.at(-1)?.text}}</p><button @click="emit('open',preview)">{{t('Open report','Открыть отчёт')}}</button></div></section>
  <section v-if="buckets.upcoming.length" class="quiet-upcoming"><h2>{{t('Coming up','Ближайшее')}}</h2><p v-if="!buckets.upcoming.length" class="muted">{{t('No upcoming rituals.','Ближайших ритуалов нет.')}}</p><a v-for="o in buckets.upcoming" :key="o.id" href="#rituals" @click.prevent="emit('open',o)"><IconCalendar :size="18" /><span><small>{{date(o.due_at)}} · {{time(o.due_at)}}</small><strong>{{o.title}}</strong><small>{{name(o.recipient_id)}}</small></span><IconChevronRight :size="15" /></a></section>
 </aside>
</div>
</template>
