import {expect,it} from 'vitest'
import {parameters,punishmentSummary} from '../src/features/discipline/parameters'
it('keeps legacy records compatible and retains parameters for exact review',()=>{
 expect(parameters().punishment_type).toBe('other')
 const physical={punishment_type:'physical' as const,device:'Рука',body_part:'Руки',strike_count:1,intensity:2}
 expect(parameters(physical)).toEqual({...physical,ban_days:null})
 expect(punishmentSummary(physical,true)).toContain('1 ударов · сила 2/10')
 expect(punishmentSummary({punishment_type:'ban',ban_days:3},true)).toBe('Запрет · 3 дн.')
})
