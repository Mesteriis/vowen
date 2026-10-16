import type {components} from '../../shared/api'
type Schedule=components['schemas']['Schedule']
export function scheduleSummary(s:Schedule,ru:boolean):string {
 const days=ru?['Пн','Вт','Ср','Чт','Пт','Сб','Вс']:['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
 const cadence=s.kind==='daily'?(ru?'Ежедневно':'Daily'):s.kind==='weekly'?(s.weekdays??[]).map(d=>days[d]).join(' '):s.start_date
 return `${cadence} · ${String(s.hour).padStart(2,'0')}:${String(s.minute).padStart(2,'0')}`
}
export function scheduleGroup(kind:string,ru:boolean):string {return kind==='daily'?(ru?'Ежедневно':'Daily'):kind==='weekly'?(ru?'По дням недели':'Weekly'):(ru?'Однократно':'Once')}
