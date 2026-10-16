<script setup lang="ts">
import {computed,ref,onMounted,onUnmounted,provide,watch,nextTick} from 'vue'
import WorkspaceHome from './features/workspace/WorkspaceHome.vue'
import RelationshipPicker from './features/workspace/RelationshipPicker.vue'
import SessionList from './features/sessions/SessionList.vue'
import {workspaceKey,partnerId,relationRole,scopeLabel,statusLabel,type Section} from './features/workspace/context'
import {IconChevronDown,IconHome,IconSun,IconShieldCheck,IconNotebook,IconGift,IconFileText,IconScale,IconUsers,IconBell,IconSettings,IconDevices,IconLogout,IconDots,IconX,IconRefresh,IconLock} from '@tabler/icons-vue'
import DisciplinePanel from './features/discipline/DisciplinePanel.vue'
import JournalPanel from './features/journal/JournalPanel.vue'
import RewardsPanel from './features/rewards/RewardsPanel.vue'
import RitualsPanel from './features/rituals/RitualsPanel.vue'
import RulesPanel from './features/rules/RulesPanel.vue'
import FormsPanel from './features/forms/FormsPanel.vue'
import NotificationSettings from './features/notifications/NotificationSettings.vue'
import ProfileSettings from './features/profile/ProfileSettings.vue'
import { SessionClient } from './features/auth/session'
import {telegramWebApp} from './features/auth/telegram'
import type { components } from './shared/api'
type Participant = components['schemas']['ParticipantView']
type Me = components['schemas']['MemberView']
type Relation = components['schemas']['RelationView']
type Session = components['schemas']['SessionView']
const reAuth=ref(false)
const client = new SessionClient(undefined,()=>{me.value=null;relations.value=[];participants.value=[];sessions.value=[];reAuth.value=true})
const instanceName=ref('Vowen'),booting=ref(true),debugAuth=ref(false),debugUser=ref('')
const debugUsers=ref<components['schemas']['DebugUserView'][]>([])
onMounted(async()=>{try{const instance=await client.get<components['schemas']['InstanceView']>('/instance');instanceName.value=instance.display_name;debugAuth.value=instance.debug_auth_enabled;if(debugAuth.value){debugUsers.value=await client.get('/auth/debug/users')}const telegram=await telegramWebApp();if(telegram?.initData){telegram.ready();await client.login(telegram.initData);await load();reAuth.value=false}}catch(e){error.value=e instanceof Error?e.message:'NETWORK_ERROR'}finally{booting.value=false}})
const ru = ref(navigator.language.startsWith('ru'))
const t = computed(() => ru.value ? {
 refresh:'Обновить',title:'Ваше пространство',login:'Войти через Telegram',closed:'Доступ только для пользователей, созданных оператором.',open:'Откройте приложение через Telegram-бота.',logout:'Выйти',pause:'Личная пауза',resume:'Снять личную паузу',relations:'Отношения',propose:'Предложить',target:'Участник',direction:'Направление',dominant:'Я предлагаю полномочия относительно участника',submissive:'Участник получает полномочия относительно меня',agreement:'Текст соглашения',accept:'Подтвердить эту версию и полномочия',relationPause:'Приостановить',relationResume:'Запросить возобновление',revoke:'Отозвать',sessions:'Сессии',empty:'Пока нет отношений',alpha:'Техническая alpha · M0–M2',error:'Ошибка',scope:'Полномочия',note:'Серверный оператор имеет технический доступ к данным. Это не E2EE.'
} : {
 refresh:'Refresh',title:'Your workspace',login:'Sign in with Telegram',closed:'Only operator-provisioned members can enter.',open:'Open this app through your Telegram bot.',logout:'Sign out',pause:'Personal pause',resume:'End personal pause',relations:'Relationships',propose:'Propose',target:'Participant',direction:'Direction',dominant:'I request authority relative to this participant',submissive:'This participant receives authority relative to me',agreement:'Agreement text',accept:'Accept this exact version and scopes',relationPause:'Pause',relationResume:'Request resumption',revoke:'Revoke',sessions:'Sessions',empty:'No relationships yet',alpha:'Technical alpha · M0–M2',error:'Error',scope:'Scopes',note:'The server operator has technical access to data. This is not E2EE.'
})
const me=ref<Me|null>(null), relations=ref<Relation[]>([]), participants=ref<Participant[]>([]), sessions=ref<Session[]>([])
const error=ref(''), busy=ref(false), target=ref(''), direction=ref('dominant'), agreement=ref('')
const scopes=ref<string[]>(['rules.assign'])
const scopeOptions=['rules.assign','rituals.assign','rituals.review','discipline.propose','discipline.review','rewards.grant']
async function run(action:()=>Promise<void>) {busy.value=true;error.value='';try{await action()}catch(e){error.value=e instanceof Error?e.message:'NETWORK_ERROR'}finally{busy.value=false}}
async function load(){
 const loaded=await Promise.all([client.get<Me>('/me'),client.get<Relation[]>('/relations'),client.get<Participant[]>('/participants'),client.get<Session[]>('/sessions')])
 ;[me.value,relations.value,participants.value,sessions.value]=loaded
 ru.value=loaded[0].language==='ru'
 refreshTick.value++
}
async function login(){await run(async()=>{
 const telegram=await telegramWebApp()
 if(!telegram?.initData) throw new Error(t.value.open)
 telegram.ready()
 await client.login(telegram.initData)
 await load()
 reAuth.value=false
})}
async function loginDebug(){await run(async()=>{await client.loginDebug(debugUser.value);await load();reAuth.value=false})}
async function logout(){await run(async()=>{try{await client.logout()}finally{me.value=null;relations.value=[];participants.value=[];sessions.value=[]}})}

async function propose(){await run(async()=>{
 if(!me.value) return
 await client.post('/relations',{dominant_user_id:direction.value==='dominant'?me.value.id:target.value,submissive_user_id:direction.value==='dominant'?target.value:me.value.id,scopes:scopes.value,agreement_text:agreement.value})
 agreement.value='';await load()
})}
async function transition(relation:Relation,action:string){await run(async()=>{
 await client.post(`/relations/${relation.id}/${action}`,{expected_version:relation.version,...(action==='accept'?{relation_version_id:relation.relation_version_id}:{})});await load()
})}
async function revokeSession(id:string){await run(async()=>{await client.delete('/sessions/'+id);await load()})}
function name(id:string){return participants.value.find(p=>p.id===id)?.display_name??id}

const ritualTarget=ref<{id:string;nonce:number}|null>(null)
function openOccurrence(o:components['schemas']['OccurrenceView']){ritualTarget.value={id:o.id,nonce:Date.now()};void navigate('rituals')}
const section=ref<Section>('home'),contextId=ref(''),refreshTick=ref(0),now=ref(new Date())
const contextual=computed(()=>!['journal','notifications','profile','sessions'].includes(section.value))
const more=ref<HTMLDialogElement|null>(null)
const labels:Record<Section,[string,string]>={home:['Home','Главная'],rituals:['Rituals','Ритуалы'],rules:['Rules','Правила'],journal:['Diary','Дневник'],rewards:['Rewards','Награды'],forms:['Forms & surveys','Анкеты и опросы'],discipline:['Discipline','Дисциплина'],relations:['Relationships','Отношения'],notifications:['Notifications','Уведомления'],profile:['Profile','Профиль'],sessions:['Sessions','Сессии']}
const icons={home:IconHome,rituals:IconSun,rules:IconShieldCheck,journal:IconNotebook,rewards:IconGift,forms:IconFileText,discipline:IconScale,relations:IconUsers,notifications:IconBell,profile:IconSettings,sessions:IconDevices}
const sections=(Object.keys(labels) as Section[])
const primary:Section[]=['home','rituals','rules','journal']
const label=(id:Section)=>labels[id][ru.value?1:0]
const selected=computed(()=>relations.value.find(r=>r.id===contextId.value)??null)
const contextName=computed(()=>selected.value?name(partnerId(selected.value,me.value?.id??'')??''):(ru.value?'Все отношения':'All relationships'))
const contextChoices=computed(()=>[{value:'',title:ru.value?'Общий день':'Shared day',detail:ru.value?'Все отношения':'All relationships',label:ru.value?'Общий день · все отношения':'Shared day · all relationships'},...relations.value.map(r=>{const role=relationRole(r,me.value?.id??'')==='dominant'?'Dominant':'Submissive';const title=name(partnerId(r,me.value?.id??'')??'');return {value:r.id,title,detail:role+' · '+statusLabel(r.status,ru.value),label:title+' · '+role+' · '+statusLabel(r.status,ru.value),status:r.status}})])
const contextRole=computed(()=>selected.value?relationRole(selected.value,me.value?.id??''):null)
const revision=computed(()=>[refreshTick.value,contextId.value,me.value?.id,me.value?.paused,...relations.value.map(r=>[r.id,r.version,r.status,...r.consent_user_ids].join(':'))].join('|'))
provide(workspaceKey,{selected,member:computed(()=>me.value),relations:computed(()=>relations.value),revision,navigate})
watch(relations,rows=>{if(contextId.value&&!rows.some(r=>r.id===contextId.value))contextId.value=''})
watch(me,value=>{if(!value){contextId.value='';section.value='home';more.value?.close()}})
function refreshOnReturn(){if(me.value&&!busy.value&&!document.hidden)void run(load)}
function syncHash(){const id=location.hash.slice(1);section.value=id==='surveys'?'forms':sections.includes(id as Section)?id as Section:'home'}
async function navigate(id:Section){section.value=id;more.value?.close();if(location.hash!=='#'+id)location.hash=id;await nextTick();document.getElementById('workspace-title')?.focus({preventScroll:true});window.scrollTo({top:0,behavior:'auto'})}
const dateLabel=computed(()=>new Intl.DateTimeFormat(ru.value?'ru-RU':'en-GB',{timeZone:me.value?.timezone??'UTC',day:'numeric',month:'long',weekday:'long'}).format(now.value))
const clockLabel=computed(()=>new Intl.DateTimeFormat(ru.value?'ru-RU':'en-GB',{timeZone:me.value?.timezone??'UTC',hour:'2-digit',minute:'2-digit'}).format(now.value))
const greeting=computed(()=>{const hour=Number(new Intl.DateTimeFormat('en-GB',{timeZone:me.value?.timezone??'UTC',hour:'numeric',hourCycle:'h23'}).format(now.value));return ru.value?(hour<6?'Доброй ночи':hour<12?'Доброе утро':hour<18?'Добрый день':'Добрый вечер'):(hour<6?'Good evening':hour<12?'Good morning':hour<18?'Good afternoon':'Good evening')})
let clockTimer:ReturnType<typeof setInterval>|undefined
onMounted(()=>{window.addEventListener('focus',refreshOnReturn);document.addEventListener('visibilitychange',refreshOnReturn);syncHash();window.addEventListener('hashchange',syncHash);clockTimer=setInterval(()=>now.value=new Date(),60000)})
onUnmounted(()=>{window.removeEventListener('focus',refreshOnReturn);document.removeEventListener('visibilitychange',refreshOnReturn);window.removeEventListener('hashchange',syncHash);if(clockTimer)clearInterval(clockTimer)})
</script>
<template>
 <div v-if="booting" class="startup-screen" role="status" :aria-label="ru?'Загрузка Vowen':'Loading Vowen'"><img src="/brand/vowen-velvet.webp" alt=""><div><span class="brand-wordmark">Vowen</span><p>{{ru?'Открываем ваше пространство…':'Opening your workspace…'}}</p></div></div>
 <main v-if="!booting&&!me" class="entry-workspace" :aria-busy="booting">
  <div class="entry-intro"><h1>{{ru?'Ближе через заботу.':'Closer through care.'}}</h1><p>{{ru?'Маленькие ритуалы. Взаимные договорённости. Пространство быть собой.':'Small rituals. Mutual agreements. Room to be yourself.'}}</p><section class="entry-card" :class="{'debug-entry-card':debugAuth}"><p v-if="reAuth" role="alert">{{ru?'Сессия завершена. Откройте приложение заново через бота.':'Session ended. Reopen the app through your bot.'}}</p><p v-if="error" role="alert">{{error===t.open?t.open:ru?'Не удалось войти. Проверьте соединение и откройте приложение через бота.':'Sign-in failed. Check your connection and open the app through your bot.'}}</p><button v-if="!debugAuth" class="entry-login" :disabled="busy" @click="login"><IconLock :size="18" />{{t.login}}</button><form v-if="debugAuth" class="debug-auth" @submit.prevent="loginDebug"><div class="debug-auth-heading"><span>DEBUG</span><span>{{ru?'Локальная разработка':'Local development'}}</span></div><label>{{ru?'Тестовый участник':'Development member'}}<span class="debug-select"><select v-model="debugUser" required :disabled="busy"><option value="" disabled>{{ru?'Выберите участника':'Choose a member'}}</option><option v-for="user in debugUsers" :key="user.id" :value="user.id">{{user.display_name}}</option></select><IconChevronDown :size="16" :stroke-width="1.5" aria-hidden="true" /></span></label><p v-if="!debugUsers.length">{{ru?'Создайте тестового участника через CLI в локальной БД.':'Create a development member using the CLI in the local database.'}}</p><button :disabled="busy||!debugUser" type="submit">{{ru?'Войти':'Sign in'}}</button></form></section></div><img class="entry-art" src="/brand/vowen-velvet.webp" alt="">
 </main>
 <main v-else-if="me&&!booting" class="member-workspace" :class="{'home-workspace':section==='home','rituals-workspace':section==='rituals'}">
  <a class="skip-link" href="#workspace-title">{{ru?'К содержимому':'Skip to content'}}</a>
  <aside class="workspace-nav" :aria-label="ru?'Основная навигация':'Main navigation'"><a class="nav-brand" :aria-label="instanceName" href="#home" @click.prevent="navigate('home')"><img src="/brand/vowen-crest.webp" alt=""><span>{{instanceName}}</span></a><p class="brand-caption">RITUALS MAKE US CLOSER</p><nav><a v-for="id in sections" :key="id" :href="'#'+id" :aria-label="label(id)" :aria-current="section===id?'page':undefined" @click.prevent="navigate(id)"><component :is="icons[id]" :size="20" :stroke-width="1.5" /><span>{{label(id)}}</span></a></nav><p class="nav-footer">{{ru?'Больше, чем правила.':'More than rules.'}}<br>{{ru?'Ближе, чем слова.':'Closer than words.'}}</p></aside>
  <div class="workspace-content"><p v-if="debugAuth" class="debug-session" role="status">DEBUG · {{ru?'Локальная разработка':'Local development'}}</p>
   <header class="workspace-header"><a class="app-brand mobile-brand" href="#home" @click.prevent="navigate('home')"><img src="/brand/vowen-crest.webp" alt=""><span>{{instanceName}}</span></a><div class="page-intro"><span v-if="section!=='home'" class="eyebrow">{{ru?'ВАШЕ ПРОСТРАНСТВО':'YOUR WORKSPACE'}}</span><h1 id="workspace-title" tabindex="-1">{{section==='home'?greeting+', '+me.display_name:label(section)}}</h1><p v-if="section==='home'">{{ru?'Близость начинается с внимания.':'Closeness begins with attention.'}}</p></div><div class="header-date"><time>{{dateLabel}}</time><strong>{{clockLabel}}</strong></div><button class="profile-shortcut" :aria-label="me.display_name+' · '+(ru?'Мой профиль':'My profile')" @click="navigate('profile')"><span class="person-monogram" aria-hidden="true">{{me.display_name.slice(0,1)}}</span><span><strong>{{me.display_name}}</strong><small>{{ru?'Моё пространство':'My workspace'}}</small></span></button></header>
   <div class="workspace-toolbar" :class="{'personal-toolbar':!contextual}"><RelationshipPicker v-if="contextual" v-model="contextId" :choices="contextChoices" :label="ru?'Контекст отношений':'Relationship context'" /><div class="toolbar-actions"><button class="icon-button" :disabled="busy" :aria-label="t.refresh" @click="run(load)"><IconRefresh :size="18" /></button><button class="icon-button" :aria-label="t.logout" :disabled="busy" @click="logout"><IconLogout :size="18" /></button></div></div>
   <p v-if="me.paused" class="context-banner pause-banner" role="status">{{ru?'Вы на личной паузе. Доступ к своему дневнику, истории и отзыву согласия сохраняется.':'You are on a personal pause. Your diary, history and consent withdrawal remain available.'}}</p>
   <div v-if="selected&&contextual&&!['home','rituals'].includes(section)" class="context-banner"><span><strong>{{contextName}}</strong> · {{contextRole==='dominant'?(ru?'Вы — Dominant в этих отношениях':'You are Dominant in this relationship'):(ru?'Вы — Submissive в этих отношениях':'You are Submissive in this relationship')}} · {{statusLabel(selected.status,ru)}}</span><button class="quiet-button" @click="navigate('relations')">{{ru?'Соглашение и права':'Agreement & permissions'}}</button></div>
   <p v-if="error" role="alert">{{ru?'Не удалось выполнить действие. Обновите данные и повторите.':'The action could not be completed. Refresh and try again.'}}</p>
   <WorkspaceHome v-show="section==='home'" :client="client" :me="me" :participants="participants" :relations="relations" :ru="ru" :active="section==='home'" @navigate="navigate" @open="openOccurrence" />
   <RitualsPanel :target="ritualTarget" :active="section==='rituals'" v-show="section==='rituals'" :client="client" :ru="ru" :me="me" :participants="participants" />
   <RewardsPanel :active="section==='rewards'" v-show="section==='rewards'" :client="client" :ru="ru" :me="me" :participants="participants" />
   <DisciplinePanel v-show="section==='discipline'" :client="client" :ru="ru" :me="me" :participants="participants" />
   <JournalPanel v-show="section==='journal'" :client="client" :ru="ru" :me="me" :participants="participants" />
   <RulesPanel v-show="section==='rules'" :client="client" :ru="ru" :me="me" :participants="participants" />
   <FormsPanel v-show="section==='forms'" :me="me" :client="client" :ru="ru" :participants="participants" />
   <NotificationSettings v-show="section==='notifications'" :key="me.timezone" :client="client" :ru="ru" />
   <div v-show="section==='profile'"><ProfileSettings :member="me" :client="client" :ru="ru" @saved="member=>{me=member;ru=member.language==='ru'}" /><p class="privacy-note">{{t.note}}</p></div>
   <section v-show="section==='relations'" id="relations"><div class="section-heading"><div><h2>{{t.relations}}</h2><p class="muted">{{ru?'Роль и полномочия действуют только в конкретных отношениях.':'Roles and permissions belong to a specific relationship.'}}</p></div></div><p v-if="!relations.length" class="empty-state">{{t.empty}}</p>
    <article v-for="relation in relations.filter(r=>!selected||r.id===selected.id)" :key="relation.id" class="agreement-card"><div class="occurrence-heading"><h3>{{name(relation.dominant_user_id)}} <span class="muted">&</span> {{name(relation.submissive_user_id)}}</h3><span class="status-tag" :data-status="relation.status">{{statusLabel(relation.status,ru)}}</span></div><p class="muted">{{ru?'Версия':'Version'}} {{relation.version}} · {{ru?'Подтверждения':'Consents'}} {{relation.consent_user_ids.length}}/2</p><p class="agreement-copy">{{relation.agreement_text}}</p><div class="scope-chips"><span v-for="scope in relation.scopes" :key="scope">{{scopeLabel(scope,ru)}}</span></div><div class="row-actions"><button v-if="relation.status==='proposed'&&!relation.consent_user_ids.includes(me.id)" :disabled="busy" @click="transition(relation,'accept')">{{t.accept}}</button><button v-if="['active','proposed'].includes(relation.status)" class="secondary" :disabled="busy" @click="transition(relation,'pause')">{{t.relationPause}}</button><button v-if="relation.status==='paused'" :disabled="busy" @click="transition(relation,'resume')">{{t.relationResume}}</button><button v-if="relation.status!=='revoked'" class="danger-button" :disabled="busy" @click="transition(relation,'revoke')">{{t.revoke}}</button></div></article>
    <details class="proposal-editor"><summary>{{ru?'Предложить отношения':'Propose a relationship'}}</summary><form @submit.prevent="propose"><label>{{t.target}}<select v-model="target" required><option value="" disabled>{{ru?'Выберите участника':'Select participant'}}</option><option v-for="p in participants.filter(p=>p.id!==me?.id)" :key="p.id" :value="p.id">{{p.display_name}}</option></select></label><label>{{t.direction}}<select v-model="direction"><option value="dominant">{{t.dominant}}</option><option value="submissive">{{t.submissive}}</option></select></label><fieldset><legend>{{t.scope}}</legend><label v-for="scope in scopeOptions" :key="scope"><input v-model="scopes" type="checkbox" :value="scope" :aria-label="scopeLabel(scope,ru)">{{scopeLabel(scope,ru)}}</label></fieldset><label>{{t.agreement}}<textarea v-model="agreement" required maxlength="10000" rows="5" /></label><p class="muted">{{ru?'Для активации оба участника отдельно подтверждают именно эту версию.':'Both participants separately accept this exact version before activation.'}}</p><button :disabled="busy||!scopes.length">{{t.propose}}</button></form></details>
   </section>
   <SessionList v-show="section==='sessions'" :sessions="sessions" :current-session-id="client.sessionId" :ru="ru" :busy="busy" @revoke="revokeSession" />
   <footer v-if="section!=='home'" class="workspace-footer">{{instanceName}} · {{ru?'Личное пространство':'A personal workspace'}}</footer>
  </div>
  <nav class="mobile-bottom-nav" :aria-label="ru?'Быстрая навигация':'Quick navigation'"><a v-for="id in primary" :key="id" :href="'#'+id" :aria-label="label(id)" :aria-current="section===id?'page':undefined" @click.prevent="navigate(id)"><component :is="icons[id]" :size="22" :stroke-width="1.5" /><span>{{label(id)}}</span></a><button :aria-expanded="more?.open??false" @click="more?.showModal()"><IconDots :size="22" /><span>{{ru?'Ещё':'More'}}</span></button></nav>
  <dialog ref="more" class="navigation-sheet" aria-labelledby="more-title"><div class="card-heading"><h2 id="more-title">{{ru?'Моё пространство':'My workspace'}}</h2><button class="icon-button" :aria-label="ru?'Закрыть меню':'Close menu'" @click="more?.close()"><IconX :size="22" /></button></div><nav><a v-for="id in sections.filter(id=>!primary.includes(id))" :key="id" :href="'#'+id" :aria-label="label(id)" :aria-current="section===id?'page':undefined" @click.prevent="navigate(id)"><component :is="icons[id]" :size="21" :stroke-width="1.5" />{{label(id)}}</a></nav></dialog>
 </main>
</template>
