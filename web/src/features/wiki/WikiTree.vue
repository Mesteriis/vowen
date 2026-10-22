<script setup lang="ts">
import {computed} from 'vue'
import {IconChevronRight,IconFileText,IconBook2} from '@tabler/icons-vue'
import type {WikiTreeView} from './api'
defineOptions({name:'WikiTree'})
const props=defineProps<{tree:WikiTreeView;parent?:string|null;selected:string;section:string;ru:boolean}>()
const emit=defineEmits<{page:[uid:string];section:[uid:string]}>()
const sections=computed(()=>props.tree.sections.filter(s=>(s.parent_uid??null)===(props.parent??null)))
const pages=computed(()=>props.tree.pages.filter(p=>p.section_uid===props.parent))
function contains(uid:string):boolean{let current=props.section;for(let i=0;i<8&&current;i++){if(current===uid)return true;current=props.tree.sections.find(s=>s.uid===current)?.parent_uid??''}return false}
</script>
<template>
 <ul class="wiki-tree-list">
  <li v-for="s in sections" :key="s.uid"><details :open="contains(s.uid)"><summary><IconChevronRight :size="14" class="wiki-tree-arrow"/><button :aria-current="section===s.uid&&!selected?'page':undefined" @click.stop="emit('section',s.uid)"><IconBook2 v-if="!s.parent_uid" :size="17"/>{{s.title}}</button></summary><WikiTree :tree="tree" :parent="s.uid" :selected="selected" :section="section" :ru="ru" @page="emit('page',$event)" @section="emit('section',$event)"/></details></li>
  <li v-for="p in pages" :key="p.uid"><button class="wiki-tree-page" :aria-current="selected===p.uid?'page':undefined" @click="emit('page',p.uid)"><IconFileText :size="14"/><span>{{p.title}}</span></button></li>
 </ul>
</template>
