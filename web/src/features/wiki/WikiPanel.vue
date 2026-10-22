<script setup lang="ts">
import {computed,ref,watch,onMounted,onUnmounted,nextTick} from 'vue'
import {IconSearch,IconX,IconListTree,IconPlus,IconBook2,IconChevronRight,IconArrowLeft,IconArrowRight} from '@tabler/icons-vue'
import type {SessionClient} from '../auth/session'
import {createWikiApi,type WikiPageSummary,type WikiEditView} from './api'
import {useWikiState} from './state'
import WikiTree from './WikiTree.vue'
import WikiReader from './WikiReader.vue'
import WikiEditor from './WikiEditor.vue'
import WikiSections from './WikiSections.vue'
import './wiki.css'
const props=defineProps<{client:SessionClient;ru:boolean;active:boolean;admin:boolean}>()
const api=createWikiApi(props.client)
const state=useWikiState(api)
const {tree,page,results,sectionUid,pageUid,query,error,loading}=state
const drawer=ref<HTMLDialogElement|null>(null),drawerButton=ref<HTMLButtonElement|null>(null)
const searchText=ref('')
const editing=ref(false),editingUid=ref<string|null>(null),editorRef=ref<InstanceType<typeof WikiEditor>|null>(null),managing=ref(false),mode=ref<'published'|'drafts'|'archived'>('published'),adminRows=ref<WikiEditView[]>([]),adminOffset=ref(0),actionBusy=ref(false),notice=ref('')
async function canLeave(){return !editing.value||!!(await editorRef.value?.canLeave())}
defineExpose({canLeave})
let acceptedHash=location.hash
function abandonEditor(){editing.value=false;editingUid.value=null;mode.value='published'}
async function startEditor(uid:string|null){if(!(await canLeave()))return;editingUid.value=uid;editing.value=true}
async function listAdmin(value:'published'|'drafts'|'archived',offset=0){if(!(await canLeave()))return;abandonEditor();mode.value=value;adminOffset.value=offset;error.value='';try{adminRows.value=value==='published'?[]:await api.list(value,offset)}catch(e){error.value=e instanceof Error?e.message:'UNAVAILABLE'}}
async function seed(){if(actionBusy.value)return;actionBusy.value=true;error.value='';try{const result=await api.seed();notice.value=props.ru?`Добавлено: ${result.created}. Уже в библиотеке: ${result.skipped}.`:`Added: ${result.created}. Already present: ${result.skipped}.`;await state.loadTree()}catch(e){error.value=e instanceof Error?e.message:'UNAVAILABLE'}finally{actionBusy.value=false}}

const currentSection=computed(()=>tree.value?.sections.find(s=>s.uid===sectionUid.value))
const childSections=computed(()=>tree.value?.sections.filter(s=>(s.parent_uid??'')===sectionUid.value)??[])
const sectionPages=computed(()=>tree.value?.pages.filter(p=>p.section_uid===sectionUid.value)??[])
const roots=computed(()=>tree.value?.sections.filter(s=>!s.parent_uid)??[])
function countLabel(uid:string){const n=count(uid);if(!props.ru)return `${n} pages`;const form=new Intl.PluralRules('ru').select(n);return `${n} ${form==='one'?'материал':form==='few'?'материала':'материалов'}`}
function count(uid:string){const ids=new Set([uid]);for(let i=0;i<8;i++)tree.value?.sections.forEach(s=>{if(s.parent_uid&&ids.has(s.parent_uid))ids.add(s.uid)});return tree.value?.pages.filter(p=>ids.has(p.section_uid)).length??0}
async function changeHash(values:Record<string,string>){if(!(await canLeave()))return;abandonEditor();const params=new URLSearchParams(Object.entries(values).filter(([,v])=>v));location.hash='wiki'+(params.size?'?'+params:'')}
function openPage(uid:string){changeHash({page:uid,section:sectionUid.value});drawer.value?.close()}
function openSection(uid:string){searchText.value='';changeHash({section:uid});drawer.value?.close()}
function search(){if(searchText.value.trim())changeHash({q:searchText.value.trim(),section:sectionUid.value});else openSection(sectionUid.value)}
async function sync(){if(props.active){if(location.hash!==acceptedHash&&!(await canLeave())){history.replaceState(null,'',acceptedHash);return}acceptedHash=location.hash;abandonEditor();const previousPage=pageUid.value;await state.restore(location.hash);searchText.value=query.value;await nextTick();const heading=document.getElementById('wiki-page-title');heading?.focus({preventScroll:true});if(pageUid.value&&pageUid.value!==previousPage)heading?.scrollIntoView({block:'start',behavior:'instant'})}}
watch(()=>props.active,async active=>{if(active){await state.loadTree();await sync()}else state.invalidate()},{immediate:true})
onMounted(()=>window.addEventListener('hashchange',sync))
onUnmounted(()=>{window.removeEventListener('hashchange',sync);state.invalidate()})
function closeDrawer(){drawerButton.value?.focus()}
const title=(p:WikiPageSummary)=>p.title
</script>
<template>
 <section class="wiki-panel" :aria-label="ru?'Библиотека знаний':'Knowledge library'">
  <div class="wiki-toolbar"><button ref="drawerButton" class="wiki-sections-trigger" :aria-expanded="drawer?.open??false" @click="drawer?.showModal()"><IconListTree :size="18"/>{{ru?'Разделы':'Sections'}}</button><form role="search" class="wiki-search" @submit.prevent="search"><IconSearch :size="19"/><input v-model="searchText" :aria-label="ru?'Поиск по Wiki':'Search Wiki'" type="search" maxlength="200" :placeholder="ru?'Найти практику, позу, девайс или статью…':'Find a practice, pose, device or article…'"><button type="submit" :aria-label="ru?'Найти':'Search'"><IconArrowRight :size="18"/></button></form><button v-if="admin" class="wiki-new" :aria-label="ru?'Новая страница':'New page'" @click="startEditor(null)"><IconPlus :size="18"/><span>{{ru?'Новая страница':'New page'}}</span></button></div>
  <div v-if="admin" class="wiki-admin-bar"><nav :aria-label="ru?'Режим библиотеки':'Library mode'"><button v-for="value in ['published','drafts','archived'] as const" :key="value" :aria-current="mode===value?'page':undefined" @click="listAdmin(value)">{{value==='published'?(ru?'Библиотека':'Library'):value==='drafts'?(ru?'Черновики':'Drafts'):(ru?'Архив':'Archive')}}</button></nav><div><button :disabled="actionBusy" @click="managing=true">{{ru?'Разделы':'Manage sections'}}</button><button :disabled="actionBusy" @click="seed">{{ru?'Добавить из справочников':'Import references'}}</button></div></div><p v-if="notice" role="status" class="wiki-notice">{{notice}}</p>
  <p v-if="error" role="alert" class="wiki-error">{{ru?'Не удалось загрузить материал. Проверьте соединение и доступ.':'Could not load this page. Check your connection and access.'}} <button @click="sync">{{ru?'Повторить':'Retry'}}</button></p>
  <WikiSections v-if="tree&&managing&&admin" :api="api" :tree="tree" :ru="ru" @close="managing=false" @changed="state.loadTree()"/>
  <WikiEditor v-if="tree&&editing" ref="editorRef" :api="api" :tree="tree" :uid="editingUid" :section="sectionUid" :admin="admin" :ru="ru" @close="abandonEditor()" @saved="state.loadTree()"/>
  <div v-else-if="admin&&mode!=='published'" class="wiki-admin-list"><h2>{{mode==='drafts'?(ru?'Черновики':'Drafts'):(ru?'Архив':'Archive')}}</h2><div class="wiki-page-list"><button v-for="p in adminRows" :key="p.uid" @click="startEditor(p.uid)"><div><h3>{{p.document.title||(ru?'Без названия':'Untitled')}}</h3><p>{{p.document.summary}}</p></div><IconChevronRight :size="18"/></button></div><p v-if="!adminRows.length" class="muted">{{ru?'Здесь пока пусто.':'Nothing here yet.'}}</p><div class="wiki-pagination"><button :disabled="adminOffset===0" @click="listAdmin(mode,Math.max(0,adminOffset-50))">{{ru?'Назад':'Previous'}}</button><button :disabled="adminRows.length<50" @click="listAdmin(mode,adminOffset+50)">{{ru?'Далее':'Next'}}</button></div></div>
  <div v-else-if="tree" class="wiki-layout"><aside class="wiki-desktop-tree"><button class="wiki-tree-home" @click="openSection('')"><IconBook2 :size="19"/>{{ru?'Библиотека':'Library'}}</button><WikiTree :tree="tree" :selected="pageUid" :section="sectionUid" :ru="ru" @page="openPage" @section="openSection"/></aside>
   <div class="wiki-content" :aria-busy="loading">
    <div v-if="results" class="wiki-section-view"><span class="wiki-kicker">{{ru?'ПОИСК ПО БИБЛИОТЕКЕ':'LIBRARY SEARCH'}}</span><h2>{{ru?'Результаты поиска':'Search results'}}</h2><p class="muted">{{query}} · {{results.total}}</p><div class="wiki-page-list"><button v-for="p in results.items" :key="p.uid" @click="openPage(p.uid)"><div><h3>{{title(p)}}</h3><p>{{p.summary}}</p></div><IconChevronRight :size="18"/></button></div><p v-if="!results.items.length">{{ru?'Ничего не найдено. Попробуйте другой запрос.':'Nothing found. Try another search.'}}</p><div v-if="results.total>50" class="wiki-pagination"><button :disabled="results.offset===0" @click="state.search(query,Math.max(0,results.offset-50))"><IconArrowLeft :size="18"/></button><span>{{results.offset+1}}–{{Math.min(results.offset+50,results.total)}} / {{results.total}}</span><button :disabled="results.offset+50>=results.total" @click="state.search(query,results.offset+50)"><IconArrowRight :size="18"/></button></div></div>
    <WikiReader v-else-if="page" :page="page" :tree="tree" :api="api" :admin="admin" :ru="ru" @page="openPage" @section="openSection" @edit="startEditor($event)"/>
    <div v-else class="wiki-section-view"><span class="wiki-kicker">{{ru?'ЭНЦИКЛОПЕДИЯ VOWEN':'VOWEN ENCYCLOPEDIA'}}</span><h2>{{currentSection?.title||(ru?'Библиотека знаний':'Knowledge library')}}</h2><p class="wiki-deck">{{currentSection?.description||(ru?'Практики, позы, девайсы и статьи — в одном месте. Выберите тему, чтобы узнать больше.':'Practices, poses, devices and articles. Choose a topic to explore.')}}</p><div class="wiki-category-grid"><button v-for="s in (sectionUid?childSections:roots)" :key="s.uid" @click="openSection(s.uid)"><IconBook2 :size="24" :stroke-width="1.3"/><h3>{{s.title}}</h3><span>{{countLabel(s.uid)}}</span><IconChevronRight :size="18" class="wiki-category-arrow"/></button></div><div class="wiki-page-list"><button v-for="p in sectionPages" :key="p.uid" @click="openPage(p.uid)"><img v-if="p.thumbnail" :src="p.thumbnail" alt="" loading="lazy"><div><h3>{{p.title}}</h3><p>{{p.summary}}</p></div><IconChevronRight :size="18"/></button></div><p v-if="sectionUid&&!childSections.length&&!sectionPages.length" class="muted">{{ru?'В этом разделе пока нет опубликованных материалов.':'No published pages in this section yet.'}}</p><div v-if="!tree.pages.length" class="wiki-empty"><IconBook2 :size="34"/><h3>{{ru?'Библиотека начинается с первой страницы':'A library starts with its first page'}}</h3><p>{{ru?'Здесь появятся опубликованные материалы.':'Published pages will appear here.'}}</p></div></div>
   </div>
  </div><p v-else role="status">{{ru?'Открываем библиотеку…':'Opening library…'}}</p>
  <dialog ref="drawer" class="wiki-tree-drawer" :aria-label="ru?'Разделы Wiki':'Wiki sections'" @close="closeDrawer"><header><h2>{{ru?'Разделы':'Sections'}}</h2><button class="icon-button" :aria-label="ru?'Закрыть разделы':'Close sections'" @click="drawer?.close()"><IconX :size="20"/></button></header><button class="wiki-tree-home" @click="openSection('')">{{ru?'Вся библиотека':'All pages'}}</button><WikiTree v-if="tree" :tree="tree" :selected="pageUid" :section="sectionUid" :ru="ru" @page="openPage" @section="openSection"/></dialog>
 </section>
</template>
