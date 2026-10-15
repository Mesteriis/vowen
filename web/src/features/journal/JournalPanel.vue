<script setup lang="ts">
import {computed,onMounted,ref,watch} from 'vue'
import type {components} from '../../shared/api'
import type {SessionClient} from '../auth/session'
type Entry=components['schemas']['JournalView']
const props=defineProps<{client:SessionClient;ru:boolean;me:components['schemas']['MemberView'];participants:components['schemas']['ParticipantView'][]}>()
const entries=ref<Entry[]>([]),busy=ref(false),error=ref(''),editing=ref(false),selected=ref<Entry|null>(null),deleting=ref<Entry|null>(null)
const date=ref(''),title=ref(''),text=ref(''),mood=ref(''),tags=ref(''),visibility=ref<'private'|'selected'|'all_current_members'>('private'),readers=ref<string[]>([]),published=ref(false),refreshAudience=ref(false),search=ref(''),tag=ref('')
const readerOptions=computed(()=>[...props.participants,...readers.value.filter(id=>!props.participants.some(p=>p.id===id)).map(id=>({id,display_name:id,profile_labels:[]}))])
const t=(en:string,ru:string)=>props.ru?ru:en
const name=(id:string)=>props.participants.find(p=>p.id===id)?.display_name??id
async function load(){entries.value=await props.client.get<Entry[]>(`/journal?search=${encodeURIComponent(search.value)}&tag=${encodeURIComponent(tag.value)}`)}
async function run(fn:()=>Promise<void>){busy.value=true;error.value='';try{await fn()}catch(e){error.value=e instanceof Error?e.message:'NETWORK_ERROR';entries.value=[]}finally{busy.value=false}}
onMounted(()=>run(load))
watch(()=>props.me.paused,()=>{entries.value=entries.value.filter(e=>e.author_id===props.me.id);void run(load)})
function edit(e:Entry|null){selected.value=e;date.value=e?.date??new Date().toLocaleDateString('en-CA');title.value=e?.title??'';text.value=e?.text??'';mood.value=e?.mood??'';tags.value=e?.tags?.join(', ')??'';visibility.value=e?.visibility??'private';readers.value=e?.reader_ids??[];published.value=e?.published??false;refreshAudience.value=false;editing.value=true}
async function save(){await run(async()=>{
 const e=selected.value,body={date:date.value,title:title.value,text:text.value,mood:mood.value||null,tags:tags.value.split(',').map(x=>x.trim()).filter(Boolean),visibility:visibility.value,reader_ids:visibility.value==='private'?[]:readers.value,published:published.value}
 if(e)await props.client.patch(`/journal/${e.id}`,{...body,expected_version:e.revision,refresh_audience:refreshAudience.value})
 else await props.client.post('/journal',body)
 editing.value=false;await load()
})}
async function remove(){const e=deleting.value;if(!e)return;await run(async()=>{await props.client.post(`/journal/${e.id}/delete`,{expected_version:e.revision});deleting.value=null;await load()})}
async function exportEntries(){await run(async()=>{const rows=await props.client.get<Entry[]>('/journal/export'),url=URL.createObjectURL(new Blob([JSON.stringify(rows,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='vowen-diary.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)})}
</script>
<template>
<section id="journal" aria-labelledby="journal-heading">
 <h2 id="journal-heading">{{t('Diary','Дневник')}}</h2><p>{{t('Private by default. Relationships do not grant diary access.','По умолчанию приватный. Отношения не открывают доступ к дневнику.')}}</p>
 <button :disabled="busy" @click="run(load)">{{t('Refresh diary','Обновить дневник')}}</button><button :disabled="busy" @click="edit(null)">{{t('New diary entry','Новая запись дневника')}}</button><button :disabled="busy" @click="exportEntries">{{t('Export accessible entries','Экспорт доступных записей')}}</button>
 <p v-if="error" role="alert">{{error}}</p>
 <form @submit.prevent="run(load)"><label>{{t('Search accessible entries','Поиск доступных записей')}}<input v-model="search" maxlength="200"></label><label>{{t('Filter by tag','Фильтр по тегу')}}<input v-model="tag" maxlength="100"></label><button :disabled="busy">{{t('Search diary','Искать в дневнике')}}</button></form>
 <form v-if="editing" @submit.prevent="save">
  <label>{{t('Entry date','Дата записи')}}<input v-model="date" type="date" required></label><label>{{t('Entry title','Заголовок записи')}}<input v-model="title" required maxlength="200"></label>
  <label>{{t('Entry text','Текст записи')}}<textarea v-model="text" required maxlength="100000" rows="7" /></label><label>{{t('Mood','Настроение')}}<input v-model="mood" maxlength="100"></label><label>{{t('Tags (comma separated)','Теги (через запятую)')}}<input v-model="tags"></label>
  <label>{{t('Published entry','Опубликованная запись')}}<input v-model="published" type="checkbox"></label><p>{{t('Drafts are visible only to you.','Черновики видны только вам.')}}</p>
  <label>{{t('Entry visibility','Видимость записи')}}<select :aria-label="t('Entry visibility','Видимость записи')" v-model="visibility"><option value="private">{{t('Private','Только мне')}}</option><option value="selected">{{t('Selected readers','Выбранные читатели')}}</option><option value="all_current_members">{{t('Current members snapshot; future members excluded','Список текущих участников; будущие не добавляются')}}</option></select></label>
  <fieldset v-if="visibility==='selected'"><legend>{{t('Explicit readers','Выбранные читатели')}}</legend><label v-for="p in readerOptions.filter(p=>p.id!==me.id)" :key="p.id"><input v-model="readers" type="checkbox" :value="p.id">{{t('Reader: ','Читатель: ')}}{{p.display_name}}</label></fieldset>
  <template v-if="visibility==='all_current_members'"><p>{{t('The snapshot stays unchanged when you edit the text.','При редактировании текста список читателей не расширяется.')}}</p><label v-if="selected">{{t('Explicitly refresh current member snapshot','Явно обновить список текущих участников')}}<input v-model="refreshAudience" type="checkbox"></label></template>
  <button :disabled="busy">{{t('Save diary entry','Сохранить запись дневника')}}</button><button type="button" :disabled="busy" @click="editing=false">{{t('Cancel','Отмена')}}</button>
 </form>
 <p v-if="!entries.length">{{t('No accessible entries','Нет доступных записей')}}</p>
 <article v-for="e in entries" :key="e.id"><h3>{{e.title}}</h3><p>{{e.date}} · {{name(e.author_id)}} · {{e.published?t('Published','Опубликовано'):t('Draft','Черновик')}} · {{e.visibility}}</p><p class="entry-text">{{e.text}}</p><p>{{e.mood}} · {{e.tags?.join(', ')}}</p><p>{{t('Readers','Читатели')}}: {{e.reader_ids?.map(name).join(', ')||'—'}}</p><template v-if="e.author_id===me.id"><button :disabled="busy" @click="edit(e)">{{t('Edit diary entry','Изменить запись дневника')}}</button><button :disabled="busy" @click="deleting=e">{{t('Delete diary entry','Удалить запись дневника')}}</button></template></article>
 <div v-if="deleting" role="dialog" aria-modal="true" :aria-label="t('Delete diary entry','Удаление записи дневника')"><p>{{t('Delete this entry and revoke all readers?','Удалить запись и доступ всех читателей?')}} {{deleting.title}}</p><button :disabled="busy" @click="remove">{{t('Confirm diary deletion','Подтвердить удаление записи')}}</button><button :disabled="busy" @click="deleting=null">{{t('Cancel','Отмена')}}</button></div>
</section>
</template>
<style scoped>.entry-text{white-space:pre-wrap;overflow-wrap:anywhere}</style>
