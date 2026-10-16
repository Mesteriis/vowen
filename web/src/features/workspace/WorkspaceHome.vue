<script setup lang="ts">
import {computed,onMounted,ref,watch} from 'vue'
import {IconArrowUpRight,IconCalendar,IconCircleCheck,IconClipboardCheck,IconGift,IconNotebook,IconUsers,IconFileText,IconChevronRight,IconRefresh} from '@tabler/icons-vue'
import type {components} from '../../shared/api'
import type {SessionClient} from '../auth/session'
import {partnerId,relationRole,statusLabel,useWorkspaceView,type Section} from './context'
type S=components['schemas']
const props=defineProps<{client:SessionClient;me:S['MemberView'];participants:S['ParticipantView'][];relations:S['RelationView'][];ru:boolean;active:boolean}>()
const emit=defineEmits<{navigate:[Section];context:[string]}>()
const view=useWorkspaceView()
const occurrences=ref<S['OccurrenceView'][]>([]),assignments=ref<S['RitualAssignmentView'][]>([]),grants=ref<S['GrantView'][]>([]),forms=ref<S['FormAccess'][]>([]),notices=ref<S['RitualNoticeView'][]>([])
const busy=ref(false),error=ref(false)
let loadId=0
const t=(en:string,ru:string)=>props.ru?ru:en
async function load(){
 const id=++loadId;busy.value=true;error.value=false
 try{const data=await Promise.all([props.client.get<S['OccurrenceView'][]>('/ritual-occurrences'),props.client.get<S['RitualAssignmentView'][]>('/ritual-assignments'),props.client.get<S['GrantView'][]>('/reward-grants'),props.client.get<S['FormAccess'][]>('/form-invitations'),props.client.get<S['RitualNoticeView'][]>('/ritual-notices')]);if(id!==loadId)return;[occurrences.value,assignments.value,grants.value,forms.value,notices.value]=data}
 catch{if(id===loadId){error.value=true;occurrences.value=[];assignments.value=[];grants.value=[];forms.value=[];notices.value=[]}}
 finally{if(id===loadId)busy.value=false}
}
onMounted(load)
watch(()=>props.active,active=>{if(active)void load()})
watch(view.revision,()=>{occurrences.value=[];grants.value=[];void load()})
const visible=computed(()=>occurrences.value.filter(o=>view.occurrence(o,assignments.value)))
const mine=computed(()=>visible.value.filter(o=>o.recipient_id===props.me.id&&['scheduled','needs_changes','submitted'].includes(o.status)).sort((a,b)=>a.due_at.localeCompare(b.due_at)))
const reviews=computed(()=>visible.value.filter(o=>o.can_review&&!props.me.paused))
const offered=computed(()=>grants.value.filter(g=>view.pair(g.issuer_id,g.recipient_id)&&g.recipient_id===props.me.id&&g.status==='offered'))
const pendingForms=computed(()=>forms.value.filter(f=>f.status==='draft'))
const team=computed(()=>visible.value.filter(o=>o.recipient_id!==props.me.id&&assignments.value.some(a=>a.id===o.assignment_id&&a.issuer_id===props.me.id)))
const agenda=computed(()=>[...new Map([...mine.value,...team.value,...reviews.value].map(o=>[o.id,o])).values()].sort((a,b)=>a.due_at.localeCompare(b.due_at)).slice(0,5))
const upcoming=computed(()=>visible.value.filter(o=>o.status==='scheduled').sort((a,b)=>a.due_at.localeCompare(b.due_at)).slice(0,4))
const connected=computed(()=>props.relations.filter(r=>r.status!=='revoked'))
const visibleNotices=computed(()=>notices.value.filter(n=>!view.selected.value||assignments.value.some(a=>a.id===n.assignment_id&&view.assignment(a))).slice(0,4))
function name(id:string){return props.participants.find(p=>p.id===id)?.display_name??t('Participant','Участник')}
function when(value:string){return new Intl.DateTimeFormat(props.ru?'ru-RU':'en-GB',{timeZone:props.me.timezone,day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}).format(new Date(value))}
const dominantContext=computed(()=>view.selected.value?.dominant_user_id===props.me.id)
const stats=computed(()=>[
 {icon:IconCalendar,value:dominantContext.value?team.value.length:mine.value.length,label:dominantContext.value?t('Participant schedule','График подчинённых'):t('For you','Ваши выполнения'),section:'rituals' as Section},
 {icon:IconClipboardCheck,value:reviews.value.length,label:t('To review','Ждут проверки'),section:'rituals' as Section},
 {icon:IconGift,value:offered.value.length,label:t('Reward offers','Предложено наград'),section:'rewards' as Section},
 {icon:IconFileText,value:pendingForms.value.length,label:t('Personal forms','Личные анкеты'),section:'forms' as Section}
])
</script>
<template>
<div class="home-layout" :aria-busy="busy">
 <div class="home-main">
  <section class="ritual-hero"><img src="/brand/vowen-trust.webp" alt=""><div><span class="eyebrow">{{t('RITUALS MAKE US CLOSER','МАЛЕНЬКИЕ ДЕЙСТВИЯ. БОЛЬШЕ БЛИЗОСТИ.')}}</span><h2>{{t('Trust grows in the little things.','Доверие растёт в маленьких действиях.')}}</h2><p>{{t('Your rhythm. Your choice. Your agreements.','Ваш ритм. Ваш выбор. Ваши договорённости.')}}</p><a href="#rituals" class="hero-link" @click.prevent="emit('navigate','rituals')">{{t('Your rituals','К ритуалам')}}<IconArrowUpRight :size="17" /></a></div></section>
  <div class="home-stats"><a v-for="stat in stats" :key="stat.label" :href="'#'+stat.section" @click.prevent="emit('navigate',stat.section)"><component :is="stat.icon" :size="23" :stroke-width="1.5" /><strong>{{busy?'…':error?'—':stat.value}}</strong><span>{{stat.label}}</span></a></div>
  <p v-if="error" role="alert">{{t('Your day could not be loaded. Try refreshing.','Не удалось загрузить ваш день. Попробуйте обновить.')}} <button class="quiet-button" @click="load">{{t('Try again','Повторить')}}</button></p>
  <section class="dashboard-card agenda-card"><div class="card-heading"><h2><IconCalendar :size="20" />{{view.selected.value?t('In this relationship','В этих отношениях'):t('Your day','Мой день')}}</h2><a href="#rituals" @click.prevent="emit('navigate','rituals')">{{t('All rituals','Все ритуалы')}}<IconChevronRight :size="14" /></a></div>
   <p v-if="busy" role="status" class="empty-state">{{t('Bringing your day together…','Собираем ваш день…')}}</p>
   <p v-else-if="error" class="muted">{{t('Your day is temporarily unavailable.','Ваш день временно недоступен.')}}</p>
   <div v-else-if="!agenda.length" class="home-empty"><IconCircleCheck :size="30" :stroke-width="1.2" /><h3>{{t('Room for your own rhythm','Есть место для своего ритма')}}</h3><p>{{t('Your rituals and reports awaiting review will appear here.','Здесь появятся ваши выполнения и отчёты, которые ждут проверки.')}}</p><a href="#rituals" @click.prevent="emit('navigate','rituals')">{{t('Open rituals','Открыть ритуалы')}}</a></div>
   <a v-for="o in agenda" v-else :key="o.id" href="#rituals" class="day-row" @click.prevent="emit('navigate','rituals')"><span class="day-marker" :data-status="o.status"><IconClipboardCheck v-if="o.can_review" :size="21" /><IconCircleCheck v-else :size="21" /></span><span><strong>{{o.title}}</strong><small>{{o.recipient_id!==me.id?name(o.recipient_id)+' · ':''}}{{o.can_review?t('Your review is requested','Ждёт вашей проверки'):statusLabel(o.status,ru)}} · {{when(o.due_at)}}</small></span><IconChevronRight :size="16" /></a>
  </section>
  <div class="personal-shortcuts"><a href="#journal" @click.prevent="emit('navigate','journal')"><IconNotebook :size="26" :stroke-width="1.5" /><h3>{{t('Diary','Дневник')}}</h3><p>{{t('A little room for yourself. Private by default.','Немного пространства для себя. Приватно по умолчанию.')}}</p><span>{{t('Open your diary','Открыть дневник')}}<IconArrowUpRight :size="16" /></span></a><a href="#forms" @click.prevent="emit('navigate','forms')"><IconFileText :size="26" :stroke-width="1.5" /><h3>{{t('Forms & surveys','Анкеты и опросы')}}</h3><p>{{pendingForms.length?t('You have personal forms to complete.','Есть личные анкеты для заполнения.'):t('Questions that help you understand one another.','Вопросы, которые помогают услышать друг друга.')}}</p><span>{{t('Open forms','Перейти к анкетам')}}<IconArrowUpRight :size="16" /></span></a></div>
 </div>
 <aside class="home-aside">
  <section class="dashboard-card connections-card"><div class="card-heading"><h2><IconUsers :size="20" />{{t('Your circle','Мои отношения')}}</h2><a href="#relations" @click.prevent="emit('navigate','relations')">{{t('Manage','Открыть')}}<IconChevronRight :size="14" /></a></div><p v-if="!connected.length" class="muted">{{t('A relationship starts with a mutual agreement.','Отношения начинаются со взаимного соглашения.')}}</p><button v-for="relation in connected" :key="relation.id" class="connection-row" @click="emit('context',relation.id)"><span class="person-monogram" aria-hidden="true">{{name(partnerId(relation,me.id)??'').slice(0,1)}}</span><span><strong>{{name(partnerId(relation,me.id)??'')}}</strong><small>{{relationRole(relation,me.id)==='dominant'?t('You are Dominant here','Вы — Dominant'):t('You are Submissive here','Вы — Submissive')}}</small></span><span class="connection-state" :data-status="relation.status">{{statusLabel(relation.status,ru)}}</span></button></section>
  <section class="dashboard-card"><div class="card-heading"><h2><IconCalendar :size="20" />{{t('Coming up','Ближайшее')}}</h2></div><p v-if="error" class="muted">{{t('Refresh to load upcoming rituals.','Обновите, чтобы загрузить ближайшие ритуалы.')}}</p><p v-else-if="!upcoming.length" class="muted">{{t('No scheduled rituals in this view.','В этом контексте пока нет запланированных ритуалов.')}}</p><a v-for="o in upcoming" :key="o.id" href="#rituals" class="upcoming-row" @click.prevent="emit('navigate','rituals')"><span>{{when(o.due_at)}}</span><strong>{{o.title}}</strong></a></section>
  <section class="dashboard-card"><div class="card-heading"><h2><IconClipboardCheck :size="20" />{{t('Updates','Обновления')}}</h2><button class="icon-button" :aria-label="t('Refresh your day','Обновить мой день')" :disabled="busy" @click="load"><IconRefresh :size="16" /></button></div><p v-if="error" class="muted">{{t('Updates are temporarily unavailable.','Обновления временно недоступны.')}}</p><p v-else-if="!visibleNotices.length" class="muted">{{t('Quiet for now. Updates will appear here.','Пока тихо. Здесь появятся новые события.')}}</p><a v-for="notice in visibleNotices" :key="notice.id" href="#rituals" class="update-row" @click.prevent="emit('navigate','rituals')"><span>{{t('There is a ritual update','Обновление по ритуалу')}}</span><small>{{when(notice.created_at)}}</small></a></section>
  <p class="home-note">{{t('Closer through care. With room to be yourself.','Ближе через заботу. С пространством быть собой.')}}</p>
 </aside>
</div>
</template>
