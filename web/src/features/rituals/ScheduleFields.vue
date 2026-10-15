<script setup lang="ts">
import type {components} from '../../shared/api'
type Schedule=components['schemas']['Schedule']
const props=defineProps<{modelValue:Schedule;ru:boolean;fixedZone?:boolean}>()
const emit=defineEmits<{ 'update:modelValue':[Schedule] }>()
const t=(en:string,ru:string)=>props.ru?ru:en
function set(patch:Partial<Schedule>){emit('update:modelValue',{...props.modelValue,...patch})}
function time(event:Event){const [hour,minute]=(event.target as HTMLInputElement).value.split(':').map(Number);set({hour:hour??0,minute:minute??0})}
function weekday(day:number){const days=props.modelValue.weekdays??[];set({weekdays:days.includes(day)?days.filter(d=>d!==day):[...days,day].sort()})}
</script>
<template>
 <div class="schedule-fields">
  <label>{{t('Repeat','Повтор')}}<select :value="modelValue.kind" @change="set({kind:($event.target as HTMLSelectElement).value as Schedule['kind'],weekdays:($event.target as HTMLSelectElement).value==='weekly'?[0]:[]})"><option value="once">{{t('Once','Один раз')}}</option><option value="daily">{{t('Daily','Каждый день')}}</option><option value="weekly">{{t('Selected weekdays','По дням недели')}}</option></select></label>
  <fieldset v-if="modelValue.kind==='weekly'"><legend>{{t('Weekdays','Дни недели')}}</legend><label v-for="(day,index) in (ru?['Пн','Вт','Ср','Чт','Пт','Сб','Вс']:['Mon','Tue','Wed','Thu','Fri','Sat','Sun'])" :key="index" class="inline"><input type="checkbox" :checked="modelValue.weekdays?.includes(index)" @change="weekday(index)">{{day}}</label></fieldset>
  <div class="field-pair"><label>{{t('Start date','Дата начала')}}<input type="date" :value="modelValue.start_date" required @input="set({start_date:($event.target as HTMLInputElement).value})"></label>
  <label>{{t('Local time','Локальное время')}}<input type="time" :value="`${String(modelValue.hour).padStart(2,'0')}:${String(modelValue.minute).padStart(2,'0')}`" required @input="time"></label></div>
  <label>{{t('IANA schedule timezone','Часовой пояс IANA')}}<input :value="modelValue.timezone" :readonly="fixedZone" required maxlength="100" @input="set({timezone:($event.target as HTMLInputElement).value})"></label>
  <label>{{t('Report window (hours)','Окно отчёта (часы)')}}<input type="number" :value="modelValue.window_hours??24" min="1" max="168" required @input="set({window_hours:Number(($event.target as HTMLInputElement).value)})"></label>
  <p class="muted">{{t('DST: missing time shifts by the gap; repeated time uses its first occurrence. Pauses create no missed obligations.','DST: отсутствующее время сдвигается на разрыв, повторяющееся берётся один раз. Пауза не создаёт пропусков.')}}</p>
 </div>
</template>
