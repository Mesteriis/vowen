<script setup lang="ts">
import {computed,nextTick} from 'vue'
import {IconLogout,IconRefresh} from '@tabler/icons-vue'
import type {ProfileSection} from './navigation'
const props=defineProps<{name:string;ru:boolean;busy:boolean}>()
const personal=defineModel<ProfileSection>({required:true})
defineEmits<{refresh:[];logout:[]}>()
const items=computed(()=>[{id:'profile' as const,label:props.ru?'Личные данные':'Personal details'},{id:'notifications' as const,label:props.ru?'Уведомления':'Notifications'},{id:'sessions' as const,label:props.ru?'Сессии':'Sessions'}])
async function moveTab(event:KeyboardEvent){if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();const ids=items.value.map(i=>i.id);const current=ids.indexOf(personal.value);personal.value=ids[event.key==='Home'?0:event.key==='End'?ids.length-1:(current+(event.key==='ArrowRight'?1:-1)+ids.length)%ids.length]!;await nextTick();document.getElementById('personal-tab-'+personal.value)?.focus()}
</script>
<template>
 <div class="personal-panel">
  <div class="account-tabs personal-tabs" role="tablist" :aria-label="ru?'Разделы профиля':'Profile sections'" @keydown="moveTab"><button v-for="item in items" :id="'personal-tab-'+item.id" :key="item.id" role="tab" :aria-selected="personal===item.id" :aria-controls="'personal-'+item.id" :tabindex="personal===item.id?0:-1" @click="personal=item.id">{{item.label}}</button></div>
  <div class="personal-body account-body">
   <div id="personal-profile" v-show="personal==='profile'" role="tabpanel" aria-labelledby="personal-tab-profile"><slot name="profile"/></div>
   <div id="personal-notifications" v-show="personal==='notifications'" role="tabpanel" aria-labelledby="personal-tab-notifications"><slot name="notifications"/></div>
   <div id="personal-sessions" v-show="personal==='sessions'" role="tabpanel" aria-labelledby="personal-tab-sessions"><slot name="sessions"/></div>
  </div>
  <div class="personal-utilities"><button class="icon-button" :disabled="busy" :aria-label="ru?'Обновить профиль и сессии':'Refresh profile and sessions'" @click="$emit('refresh')"><IconRefresh :size="18"/></button><button class="icon-button" :disabled="busy" :aria-label="ru?'Выйти':'Sign out'" @click="$emit('logout')"><IconLogout :size="18"/></button></div>
 </div>
</template>
