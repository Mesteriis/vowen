import {describe,it,expect} from 'vitest'
import {pointAt,hitsStroke} from '../src/features/journal/ink'
describe('journal page coordinates',()=>{
 it('normalizes ink independently of viewport and clamps out of bounds',()=>{expect(pointAt(50,70,100,140,.6)).toEqual(pointAt(500,700,1000,1400,.6));expect(pointAt(-1,200,100,140,2)).toEqual({x:0,y:1,p:1})})
 it('eraser hits between sparse vertices without erasing distant lines',()=>{const stroke={color:'ivory' as const,width:.003,points:[{x:.1,y:.1,p:.5},{x:.9,y:.1,p:.5}]};expect(hitsStroke(stroke,{x:.5,y:.105,p:.5})).toBe(true);expect(hitsStroke(stroke,{x:.5,y:.4,p:.5})).toBe(false)})
})
