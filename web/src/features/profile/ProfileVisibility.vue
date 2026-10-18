<script setup lang="ts">
import type {components} from '../../shared/api'
import {chapters} from './profile-fields'
type Visibility=components['schemas']['VisibilitySection']
const props=defineProps<{modelValue:Visibility;partners:components['schemas']['ParticipantView'][];ru:boolean}>()
const emit=defineEmits<{'update:modelValue':[Visibility]}>()
function ids(section:string){return props.modelValue.sections?.find(s=>s.section===section)?.reader_ids??[]}
function toggle(section:string,id:string){const values=ids(section);emit('update:modelValue',{sections:[...(props.modelValue.sections??[]).filter(s=>s.section!==section),{section:section as components['schemas']['SectionReaders']['section'],reader_ids:values.includes(id)?values.filter(v=>v!==id):[...values,id]}]})}
</script>
<template><div class="profile-visibility"><p class="muted">{{ru?'Каждый раздел закрыт, пока вы не выберете конкретного партнёра. Черновик всегда виден только вам.':'Each section stays private until you choose a specific partner. Drafts are always private.'}}</p><fieldset v-for="chapter in chapters.slice(0,5)" :key="chapter[0]"><legend>{{chapter[ru?1:2]}}</legend><p class="profile-private-label">{{ids(chapter[0]).length?(ru?'Выбранные партнёры':'Selected partners'):(ru?'Только я':'Only me')}}</p><label v-for="partner in partners" :key="partner.id" class="profile-check"><input type="checkbox" :checked="ids(chapter[0]).includes(partner.id)" @change="toggle(chapter[0],partner.id)">{{partner.display_name}}</label><p v-if="!partners.length" class="muted">{{ru?'Нет действующих прямых отношений.':'No active direct relationships.'}}</p><template v-for="uid in ids(chapter[0]).filter(id=>!partners.some(p=>p.id===id))" :key="uid"><label class="profile-check"><input type="checkbox" checked @change="toggle(chapter[0],uid)">{{ru?'Недействующий доступ — убрать':'Inactive access — remove'}}</label></template></fieldset></div></template>
