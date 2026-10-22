<script setup lang="ts">
import {computed,ref,watch} from 'vue'
import {IconArrowUpRight,IconPencil,IconChevronRight} from '@tabler/icons-vue'
import type {WikiApi,WikiPageView,WikiTreeView,Reference} from './api'
import MarkdownContent from './MarkdownContent'
import {parseWikiMarkdown} from './markdown'
const props=defineProps<{page:WikiPageView;tree:WikiTreeView;api:WikiApi;admin:boolean;ru:boolean}>()
function scrollHeading(id:string){document.getElementById(id)?.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'})}
const emit=defineEmits<{page:[uid:string];section:[uid:string];edit:[uid:string]}>()
const headings=computed(()=>parseWikiMarkdown(props.page.document.body).headings)
const crumbs=computed(()=>{const path=[];let id=props.page.document.section_uid;for(let i=0;i<8&&id;i++){const s=props.tree.sections.find(s=>s.uid===id);if(!s)break;path.unshift(s);id=s.parent_uid??''}return path})
const references=ref<Reference[]>([]),refError=ref(false)
let request=0
watch(()=>props.page.revision_uid,async()=>{const token=++request;references.value=[];refError.value=false;try{const found:Reference[]=[];for(const [kind,main,related] of [['practices',props.page.practice_uid,props.page.document.practice_uids],['poses',props.page.pose_uid,props.page.document.pose_uids],['devices',props.page.device_uid,props.page.document.device_uids]] as const){const ids=new Set([main,...(related??[])]);if(ids.size>1||main){const all=await props.api.references(kind);found.push(...all.filter(r=>ids.has(r.uid)))}}if(token===request)references.value=found}catch{if(token===request)refError.value=true}},{immediate:true})
</script>
<template>
 <article class="wiki-article" aria-labelledby="wiki-page-title">
  <nav class="wiki-breadcrumbs" :aria-label="ru?'Путь к материалу':'Breadcrumbs'"><template v-for="s in crumbs" :key="s.uid"><button @click="emit('section',s.uid)">{{s.title}}</button><IconChevronRight :size="13"/></template><span>{{ru?'Материал':'Page'}}</span></nav>
  <header class="wiki-article-header"><div><span class="wiki-kicker">{{page.kind==='article'?(ru?'СТАТЬЯ':'ARTICLE'):(ru?'ЭНЦИКЛОПЕДИЯ':'ENCYCLOPEDIA')}}</span><h2 id="wiki-page-title" tabindex="-1">{{page.document.title}}</h2><p v-if="page.document.summary" class="wiki-deck">{{page.document.summary}}</p></div><button v-if="admin" class="icon-button" :aria-label="ru?'Редактировать материал':'Edit page'" @click="emit('edit',page.uid)"><IconPencil :size="19"/></button></header>
  <div class="wiki-reading-layout"><div class="wiki-reading-main"><img v-if="page.document.thumbnail" class="wiki-page-image" :src="page.document.thumbnail" alt="" loading="lazy"><details v-if="headings.length" class="wiki-toc-inline"><summary>{{ru?'В этом материале':'On this page'}}</summary><nav><a v-for="h in headings" :key="h.id" :href="'#'+h.id" @click.prevent="scrollHeading(h.id)">{{h.text}}</a></nav></details><MarkdownContent :source="page.document.body"/>
   <section v-if="page.document.sources?.length" class="wiki-related"><h3>{{ru?'Источники':'Sources'}}</h3><a v-for="source in page.document.sources" :key="source.url" :href="source.url" target="_blank" rel="noopener noreferrer">{{source.name||source.url}}<IconArrowUpRight :size="16"/></a></section>
   <section v-if="references.length||refError" class="wiki-related"><h3>{{ru?'В справочниках':'Reference details'}}</h3><p v-if="refError" class="muted">{{ru?'Не удалось загрузить связанные записи.':'Could not load references.'}}</p><details v-for="r in references" :key="r.uid"><summary>{{r.name}}</summary><p>{{r.description}}</p><img v-if="r.thumbnail" :src="r.thumbnail" alt="" class="wiki-reference-image" loading="lazy"></details></section>
   <section v-if="page.related_pages.length" class="wiki-related"><h3>{{ru?'Продолжить изучение':'Related reading'}}</h3><button v-for="p in page.related_pages" :key="p.uid" class="wiki-text-link" @click="emit('page',p.uid)">{{p.title}}<IconChevronRight :size="16"/></button></section>
   <p v-if="page.published_at" class="wiki-byline">{{ru?'Опубликовано':'Published'}} {{new Date(page.published_at).toLocaleDateString(ru?'ru-RU':'en-GB')}}</p>
  </div><aside v-if="headings.length" class="wiki-toc"><span class="wiki-kicker">{{ru?'В ЭТОМ МАТЕРИАЛЕ':'ON THIS PAGE'}}</span><a v-for="h in headings" :key="h.id" :href="'#'+h.id" @click.prevent="scrollHeading(h.id)">{{h.text}}</a></aside></div>
 </article>
</template>
