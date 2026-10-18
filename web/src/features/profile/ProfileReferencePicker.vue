<script setup lang="ts">
import {computed,ref} from 'vue'
import type {Reference} from './profile-fields'
const props=defineProps<{modelValue:string[];items:Reference[];label:string;ru:boolean}>()
const emit=defineEmits<{'update:modelValue':[string[]]}>()
const search=ref('')
const shown=computed(()=>props.items.filter(item=>item.name.toLocaleLowerCase().includes(search.value.toLocaleLowerCase())))
function toggle(uid:string){emit('update:modelValue',props.modelValue.includes(uid)?props.modelValue.filter(id=>id!==uid):[...props.modelValue,uid])}
</script>
<template><fieldset class="profile-reference-picker"><legend>{{label}}</legend><label class="profile-search"><span class="sr-only">{{ru?'Поиск: ':'Search: '}}{{label}}</span><input v-model="search" type="search" :placeholder="ru?'Найти в справочнике…':'Search catalogue…'"></label><div class="profile-reference-options"><label v-for="item in shown" :key="item.uid" class="profile-choice" :class="{selected:modelValue.includes(item.uid)}"><input type="checkbox" :checked="modelValue.includes(item.uid)" @change="toggle(item.uid)"><img v-if="item.thumbnail" :src="item.thumbnail" alt="" loading="lazy"><span>{{item.name}}</span></label><p v-if="!shown.length" class="muted">{{ru?'Ничего не найдено':'No results'}}</p></div><small class="muted">{{modelValue.length? (ru?'Выбрано: ':'Selected: ')+modelValue.length:(ru?'Не указано':'Not specified')}}</small></fieldset></template>
