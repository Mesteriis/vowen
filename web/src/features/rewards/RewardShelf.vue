<script setup lang="ts">
import {computed,ref} from 'vue'
import {IconCoins,IconPencil,IconShoppingBag,IconAdjustments,IconInfoCircle,IconChevronDown} from '@tabler/icons-vue'
import type {components} from '../../shared/api'
const props=withDefaults(defineProps<{title:string;items:components['schemas']['ListingView'][];manager:boolean;ru:boolean;disabled:boolean;initial?:number}>(),{initial:4})
const emit=defineEmits<{open:[components['schemas']['ListingView']]}>()
const limit=ref(props.initial)
const visible=computed(()=>props.items.slice(0,limit.value))
function action(item:components['schemas']['ListingView']){return item.can_manage?(props.ru?'Редактировать':'Edit'):item.can_toggle?(props.ru?'Доступ':'Availability'):item.purchase_relation_id?(props.ru?'Купить':'Buy'):(props.ru?'Подробнее':'Details')}
</script>
<template>
 <section v-if="items.length" class="shop-collection" :aria-label="title">
  <header><h3>{{title}} <small>{{items.length}}</small></h3></header>
  <div class="shop-product-list">
   <article v-for="item in visible" :key="item.id" class="shop-product-row" :class="{'is-disabled':!item.active}">
    <button class="shop-row-main" :disabled="disabled" :aria-label="(ru?'Открыть товар: ':'Open product: ')+item.title" @click="emit('open',item)">
     <img :src="'/shop/'+item.cover+'.png'" alt="" loading="lazy" width="64" height="64">
     <span><strong>{{item.title}}</strong><small>{{item.description}}</small><small v-if="!item.active" class="shop-disabled-label">{{ru?'Выключен':'Disabled'}}</small></span>
    </button>
    <span class="shop-row-price"><IconCoins :size="17" aria-hidden="true"/>{{item.price}}</span>
    <button class="shop-row-action icon-button" :disabled="disabled" :aria-label="action(item)+': '+item.title" :title="action(item)" @click="emit('open',item)">
     <IconPencil v-if="item.can_manage" :size="20"/><IconAdjustments v-else-if="item.can_toggle" :size="20"/><IconShoppingBag v-else-if="item.purchase_relation_id" :size="20"/><IconInfoCircle v-else :size="20"/>
    </button>
   </article>
  </div>
  <button v-if="limit<items.length" class="shop-show-more quiet-button" @click="limit+=8"><IconChevronDown :size="16"/>{{ru?'Показать ещё':'Show more'}}<small>{{items.length-limit}}</small></button>
  <button v-if="limit>initial" class="shop-show-more quiet-button" @click="limit=initial">{{ru?'Свернуть':'Show less'}}</button>
 </section>
</template>
