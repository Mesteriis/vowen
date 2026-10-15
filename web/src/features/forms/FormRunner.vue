<script setup lang="ts">
import {computed,ref,toRaw} from 'vue'
import {isVisible,type Schema,type AnswerMap} from './types'
const props=defineProps<{schema:Schema;initial:AnswerMap;ru:boolean;busy:boolean;guest?:boolean}>()
const emit=defineEmits<{save:[AnswerMap];submit:[AnswerMap,string]}>()
const answers=ref<AnswerMap>(structuredClone(toRaw(props.initial))),review=ref(false),ack=ref(false)
const key=crypto.randomUUID()
const visible=computed(()=>{const clean:AnswerMap={};return props.schema.questions.filter(q=>{
 if(!isVisible(q,clean))return false
 if(answers.value[q.id]!=null)clean[q.id]=answers.value[q.id]!
 return true
})})
function scalar(id:string):string|number{const v=answers.value[id];return typeof v==='string'||typeof v==='number'?v:''}
function value(id:string,event:Event,numeric=false){const raw=(event.target as HTMLInputElement).value;answers.value[id]=numeric?(raw===''?null:Number(raw)):raw}
function multi(id:string,option:string,event:Event){const previous=answers.value[id];const values=Array.isArray(previous)?previous:[];answers.value[id]=(event.target as HTMLInputElement).checked?[...values,option]:values.filter(v=>v!==option)}
</script>
<template>
 <div>
  <p>{{schema.description}}</p>
  <template v-if="!review">
   <fieldset v-for="q in visible" :key="q.id" :disabled="busy"><legend>{{q.label}}{{q.required?' *':''}}</legend>
    <label v-if="q.kind==='long_text'">{{q.label}}<textarea :value="scalar(q.id)" :maxlength="q.max_length??10000" @input="value(q.id,$event)" /></label>
    <label v-else-if="['short_text','number','date','scale','rating'].includes(q.kind)">{{q.label}}<input :type="['number','scale','rating'].includes(q.kind)?'number':q.kind==='date'?'date':'text'" :value="scalar(q.id)" :min="q.kind==='number'?undefined:q.minimum??1" :max="q.kind==='number'?undefined:q.maximum??5" :step="q.kind==='number'?'any':1" :maxlength="q.max_length??10000" @input="value(q.id,$event,['number','scale','rating'].includes(q.kind))"></label>
    <label v-else-if="q.kind==='single_choice'">{{q.label}}<select :value="scalar(q.id)" @change="value(q.id,$event)"><option value="">—</option><option v-for="o in q.options" :key="o.id" :value="o.id">{{o.label}}</option></select></label>
    <template v-else-if="q.kind==='multiple_choice'"><label v-for="o in q.options" :key="o.id"><input type="checkbox" :checked="Array.isArray(answers[q.id])&&(answers[q.id] as unknown[]).includes(o.id)" @change="multi(q.id,o.id,$event)">{{o.label}}</label></template>
    <label v-else-if="q.kind==='boolean'">{{q.label}}<select :value="answers[q.id]===true?'true':answers[q.id]===false?'false':''" @change="answers[q.id]=($event.target as HTMLSelectElement).value===''?null:($event.target as HTMLSelectElement).value==='true'"><option value="">—</option><option value="true">{{ru?'Да':'Yes'}}</option><option value="false">{{ru?'Нет':'No'}}</option></select></label>
    <label v-else><input type="checkbox" :checked="answers[q.id]===true" @change="answers[q.id]=($event.target as HTMLInputElement).checked">{{q.label}}</label>
   </fieldset>
   <p>{{ru?'Ввод сохраняется только после успешного запроса. При ошибке он остаётся в этом окне.':'Input is saved only after a successful request. Failed requests keep your input in this window.'}}</p>
   <button :disabled="busy" @click="emit('save',answers)">{{ru?'Сохранить черновик':'Save draft'}}</button>
   <label><input v-model="ack" type="checkbox">{{guest?(ru?'Мне 18 лет или больше; я ознакомился с читателями и сроком хранения':'I am 18 or older and have reviewed the readers and retention'):(ru?'Я ознакомился с читателями и сроком хранения':'I have reviewed the readers and retention')}}</label>
   <button :disabled="busy||!ack" @click="review=true">{{ru?'Проверить ответы':'Review answers'}}</button>
  </template>
  <template v-else>
   <h3>{{ru?'Проверка перед отправкой':'Review before sending'}}</h3>
   <dl v-for="q in visible" :key="q.id"><dt>{{q.label}}</dt><dd>{{answers[q.id]}}</dd></dl>
   <button :disabled="busy" @click="review=false">{{ru?'Изменить':'Edit answers'}}</button>
   <button :disabled="busy" @click="emit('submit',answers,key)">{{ru?'Отправить ответы':'Send answers'}}</button>
  </template>
 </div>
</template>
