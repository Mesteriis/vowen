<script setup lang="ts">
import {computed,ref,watch,nextTick,onBeforeUnmount} from 'vue'
import {IconX} from '@tabler/icons-vue'
import type {components} from '../../shared/api'
import type {SessionClient} from '../auth/session'
import {templateRuleText} from './catalogue'
import VoiceText from '../../shared/components/VoiceText.vue'
type Template=components['schemas']['PunishmentTemplateView']
const props=defineProps<{client:SessionClient;ru:boolean;relationId:string;recipientName:string;template?:Template|null;ruleVersionId?:string;initialConditions?:string}>()
const emit=defineEmits<{close:[];assigned:[]}>()
const dialog=ref<HTMLDialogElement|null>(null),templates=ref<Template[]>([]),chosen=ref(''),intensity=ref(1),comment=ref(''),busy=ref(false),loading=ref(false),error=ref(''),dictating=ref(false)
const selected=computed(()=>props.template??templates.value.find(t=>t.id===chosen.value))
const t=(en:string,ru:string)=>props.ru?ru:en
let key=crypto.randomUUID(),generation=0
watch([chosen,intensity,comment],()=>{key=crypto.randomUUID()})
watch(()=>props.relationId,async rid=>{const id=++generation;error.value='';if(props.template)return;loading.value=true;try{const rows=await props.client.get<Template[]>(`/punishment-templates?relation_id=${rid}`);if(id===generation){templates.value=rows;chosen.value=rows.find(x=>templateRuleText(x)===props.initialConditions||x.conditions===props.initialConditions||x.description===props.initialConditions)?.id??''}}catch{if(id===generation)error.value=t('Could not load catalogue.','Не удалось загрузить каталог.')}finally{if(id===generation)loading.value=false}},{immediate:true})
watch(dialog,async el=>{await nextTick();if(el&&!el.open)el.showModal()},{flush:'post'})
onBeforeUnmount(()=>{generation++;dialog.value?.close()})
async function assign(){const item=selected.value;if(!item||busy.value||dictating.value)return;busy.value=true;error.value='';try{await props.client.post(`/punishment-templates/${item.id}/assign`,{expected_version:item.revision,idempotency_key:key,comment:comment.value,intensity:item.punishment_type==='physical'?intensity.value:null,rule_version_id:props.ruleVersionId??null});emit('assigned');emit('close')}catch(e){error.value=e instanceof Error&&e.message==='VERSION_CONFLICT'?t('This variant changed. Reopen the assignment.','Вариант изменился. Откройте назначение заново.'):t('Could not assign. Check the relationship and try again.','Не удалось назначить. Проверьте отношения и повторите.')}finally{busy.value=false}}
</script>
<template>
 <dialog ref="dialog" class="punishment-dialog punishment-assign-dialog" :aria-label="t('Assign punishment','Назначить наказание')" @cancel.prevent="!busy&&emit('close')">
  <header><h3>{{t('Assign punishment','Назначить наказание')}}</h3><button class="icon-button" :disabled="busy" :aria-label="t('Close','Закрыть')" @click="emit('close')"><IconX :size="20"/></button></header>
  <p class="punishment-recipient">{{t('To: ','Кому: ')}}<strong>{{recipientName}}</strong></p>
  <p v-if="template" class="punishment-selected-title">{{template.title}}</p>
  <label v-else>{{t('Saved variant','Сохранённый вариант')}}<select v-model="chosen" :disabled="busy||loading"><option value="" disabled>{{loading?t('Loading…','Загрузка…'):t('Choose a variant','Выберите вариант')}}</option><option v-for="item in templates" :key="item.id" :value="item.id">{{item.title}}</option></select></label>
  <p v-if="ruleVersionId" class="muted">{{t('For a rule violation','За нарушение правила')}}</p>
  <form @submit.prevent="assign">
   <label v-if="selected?.punishment_type==='physical'" class="punishment-intensity"><span>{{t('Intensity','Сила воздействия')}} <output>{{intensity}} / 10</output></span><input v-model.number="intensity" type="range" min="1" max="10" step="1" :disabled="busy"><span class="range-ends"><small>1</small><small>10</small></span></label>
   <VoiceText v-model="comment" :ru="ru" :label="t('Comment (optional)','Комментарий (необязательно)')" :disabled="busy" :rows="2" @listening="dictating=$event"/>
   <p v-if="error" role="alert">{{error}}</p>
   <footer><button type="button" :disabled="busy" @click="emit('close')">{{t('Cancel','Отмена')}}</button><button class="punishment-primary" :disabled="busy||dictating||!selected||loading">{{busy?t('Assigning…','Назначаем…'):t('Assign','Назначить')}}</button></footer>
  </form>
 </dialog>
</template>
