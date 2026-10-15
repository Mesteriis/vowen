<script setup lang="ts">
import {onMounted,ref} from 'vue'
import type {components} from '../../shared/api'
import type {SessionClient} from '../auth/session'
type Settings=components['schemas']['NotificationView']
const props=defineProps<{client:SessionClient;ru:boolean}>()
const value=ref<Settings|null>(null),busy=ref(false),error=ref(''),saved=ref(false)
const t=(en:string,ru:string)=>props.ru?ru:en
const clock=(minute:number)=>`${String(Math.floor(minute/60)).padStart(2,'0')}:${String(minute%60).padStart(2,'0')}`
function minute(event:Event){const [h,m]=(event.target as HTMLInputElement).value.split(':').map(Number);return (h??0)*60+(m??0)}
async function run(action:()=>Promise<void>){busy.value=true;error.value='';saved.value=false;try{await action()}catch(e){error.value=e instanceof Error?e.message:'NETWORK_ERROR'}finally{busy.value=false}}
async function load(){value.value=await props.client.get<Settings>('/me/notifications')}
onMounted(()=>run(load))
async function save(){await run(async()=>{if(!value.value)return;const v=value.value;value.value=await props.client.patch<Settings>('/me/notifications',{expected_version:v.revision,channels:v.channels,quiet_enabled:v.quiet_enabled,quiet_start:v.quiet_start,quiet_end:v.quiet_end});saved.value=true})}
</script>
<template>
<section id="notifications" :aria-busy="busy"><h2>{{t('Notifications','Уведомления')}}</h2>
<p v-if="busy" role="status">{{t('Loading notification settings…','Загружаем настройки уведомлений…')}}</p><p v-if="error" role="alert">{{error}}</p><p v-if="saved" role="status">{{t('Notification settings saved','Настройки уведомлений сохранены')}}</p>
<button :disabled="busy" @click="run(load)">{{t('Refresh notification settings','Обновить настройки уведомлений')}}</button>
<form v-if="value" @submit.prevent="save"><fieldset :disabled="busy"><legend>{{t('Delivery channels','Каналы уведомлений')}}</legend>
<label><input v-model="value.channels" type="checkbox" value="in_app">{{t('In-app notices','Уведомления в приложении')}}</label>
<label><input v-model="value.channels" type="checkbox" value="telegram">Telegram</label>
<p>{{value.telegram_connected?t('Bot connected','Бот подключён'):t('Bot not connected','Бот не подключён')}}. {{t('Enable delivery personally with /notifications_on in the bot. Channel selection does not grant consent.','Включите доставку лично командой /notifications_on в боте. Выбор канала не заменяет согласие.')}}</p>
<label><input v-model="value.quiet_enabled" type="checkbox">{{t('Quiet hours','Тихие часы')}}</label>
<div class="quiet-hours-fields"><label>{{t('Quiet from','Тишина с')}}<input type="time" :value="clock(value.quiet_start)" required @input="value.quiet_start=minute($event)"></label>
<label>{{t('Quiet until','Тишина до')}}<input type="time" :value="clock(value.quiet_end)" required @input="value.quiet_end=minute($event)"></label></div>
<p>{{t('Profile timezone','Часовой пояс профиля')}}: {{value.timezone}}. {{t('Telegram delivery waits; tasks remain available. Turning a channel back on does not resend cancelled messages.','Telegram ждёт окончания тишины; задания доступны. Повторное включение канала не возвращает отменённые сообщения.')}}</p>
<button :disabled="value.quiet_enabled&&value.quiet_start===value.quiet_end">{{t('Save notifications','Сохранить уведомления')}}</button></fieldset></form>
</section>
</template>
