/** Dates belong to the viewer's timezone, not the assignment's local_day. */
export function dayKey(value:Date|string,zone:string):string {
 return new Intl.DateTimeFormat('en-CA',{timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(value))
}
export function dayAgenda<T extends {due_at:string;status:string;can_review:boolean}>(rows:T[],zone:string,now=new Date()) {
 const today=dayKey(now,zone)
 const ordered=[...rows].sort((a,b)=>a.due_at.localeCompare(b.due_at))
 return {today:ordered.filter(o=>dayKey(o.due_at,zone)===today&&o.status!=='cancelled'),reviews:ordered.filter(o=>o.can_review&&o.status==='submitted'),upcoming:ordered.filter(o=>o.status==='scheduled'&&dayKey(o.due_at,zone)>today).slice(0,4)}
}
