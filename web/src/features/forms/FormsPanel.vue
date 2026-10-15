<script setup lang="ts">
import {onMounted,ref,watch} from 'vue'
import SurveysPanel from '../surveys/SurveysPanel.vue'
import FormEditor from './FormEditor.vue'
import FormRunner from './FormRunner.vue'
import type {SessionClient} from '../auth/session'
import type {components} from '../../shared/api'
import type {Form,Schema,Access,Result,Invitation,AnswerMap} from './types'
const props=defineProps<{client:SessionClient;me:components['schemas']['MemberView'];ru:boolean;participants:components['schemas']['ParticipantView'][]}>()
const forms=ref<Form[]>([]),assigned=ref<Access[]>([]),results=ref<Result[]>([])
const editing=ref<Form|null>(null),editor=ref(false),inviting=ref<Form|null>(null),opened=ref<Access|null>(null)
const recipient=ref(''),readers=ref<string[]>([]),link=ref(''),busy=ref(false),error=ref(''),message=ref(''),deliver=ref(false),contact=ref(''),ttl=ref(7),retention=ref(90),invitations=ref<Invitation[]>([])
async function run(action:()=>Promise<void>){busy.value=true;error.value='';message.value='';try{await action()}catch(e){error.value=e instanceof Error?e.message:'NETWORK_ERROR'}finally{busy.value=false}}
async function load(){forms.value=await props.client.get<Form[]>('/forms');assigned.value=await props.client.get<Access[]>('/form-invitations');results.value=await props.client.get<Result[]>('/form-submissions')}
onMounted(()=>run(load))
watch([recipient,readers,ttl,retention,deliver,contact],()=>{link.value=''})
async function save(schema:Schema){await run(async()=>{
 if(editing.value){const f=editing.value;await props.client[f.status==='draft'?'patch':'post']('/forms/'+f.id+(f.status==='draft'?'':'/versions'),{expected_version:f.revision,schema_body:schema})}
 else await props.client.post('/forms',schema)
 editor.value=false;editing.value=null;await load()
})}
function edit(f:Form|null){editing.value=f;editor.value=true}
async function publish(f:Form){await run(async()=>{await props.client.post('/forms/'+f.id+'/publish',{expected_version:f.revision});await load()})}
async function invite(f:Form){inviting.value=f;recipient.value='';readers.value=[];link.value='';await run(async()=>{invitations.value=await props.client.get<Invitation[]>('/forms/'+f.id+'/invitations')})}
async function createInvitation(){await run(async()=>{if(!inviting.value)return;link.value='';const i=await props.client.post<Invitation>('/forms/'+inviting.value.id+'/invitations',{recipient_user_id:recipient.value||null,reader_ids:readers.value,ttl_days:ttl.value,retention_days:retention.value,deliver:deliver.value,contact_telegram_id:contact.value?Number(contact.value):null});link.value=i.link??'';message.value=i.delivery_status;invitations.value.push(i);await load()})}
async function draft(a:AnswerMap){await run(async()=>{if(!opened.value)return;await props.client.put('/form-invitations/'+opened.value.id+'/draft',{answers:a});message.value=props.ru?'Черновик сохранён':'Draft saved'})}
async function submit(a:AnswerMap,key:string){await run(async()=>{if(!opened.value)return;await props.client.post('/form-invitations/'+opened.value.id+'/submit',{answers:a,idempotency_key:key,acknowledged:true});opened.value=null;await load()})}
async function copyLink(){await run(async()=>{await navigator.clipboard.writeText(link.value);message.value=props.ru?'Скопировано':'Copied'})}
const deleting=ref<Result|null>(null)
async function remove(){await run(async()=>{if(!deleting.value)return;await props.client.delete('/form-submissions/'+deleting.value.id);deleting.value=null;await load()})}
</script>
<template>
 <section id="forms"><h2>{{ru?'Анкеты':'Forms'}}</h2><p v-if="error" role="alert">{{error}}</p><p role="status">{{message}}</p>
  <button :disabled="busy" @click="run(load)">{{ru?'Обновить анкеты':'Refresh forms'}}</button><button @click="edit(null)">{{ru?'Новая анкета':'New form'}}</button>
  <FormEditor v-if="editor" :key="editing?.version_id??'new'" :initial="editing?.schema_body" :ru="ru" :busy="busy" @save="save" @cancel="editor=false" />
  <article v-for="f in forms" :key="f.id"><h3>{{f.schema_body.title}}</h3><p>{{f.status}} · v{{f.revision}}</p><button @click="edit(f)">{{f.status==='draft'?(ru?'Редактировать':'Edit'):(ru?'Новая версия':'New version')}}</button><button v-if="f.status==='draft'" :disabled="busy" @click="publish(f)">{{ru?'Опубликовать':'Publish'}}</button><button v-if="f.status==='published'" @click="invite(f)">{{ru?'Пригласить':'Invite'}}</button><button v-if="f.status!=='archived'" @click="run(async()=>{await client.post('/forms/'+f.id+'/archive',{expected_version:f.revision});await load()})">{{ru?'Архивировать':'Archive'}}</button></article>
  <section v-if="inviting"><h3>{{ru?'Приглашение':'Invitation'}}: {{inviting.schema_body.title}}</h3>
   <label>{{ru?'Адресат':'Recipient'}}<select v-model="recipient"><option value="">{{ru?'Внешний гость':'External guest'}}</option><option v-for="p in participants" :key="p.id" :value="p.id">{{p.display_name}}</option></select></label>
   <fieldset><legend>{{ru?'Читатели результатов':'Results readers'}}</legend><label v-for="p in participants" :key="p.id"><input v-model="readers" :value="p.id" type="checkbox" :aria-label="'Reader: '+p.display_name">{{p.display_name}}</label></fieldset>
   <label>{{ru?'Срок приглашения, дней':'Invitation days'}}<input v-model.number="ttl" type="number" min="1" max="7"></label><label>{{ru?'Хранение ответа, дней':'Retention days'}}<input v-model.number="retention" type="number" min="1" max="365"></label>
   <label><input v-model="deliver" type="checkbox">{{ru?'Попробовать доставку через бота':'Try bot delivery'}}</label><label v-if="deliver&&!recipient">Telegram contact ID<input v-model="contact" inputmode="numeric"></label>
   <button :disabled="busy" @click="createInvitation">{{ru?'Создать приглашение':'Create invitation'}}</button>
   <template v-if="link"><label>{{ru?'Ссылка приглашения':'Invitation link'}}<input :value="link" readonly></label><button @click="copyLink">{{ru?'Копировать секретную ссылку':'Copy secret link'}}</button></template>
   <p>{{ru?'Ссылка секретная; первый обладатель может открыть её. Это не подтверждение личности.':'The link is secret; its first holder can activate it. It does not verify identity.'}}</p>
   <article v-for="i in invitations" :key="i.id"><p>{{i.id}} · {{i.delivery_status}} · {{i.revoked?'revoked':i.expires_at}}</p><button :disabled="busy||i.revoked" @click="run(async()=>{await client.delete('/forms/invitations/'+i.id);i.revoked=true})">{{ru?'Отозвать приглашение':'Revoke invitation'}}</button><label>{{ru?'Удалить читателя':'Remove reader'}}<select @change="run(async()=>{const uid=($event.target as HTMLSelectElement).value;if(uid)await client.delete('/forms/invitations/'+i.id+'/readers/'+uid)})"><option value="">—</option><option v-for="p in participants" :key="p.id" :value="p.id">{{p.display_name}}</option></select></label></article>
  </section>
  <SurveysPanel :client="client" :me="me" :participants="participants" :ru="ru" @changed="run(load)" />
  <h3>{{ru?'Мне назначены':'Assigned to me'}}</h3><article v-for="a in assigned" :key="a.id"><p>{{a.schema_body.title}} · {{a.status}}</p><button v-if="a.status==='draft'" @click="opened=a">{{ru?'Заполнить':'Fill form'}}</button></article>
  <section v-if="opened"><h3>{{opened.schema_body.title}}</h3><p>{{ru?'Читатели результатов:':'Results readers:'}} {{opened.readers.map(r=>r.display_name).join(', ')||'—'}}</p><p>{{ru?'Хранение до':'Retained until'}} {{opened.retention_until??(opened.retention_days+' '+(ru?'дней после отправки':'days after submission'))}}</p><FormRunner :key="opened.id" :schema="opened.schema_body" :initial="opened.answers" :ru="ru" :busy="busy" @save="draft" @submit="submit" /></section>
  <h3>{{ru?'Доступные ответы':'Available responses'}}</h3><article v-for="r in results" :key="r.id"><h4>{{r.schema_body.title}}</h4><dl v-for="q in r.schema_body.questions.filter(q=>r.answers[q.id]!==undefined)" :key="q.id"><dt>{{q.label}}</dt><dd>{{r.answers[q.id]}}</dd></dl><button v-if="r.can_delete" @click="deleting=r">{{ru?'Удалить свой ответ':'Delete own response'}}</button></article>
  <div v-if="deleting" role="alertdialog" aria-label="Delete response"><p>{{ru?'Удалить тело ответа и отозвать доступ читателей?':'Delete the response body and revoke reader access?'}}</p><button :disabled="busy" @click="remove">{{ru?'Подтвердить удаление':'Confirm deletion'}}</button><button @click="deleting=null">{{ru?'Отмена':'Cancel'}}</button></div>
 </section>
</template>
