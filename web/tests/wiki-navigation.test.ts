import {it,expect} from 'vitest'
import {useWikiLeaveGuard} from '../src/features/wiki/navigation'
it('waits for a local discard choice and keeps the editor on cancellation',async()=>{
 const guard=useWikiLeaveGuard(()=>true,()=>false)
 let resolved=false
 const pending=guard.canLeave().then(value=>{resolved=true;return value})
 await Promise.resolve();expect(resolved).toBe(false);expect(guard.open.value).toBe(true)
 guard.decide(false);expect(await pending).toBe(false);expect(guard.open.value).toBe(false)
 const accepted=guard.canLeave();guard.decide(true);expect(await accepted).toBe(true)
})
it('does not open a prompt for clean state and blocks during save',async()=>{
 const guard=useWikiLeaveGuard(()=>false,()=>false);expect(await guard.canLeave()).toBe(true)
 const busy=useWikiLeaveGuard(()=>true,()=>true);expect(await busy.canLeave()).toBe(false);expect(busy.open.value).toBe(false)
})
