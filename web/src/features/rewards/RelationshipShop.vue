<script setup lang="ts">
import {computed,ref,watch} from 'vue'
import type {components} from '../../shared/api'
import type {SessionClient} from '../auth/session'
import {useWorkspaceView} from '../workspace/context'
type S=components['schemas']
const props=defineProps<{client:SessionClient;ru:boolean;rewards:S['RewardView'][];active:boolean;recipientName:string;paused:boolean}>()
const emit=defineEmits<{changed:[]}>()
const view=useWorkspaceView(),wallet=ref<S['WalletView']|null>(null),listings=ref<S['ListingView'][]>([]),busy=ref(false),error=ref('')
const amount=ref(10),comment=ref(''),creditKey=ref(crypto.randomUUID()),crediting=ref(false),adding=ref(false),reward=ref(''),price=ref(10)
const purchaseKeys=new Map<string,string>()
let generation=0
const t=(en:string,ru:string)=>props.ru?ru:en
const relation=computed(()=>view.selected.value)
const manager=computed(()=>relation.value?.dominant_user_id===view.memberId.value)
const allowed=computed(()=>!!relation.value&&!props.paused&&relation.value.status==='active'&&relation.value.scopes.includes('rewards.grant')&&relation.value.consent_user_ids.length===2)
const messages:Record<string,[string,string]>={INSUFFICIENT_BALANCE:['Not enough coins.','Недостаточно монет.'],LISTING_CHANGED:['The item changed. Review its current price.','Лот изменился. Проверьте актуальную цену.'],ACCESS_DENIED:['This action is no longer available.','Это действие больше недоступно.']}
function message(e:unknown){const code=e instanceof Error?e.message:'';return messages[code]?.[props.ru?1:0]??t('Could not complete the action. Try again.','Не удалось выполнить действие. Повторите попытку.')}
async function load(){
 const id=++generation,rid=relation.value?.id;wallet.value=null;listings.value=[];error.value=''
 if(!rid)return
 busy.value=true
 try{const [w,s]=await Promise.all([props.client.get<S['WalletView']>(`/relations/${rid}/wallet`),props.client.get<S['ListingView'][]>(`/relations/${rid}/shop`)]);if(id===generation){wallet.value=w;listings.value=s}}
 catch(e){if(id===generation)error.value=message(e)}finally{if(id===generation)busy.value=false}
}
watch(view.revision,()=>{crediting.value=false;adding.value=false;purchaseKeys.clear();void load()},{immediate:true})
watch(()=>props.active,active=>{if(active)void load()})
watch([amount,comment],()=>creditKey.value=crypto.randomUUID())
async function act(fn:()=>Promise<void>){busy.value=true;error.value='';try{await fn();await load();emit('changed')}catch(e){const text=message(e);await load();error.value=text}finally{busy.value=false}}
async function credit(){const rid=relation.value?.id;if(!rid)return;await act(async()=>{await props.client.post(`/relations/${rid}/wallet/credits`,{amount:amount.value,comment:comment.value,idempotency_key:creditKey.value});crediting.value=false;comment.value='';creditKey.value=crypto.randomUUID()})}
async function add(){const rid=relation.value?.id;if(!rid)return;await act(async()=>{await props.client.post(`/relations/${rid}/shop`,{reward_version_id:reward.value,price:price.value});adding.value=false})}
async function buy(s:S['ListingView']){if(!purchaseKeys.has(s.id))purchaseKeys.set(s.id,crypto.randomUUID());await act(async()=>{await props.client.post(`/shop/${s.id}/purchases`,{expected_version:s.revision,idempotency_key:purchaseKeys.get(s.id)});purchaseKeys.delete(s.id)})}
async function toggle(s:S['ListingView']){await act(async()=>{await props.client.patch(`/shop/${s.id}`,{expected_version:s.revision,price:s.price,active:!s.active})})}
const date=(value:string)=>new Intl.DateTimeFormat(props.ru?'ru-RU':'en-GB',{dateStyle:'medium',timeStyle:'short'}).format(new Date(value))
</script>
<template>
<div class="relationship-shop">
 <p v-if="!relation" class="muted">{{t('Choose a relationship above to open its shop and wallet.','Выберите отношения сверху, чтобы открыть их магазин и баланс.')}}</p>
 <template v-else>
  <div class="shop-balance"><div><span class="muted">{{manager?t('Coins for ','Монеты участника: ')+recipientName:t('Your balance','Ваш баланс')}}</span><strong>{{wallet?wallet.balance:'—'}} <small>{{t('coins','монет')}}</small></strong></div><button v-if="manager&&allowed" :disabled="busy" @click="crediting=!crediting">{{t('Grant coins','Начислить монеты')}}</button></div>
  <p v-if="error" role="alert">{{error}}</p>
  <p v-if="!allowed" class="muted">{{t('Purchases and credits are unavailable. Earned rewards and history remain.','Покупки и начисления недоступны. Заработанное и история сохраняются.')}}</p>
  <form v-if="crediting&&manager&&allowed" @submit.prevent="credit"><label>{{t('Coin amount','Количество монет')}}<input v-model.number="amount" type="number" min="1" max="1000000000" step="1" required></label><label>{{t('Credit comment','Комментарий к начислению')}}<textarea v-model="comment" maxlength="2000" required /></label><button :disabled="busy">{{t('Confirm credit','Подтвердить начисление')}}</button><button type="button" :disabled="busy" @click="crediting=false">{{t('Cancel','Отмена')}}</button></form>
  <div class="section-heading"><h3>{{t('Shop','Магазин')}}</h3><button v-if="manager&&allowed" :disabled="busy||!rewards.length" @click="adding=!adding">{{t('Add shop item','Добавить лот')}}</button></div>
  <form v-if="adding&&manager&&allowed" @submit.prevent="add"><label>{{t('Shop reward','Награда для магазина')}}<select v-model="reward" required><option value="" disabled>—</option><option v-for="r in rewards" :key="r.version_id" :value="r.version_id">{{r.title}}</option></select></label><label>{{t('Price in coins','Цена в монетах')}}<input v-model.number="price" type="number" min="1" max="1000000000" step="1" required></label><button :disabled="busy">{{t('Save shop item','Сохранить лот')}}</button><button type="button" @click="adding=false">{{t('Cancel','Отмена')}}</button></form>
  <p v-if="!listings.length&&!busy" class="muted">{{t('No shop items yet.','В магазине пока нет лотов.')}}</p>
  <article v-for="s in listings" :key="s.id" class="shop-item"><div><h4>{{s.title}}</h4><p>{{s.description}}</p><small class="muted">{{s.conditions}}</small></div><div><strong>{{s.price}} {{t('coins','монет')}}</strong><button v-if="!manager&&s.active" :disabled="busy||!allowed||!wallet||wallet.balance<s.price" @click="buy(s)">{{t('Buy','Купить')}}</button><button v-if="manager" :disabled="busy||!allowed" @click="toggle(s)">{{s.active?t('Hide item','Скрыть лот'):t('Restore item','Вернуть лот')}}</button></div></article>
  <details v-if="wallet?.entries.length" class="currency-history"><summary>{{t('Coin history','История монет')}}</summary><p class="muted">{{t('Latest 500 operations','Последние 500 операций')}}</p><article v-for="e in wallet.entries" :key="e.id"><div class="section-heading"><strong>{{e.amount>0?'+':''}}{{e.amount}}</strong><time class="muted">{{date(e.created_at)}}</time></div><p>{{e.kind==='ritual'?t('Ritual completed','Выполнен ритуал'):e.kind==='purchase'?t('Shop purchase','Покупка в магазине'):t('Manual credit','Ручное начисление')}}</p><p v-if="e.comment">{{e.comment}}</p></article></details>
 </template>
</div>
</template>
