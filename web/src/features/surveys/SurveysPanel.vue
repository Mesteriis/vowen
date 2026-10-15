<script setup lang="ts">
import {onMounted,ref,watch} from 'vue'
import type {components} from '../../shared/api'
import type {SessionClient} from '../auth/session'
import ScheduleFields from '../rituals/ScheduleFields.vue'
type S=components['schemas'];type Plan=S['SurveyView'];type Wave=S['WaveView']
const props=defineProps<{client:SessionClient;me:S['MemberView'];participants:S['ParticipantView'][];ru:boolean}>()
const emit=defineEmits<{changed:[]}>()
const plans=ref<Plan[]>([]),forms=ref<S['FormView'][]>([]),rituals=ref<S['RitualAssignmentView'][]>([]),waves=ref<Wave[]>([]),history=ref('')
const editing=ref(false),version=ref(''),recipient=ref(''),readers=ref<string[]>([]),mode=ref('periodic'),assignment=ref(''),retention=ref(90),ttl=ref(7),deliver=ref(true),busy=ref(false),error=ref('')
const schedule=ref<S['Schedule']>({kind:'daily',timezone:props.me.timezone,hour:10,minute:0,start_date:new Intl.DateTimeFormat('en-CA',{timeZone:props.me.timezone,year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date()),weekdays:[],window_hours:24})
let key=crypto.randomUUID();const manualKeys=new Map<string,string>()
watch([version,recipient,readers,mode,assignment,schedule,retention,ttl,deliver],()=>{key=crypto.randomUUID()},{deep:true})
const t=(en:string,ru:string)=>props.ru?ru:en
function label(value:string){const labels:Record<string,[string,string]>={created:['Created','Создано'],skipped:['Skipped','Пропущено'],paused:['Paused','На паузе'],before_creation:['Before plan creation','До создания расписания'],expired:['Invitation window expired','Окно приглашения истекло'],audience_unavailable:['Participant unavailable','Участник недоступен'],source_unavailable:['Source unavailable','Источник недоступен'],once:['Once','Один раз'],daily:['Daily','Каждый день'],weekly:['Selected weekdays','По дням недели']};const pair=labels[value];return pair?t(pair[0],pair[1]):t('Unavailable','Недоступно')}
function name(id:string){return props.participants.find(p=>p.id===id)?.display_name??id}
async function run(action:()=>Promise<void>){busy.value=true;error.value='';try{await action()}catch(e){error.value=e instanceof Error?e.message:'NETWORK_ERROR'}finally{busy.value=false}}
async function load(){plans.value=await props.client.get<Plan[]>('/survey-schedules');forms.value=await props.client.get<S['FormView'][]>('/forms');rituals.value=await props.client.get<S['RitualAssignmentView'][]>('/ritual-assignments')}
onMounted(()=>run(load))
async function create(){await run(async()=>{const source=rituals.value.find(a=>a.id===assignment.value);await props.client.post('/survey-schedules',{form_version_id:version.value,recipient_id:mode.value==='feedback'?source?.recipient_id:recipient.value,reader_ids:readers.value,schedule:mode.value==='periodic'?schedule.value:null,ritual_assignment_id:mode.value==='feedback'?assignment.value:null,retention_days:retention.value,ttl_days:ttl.value,deliver:deliver.value,idempotency_key:key});key=crypto.randomUUID();editing.value=false;await load();emit('changed')})}
async function pause(p:Plan){await run(async()=>{const paused=p.author_id===props.me.id?p.owner_paused:p.recipient_paused;await props.client.post(`/survey-schedules/${p.id}/${paused?'resume':'pause'}`,{expected_version:p.revision});await load()})}
async function show(p:Plan){await run(async()=>{waves.value=await props.client.get<Wave[]>(`/survey-schedules/${p.id}/waves`);history.value=p.id})}
async function send(p:Plan){await run(async()=>{const k=manualKeys.get(p.id)??crypto.randomUUID();manualKeys.set(p.id,k);await props.client.post(`/survey-schedules/${p.id}/send-now`,{expected_version:p.revision,idempotency_key:k});manualKeys.delete(p.id);waves.value=await props.client.get<Wave[]>(`/survey-schedules/${p.id}/waves`);history.value=p.id;emit('changed')})}
</script>
<template>
<section id="surveys" :aria-busy="busy"><h2>{{t('Recurring surveys','Повторные анкеты')}}</h2><p v-if="error" role="alert">{{error}}</p>
<p>{{t('Each wave has a separate invitation and fixed published form version. Readers are explicit. Guests use fresh manual invitations.','Каждая волна — отдельное приглашение с закреплённой опубликованной версией. Читатели заданы явно. Для гостей создавайте новые приглашения вручную.')}}</p>
<button :disabled="busy" @click="run(load)">{{t('Refresh surveys','Обновить повторные анкеты')}}</button><button :disabled="busy||me.paused" @click="run(async()=>{await load();editing=true})">{{t('New survey schedule','Новое расписание анкеты')}}</button>
<p v-if="!plans.length&&!busy">{{t('No survey schedules yet','Пока нет расписаний анкет')}}</p>
<form v-if="editing" @submit.prevent="create"><fieldset :disabled="busy"><legend>{{t('Survey schedule','Расписание анкеты')}}</legend>
<label>{{t('Published form version','Опубликованная версия анкеты')}}<select v-model="version" required><option value="" disabled>—</option><option v-for="f in forms.filter(f=>f.status==='published')" :key="f.version_id" :value="f.version_id">{{f.schema_body.title}} · v{{f.revision}}</option></select></label>
<label>{{t('Survey trigger','Условие анкеты')}}<select v-model="mode"><option value="periodic">{{t('Schedule','Расписание')}}</option><option value="feedback">{{t('After approved ritual','После принятого ритуала')}}</option></select></label>
<template v-if="mode==='periodic'"><label>{{t('Survey recipient','Получатель анкеты')}}<select v-model="recipient" required><option value="" disabled>—</option><option v-for="p in participants" :key="p.id" :value="p.id">{{p.display_name}}</option></select></label><ScheduleFields v-model="schedule" :ru="ru" :window-label="t('Invitation window (hours)','Окно приглашения (часы)')" /></template>
<label v-else>{{t('Source ritual assignment','Назначенный ритуал')}}<select v-model="assignment" required><option value="" disabled>—</option><option v-for="a in rituals.filter(a=>a.issuer_id===me.id&&a.effective)" :key="a.id" :value="a.id">{{a.title}} → {{name(a.recipient_id)}}</option></select></label>
<fieldset><legend>{{t('Survey readers','Читатели анкеты')}}</legend><label v-for="p in participants" :key="p.id"><input v-model="readers" type="checkbox" :value="p.id">{{p.display_name}}</label></fieldset>
<label v-if="mode==='feedback'">{{t('Feedback invitation days','Срок обратной связи, дней')}}<input v-model.number="ttl" type="number" min="1" max="7" required></label>
<label>{{t('Survey retention days','Хранение анкеты, дней')}}<input v-model.number="retention" type="number" min="1" max="365" required></label>
<label><input v-model="deliver" type="checkbox">{{t('Try Telegram delivery','Попробовать доставку в Telegram')}}</label><button>{{t('Create survey schedule','Создать расписание анкеты')}}</button><button type="button" @click="editing=false">{{t('Cancel','Отмена')}}</button>
</fieldset></form>
<article v-for="p in plans" :key="p.id"><h3>{{p.title}}</h3><p>{{name(p.author_id)}} → {{name(p.recipient_id)}} · {{p.schedule?`${label(p.schedule.kind)} · ${p.schedule.timezone}`:t('After approved ritual','После принятого ритуала')}}</p><p>{{t('Fixed version','Закреплённая версия')}}: {{p.form_version_id}}</p><p>{{t('Readers','Читатели')}}: {{p.reader_ids.map(name).join(', ')||'—'}}</p><p>{{t('Author pause','Пауза автора')}}: {{p.owner_paused}} · {{t('Recipient pause','Пауза получателя')}}: {{p.recipient_paused}}</p><p v-if="!p.source_effective">{{t('Form or source authority unavailable; review before creating a new schedule.','Анкета или полномочия источника недоступны; проверьте их перед созданием нового расписания.')}}</p>
<button :disabled="busy" @click="pause(p)">{{(p.author_id===me.id?p.owner_paused:p.recipient_paused)?t('Resume my survey schedule','Снять мою паузу анкеты'):t('Pause my survey schedule','Поставить мою паузу анкеты')}}</button>
<button v-if="p.author_id===me.id" :disabled="busy||p.owner_paused||p.recipient_paused||!p.source_effective||me.paused" @click="send(p)">{{t('Send a new wave now','Создать новую волну сейчас')}}</button><button :disabled="busy" @click="show(p)">{{t('Wave history','История волн')}}</button>
<ul v-if="history===p.id"><li v-for="w in waves" :key="w.id">{{w.due_at}} · {{label(w.status)}} · {{w.reason?label(w.reason):''}} <span v-if="w.invitation_id">{{t('Invitation','Приглашение')}} {{w.invitation_id}}</span></li></ul>
</article>
</section>
</template>
