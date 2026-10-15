<script setup lang="ts">
import {ref,toRaw} from 'vue'
import FormRunner from './FormRunner.vue'
import type {Schema,Question} from './types'
const props=defineProps<{initial?:Schema;ru:boolean;busy:boolean}>()
const emit=defineEmits<{save:[Schema];cancel:[]}>()
const schema=ref<Schema>(structuredClone(toRaw(props.initial)??{title:'',description:'',kind:'questionnaire',questions:[question()]}))
const preview=ref(false)
const kinds:Question['kind'][]=['short_text','long_text','number','date','boolean','single_choice','multiple_choice','scale','rating','acknowledgement']
function question():Question{return {id:'q_'+crypto.randomUUID().replaceAll('-',''),kind:'short_text',label:'',required:false,options:[],minimum:null,maximum:null,max_length:10000}}
function kind(q:Question){if(['scale','rating'].includes(q.kind)){q.minimum??=1;q.maximum??=5}q.options=q.kind.includes('choice')?[{id:'o1',label:'Option 1'},{id:'o2',label:'Option 2'}]:[]}
function options(q:Question,event:Event){q.options=(event.target as HTMLTextAreaElement).value.split('\n').filter(Boolean).map((label,i)=>({id:q.options?.[i]?.id??'o'+(i+1),label}))}
function condition(q:Question){q.visibility={all:[{question_id:schema.value.questions[0]!.id,op:'answered',value:null}],any:[]}}
function source(id:string){return schema.value.questions.find(q=>q.id===id)}
function conditionValue(c:{question_id:string;value?:unknown;op?:string},event:Event){const raw=(event.target as HTMLInputElement).value;const source=schema.value.questions.find(q=>q.id===c.question_id);c.value=source?.kind==='multiple_choice'&&c.op!=='contains'?[raw]:['number','scale','rating'].includes(source?.kind??'')?Number(raw):['boolean','acknowledgement'].includes(source?.kind??'')?raw==='true':raw}
</script>
<template>
 <section><h3>{{ru?'Конструктор анкеты':'Form editor'}}</h3>
  <label>{{ru?'Название анкеты':'Form title'}}<input v-model="schema.title" maxlength="200"></label>
  <label>{{ru?'Описание':'Description'}}<textarea v-model="schema.description" maxlength="10000" /></label>
  <label>{{ru?'Тип формы':'Form kind'}}<select v-model="schema.kind"><option value="questionnaire">Questionnaire / Анкета</option><option value="survey">Survey / Опрос</option></select></label>
  <fieldset v-for="(q,i) in schema.questions" :key="q.id"><legend>{{ru?'Вопрос':'Question'}} {{i+1}}</legend>
   <label :for="q.id">{{ru?'Текст вопроса':'Question '+(i+1)+' label'}}</label><input :id="q.id" v-model="q.label" maxlength="500">
   <label>{{ru?'Тип вопроса':'Question type'}}<select v-model="q.kind" @change="kind(q)"><option v-for="k in kinds" :key="k">{{k}}</option></select></label>
   <label><input v-model="q.required" type="checkbox">{{ru?'Обязательный':'Required'}}</label>
   <label v-if="q.kind.includes('choice')">{{ru?'Варианты: один на строку':'Options: one per line'}}<textarea :value="q.options?.map(o=>o.label).join('\n')" @change="options(q,$event)" /></label>
   <template v-if="['scale','rating'].includes(q.kind)"><label>Min<input v-model.number="q.minimum" type="number"></label><label>Max<input v-model.number="q.maximum" type="number"></label></template>
   <template v-if="i>0"><button @click="condition(q)">{{ru?'Добавить условие':'Add condition'}}</button>
    <template v-if="q.visibility">
     <label>{{ru?'Комбинация':'Combination'}}<select :value="q.visibility.any?.length?'any':'all'" @change="($event.target as HTMLSelectElement).value==='any'?(q.visibility.any=q.visibility.all,q.visibility.all=[]):(q.visibility.all=q.visibility.any,q.visibility.any=[])"><option>all</option><option>any</option></select></label>
     <div v-for="(c,j) in [...(q.visibility.all??[]),...(q.visibility.any??[])]" :key="j"><label>Previous question<select v-model="c.question_id"><option v-for="previous in schema.questions.slice(0,i)" :key="previous.id" :value="previous.id">{{previous.label}}</option></select></label><select v-model="c.op" aria-label="Condition operator"><option>answered</option><option>equals</option><option>not_equals</option><option>contains</option></select><template v-if="c.op!=='answered'"><select v-if="source(c.question_id)?.options?.length" :value="Array.isArray(c.value)?c.value[0]:c.value??''" aria-label="Condition value" @change="conditionValue(c,$event)"><option value="">—</option><option v-for="o in source(c.question_id)?.options" :key="o.id" :value="o.id">{{o.label}}</option></select><select v-else-if="['boolean','acknowledgement'].includes(source(c.question_id)?.kind??'')" :value="String(c.value??'')" aria-label="Condition value" @change="conditionValue(c,$event)"><option value="">—</option><option value="true">{{ru?'Да':'Yes'}}</option><option value="false">{{ru?'Нет':'No'}}</option></select><input v-else :value="c.value??''" aria-label="Condition value" @input="conditionValue(c,$event)"></template></div>
     <button @click="(q.visibility.any?.length?q.visibility.any:q.visibility.all)?.push({question_id:schema.questions[0]!.id,op:'answered',value:null})">+</button><button @click="q.visibility=null">{{ru?'Убрать условия':'Remove conditions'}}</button>
    </template>
   </template>
   <button :disabled="schema.questions.length===1" @click="schema.questions.splice(i,1)">{{ru?'Удалить вопрос':'Remove question'}}</button>
  </fieldset>
  <button :disabled="schema.questions.length>=100" @click="schema.questions.push(question())">{{ru?'Добавить вопрос':'Add question'}}</button>
  <button @click="preview=!preview">{{ru?'Предпросмотр':'Preview'}}</button>
  <FormRunner v-if="preview" :schema="schema" :initial="{}" :ru="ru" :busy="true" />
  <button :disabled="busy" @click="emit('save',schema)">{{ru?'Сохранить анкету':'Save form'}}</button><button @click="emit('cancel')">{{ru?'Отмена':'Cancel'}}</button>
 </section>
</template>
