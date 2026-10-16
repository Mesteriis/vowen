<script setup lang="ts">
import {computed,nextTick,onMounted,onUnmounted,ref,useId,watch} from 'vue'
import {IconCheck,IconChevronDown,IconUsers,IconArrowRight,IconArrowLeft,IconPlayerPause,IconUnlink,IconLinkPlus} from '@tabler/icons-vue'
export type RelationshipChoice={value:string;title:string;detail:string;label:string;status?:string;role?:'dominant'|'submissive'}
const props=defineProps<{modelValue:string;choices:RelationshipChoice[];label:string;avatarName?:string}>()
const emit=defineEmits<{'update:modelValue':[string]}>()
const root=ref<HTMLElement|null>(null),trigger=ref<HTMLButtonElement|null>(null),open=ref(false),active=ref(0),id=useId()
const selected=computed(()=>props.choices.find(c=>c.value===props.modelValue)??props.choices[0])
function show(){active.value=Math.max(0,props.choices.findIndex(c=>c.value===props.modelValue));open.value=true;void reveal()}
async function reveal(){await nextTick();document.getElementById(`${id}-${active.value}`)?.scrollIntoView({block:'nearest'})}
function choose(index:number){const choice=props.choices[index];if(choice){emit('update:modelValue',choice.value);open.value=false;trigger.value?.focus()}}
function key(e:KeyboardEvent){
 if(e.key==='Escape'&&open.value){e.preventDefault();open.value=false;return}
 if(e.key==='Tab'){open.value=false;return}
 if(['ArrowDown','ArrowUp','Home','End'].includes(e.key)){
  e.preventDefault();if(!open.value){show();return}
  active.value=e.key==='Home'?0:e.key==='End'?props.choices.length-1:(active.value+(e.key==='ArrowDown'?1:-1)+props.choices.length)%props.choices.length;void reveal()
 }else if(e.key==='Enter'||e.key===' '){e.preventDefault();if(open.value)choose(active.value);else show()}
}
function outside(e:PointerEvent){if(!root.value?.contains(e.target as Node))open.value=false}
watch(()=>props.choices,()=>{if(active.value>=props.choices.length)active.value=0})
onMounted(()=>document.addEventListener('pointerdown',outside))
onUnmounted(()=>document.removeEventListener('pointerdown',outside))
</script>
<template>
<div ref="root" class="relationship-picker" :class="{'relationship-avatar-picker':avatarName}">
 <button ref="trigger" type="button" class="relationship-trigger" role="combobox" aria-haspopup="listbox" :aria-label="label" :title="avatarName?avatarName+' · '+selected?.label:undefined" :aria-expanded="open" :aria-controls="id" :aria-activedescendant="open?`${id}-${active}`:undefined" @keydown="key" @click="open?open=false:show()"><template v-if="avatarName"><span class="person-monogram" aria-hidden="true">{{avatarName.slice(0,1)}}</span><component :is="selected?.status==='paused'?IconPlayerPause:selected?.status==='revoked'?IconUnlink:selected?.status==='proposed'?IconLinkPlus:selected?.role==='dominant'?IconArrowRight:selected?.role==='submissive'?IconArrowLeft:IconUsers" :size="18" :stroke-width="1.5" aria-hidden="true" /><span v-if="selected?.value" class="person-monogram partner-monogram" aria-hidden="true">{{selected.title.slice(0,1)}}</span><span class="sr-only">{{selected?.label}}</span></template><template v-else><IconUsers :size="19" :stroke-width="1.5" /><span><strong>{{selected?.title}}</strong><small>{{selected?.detail}}</small></span></template><IconChevronDown :size="16" :class="{'is-open':open}" /></button>
 <ul v-if="open" :id="id" role="listbox" :aria-label="label" class="relationship-options">
  <li v-for="(choice,index) in choices" :id="`${id}-${index}`" :key="choice.value" role="option" :aria-label="choice.label" :aria-selected="choice.value===modelValue" :data-active="index===active" :data-status="choice.status" @pointermove="active=index" @mousedown.prevent @click="choose(index)"><span v-if="avatarName" class="person-monogram option-avatar" aria-hidden="true">{{choice.value?choice.title.slice(0,1):avatarName.slice(0,1)}}</span><span><strong>{{choice.title}}</strong><small>{{choice.detail}}</small></span><IconCheck v-if="choice.value===modelValue" :size="17" :stroke-width="1.5" /></li>
 </ul>
</div>
</template>
