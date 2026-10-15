<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import RulesPanel from './features/rules/RulesPanel.vue'
import FormsPanel from './features/forms/FormsPanel.vue'
import ProfileSettings from './features/profile/ProfileSettings.vue'
import { SessionClient } from './features/auth/session'
import type { components } from './shared/api'
type Participant = components['schemas']['ParticipantView']
type Me = components['schemas']['MemberView']
type Relation = components['schemas']['RelationView']
type Session = components['schemas']['SessionView']
const client = new SessionClient()
const instanceName=ref('Vowen')
onMounted(async()=>{try{instanceName.value=(await client.get<{display_name:string}>('/instance')).display_name}catch{error.value='NETWORK_ERROR'}})
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
 me.value=await client.get<Me>('/me')
 ru.value=me.value.language==='ru'
 relations.value=await client.get<Relation[]>('/relations')
 participants.value=await client.get<Participant[]>('/participants')
 sessions.value=await client.get<Session[]>('/sessions')
}
async function login(){await run(async()=>{
 const telegram=(window as Window & {Telegram?:{WebApp:{initData:string;ready:()=>void}}}).Telegram?.WebApp
 if(!telegram?.initData) throw new Error(t.value.open)
 telegram.ready()
 await client.login(telegram.initData)
 await load()
})}
async function logout(){await run(async()=>{try{await client.logout()}finally{me.value=null;relations.value=[];participants.value=[];sessions.value=[]}})}
async function personal(){await run(async()=>{await client.post(me.value?.paused?'/me/resume':'/me/pause');await load()})}
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
</script>
<template>
 <main>
  <header><span>{{instanceName}}</span><button @click="ru=!ru" :aria-label="ru?'English':'Русский'">{{ru?'EN':'RU'}}</button></header>
  <p class="muted">{{t.alpha}}</p><h1>{{t.title}}</h1>
  <p v-if="error" role="alert">{{t.error}}: {{error}}</p>
  <section v-if="!me"><p>{{t.closed}}</p><button :disabled="busy" @click="login">{{t.login}}</button></section>
  <template v-else>
   <section><h2>{{me.display_name}}</h2><button :disabled="busy" @click="run(load)">{{t.refresh}}</button><p v-if="me.paused">⏸ {{t.pause}}</p><button :disabled="busy" @click="personal">{{me.paused?t.resume:t.pause}}</button> <button :disabled="busy" @click="logout">{{t.logout}}</button></section>
   <RulesPanel :client="client" :ru="ru" :me="me" :participants="participants" />
   <FormsPanel :client="client" :ru="ru" :participants="participants" />
   <ProfileSettings :member="me" :client="client" :ru="ru" @saved="member => {me=member;ru=member.language==='ru'}" />
   <section><h2>{{t.relations}}</h2><p v-if="!relations.length">{{t.empty}}</p>
    <article v-for="relation in relations" :key="relation.id">
     <h3>{{name(relation.dominant_user_id)}} → {{name(relation.submissive_user_id)}}</h3>
     <p>{{relation.status}} · v{{relation.version}} · {{relation.consent_user_ids.length}}/2</p>
     <p>{{relation.agreement_text}}</p><p>{{relation.scopes.join(', ')}}</p>
     <button v-if="relation.status==='proposed' && !relation.consent_user_ids.includes(me.id)" :disabled="busy" @click="transition(relation,'accept')">{{t.accept}}</button>
     <button v-if="['active','proposed'].includes(relation.status)" :disabled="busy" @click="transition(relation,'pause')">{{t.relationPause}}</button>
     <button v-if="relation.status==='paused'" :disabled="busy" @click="transition(relation,'resume')">{{t.relationResume}}</button>
     <button v-if="relation.status!=='revoked'" :disabled="busy" @click="transition(relation,'revoke')">{{t.revoke}}</button>
    </article>
    <form @submit.prevent="propose">
     <label>{{t.target}}<select v-model="target" required><option value="" disabled>—</option><option v-for="p in participants.filter(p=>p.id!==me?.id)" :key="p.id" :value="p.id">{{p.display_name}}</option></select></label>
     <label>{{t.direction}}<select v-model="direction"><option value="dominant">{{t.dominant}}</option><option value="submissive">{{t.submissive}}</option></select></label>
     <fieldset><legend>{{t.scope}}</legend><label v-for="scope in scopeOptions" :key="scope"><input v-model="scopes" type="checkbox" :value="scope"> {{scope}}</label></fieldset>
     <label>{{t.agreement}}<textarea v-model="agreement" required maxlength="10000" rows="5" /></label><button :disabled="busy || !scopes.length">{{t.propose}}</button>
    </form>
   </section>
   <section><h2>{{t.sessions}}</h2><article v-for="session in sessions" :key="session.id"><p>{{session.device_label}} · {{session.revoked?'revoked':'active'}}</p><button v-if="!session.revoked" :disabled="busy" @click="revokeSession(session.id)">{{t.revoke}}</button></article></section>
  </template>
  <footer>{{t.note}}</footer>
 </main>
</template>
