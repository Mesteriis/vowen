import type {components} from '../../shared/api'
export type PunishmentParameters = Pick<components['schemas']['DisciplineEdit'], 'punishment_type'|'device'|'body_part'|'strike_count'|'intensity'|'ban_days'>
export function parameters(v?: PunishmentParameters): PunishmentParameters {
  return {punishment_type:v?.punishment_type??'other',device:v?.device??null,body_part:v?.body_part??null,strike_count:v?.strike_count??null,intensity:v?.intensity??null,ban_days:v?.ban_days??null}
}
export function punishmentSummary(v:PunishmentParameters,ru:boolean):string {
  if(v.punishment_type==='physical')return `${ru?'Физическое':'Physical'} · ${v.device} · ${v.body_part} · ${v.strike_count} ${ru?'ударов':'strikes'} · ${ru?'сила':'intensity'} ${v.intensity}/10`
  if(v.punishment_type==='ban')return `${ru?'Запрет':'Ban'} · ${v.ban_days} ${ru?'дн.':'days'}`
  return ru?'Другое':'Other'
}
