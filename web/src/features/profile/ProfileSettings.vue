<script setup lang="ts">
import { computed, ref, watch, nextTick } from 'vue'
import type { components } from '../../shared/api'
import {preferencePatch} from './preferences'
import type { SessionClient } from '../auth/session'
type Member = components['schemas']['MemberView']
const props=defineProps<{member:Member;client:SessionClient;ru:boolean;mode?:'profile'|'general'|'all'}>()
const emit=defineEmits<{saved:[Member]}>()
const displayName=ref(''),language=ref('en'),timezone=ref('UTC'),labels=ref<string[]>([])
const busy=ref(false),error=ref(''),saved=ref(false)
watch(()=>props.member,m=>{displayName.value=m.display_name;language.value=m.language;timezone.value=m.timezone;labels.value=[...m.profile_labels]},{immediate:true})
const t=computed(()=>props.ru?{title:'Профиль',name:'Отображаемое имя',language:'Язык',timezone:'Часовой пояс IANA',labels:'Самоописание',note:'Метки профиля не предоставляют полномочий.',save:'Сохранить профиль',conflict:'Профиль изменён. Обновите данные и повторите.'}:{title:'Profile',name:'Display name',language:'Language',timezone:'IANA timezone',labels:'Self-description',note:'Profile labels do not grant permissions.',save:'Save profile',conflict:'Profile changed. Refresh before retrying.'})
async function save(){if(busy.value)return;busy.value=true;error.value='';saved.value=false;try{
 const result=await props.client.patch<Member>('/me/preferences',preferencePatch(props.member,props.mode??'all',{name:displayName.value,language:language.value,timezone:timezone.value,labels:labels.value}))
 emit('saved',result);await nextTick();saved.value=true
}catch(e){error.value=e instanceof Error&&['CONFLICT','VERSION_CONFLICT'].includes(e.message)?t.value.conflict:e instanceof Error?e.message:'NETWORK_ERROR'}finally{busy.value=false}}
watch([displayName,language,timezone,labels],()=>{saved.value=false},{deep:true,flush:'sync'})
</script>
<template>
 <section class="account-editor" :aria-labelledby="mode==='general'?'general-heading':'profile-heading'">
 <h2 :id="mode==='general'?'general-heading':'profile-heading'">{{mode==='general'?(ru?'Общие':'General'):(ru?'Личные данные':'Personal details')}}</h2>
 <p class="muted">{{mode==='general'?(ru?'Основные параметры вашего аккаунта.':'The basics of your account.'):(ru?'Как вас видят участники пространства.':'How you appear to other members.')}}</p>
 <p v-if="error" role="alert">{{error}}</p>
 <form @submit.prevent="save">
 <label v-if="mode!=='general'">{{t.name}}<input v-model="displayName" required maxlength="100" :disabled="busy" autocomplete="nickname"></label>

 <template v-if="mode!=='profile'">
 <label>{{t.language}}<select v-model="language" :disabled="busy"><option value="en">English</option><option value="ru">Русский</option></select></label>
 <label>{{t.timezone}}<input v-model="timezone" required maxlength="64" :disabled="busy" autocomplete="off"></label>
 </template>
 <template v-if="mode!=='general'">

 <fieldset><legend>{{t.labels}}</legend><p>{{t.note}}</p><label v-for="label in ['dominant','submissive','switch']" :key="label"><input v-model="labels" type="checkbox" :value="label" :disabled="busy"> {{label.charAt(0).toUpperCase()+label.slice(1)}}</label></fieldset>
 </template>
 <footer><button :disabled="busy">{{busy?(ru?'Сохранение…':'Saving…'):(ru?'Сохранить изменения':'Save changes')}}</button><span v-if="saved" role="status">{{ru?'Сохранено':'Saved'}}</span></footer>
 </form></section>
</template>
