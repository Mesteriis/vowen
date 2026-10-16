import {expect,it} from 'vitest'
import {dayAgenda,dayKey} from '../src/features/workspace/day'
const row=(id:string,due_at:string,status='scheduled',can_review=false)=>({id,due_at,status,can_review})
it('uses the viewer timezone across midnight and DST, not an assignment day',()=>{
 expect(dayKey('2026-10-16T23:30:00Z','Europe/Madrid')).toBe('2026-10-17')
 expect(dayKey('2026-10-25T01:30:00Z','Europe/Madrid')).toBe('2026-10-25')
})
it('keeps historical review backlog out of today and tomorrow out of today',()=>{
 const result=dayAgenda([row('old','2026-10-15T12:00:00Z','submitted',true),row('today','2026-10-16T12:00:00Z'),row('tomorrow','2026-10-17T12:00:00Z'),row('cancelled','2026-10-16T13:00:00Z','cancelled')],'UTC',new Date('2026-10-16T16:00:00Z'))
 expect(result.today.map(o=>o.id)).toEqual(['today'])
 expect(result.reviews.map(o=>o.id)).toEqual(['old'])
 expect(result.upcoming.map(o=>o.id)).toEqual(['tomorrow'])
})
