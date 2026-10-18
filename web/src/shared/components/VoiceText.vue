<script setup lang="ts">
import {ref,onMounted,onBeforeUnmount,watch} from 'vue'
import {IconMicrophone,IconPlayerStop} from '@tabler/icons-vue'
const props=withDefaults(defineProps<{ru:boolean;label:string;disabled?:boolean;maxlength?:number;rows?:number}>(),{disabled:false,maxlength:5000,rows:3})
const model=defineModel<string>({required:true})
const emit=defineEmits<{listening:[boolean]}>()
type Recognition={lang:string;continuous:boolean;interimResults:boolean;onresult:((e:{resultIndex:number;results:ArrayLike<{isFinal:boolean;0:{transcript:string}}>})=>void)|null;onerror:((e:{error:string})=>void)|null;onend:(()=>void)|null;start:()=>void;stop:()=>void;abort:()=>void}
type SpeechWindow=Window&{SpeechRecognition?:new()=>Recognition;webkitSpeechRecognition?:new()=>Recognition}
const available=ref(false),listening=ref(false),message=ref(''),input=ref<HTMLTextAreaElement|null>(null)
let recognition:Recognition|null=null
watch(listening,value=>emit('listening',value))
watch(()=>props.disabled,disabled=>{if(disabled)dispose()})
const t=(en:string,ru:string)=>props.ru?ru:en
onMounted(()=>{const w=window as SpeechWindow;available.value=!!(w.SpeechRecognition??w.webkitSpeechRecognition)})
function dispose(){if(recognition){recognition.onresult=null;recognition.onerror=null;recognition.onend=null;recognition.abort();recognition=null}listening.value=false}
onBeforeUnmount(dispose)
function dictate(){
 if(props.disabled)return
 if(listening.value){recognition?.stop();return}
 const w=window as SpeechWindow,Ctor=w.SpeechRecognition??w.webkitSpeechRecognition
 if(!Ctor){input.value?.focus();message.value=t('Use your keyboard or system dictation in this field.','Используйте диктовку клавиатуры или системы в этом поле.');return}
 dispose();message.value='';const speech=new Ctor();recognition=speech;speech.lang=props.ru?'ru-RU':'en-US';speech.continuous=false;speech.interimResults=false
 const seen=new Set<number>()
 speech.onresult=e=>{for(let i=e.resultIndex;i<e.results.length;i++){const result=e.results[i];if(!result?.isFinal||seen.has(i))continue;seen.add(i);const text=result[0].transcript.trim();if(text)model.value=(model.value+(model.value&&!/\s$/.test(model.value)?' ':'')+text).slice(0,props.maxlength)}}
 speech.onerror=e=>{listening.value=false;message.value=e.error==='not-allowed'?t('Microphone access was not granted. You can type or use system dictation.','Нет доступа к микрофону. Можно набрать текст или использовать системную диктовку.'):t('Could not recognize speech. Try again or type.','Не удалось распознать речь. Повторите или введите текст.')}
 speech.onend=()=>{listening.value=false}
 try{speech.start();listening.value=true}catch{dispose();message.value=t('Dictation is unavailable here. Use system dictation.','Диктовка здесь недоступна. Используйте системную диктовку.')}
}
</script>
<template>
 <div class="voice-text"><label>{{label}}<span class="voice-text-input"><textarea ref="input" v-model="model" :rows="rows" :maxlength="maxlength" :disabled="disabled"/><button type="button" class="icon-button voice-mic" :aria-label="listening?t('Stop dictation','Остановить диктовку'):t('Dictate comment','Надиктовать комментарий')" :aria-pressed="listening" :disabled="disabled" @click="dictate"><IconPlayerStop v-if="listening" :size="19"/><IconMicrophone v-else :size="19"/></button></span></label>
 <small v-if="available" class="muted">{{t('Speech recognition is provided by your browser and may use an online service.','Речь распознаёт браузер, возможно через онлайн-сервис.')}}</small>
 <small v-if="message||listening" role="status">{{listening?t('Listening…','Слушаю…'):message}}</small></div>
</template>
