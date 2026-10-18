<script setup lang="ts">
import {ref,onMounted,onUnmounted,watch,nextTick} from 'vue'
import type {Ink,Stroke,Point} from './ink'
import {emptyInk,inkColors,pointAt,hitsStroke} from './ink'
const props=withDefaults(defineProps<{modelValue:Ink|null|undefined;readonly?:boolean;tool?:'pen'|'eraser';color?:Stroke['color'];width?:number;finger?:boolean;ru:boolean}>(),{readonly:false,tool:'pen',color:'ivory',width:.003,finger:false})
const emit=defineEmits<{ 'update:modelValue':[Ink];history:[{undo:boolean;redo:boolean}];limit:[] }>()
const canvas=ref<HTMLCanvasElement|null>(null),page=ref<HTMLDivElement|null>(null)
let observer:ResizeObserver|undefined,pointer:number|null=null,current:Stroke|null=null,erased=new Set<number>(),undoStack:Ink[]=[],redoStack:Ink[]=[]
function value(){return props.modelValue??emptyInk()}
function history(){emit('history',{undo:!!undoStack.length,redo:!!redoStack.length})}
function paint(){const c=canvas.value;if(!c)return;const rect=c.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,2);c.width=Math.round(rect.width*dpr);c.height=Math.round(rect.height*dpr);const ctx=c.getContext('2d');if(!ctx)return;ctx.scale(dpr,dpr);ctx.lineCap='round';ctx.lineJoin='round';
 ctx.strokeStyle='#d6b57916';ctx.lineWidth=1;for(let y=32;y<rect.height;y+=32){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(rect.width,y);ctx.stroke()}
 const draw=(s:Stroke)=>{ctx.strokeStyle=inkColors[s.color??'ivory'];ctx.fillStyle=ctx.strokeStyle;const points=s.points;if(points.length===1){const p=points[0]!;ctx.beginPath();ctx.arc(p.x*rect.width,p.y*rect.height,(s.width??.003)*rect.width/2,0,2*Math.PI);ctx.fill()}
 for(let i=1;i<points.length;i++){const a=points[i-1]!,b=points[i]!;ctx.lineWidth=(s.width??.003)*rect.width*(.55+((a.p??.5)+(b.p??.5))*.45);ctx.beginPath();ctx.moveTo(a.x*rect.width,a.y*rect.height);ctx.lineTo(b.x*rect.width,b.y*rect.height);ctx.stroke()}}
 value().strokes?.forEach((s,i)=>{if(!erased.has(i))draw(s)});if(current)draw(current)
}
function point(e:PointerEvent){const r=canvas.value!.getBoundingClientRect();return pointAt(e.clientX-r.left,e.clientY-r.top,r.width,r.height,e.pressure)}
function down(e:PointerEvent){if(props.readonly||pointer!==null||e.button>0||e.pointerType==='touch'&&!props.finger)return;e.preventDefault();pointer=e.pointerId;canvas.value?.setPointerCapture(pointer);erased=new Set();if(props.tool==='pen')current={color:props.color,width:props.width,points:[point(e)]};else erase(point(e));paint()}
function erase(p:Point){value().strokes?.forEach((s,i)=>{if(hitsStroke(s,p))erased.add(i)})}
function move(e:PointerEvent){if(e.pointerId!==pointer)return;e.preventDefault();if(props.tool==='eraser'){erase(point(e));paint();return}if(!current)return;const last=current.points.at(-1)!;const samples=e.getCoalescedEvents?.();for(const event of samples?.length?samples:[e]){const p=point(event);if(Math.hypot(p.x-last.x,p.y-last.y)<.0005)continue;if(current.points.length>=1500)break;current.points.push(p)}paint()}
function commit(next:Ink){undoStack.push(value());if(undoStack.length>40)undoStack.shift();redoStack=[];emit('update:modelValue',next);history();void nextTick(paint)}
function up(e:PointerEvent){if(e.pointerId!==pointer)return;const previous=value(),strokes=previous.strokes??[];if(current){if(strokes.length>=500||strokes.reduce((n,s)=>n+s.points.length,0)+current.points.length>5000)emit('limit');else commit({version:1,strokes:[...strokes,current]})}else if(erased.size)commit({version:1,strokes:strokes.filter((_,i)=>!erased.has(i))});cancel()}
function cancel(){pointer=null;current=null;erased=new Set();void nextTick(paint)}
function undo(){const previous=undoStack.pop();if(previous){redoStack.push(value());emit('update:modelValue',previous);history()}}
function redo(){const next=redoStack.pop();if(next){undoStack.push(value());emit('update:modelValue',next);history()}}
onMounted(()=>{observer=new ResizeObserver(paint);if(page.value)observer.observe(page.value);paint();history()});onUnmounted(()=>observer?.disconnect());watch(()=>props.modelValue,()=>nextTick(paint),{deep:true});watch(()=>props.tool,cancel)
defineExpose({undo,redo})
</script>
<template><div ref="page" class="ink-page" :class="{'ink-preview':readonly}"><canvas ref="canvas" role="img" :aria-label="ru?'Рукописная страница дневника':'Handwritten diary page'" :style="{touchAction:readonly?'pan-y':'none'}" @pointerdown="down" @pointermove="move" @pointerup="up" @pointercancel="cancel" @lostpointercapture="cancel" /></div></template>
