<script setup lang="ts">
import {ref,nextTick} from 'vue'
import type {components} from '../../shared/api'
import type {SessionClient} from '../auth/session'
import AdministrationPanel from './AdministrationPanel.vue'
import ReferencesPanel from './ReferencesPanel.vue'
defineProps<{client:SessionClient;me:components['schemas']['MemberView'];ru:boolean;active:boolean}>()
defineEmits<{changed:[]}>()
const tab=ref<'administrators'|'references'>('administrators')
async function key(event:KeyboardEvent){if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();tab.value=event.key==='Home'?'administrators':event.key==='End'?'references':tab.value==='administrators'?'references':'administrators';await nextTick();document.getElementById('settings-tab-'+tab.value)?.focus()}
</script>
<template>
 <div class="space-settings-panel">
  <p v-if="!me.is_admin" class="muted">{{ru?'Настройки доступны только администраторам.':'Settings are available to administrators only.'}}</p>
  <template v-else>
   <div class="account-tabs" role="tablist" @keydown="key" :aria-label="ru?'Разделы настроек':'Settings sections'"><button id="settings-tab-administrators" role="tab" aria-controls="settings-administrators" :tabindex="tab==='administrators'?0:-1" :aria-selected="tab==='administrators'" @click="tab='administrators'">{{ru?'Администраторы':'Administrators'}}</button><button id="settings-tab-references" role="tab" aria-controls="settings-references" :tabindex="tab==='references'?0:-1" :aria-selected="tab==='references'" @click="tab='references'">{{ru?'Справочники':'References'}}</button></div>
   <div class="space-settings-body"><AdministrationPanel id="settings-administrators" role="tabpanel" aria-labelledby="settings-tab-administrators" v-show="tab==='administrators'" :active="active&&tab==='administrators'" :client="client" :me="me" :ru="ru" @changed="$emit('changed')"/><ReferencesPanel id="settings-references" role="tabpanel" aria-labelledby="settings-tab-references" v-show="tab==='references'" :active="active&&tab==='references'" :client="client" :ru="ru"/></div>
  </template>
 </div>
</template>
