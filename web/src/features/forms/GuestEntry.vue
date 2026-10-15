<script setup lang="ts">
import {onMounted,onUnmounted,ref} from 'vue'
import FormRunner from './FormRunner.vue'
import type {components} from '../../shared/api'
import type {Access,Result,AnswerMap} from './types'
const replacing=ref(false)
const ru=ref(navigator.language.startsWith('ru')),data=ref<Access|null>(null),result=ref<Result|null>(null),busy=ref(false),error=ref(''),message=ref(''),receipt=ref(''),confirmDelete=ref(false),deleted=ref(false)
let csrf=''
const receiptMode=location.pathname.startsWith('/r/'),publicId=location.pathname.split('/')[2]??''
let token=new URLSearchParams(location.hash.slice(1)).get('token')??''
async function call<T>(path:string,method='GET',body?:unknown,retry=true):Promise<T>{
 const response=await fetch('/api/v1/guest'+path,{method,credentials:'same-origin',cache:'no-store',redirect:'error',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,'X-Guest-Context':publicId},body:body===undefined?undefined:JSON.stringify(body)})
 if(!response.ok){
  const error=await response.json().catch(()=>null) as {error?:{code?:string}}|null
  const code=error?.error?.code??'NETWORK_ERROR'
  // Another tab can refresh the synchronizer token. Retry only the same live
  // capability; replacement exchanges always require their explicit warning.
  if(retry&&method!=='GET'&&!path.endsWith('/exchange')&&response.status===403&&code==='INVALID_CSRF'){
   const context=await call<components['schemas']['GuestSessionView']>('/session','GET',undefined,false)
   if(context.public_id!==publicId||context.kind!==(receiptMode?'receipt':'invitation'))throw new Error('GUEST_CONTEXT_CHANGED')
   csrf=context.csrf_token
   return call<T>(path,method,body,false)
  }
  throw new Error(code)
 }
 return response.status===204?undefined as T:await response.json() as T
}
async function run(action:()=>Promise<void>){busy.value=true;error.value='';message.value='';try{await action()}catch(e){error.value=e instanceof Error?e.message:'NETWORK_ERROR'}finally{busy.value=false}}
async function restore(){const a=await call<Access>('/form');if(a.context_id!==publicId||a.context_kind!==(receiptMode?'receipt':'invitation'))throw new Error('INVITATION_MISMATCH');data.value=a;csrf=a.csrf_token??'';if(a.status==='submitted')result.value=await call<Result>('/submission')}
function readToken(){token=new URLSearchParams(location.hash.slice(1)).get('token')??'';if(token&&!data.value){error.value='';replacing.value=false;deleted.value=false}}
onMounted(()=>{window.addEventListener('hashchange',readToken);if(!token)void run(restore)})
onUnmounted(()=>window.removeEventListener('hashchange',readToken))
async function open(replace=false){await run(async()=>{
 try {
  const a=await call<Access>(receiptMode?'/receipts/exchange':'/invitations/exchange','POST',{public_id:publicId,token,replace_session:replace});
  data.value=a;csrf=a.csrf_token??'';token='';replacing.value=false;
  history.replaceState(null,'',location.pathname);if(a.status==='submitted')result.value=await call<Result>('/submission')
 } catch(e) {
  if(e instanceof Error&&e.message==='SESSION_REPLACEMENT_REQUIRED'){
   const context=await call<{csrf_token:string}>('/session');csrf=context.csrf_token;replacing.value=true;
  } else throw e
 }
})}
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
  <button v-else-if="!data" :disabled="busy" @click="open()">{{receiptMode?(ru?'Открыть квитанцию':'Open receipt'):(ru?'Открыть анкету':'Open form')}}</button>
  <template v-if="data&&!deleted"><h2>{{data.schema_body.title}}</h2><p>{{ru?'Читатели результатов:':'Results readers:'}} {{data.readers.map(r=>r.display_name).join(', ')||'—'}}</p><p>{{ru?'Хранение до:':'Retained until:'}} {{data.retention_until??(data.retention_days+' '+(ru?'дней после отправки':'days after submission'))}}</p><p>{{ru?'Можно удалить свой отправленный ответ. Копии в резервных копиях исчезают по политике хранения.':'You can delete your submitted response. Offline backup copies expire according to the retention policy.'}}</p>
   <FormRunner v-if="!result&&data.status==='draft'&&!receiptMode" :schema="data.schema_body" :initial="data.answers" :ru="ru" :busy="busy" guest @save="save" @submit="submit" />
   <template v-if="result"><h2>{{ru?'Ответ отправлен':'Response submitted'}}</h2><dl v-for="q in result.schema_body.questions.filter(q=>result!.answers[q.id]!==undefined)" :key="q.id"><dt>{{q.label}}</dt><dd>{{result.answers[q.id]}}</dd></dl><button v-if="!receiptMode" :disabled="busy" @click="issueReceipt">{{ru?'Создать квитанцию':'Create receipt'}}</button><label v-if="receipt">{{ru?'Ссылка квитанции':'Receipt link'}}<input :value="receipt" readonly></label><p v-if="receipt">{{ru?'Сохраните секретную ссылку. Новая квитанция отзывает старую.':'Keep this secret link. Issuing a new receipt revokes the previous one.'}}</p><button @click="confirmDelete=true">{{ru?'Удалить ответ':'Delete response'}}</button></template>
  </template>
  <div v-if="replacing" role="alertdialog" aria-label="Replace guest session"><p>{{ru?'Уже открыт другой гостевой сеанс. Продолжение закроет его: несданный черновик потребует нового приглашения. Сначала сохраните квитанцию отправленного ответа.':'Another guest session is active. Continuing closes it: an unsubmitted draft will require a new invitation. Save a receipt for any submitted response first.'}}</p><button :disabled="busy" @click="open(true)">{{ru?'Закрыть прежний сеанс и открыть ссылку':'Close previous session and open link'}}</button><button @click="replacing=false">{{ru?'Отмена':'Cancel'}}</button></div>
  <div v-if="confirmDelete" role="alertdialog" aria-label="Delete response"><p>{{ru?'Удалить тело ответа и закрыть доступ читателей?':'Delete the response body and close reader access?'}}</p><button :disabled="busy" @click="remove">{{ru?'Подтвердить удаление':'Confirm deletion'}}</button><button @click="confirmDelete=false">{{ru?'Отмена':'Cancel'}}</button></div>
 </main>
</template>
