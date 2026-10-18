<script setup lang="ts">
import {computed,ref,watch,nextTick,inject,onMounted,onUnmounted} from 'vue'
import type {components} from '../../shared/api'
import type {SessionClient} from '../auth/session'
import {IconPlus,IconCoins,IconX,IconEyeOff,IconEye,IconCheck,IconPencil,IconTrash,IconPlayerPause,IconPlayerPlay,IconSearch} from '@tabler/icons-vue'
import {searchProducts} from './search'
import {rewardCategories} from './categories'
import RewardShelf from './RewardShelf.vue'
import {useWorkspaceView,workspaceKey} from '../workspace/context'
type S=components['schemas'];type Item=S['ListingView']
const props=defineProps<{client:SessionClient;ru:boolean;me:S['MemberView'];rewards:S['RewardView'][];active:boolean;recipientName:string;paused:boolean;participants:S['ParticipantView'][]}>()
const emit=defineEmits<{changed:[];create:[source?:S['RewardView']];edit:[item:Item]}>()
const view=useWorkspaceView(),wallet=ref<S['WalletView']|null>(null),listings=ref<Item[]>([]),busy=ref(false),error=ref(''),success=ref('')
const query=ref('')
const filteredItems=computed(()=>searchProducts(listings.value,query.value))
const dialog=ref<HTMLDialogElement|null>(null),detail=ref<Item|null>(null),purchaseWallet=ref<S['WalletView']|null>(null),removing=ref(false),crediting=ref(false)
const amount=ref(10),comment=ref(''),creditKey=ref(crypto.randomUUID()),purchaseKeys=new Map<string,string>()
const workspace=inject(workspaceKey,null)
const t=(en:string,ru:string)=>props.ru?ru:en
function targetName(item:Item){const r=workspace?.relations.value.find(r=>r.id===item.toggle_relation_id);return props.participants.find(p=>p.id===r?.submissive_user_id)?.display_name||props.recipientName||t('your subordinate','подчинённого')}
const relation=computed(()=>view.selected.value)
const manager=computed(()=>props.me.shop_role==='dominant')
const upper=computed(()=>relation.value?.dominant_user_id===view.memberId.value&&['dominant','switch'].includes(props.me.shop_role??'viewer'))
const lower=computed(()=>relation.value?.submissive_user_id===view.memberId.value&&['bottom','switch'].includes(props.me.shop_role??'viewer'))
const allowed=computed(()=>!!relation.value&&!props.paused&&relation.value.status==='active'&&relation.value.scopes.includes('rewards.grant')&&relation.value.consent_user_ids.length===2)
const messages:Record<string,[string,string]>={VERSION_CONFLICT:['The item changed. Reopen it.','Товар изменился. Откройте его заново.'],INSUFFICIENT_BALANCE:['Not enough available coins.','Недостаточно свободных монет.'],LISTING_CHANGED:['The item changed. Review it again.','Товар изменился. Проверьте его заново.'],ACCESS_DENIED:['This action is unavailable.','Это действие недоступно.'],RELATION_REQUIRED:['Choose your dominant using the avatars above.','Выберите своего доминанта через аватары сверху.']}
function message(e:unknown){const code=e instanceof Error?e.message:'';return messages[code]?.[props.ru?1:0]??t('Could not complete the action.','Не удалось выполнить действие.')}
let generation=0
async function load(){const id=++generation,rid=relation.value?.id;if(wallet.value?.relation_id!==rid)wallet.value=null;busy.value=true;error.value='';try{const[w,s]=await Promise.all([rid?props.client.get<S['WalletView']>(`/relations/${rid}/wallet`):Promise.resolve(null),props.client.get<Item[]>('/shop/catalogue'+(rid?`?relation_id=${rid}`:''))]);if(id===generation){wallet.value=w;listings.value=s}}catch(e){if(id===generation)error.value=message(e)}finally{if(id===generation)busy.value=false}}
let closing=false
async function close(){if(busy.value||closing)return;closing=true;try{const el=dialog.value;if(el?.open&&!matchMedia('(prefers-reduced-motion: reduce)').matches)await el.animate([{opacity:1,transform:'translateY(0)'},{opacity:0,transform:'translateY(12px)'}],{duration:160,easing:'ease-in'}).finished.catch(()=>{});detail.value=null;crediting.value=false;removing.value=false}finally{closing=false}}
const dialogOpen=computed(()=>crediting.value||!!detail.value)
watch(dialogOpen,async open=>{await nextTick();if(open&&!dialog.value?.open)dialog.value?.showModal();else if(!open)dialog.value?.close()})
watch(view.revision,()=>{detail.value=null;crediting.value=false;removing.value=false;success.value='';purchaseKeys.clear();void load()},{immediate:true})
watch(()=>props.active,active=>{if(active)void load()})
watch([amount,comment],()=>creditKey.value=crypto.randomUUID())
async function act(fn:()=>Promise<void>){busy.value=true;error.value='';try{await fn();await load();emit('changed')}catch(e){error.value=message(e)}finally{busy.value=false}}
async function inspect(item:Item){detail.value=item;purchaseWallet.value=null;removing.value=false;error.value='';if(item.purchase_relation_id){try{const w=await props.client.get<S['WalletView']>(`/relations/${item.purchase_relation_id}/wallet`);if(detail.value?.id===item.id)purchaseWallet.value=w}catch(e){error.value=message(e)}}}
async function buy(item:Item){const key=`${item.id}:${item.purchase_relation_id}`;if(!purchaseKeys.has(key))purchaseKeys.set(key,crypto.randomUUID());await act(async()=>{await props.client.post(`/shop/${item.id}/purchases`,{relation_id:item.purchase_relation_id,expected_version:item.revision,idempotency_key:purchaseKeys.get(key)});purchaseKeys.delete(key);detail.value=null;success.value=t('Request sent. Coins are reserved until approval.','Запрос отправлен. Монеты в резерве до решения.')})}
async function globalToggle(item:Item){await act(async()=>{await props.client.post(`/shop/products/${item.product_id}/state`,{expected_version:item.product_revision,enabled:!item.global_enabled});detail.value=null})}
async function relationToggle(item:Item){await act(async()=>{await props.client.post(`/relations/${item.toggle_relation_id}/shop/products/${item.product_id}/state`,{expected_version:item.toggle_revision,enabled:!item.relation_enabled});detail.value=null})}
async function remove(item:Item){await act(async()=>{await props.client.post(`/shop/products/${item.product_id}/archive`,{expected_version:item.product_revision});detail.value=null;removing.value=false})}
async function credit(){const rid=relation.value?.id;if(!rid)return;await act(async()=>{await props.client.post(`/relations/${rid}/wallet/credits`,{amount:amount.value,comment:comment.value,idempotency_key:creditKey.value});crediting.value=false;comment.value='';creditKey.value=crypto.randomUUID()})}
function openAdd(version=''){emit('create',props.rewards.find(r=>r.version_id===version))}
defineExpose({load,openAdd})
const filmstrip=ref<HTMLElement|null>(null),autoScroll=ref(true),motionReduced=ref(false)
let frame=0,lastFrame=0,fraction=0,quietUntil=0,pointerInside=false,hasFocus=false
function restFilmstrip(){quietUntil=performance.now()+10000}
function enterFilmstrip(){pointerInside=true;restFilmstrip()}
function leaveFilmstrip(){pointerInside=false;restFilmstrip()}
function leaveFilmstripFocus(event:FocusEvent){hasFocus=filmstrip.value?.contains(event.relatedTarget as Node)??false;restFilmstrip()}
onMounted(()=>{
 const preference=matchMedia('(prefers-reduced-motion: reduce)')
 const updateMotion=()=>{motionReduced.value=preference.matches}
 updateMotion();preference.addEventListener('change',updateMotion)
 const advance=(now:number)=>{
  const delta=lastFrame?Math.min(now-lastFrame,48):0;lastFrame=now
  const el=filmstrip.value
  if(el&&props.active&&!query.value.trim()&&!dialogOpen.value&&autoScroll.value&&!motionReduced.value&&!document.hidden&&!pointerInside&&!hasFocus&&now>=quietUntil){
   const repeat=el.querySelector<HTMLElement>('[data-repeat-start]')
   const cycle=repeat?.offsetLeft??0
   if(cycle>el.clientWidth){fraction+=delta*.012;const pixels=Math.floor(fraction);fraction-=pixels;el.scrollLeft+=pixels;if(el.scrollLeft>=cycle)el.scrollLeft-=cycle}
  }
  frame=requestAnimationFrame(advance)
 }
 frame=requestAnimationFrame(advance)
 removeMotionListener=()=>preference.removeEventListener('change',updateMotion)
})
let removeMotionListener=()=>{}
onUnmounted(()=>{cancelAnimationFrame(frame);removeMotionListener()})
const date=(value:string)=>new Intl.DateTimeFormat(props.ru?'ru-RU':'en-GB',{dateStyle:'medium',timeStyle:'short'}).format(new Date(value))
</script>
<template>
<div class="relationship-shop quiet-market" :class="{'shop-as-buyer':lower}">
 <div class="market-wallet" :class="{'manager-wallet':manager||upper}">
  <div v-if="lower"><IconCoins :size="23"/><span><strong>{{wallet?wallet.balance:'—'}} {{t('coins','монет')}}</strong><small v-if="wallet?.reserved">{{t('Reserved: ','В резерве: ')}}{{wallet.reserved}}</small></span></div>
  <span v-else-if="upper" class="muted">{{t('Availability for ','Доступность для ')+recipientName}}</span>
  <div class="market-manage"><button v-if="manager" :disabled="busy||paused" @click="openAdd()"><IconPlus :size="18"/>{{t('New product','Новый товар')}}</button><button v-if="manager&&upper" :disabled="busy||!allowed" @click="crediting=true"><IconCoins :size="18"/>{{t('Grant coins','Начислить')}}</button><details v-if="wallet?.entries.length&&(manager||lower)" class="wallet-history-menu"><summary :aria-label="t('Coin history','История монет')"><IconCoins :size="18"/></summary><div class="wallet-history"><h4>{{t('Coin history','История монет')}}</h4><p v-for="e in wallet.entries" :key="e.id"><strong>{{e.amount>0?'+':''}}{{e.amount}}</strong> · {{date(e.created_at)}}<small v-if="e.comment">{{e.comment}}</small></p></div></details></div>
 </div>
 <p v-if="error&&!dialogOpen" role="alert">{{error}}</p><p v-if="success" role="status" class="market-success">{{success}}</p>
 <p v-if="busy&&!listings.length" class="muted">{{t('Loading shop…','Загружаем магазин…')}}</p>
 <div v-else-if="!listings.length" class="market-empty"><h3>{{t('No available products','Нет доступных товаров')}}</h3></div>
 <div v-if="listings.length" class="shop-search" role="search">
  <IconSearch :size="18" aria-hidden="true"/>
  <input v-model="query" type="search" :aria-label="t('Search products','Поиск товаров')" :placeholder="t('Search products','Поиск товаров')" maxlength="200" autocomplete="off">
  <button v-if="query" class="icon-button" :aria-label="t('Clear search','Очистить поиск')" @click="query=''"><IconX :size="18"/></button>
 </div>
 <p v-if="query.trim()" class="shop-search-result muted" role="status">{{filteredItems.length?t('Found: ','Найдено: ')+filteredItems.length:t('No matching products. Try another search.','Ничего не найдено. Попробуйте другой запрос.')}}</p>
 <div v-if="filteredItems.length&&!query.trim()" class="shop-filmstrip-wrap">
  <div ref="filmstrip" class="shop-filmstrip" :aria-label="t('Quick product preview','Быстрый просмотр товаров')" tabindex="0" @pointerenter="enterFilmstrip" @pointerleave="leaveFilmstrip" @pointerdown="restFilmstrip" @wheel.passive="restFilmstrip" @focusin="hasFocus=true;restFilmstrip()" @focusout="leaveFilmstripFocus">
   <template v-for="copy in 2" :key="copy"><button v-for="(item,index) in filteredItems" :key="item.id" :disabled="busy" :aria-label="t('Preview: ','Просмотр: ')+item.title" :aria-hidden="copy===2?true:undefined" :tabindex="copy===2?-1:0" :data-repeat-start="copy===2&&index===0?'':undefined" :class="{'is-disabled-cover':!item.active}" @click="inspect(item)"><img :src="'/shop/'+item.cover+'.png'" :alt="copy===1?item.title:''" loading="lazy" width="112" height="128"></button></template>
  </div>
  <button v-if="!motionReduced" class="shop-filmstrip-pause icon-button" :aria-label="autoScroll?t('Pause automatic scrolling','Остановить автопрокрутку'):t('Resume automatic scrolling','Продолжить автопрокрутку')" :aria-pressed="!autoScroll" @click="autoScroll=!autoScroll"><IconPlayerPause v-if="autoScroll" :size="16"/><IconPlayerPlay v-else :size="16"/></button>
 </div>
 <div class="shop-collections">
  <template v-for="c in rewardCategories" :key="c.id">
   <RewardShelf v-if="filteredItems.some(s=>(s.category??'together')===c.id)" :title="t(c.en,c.ru)" :items="filteredItems.filter(s=>(s.category??'together')===c.id)" :initial="4" :manager="manager" :ru="ru" :disabled="busy" @open="inspect"/>
  </template>
 </div>
 <dialog ref="dialog" class="market-dialog" :aria-label="crediting?t('Grant coins','Начислить монеты'):detail?.title" @cancel.prevent="close">
  <header><h3>{{crediting?t('Grant coins','Начислить монеты'):detail?.title}}</h3><button class="icon-button" :disabled="busy" :aria-label="t('Close','Закрыть')" @click="close"><IconX :size="20"/></button></header>
  <p v-if="error" role="alert">{{error}}</p>
  <form v-if="crediting&&manager&&upper&&allowed" @submit.prevent="credit"><p class="muted">{{recipientName}}</p><label>{{t('Coins','Монеты')}}<input v-model.number="amount" type="number" min="1" max="1000000000" required></label><label>{{t('Comment','Комментарий')}}<textarea v-model="comment" maxlength="2000" required rows="3"/></label><footer><button :disabled="busy||!Number.isInteger(amount)||amount<1||!comment.trim()"><IconCheck :size="18"/>{{t('Confirm credit','Подтвердить начисление')}}</button></footer></form>
  <template v-else-if="detail">
   <img class="market-detail-photo" :class="{'is-disabled-cover':!detail.active}" :src="'/shop/'+detail.cover+'.png'" alt=""><strong class="market-price"><IconCoins :size="18"/>{{detail.price}} {{t('coins','монет')}}</strong><p>{{detail.description}}</p><div v-if="detail.conditions" class="market-conditions"><h4>{{t('Conditions','Условия')}}</h4><p>{{detail.conditions}}</p></div>
   <template v-if="detail.can_manage"><p v-if="removing">{{t('Remove this product from the shop? Purchases and history are preserved.','Удалить товар из магазина? Покупки и история сохранятся.')}}</p><footer v-if="removing"><button :disabled="busy" @click="remove(detail)">{{t('Remove product','Удалить товар')}}</button><button :disabled="busy" @click="removing=false">{{t('Cancel','Отмена')}}</button></footer><footer v-else><button class="icon-button" :aria-label="t('Edit product','Редактировать товар')" :disabled="busy" @click="emit('edit',detail);close()"><IconPencil :size="18"/></button><button class="icon-button" :aria-label="detail.global_enabled?t('Disable product','Выключить товар'):t('Enable product','Включить товар')" :disabled="busy" @click="globalToggle(detail)"><IconEyeOff v-if="detail.global_enabled" :size="18"/><IconEye v-else :size="18"/></button><button class="icon-button" :aria-label="t('Remove product','Удалить товар')" :disabled="busy" @click="removing=true"><IconTrash :size="18"/></button></footer></template>
   <label v-if="detail.can_toggle" class="shop-relation-switch"><input type="checkbox" :checked="detail.relation_enabled" :disabled="busy" @change="relationToggle(detail)">{{t('Available for ','Доступен для ')+targetName(detail)}}</label>
   <template v-if="detail.purchase_relation_id"><small class="muted">{{t('Approval is required. Coins are reserved now and charged after approval.','Нужно разрешение. Монеты резервируются сейчас и списываются после одобрения.')}}</small><p v-if="purchaseWallet&&purchaseWallet.balance<detail.price" class="muted">{{t('Not enough available coins.','Недостаточно свободных монет.')}}</p><footer><button :disabled="busy||paused||!detail.active||!purchaseWallet||purchaseWallet.balance<detail.price" @click="buy(detail)"><IconCoins :size="18"/>{{t('Request for ','Запросить за ')+detail.price}}</button></footer></template>
   <p v-else-if="!detail.can_manage&&!detail.can_toggle" class="muted">{{['bottom','switch'].includes(me.shop_role??'viewer')?t('Choose your dominant in the avatars above to request a purchase.','Для покупки выберите доминанта через аватары сверху.'):t('Viewing only','Только просмотр')}}</p>
  </template>
 </dialog>
</div>
</template>
