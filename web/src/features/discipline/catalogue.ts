import type {components} from '../../shared/api'
type Template=components['schemas']['PunishmentTemplateView']
/** Plain text snapshot kept by an immutable rule version; no assignment intensity. */
export function templateRuleText(item:Template):string {
  const parameters=item.punishment_type==='physical'?`${item.device} · ${item.body_part} · ${item.strike_count}`:item.punishment_type==='ban'?`${item.ban_days} дн.`:''
  return [item.title,item.description,parameters,item.conditions].filter(Boolean).join('\n')
}
