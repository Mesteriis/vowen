<script setup lang="ts">
import {onMounted,ref} from 'vue'
import FormRunner from './FormRunner.vue'
import type {Access,Result,AnswerMap} from './types'
const ru=ref(navigator.language.startsWith('ru')),data=ref<Access|null>(null),result=ref<Result|null>(null),busy=ref(false),error=ref(''),message=ref(''),receipt=ref(''),confirmDelete=ref(false),deleted=ref(false)
let csrf=''
const receiptMode=location.pathname.startsWith('/r/'),publicId=location.pathname.split('/')[2]??''
let token=new URLSearchParams(location.hash.slice(1)).get('token')??''
async function call<T>(path:string,method='GET',body?:unknown):Promise<T>{const response=await fetch('/api/v1/guest'+path,{method,credentials:'same-origin',cache:'no-store',redirect:'error',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:body===undefined?undefined:JSON.stringify(body)});if(!response.ok){const e=await response.json().catch(()=>null) as {error?:{code:string}}|null;throw new Error(e?.error?.code??'NETWORK_ERROR')}return response.status===204?undefined as T:await response.json() as T}
async function run(action:()=>Promise<void>){busy.value=true;error.value='';message.value='';try{await action()}catch(e){error.value=e instanceof Error?e.message:'NETWORK_ERROR'}finally{busy.value=false}}
async function restore(){const a=await call<Access>('/form');if(!receiptMode&&a.id!==publicId)throw new Error('INVITATION_MISMATCH');data.value=a;csrf=a.csrf_token??'';if(a.status==='submitted')result.value=await call<Result>('/submission')}
onMounted(()=>{if(!token)void run(restore)})
async function open(){await run(async()=>{const a=await call<Access>(receiptMode?'/receipts/exchange':'/invitations/exchange','POST',{public_id:publicId,token});data.value=a;csrf=a.csrf_token??'';token='';history.replaceState(null,'',location.pathname);if(a.status==='submitted')result.value=await call<Result>('/submission')})}
async function save(answers:AnswerMap){await run(async()=>{await call('/draft','PUT',{answers});message.value=ru.value?'Черновик сохранён':'Draft saved'})}
async function submit(answers:AnswerMap,key:string){await run(async()=>{result.value=await call<Result>('/submit','POST',{answers,idempotency_key:key,acknowledged:true})})}
async function issueReceipt(){await run(async()=>{const r=await call<{public_id:string;token:string}>('/receipt','POST');receipt.value=location.origin+'/r/'+r.public_id+'#token='+r.token})}
async function remove(){await run(async()=>{await call('/submission','DELETE');deleted.value=true;result.value=null;data.value=null;confirmDelete.value=false;receipt.value=''})}
</script>
<template>
 <main><header><span>Vowen</span><button @click="ru=!ru">{{ru?'EN':'RU'}}</button></header><h1>{{ru?'Гостевая анкета':'Guest form'}}</h1>
  <p>{{ru?'Ссылка даёт доступ только к одной анкете. Аккаунт не создаётся; Telegram не нужен.':'This secret link grants access to one form. No account is created; Telegram is not required.'}}</p>
  <p>{{ru?'Ответ не анонимный. Оператор сервера имеет технический доступ. Проверка возраста — только ваше подтверждение.':'Responses are not anonymous. The server operator has technical access. Age is self-confirmed only.'}}</p>
  <p v-if="error" role="alert">{{error}}</p><p role="status">{{message}}</p>
  <p v-if="deleted">{{ru?'Ответ удалён':'Response deleted'}}</p>
  <button v-else-if="!data" :disabled="busy" @click="open">{{receiptMode?(ru?'Открыть квитанцию':'Open receipt'):(ru?'Открыть анкету':'Open form')}}</button>
  <template v-if="data&&!deleted"><h2>{{data.schema_body.title}}</h2><p>{{ru?'Читатели результатов:':'Results readers:'}} {{data.readers.map(r=>r.display_name).join(', ')||'—'}}</p><p>{{ru?'Хранение до:':'Retained until:'}} {{data.retention_until}}</p><p>{{ru?'Можно удалить свой отправленный ответ. Копии в резервных копиях исчезают по политике хранения.':'You can delete your submitted response. Offline backup copies expire according to the retention policy.'}}</p>
   <FormRunner v-if="!result&&data.status==='draft'&&!receiptMode" :schema="data.schema_body" :initial="data.answers" :ru="ru" :busy="busy" guest @save="save" @submit="submit" />
   <template v-if="result"><h2>{{ru?'Ответ отправлен':'Response submitted'}}</h2><dl v-for="q in result.schema_body.questions.filter(q=>result!.answers[q.id]!==undefined)" :key="q.id"><dt>{{q.label}}</dt><dd>{{result.answers[q.id]}}</dd></dl><button v-if="!receiptMode" :disabled="busy" @click="issueReceipt">{{ru?'Создать квитанцию':'Create receipt'}}</button><label v-if="receipt">{{ru?'Ссылка квитанции':'Receipt link'}}<input :value="receipt" readonly></label><p v-if="receipt">{{ru?'Сохраните секретную ссылку. Новая квитанция отзывает старую.':'Keep this secret link. Issuing a new receipt revokes the previous one.'}}</p><button @click="confirmDelete=true">{{ru?'Удалить ответ':'Delete response'}}</button></template>
  </template>
  <div v-if="confirmDelete" role="alertdialog" aria-label="Delete response"><p>{{ru?'Удалить тело ответа и закрыть доступ читателей?':'Delete the response body and close reader access?'}}</p><button :disabled="busy" @click="remove">{{ru?'Подтвердить удаление':'Confirm deletion'}}</button><button @click="confirmDelete=false">{{ru?'Отмена':'Cancel'}}</button></div>
 </main>
</template>
