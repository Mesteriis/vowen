import type {components} from '../../shared/api'
export type Ink=components['schemas']['InkDocument']
export type Stroke=components['schemas']['InkStroke']
export type Point=components['schemas']['InkPoint']
export const inkColors={ivory:'#ede9df',gold:'#d6b579',rose:'#d89c90'}
export function emptyInk():Ink{return {version:1,strokes:[]}}
export function pointAt(x:number,y:number,width:number,height:number,pressure:number):Point{
 const clamp=(v:number)=>Math.max(0,Math.min(1,v))
 return {x:Math.round(clamp(x/width)*10000)/10000,y:Math.round(clamp(y/height)*10000)/10000,p:Math.round(clamp(pressure||.5)*100)/100}
}
export function hitsStroke(s:Stroke,p:Point,radius=.018):boolean{
 // Test segment distances in page coordinates, not only sampled vertices.
 const distance=(a:Point,b:Point)=>{const dx=b.x-a.x,dy=(b.y-a.y)*1.4,px=p.x-a.x,py=(p.y-a.y)*1.4;const t=Math.max(0,Math.min(1,(px*dx+py*dy)/(dx*dx+dy*dy||1)));return Math.hypot(px-t*dx,py-t*dy)}
 return s.points.length===1?distance(s.points[0]!,s.points[0]!)<radius:s.points.some((b,i)=>i>0&&distance(s.points[i-1]!,b)<radius)
}
