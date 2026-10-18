<script setup lang="ts">
import {computed,ref} from 'vue'
import {IconX} from '@tabler/icons-vue'
import type {components} from '../../shared/api'
type Session=components['schemas']['SessionView']
const props=defineProps<{sessions:Session[];currentSessionId:string|null;ru:boolean;busy:boolean}>()
const emit=defineEmits<{revoke:[id:string]}>()
const confirmation=ref<HTMLDialogElement|null>(null),pending=ref<Session|null>(null)
function requestRevoke(session:Session){pending.value=session;confirmation.value?.showModal()}
function confirmRevoke(){if(!pending.value||props.busy)return;const id=pending.value.id;confirmation.value?.close();pending.value=null;emit('revoke',id)}
const active=computed(()=>props.sessions.filter(s=>!s.revoked&&Date.parse(s.expires_at)>Date.now()).sort((a,b)=>b.created_at.localeCompare(a.created_at)))
const history=computed(()=>props.sessions.filter(s=>!active.value.some(a=>a.id===s.id)).sort((a,b)=>b.created_at.localeCompare(a.created_at)))
function when(value:string){return new Intl.DateTimeFormat(props.ru?'ru-RU':'en-GB',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}).format(new Date(value))}
</script>
<template>
<section id="sessions" class="session-list">
 <p class="muted">{{ru?'Управляйте доступом со своих устройств.':'Manage access from your devices.'}}</p>
 <p v-if="!active.length" class="muted">{{ru?'Нет активных сессий.':'No active sessions.'}}</p>
 <article v-for="session in active" :key="session.id" class="session-row" :data-current="session.id===currentSessionId"><div><h3>{{session.device_label}}</h3><p><span>{{session.id===currentSessionId?(ru?'Это устройство':'This device'):(ru?'Активна':'Active')}}</span><span aria-hidden="true"> · </span><time :datetime="session.created_at">{{when(session.created_at)}}</time></p></div><button class="compact-action" :disabled="busy" :aria-label="(ru?'Отозвать сессию ':'Revoke session ')+session.device_label" @click="requestRevoke(session)">{{ru?'Отозвать':'Revoke'}}</button></article>
 <details v-if="history.length" class="session-history"><summary>{{ru?'История доступа':'Access history'}} · {{history.length}}</summary><article v-for="session in history" :key="session.id" class="session-row"><div><h3>{{session.device_label}}</h3><p>{{session.revoked?(ru?'Отозвана':'Revoked'):(ru?'Истекла':'Expired')}} · <time :datetime="session.created_at">{{when(session.created_at)}}</time></p></div></article></details>
<dialog ref="confirmation" class="account-session-confirm" aria-labelledby="session-confirm-title" @close="pending=null"><header><h2 id="session-confirm-title">{{ru?'Отозвать сессию?':'Revoke session?'}}</h2><button class="icon-button" :aria-label="ru?'Закрыть':'Close'" @click="confirmation?.close()"><IconX :size="20"/></button></header><p>{{pending?.device_label}}</p><p>{{pending?.id===currentSessionId?(ru?'Вы выйдете из приложения на этом устройстве.':'You will be signed out on this device.'):(ru?'На этом устройстве потребуется войти заново.':'This device will need to sign in again.')}}</p><footer><button :disabled="busy" @click="confirmRevoke">{{ru?'Отозвать сессию':'Revoke session'}}</button><button @click="confirmation?.close()">{{ru?'Отмена':'Cancel'}}</button></footer></dialog>
</section>
</template>
