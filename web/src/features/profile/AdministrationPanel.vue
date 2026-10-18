<script setup lang="ts">
import {ref,watch} from 'vue'
import {IconShieldCheck,IconUserPlus,IconArrowRight,IconRefresh,IconX} from '@tabler/icons-vue'
import type {components} from '../../shared/api'
import type {SessionClient} from '../auth/session'
type View=components['schemas']['AdministrationView']
type Person=components['schemas']['AdministratorMember']
const props=defineProps<{client:SessionClient;me:components['schemas']['MemberView'];ru:boolean;active:boolean}>()
const emit=defineEmits<{changed:[]}>()
const value=ref<View|null>(null),busy=ref(false),error=ref(''),saved=ref(false)
const dialog=ref<HTMLDialogElement|null>(null),pending=ref<{person:Person;action:'grant'|'transfer';revision:number}|null>(null)
const t=(en:string,ru:string)=>props.ru?ru:en
async function load(){value.value=await props.client.get<View>('/administration')}
async function run(action:()=>Promise<void>){if(busy.value)return;busy.value=true;error.value='';saved.value=false;try{await action()}catch(e){const code=e instanceof Error?e.message:'';error.value=code==='ACCESS_DENIED'?t('Administrator access required.','Нужны права администратора.'):code==='VERSION_CONFLICT'?t('The member list changed. Reload and retry.','Список участников изменился. Обновите его и повторите.'):t('Could not complete the action. Please retry.','Не удалось выполнить действие. Повторите попытку.');if(code==='ACCESS_DENIED'){value.value=null;emit('changed')}}finally{busy.value=false}}
watch([()=>props.active,()=>props.me.is_admin],([active,admin])=>{if(!admin){value.value=null;dialog.value?.close()}else if(active)void run(load)},{immediate:true})
function review(person:Person,action:'grant'|'transfer'){if(!value.value||busy.value)return;pending.value={person:{...person},action,revision:value.value.revision};dialog.value?.showModal()}
async function confirm(){const command=pending.value;if(!command||busy.value)return;await run(async()=>{await props.client.post(`/administration/administrators/${command.person.id}/${command.action}`,{expected_revision:command.revision});dialog.value?.close();if(command.action==='grant'){await load();saved.value=true}else value.value=null;emit('changed')})}
</script>
<template>
 <section class="administration-panel" :aria-label="t('Space settings','Настройки пространства')">
  <p v-if="!me.is_admin" class="muted">{{t('Settings are available to administrators only.','Настройки доступны только администраторам.')}}</p>
  <template v-else>
   <header class="administration-heading"><div><IconShieldCheck :size="23"/><h2>{{t('Administrators','Администраторы')}}</h2></div><button class="icon-button" :disabled="busy" :aria-label="t('Reload members','Обновить участников')" @click="run(load)"><IconRefresh :size="19"/></button></header>
   <p class="muted">{{t('Grant access to space settings or transfer your administrator role.','Назначайте доступ к настройкам пространства или передайте свои права администратора.')}}</p>
   <p v-if="error" role="alert">{{error}}</p><p v-if="saved" role="status">{{t('Administrator appointed.','Администратор назначен.')}}</p>
   <p v-if="busy&&!value" role="status">{{t('Loading…','Загрузка…')}}</p>
   <div v-if="value" class="administration-members"><article v-for="person in value.members" :key="person.id" class="administration-member"><span class="person-monogram" aria-hidden="true">{{person.display_name.slice(0,1)}}</span><div><strong>{{person.display_name}}</strong><small>{{person.is_admin?t('Administrator','Администратор'):t('Member','Участник')}}{{person.id===me.id?t(' · You',' · Вы'):''}}</small></div><div v-if="person.id!==me.id" class="administration-actions"><button v-if="!person.is_admin" :disabled="busy" :aria-label="t('Appoint administrator: ','Назначить администратором: ')+person.display_name" @click="review(person,'grant')"><IconUserPlus :size="18"/><span>{{t('Appoint','Назначить')}}</span></button><button :disabled="busy" :aria-label="t('Transfer your role to: ','Передать свои права: ')+person.display_name" @click="review(person,'transfer')"><IconArrowRight :size="18"/><span>{{t('Transfer','Передать')}}</span></button></div></article></div>
   <p class="administration-note">{{t('Administrator status does not grant access to private diaries or relationship permissions.','Роль администратора не открывает личные дневники и не даёт полномочий в отношениях.')}}</p>
  </template>
  <dialog ref="dialog" class="administration-confirm" aria-labelledby="administration-confirm-title" @close="pending=null"><header><h2 id="administration-confirm-title">{{pending?.action==='transfer'?t('Transfer administrator role?','Передать роль администратора?'):t('Appoint administrator?','Назначить администратора?')}}</h2><button class="icon-button" :disabled="busy" :aria-label="t('Close','Закрыть')" @click="dialog?.close()"><IconX :size="20"/></button></header><p><strong>{{pending?.person.display_name}}</strong></p><p>{{pending?.action==='transfer'?t('They will become an administrator. You will lose access to space settings.','Участник станет администратором. Вы потеряете доступ к настройкам пространства.'):t('They will gain access to space settings. Your administrator role will remain.','Участник получит доступ к настройкам пространства. Ваши права администратора сохранятся.')}}</p><p v-if="error" role="alert">{{error}}</p><footer><button :disabled="busy" @click="confirm">{{busy?t('Applying…','Выполнение…'):pending?.action==='transfer'?t('Transfer role','Передать права'):t('Appoint','Назначить')}}</button><button :disabled="busy" @click="dialog?.close()">{{t('Cancel','Отмена')}}</button></footer></dialog>
 </section>
</template>
