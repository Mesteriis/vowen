<script setup lang="ts">
import {computed,ref,watch} from 'vue'
import {IconBrandTelegram,IconCheck,IconChevronRight,IconDeviceMobile,IconInfoCircle,IconMoon,IconRefresh} from '@tabler/icons-vue'
import type {components} from '../../shared/api'
import type {SessionClient} from '../auth/session'
type Settings=components['schemas']['NotificationView']
const props=defineProps<{client:SessionClient;ru:boolean;active?:boolean}>()
const value=ref<Settings|null>(null),busy=ref(false),error=ref(''),saved=ref(false),start=ref(''),end=ref('')
const t=(en:string,ru:string)=>props.ru?ru:en
const clock=(minute:number)=>`${String(Math.floor(minute/60)).padStart(2,'0')}:${String(minute%60).padStart(2,'0')}`
function minute(text:string){if(!/^\d{2}:\d{2}$/.test(text))return null;const[h,m]=text.split(':').map(Number);return h!==undefined&&m!==undefined&&h<24&&m<60?h*60+m:null}
const valid=computed(()=>!value.value?.quiet_enabled||(minute(start.value)!==null&&minute(end.value)!==null&&minute(start.value)!==minute(end.value)))
const message=computed(()=>error.value==='VERSION_CONFLICT'?t('Settings changed elsewhere. Reload them before saving again.','Настройки изменились в другом окне. Загрузите их заново перед сохранением.'):t('Could not update settings. Check your connection and retry.','Не удалось обновить настройки. Проверьте соединение и повторите.'))
async function run(action:()=>Promise<void>){if(busy.value)return;busy.value=true;error.value='';saved.value=false;try{await action()}catch(e){error.value=e instanceof Error?e.message:'NETWORK_ERROR'}finally{busy.value=false}}
function apply(v:Settings){value.value=v;start.value=clock(v.quiet_start);end.value=clock(v.quiet_end)}
async function load(){apply(await props.client.get<Settings>('/me/notifications'))}
watch(()=>props.active??true,active=>{if(active&&!value.value)void run(load)},{immediate:true})
async function save(){if(!valid.value)return;await run(async()=>{if(!value.value)return;const v=value.value;apply(await props.client.patch<Settings>('/me/notifications',{expected_version:v.revision,channels:v.channels,quiet_enabled:v.quiet_enabled,quiet_start:minute(start.value)??v.quiet_start,quiet_end:minute(end.value)??v.quiet_end}));saved.value=true})}
watch([start,end,()=>value.value?.channels.join(','),()=>value.value?.quiet_enabled],()=>{saved.value=false},{flush:'sync'})
</script>
<template>
<section id="notifications" class="notification-settings" :aria-busy="busy" :aria-label="t('Notification settings','Настройки уведомлений')">
 <div class="notification-tools"><button type="button" class="icon-button" :disabled="busy" :aria-label="t('Reload notification settings','Загрузить настройки уведомлений заново')" :title="t('Reload notification settings','Загрузить настройки уведомлений заново')" @click="run(load)"><IconRefresh :size="18"/></button></div>
 <p v-if="busy&&!value" class="notification-state" role="status">{{t('Loading settings…','Загружаем настройки…')}}</p>
 <form v-if="value" @submit.prevent="save"><div class="notification-columns">
  <div class="notification-channels"><header><h2>{{t('Where to deliver','Куда доставлять')}}</h2><p>{{t('Choose where to receive notifications.','Выберите, где получать уведомления.')}}</p></header>
   <div class="notification-channel"><IconDeviceMobile :size="25" :stroke-width="1.5"/><label class="notification-switch-row"><span><strong>{{t('In the app','В приложении')}}</strong><small>{{t('Notifications inside Vowen','Уведомления внутри Vowen')}}</small></span><input v-model="value.channels" type="checkbox" role="switch" value="in_app" :disabled="busy" :aria-label="t('In-app notifications','Уведомления в приложении')"></label></div>
   <div class="notification-channel"><IconBrandTelegram :size="25" :stroke-width="1.5"/><div class="notification-channel-body"><label class="notification-switch-row"><span><strong>Telegram</strong><small>{{t('Delivery to your private chat with the bot','Доставка в ваш личный чат с ботом')}}</small></span><input v-model="value.channels" type="checkbox" role="switch" value="telegram" :disabled="busy" aria-label="Telegram"></label><p class="notification-connection" :data-connected="value.telegram_connected">{{value.telegram_connected?t('Bot connected','Бот подключён'):t('Bot not connected','Бот не подключён')}}</p><details class="notification-help"><summary>{{t('How to connect','Как подключить')}}<IconChevronRight :size="15"/></summary><p>{{t('Send the command personally in the bot:','Отправьте команду лично в боте:')}} <code>/notifications_on</code>. {{t('The channel switch does not connect the bot.','Переключатель канала не подключает бота.')}}</p></details></div></div>
  </div>
  <div class="notification-quiet"><header><h2>{{t('When not to disturb','Когда не беспокоить')}}</h2><p>{{t('During quiet hours Telegram waits; tasks remain available.','Во время тишины Telegram ждёт, задания доступны.')}}</p></header><div class="notification-quiet-toggle"><IconMoon :size="25" :stroke-width="1.5"/><label class="notification-switch-row"><strong>{{t('Quiet hours','Тихие часы')}}</strong><input v-model="value.quiet_enabled" type="checkbox" role="switch" :disabled="busy" :aria-label="t('Quiet hours','Тихие часы')"></label></div>
   <div class="notification-times"><label>{{t('Quiet from','Тишина с')}}<input v-model="start" type="time" required :disabled="busy||!value.quiet_enabled" :aria-invalid="value.quiet_enabled&&!valid" :aria-describedby="value.quiet_enabled&&!valid?'notification-time-error':undefined"></label><label>{{t('Quiet until','Тишина до')}}<input v-model="end" type="time" required :disabled="busy||!value.quiet_enabled" :aria-invalid="value.quiet_enabled&&!valid" :aria-describedby="value.quiet_enabled&&!valid?'notification-time-error':undefined"></label></div><p v-if="value.quiet_enabled&&!valid" id="notification-time-error" class="notification-validation" role="alert">{{minute(start)===minute(end)&&minute(start)!==null?t('Start and end must differ.','Начало и конец должны отличаться.'):t('Enter both times.','Укажите оба времени.')}}</p><p class="notification-timezone">{{t('Profile timezone','Часовой пояс профиля')}}<strong>{{value.timezone}}</strong></p>
  </div></div>
  <footer class="notification-footer"><details class="notification-explanation"><summary><IconInfoCircle :size="18"/>{{t('Good to know','Важно знать')}}<IconChevronRight :size="15"/></summary><p>{{t('Channel selection does not replace your personal opt-in in the bot. Turning a channel back on does not resend cancelled messages.','Выбор канала не заменяет личное включение доставки в боте. Повторное включение канала не возвращает отменённые сообщения.')}}</p></details><div class="notification-save"><span v-if="saved" class="notification-saved" role="status"><IconCheck :size="16"/>{{t('Saved','Сохранено')}}</span><button :disabled="busy||!valid">{{busy?t('Please wait…','Подождите…'):t('Save changes','Сохранить изменения')}}</button></div></footer>
 </form><p v-if="error" class="notification-error" role="alert">{{message}}</p>
</section>
</template>
