<script setup lang="ts">
import {onMounted,onUnmounted,ref,watch} from 'vue'
const props=defineProps<{ru:boolean}>()
const media=window.matchMedia('(prefers-color-scheme: dark)')
const selected=ref('dark')
try{const saved=localStorage.getItem('vowen.appearance');if(saved&&['dark','light','system'].includes(saved))selected.value=saved}catch{/* Appearance works without storage. */}
function apply(){document.documentElement.dataset.theme=selected.value==='system'?(media.matches?'dark':'light'):selected.value}
watch(selected,()=>{apply();try{localStorage.setItem('vowen.appearance',selected.value)}catch{/* Optional device preference. */}})
onMounted(()=>{apply();media.addEventListener('change',apply)})
onUnmounted(()=>media.removeEventListener('change',apply))
</script>
<template><label class="appearance-select">{{props.ru?'Оформление':'Appearance'}}<select v-model="selected"><option value="dark">{{ru?'Тёмное':'Dark'}}</option><option value="light">{{ru?'Светлое':'Light'}}</option><option value="system">{{ru?'Системное':'System'}}</option></select></label></template>
