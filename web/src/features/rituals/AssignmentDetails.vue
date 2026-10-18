<script setup lang="ts">
import {IconCalendar,IconClock,IconUsers,IconShieldCheck,IconPaperclip,IconGift,IconPlayerPause,IconPlayerPlay} from '@tabler/icons-vue'
import type {components} from '../../shared/api'
import {statusLabel} from '../workspace/context'
import {scheduleSummary} from './presentation'
type A=components['schemas']['RitualAssignmentView']
const props=defineProps<{assignment:A;memberId:string;recipient:string;ru:boolean;busy:boolean;paused:boolean}>()
const emit=defineEmits<{schedule:[A];rewards:[A];transition:[A,string]}>()
const t=(en:string,ru:string)=>props.ru?ru:en
const kinds:Record<string,[string,string]>={link:['Link','Ссылка'],photo:['Photo','Фото'],video:['Video','Видео']}
</script>
<template>
<div class="assignment-detail-content">
 <header><h3>{{assignment.title}}</h3><span class="status-tag" :data-status="assignment.status">{{statusLabel(assignment.status,ru)}}</span></header>
 <p class="muted">{{scheduleSummary(assignment.schedule,ru)}} · {{recipient}}</p><p>{{assignment.description}}</p>
 <dl class="ritual-facts">
  <div><dt><IconUsers :size="18" />{{t('Participant','Участник')}}</dt><dd>{{recipient}}</dd></div>
  <div><dt><IconCalendar :size="18" />{{t('Schedule','Расписание')}}</dt><dd>{{scheduleSummary(assignment.schedule,ru)}}</dd></div>
  <div><dt><IconClock :size="18" />{{t('Timezone','Часовой пояс')}}</dt><dd>{{assignment.schedule.timezone}}</dd></div>
  <div><dt><IconShieldCheck :size="18" />{{t('Review','Проверка')}}</dt><dd>{{assignment.approval_required?t('Required','Обязательна'):t('Not required','Не требуется')}}</dd></div>
  <div><dt><IconPaperclip :size="18" />{{t('Evidence','Доказательство')}}</dt><dd>{{(assignment.evidence_policy?.allowed_types??['link','photo','video']).map(k=>kinds[k]?.[ru?1:0]).join(', ')}}<small>{{assignment.evidence_policy?.required?t('Required','Обязательно'):t('Optional','Необязательно')}}</small></dd></div>
  <div><dt><IconGift :size="18" />{{t('Rewards','Награды')}}</dt><dd><span v-if="assignment.currency_amount">+{{assignment.currency_amount}} {{t('coins','монет')}}</span><span v-for="id in assignment.reward_version_ids" :key="id">{{assignment.reward_titles?.[id]??t('Saved reward version','Сохранённая версия награды')}}</span><span v-if="!assignment.currency_amount&&!assignment.reward_version_ids?.length">{{t('None','Без награды')}}</span></dd></div>
 </dl>
 <div class="row-actions"><button class="ritual-icon-action" :aria-label="t('Change schedule','Изменить расписание')" :title="t('Change schedule','Изменить расписание')" v-if="assignment.issuer_id===memberId&&assignment.effective" :disabled="busy||paused" @click="emit('schedule',assignment)"><IconCalendar :size="19" :stroke-width="1.5" /></button><button class="ritual-icon-action" :aria-label="t('Change ritual rewards','Изменить награды ритуала')" :title="t('Change ritual rewards','Изменить награды ритуала')" v-if="assignment.issuer_id===memberId&&assignment.effective" :disabled="busy||paused" @click="emit('rewards',assignment)"><IconGift :size="19" :stroke-width="1.5" /></button><button class="ritual-icon-action" :aria-label="assignment.recipient_id===memberId?t('Request pause','Запросить паузу'):t('Pause ritual','Приостановить ритуал')" :title="assignment.recipient_id===memberId?t('Request pause','Запросить паузу'):t('Pause ritual','Приостановить ритуал')" v-if="assignment.status==='active'&&(assignment.recipient_id===memberId||assignment.issuer_id===memberId)" :disabled="busy" @click="emit('transition',assignment,'pause')"><IconPlayerPause :size="19" :stroke-width="1.5" /></button><button class="ritual-icon-action" :aria-label="t('Resume ritual','Возобновить ритуал')" :title="t('Resume ritual','Возобновить ритуал')" v-if="assignment.status==='paused'&&(assignment.paused_by_id??assignment.recipient_id)===memberId" :disabled="busy||paused" @click="emit('transition',assignment,'resume')"><IconPlayerPlay :size="19" :stroke-width="1.5" /></button></div>
 <details v-if="assignment.status!=='revoked'&&(assignment.recipient_id===memberId||assignment.issuer_id===memberId)"><summary>{{t('More actions','Другие действия')}}</summary><button :disabled="busy" class="danger-button" @click="emit('transition',assignment,'revoke')">{{t('Revoke ritual','Отозвать ритуал')}}</button></details>
</div>
</template>
