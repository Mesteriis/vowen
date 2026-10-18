<script setup lang="ts">
import {ref,watch} from 'vue'
import {IconPlus} from '@tabler/icons-vue'
import type {SessionClient} from '../auth/session'
import type {PunishmentParameters} from './parameters'
const props=defineProps<{client:SessionClient;relationId:string;ru:boolean;busy:boolean;templateMode?:boolean}>()
const model=defineModel<PunishmentParameters>({required:true})
const devices=ref<string[]>([]),parts=ref<string[]>([]),newDevice=ref(''),newPart=ref(''),adding=ref(false),error=ref('')
const t=(en:string,ru:string)=>props.ru?ru:en
let generation=0
watch(()=>props.relationId,async rid=>{const id=++generation;devices.value=[];parts.value=[];error.value='';newDevice.value='';newPart.value='';if(!rid)return;try{const[d,p]=await Promise.all([props.client.get<string[]>(`/discipline-records/dictionaries/${rid}/device`),props.client.get<string[]>(`/discipline-records/dictionaries/${rid}/body_part`)]);if(id===generation){devices.value=d;parts.value=p}}catch{if(id===generation)error.value=t('Could not load dictionaries','Не удалось загрузить справочники')}},{immediate:true})
function changeType(){const type=model.value.punishment_type;model.value={punishment_type:type,device:null,body_part:null,strike_count:null,intensity:null,ban_days:null}}
async function add(kind:'device'|'body_part'){const name=(kind==='device'?newDevice.value:newPart.value).trim().replace(/\s+/g,' '),rid=props.relationId,id=generation;if(!name||!rid)return;adding.value=true;error.value='';try{const result=await props.client.post<string[]>(`/discipline-records/dictionaries/${rid}/${kind}`,{name});if(id!==generation)return;if(kind==='device'){devices.value=result;model.value.device=result.find(v=>v.toLowerCase()===name.toLowerCase())??result.at(-1);newDevice.value=''}else{parts.value=result;model.value.body_part=result.find(v=>v.toLowerCase()===name.toLowerCase())??result.at(-1);newPart.value=''}}catch{if(id===generation)error.value=t('Could not add the entry','Не удалось добавить запись')}finally{adding.value=false}}
</script>
<template>
 <label>{{t('Punishment type','Тип наказания')}}<select v-model="model.punishment_type" :disabled="busy" @change="changeType"><option value="physical">{{t('Physical','Физическое')}}</option><option value="ban">{{t('Ban','Запреты')}}</option><option value="other">{{t('Other','Другое')}}</option></select></label>
 <div v-if="model.punishment_type==='physical'" class="punishment-grid">
  <div><label>{{t('Device','Девайс')}}<select v-model="model.device" required :disabled="busy||adding||!relationId"><option :value="null" disabled>—</option><option v-for="d in devices" :key="d">{{d}}</option></select></label><div class="punishment-dictionary-add"><input v-model="newDevice" @keydown.enter.prevent="add('device')" :aria-label="t('New device','Новый девайс')" :placeholder="t('Add device','Добавить девайс')" maxlength="100" :disabled="busy||adding||!relationId"><button type="button" class="icon-button" :aria-label="t('Add device','Добавить девайс')" :disabled="busy||adding||!relationId||!newDevice.trim()" @click="add('device')"><IconPlus :size="18"/></button></div></div>
  <div><label>{{t('Body part','Часть тела')}}<select v-model="model.body_part" required :disabled="busy||adding||!relationId"><option :value="null" disabled>—</option><option v-for="p in parts" :key="p">{{p}}</option></select></label><div class="punishment-dictionary-add"><input v-model="newPart" @keydown.enter.prevent="add('body_part')" :aria-label="t('New body part','Новая часть тела')" :placeholder="t('Add body part','Добавить часть тела')" maxlength="100" :disabled="busy||adding||!relationId"><button type="button" class="icon-button" :aria-label="t('Add body part','Добавить часть тела')" :disabled="busy||adding||!relationId||!newPart.trim()" @click="add('body_part')"><IconPlus :size="18"/></button></div></div>
  <label>{{t('Strike count','Количество ударов')}}<input v-model.number="model.strike_count" type="number" min="1" max="1000000" step="1" required :disabled="busy"></label>
  <label v-if="!templateMode">{{t('Intensity (1–10)','Сила воздействия (1–10)')}}<input v-model.number="model.intensity" type="number" min="1" max="10" step="1" required :disabled="busy"></label>
 </div>
 <label v-if="model.punishment_type==='ban'">{{t('Duration in days','Время запрета в днях')}}<input v-model.number="model.ban_days" type="number" min="1" max="36500" step="1" required :disabled="busy"></label>
 <p v-if="error" role="alert">{{error}}</p>
</template>
