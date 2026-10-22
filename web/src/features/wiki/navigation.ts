import {ref} from 'vue'
/** Component-owned promise: no browser confirm, persisted drafts or shared global state. */
export function useWikiLeaveGuard(dirty:()=>boolean,busy:()=>boolean){
 const open=ref(false)
 let resolve:((value:boolean)=>void)|null=null
 function canLeave():Promise<boolean>{if(busy())return Promise.resolve(false);if(!dirty())return Promise.resolve(true);if(resolve)return Promise.resolve(false);open.value=true;return new Promise<boolean>(done=>{resolve=done})}
 function decide(value:boolean){const done=resolve;resolve=null;open.value=false;done?.(value)}
 return {open,canLeave,decide}
}
