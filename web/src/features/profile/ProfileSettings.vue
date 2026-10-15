<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { components } from '../../shared/api'
import type { SessionClient } from '../auth/session'
type Member = components['schemas']['MemberView']
const props=defineProps<{member:Member;client:SessionClient;ru:boolean}>()
const emit=defineEmits<{saved:[Member]}>()
const displayName=ref(''),language=ref('en'),timezone=ref('UTC'),labels=ref<string[]>([])
const version=ref(1),busy=ref(false),error=ref('')
watch(()=>props.member,m=>{displayName.value=m.display_name;language.value=m.language;timezone.value=m.timezone;labels.value=[...m.profile_labels];version.value=m.profile_version},{immediate:true})
const t=computed(()=>props.ru?{title:'Профиль',name:'Отображаемое имя',language:'Язык',timezone:'Часовой пояс IANA',labels:'Самоописание',note:'Метки профиля не предоставляют полномочий.',save:'Сохранить профиль',conflict:'Профиль изменён. Обновите данные и повторите.'}:{title:'Profile',name:'Display name',language:'Language',timezone:'IANA timezone',labels:'Self-description',note:'Profile labels do not grant permissions.',save:'Save profile',conflict:'Profile changed. Refresh before retrying.'})
async function save(){busy.value=true;error.value='';try{
 const result=await props.client.patch<Member>('/me/preferences',{expected_version:version.value,display_name:displayName.value,language:language.value,timezone:timezone.value,profile_labels:labels.value})
 emit('saved',result)
}catch(e){error.value=e instanceof Error&&e.message==='CONFLICT'?t.value.conflict:e instanceof Error?e.message:'NETWORK_ERROR'}finally{busy.value=false}}
</script>
<template>
 <section id="profile"><h2>{{t.title}}</h2><p v-if="error" role="alert">{{error}}</p>
 <form @submit.prevent="save">
 <label>{{t.name}}<input v-model="displayName" required maxlength="100" :disabled="busy"></label>
 <label>{{t.language}}<select v-model="language" :disabled="busy"><option value="en">English</option><option value="ru">Русский</option></select></label>
 <label>{{t.timezone}}<input v-model="timezone" required maxlength="64" :disabled="busy"></label>
 <fieldset><legend>{{t.labels}}</legend><p>{{t.note}}</p><label v-for="label in ['dominant','submissive','switch']" :key="label"><input v-model="labels" type="checkbox" :value="label" :disabled="busy"> {{label}}</label></fieldset>
 <button :disabled="busy">{{t.save}}</button>
 </form></section>
</template>
