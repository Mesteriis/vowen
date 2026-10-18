<script setup lang="ts">
import {computed,onMounted,ref,watch} from 'vue'
import {IconChevronDown,IconCheck} from '@tabler/icons-vue'
import type {components} from '../../shared/api'
import type {SessionClient} from '../auth/session'
import {templateRuleText} from '../discipline/catalogue'
import {useWorkspaceView} from '../workspace/context'
const props=defineProps<{client:SessionClient;ru:boolean;modelValue:string}>()
const emit=defineEmits<{'update:modelValue':[string]}>()
const view=useWorkspaceView(),rows=ref<components['schemas']['PunishmentTemplateView'][]>([]),error=ref(''),loading=ref(true),menu=ref<HTMLDetailsElement|null>(null)
const choices=computed(()=>rows.value.map(item=>({id:item.id,title:item.title,conditions:templateRuleText(item)})))
const selected=computed(()=>choices.value.find(c=>c.conditions===props.modelValue))
const t=(en:string,ru:string)=>props.ru?ru:en
async function load(){loading.value=true;error.value='';try{const id=view.selected.value?.id;rows.value=id?await props.client.get<components['schemas']['PunishmentTemplateView'][]>(`/punishment-templates?relation_id=${id}`):[]}catch{error.value=t('Could not load punishments. Existing conditions are preserved.','Не удалось загрузить наказания. Сохранённые условия остаются.')}finally{loading.value=false}}
onMounted(load);watch(view.revision,load)
function choose(value:string){emit('update:modelValue',value);if(menu.value)menu.value.open=false}
</script>
<template>
 <div class="punishment-picker">
  <span class="punishment-label">{{t('Punishment','Наказание')}}</span>
  <details ref="menu"><summary :aria-label="t('Choose punishment','Выбрать наказание')"><span>{{loading?t('Loading…','Загрузка…'):selected?.title||(modelValue?t('Saved punishment conditions','Сохранённые условия наказания'):t('No punishment','Без наказания'))}}</span><IconChevronDown :size="18" /></summary>
   <div class="punishment-options"><button type="button" :aria-pressed="!modelValue" @click="choose('')">{{t('No punishment','Без наказания')}}<IconCheck v-if="!modelValue" :size="16" /></button><button v-for="choice in choices" :key="choice.id" type="button" :aria-pressed="choice.conditions===modelValue" @click="choose(choice.conditions)"><span>{{choice.title}}<small>{{choice.conditions}}</small></span><IconCheck v-if="choice.conditions===modelValue" :size="16" /></button><p v-if="!loading&&!choices.length&&!error">{{t('No available punishment records yet. Create one in the Punishments catalogue.','Пока нет доступных записей. Создайте вариант в каталоге «Наказания».')}}</p><p v-if="error" role="alert">{{error}}</p></div>
  </details>
  <p v-if="modelValue" class="punishment-preview">{{modelValue}}</p>
  <small>{{t('The selected conditions are saved with this rule version. This does not start a punishment.','Условия сохраняются в этой версии правила. Выбор не запускает наказание.')}}</small>
 </div>
</template>
