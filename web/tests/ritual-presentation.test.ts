import {expect,it} from 'vitest'
import {scheduleSummary,scheduleGroup} from '../src/features/rituals/presentation'
it('shows selected weekdays and local time without converting to the viewer timezone',()=>{
 expect(scheduleSummary({kind:'weekly',timezone:'Europe/Madrid',start_date:'2026-10-16',hour:8,window_hours:24,minute:5,weekdays:[0,2,4]},true)).toBe('Пн Ср Пт · 08:05')
 expect(scheduleSummary({kind:'once',timezone:'UTC',start_date:'2026-10-18',hour:21,window_hours:24,minute:0},false)).toBe('2026-10-18 · 21:00')
 expect(scheduleGroup('weekly',true)).toBe('По дням недели')
})
