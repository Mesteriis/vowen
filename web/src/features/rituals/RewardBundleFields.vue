<script setup lang="ts">
import type {components} from '../../shared/api'
defineProps<{options:Pick<components['schemas']['RewardView'],'version_id'|'title'>[];ru:boolean}>()
const rewards=defineModel<string[]>('rewards',{required:true})
const currency=defineModel<number>('currency',{required:true})
</script>
<template>
<fieldset><legend>{{ru?'Награды за выполнение':'Completion rewards'}}</legend><label>{{ru?'Монет за выполнение':'Coins per completion'}}<input v-model.number="currency" type="number" min="0" max="1000000000" step="1" required></label><label v-for="r in options" :key="r.version_id"><input v-model="rewards" type="checkbox" :value="r.version_id">{{r.title}}</label><p class="muted">{{ru?'Можно выбрать несколько наград и добавить монеты. Выдача — автоматически после завершения или обязательной проверки.':'Choose several rewards and coins. Awarded automatically after completion or required approval.'}}</p></fieldset>
</template>
