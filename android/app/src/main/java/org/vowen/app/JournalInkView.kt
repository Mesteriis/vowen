package org.vowen.app

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.view.MotionEvent
import android.view.View
import kotlin.math.hypot
import kotlin.math.round

/** One normalized 5:7 page. Finger input is opt-in; stylus never starts a scroll gesture. */
class JournalInkView(context:Context):View(context) {
 var document:InkDocument?=null
 var tool="pen"
 var nib=.003
 var finger=false
 var readOnly=false
 var changed:((InkDocument)->Unit)?=null
 var limit:(()->Unit)?=null
 private var points=mutableListOf<InkPoint>()
 private var erased=mutableSetOf<Int>()
 private var pointer=-1
 private val paint=Paint(Paint.ANTI_ALIAS_FLAG).apply{strokeCap=Paint.Cap.ROUND;strokeJoin=Paint.Join.ROUND}
 private fun color(name:String?)=Color.parseColor(when(name){"gold"->"#d6b579";"rose"->"#d89c90";else->"#ede9df"})
 override fun onDraw(canvas:Canvas){
  super.onDraw(canvas)
  paint.color=Color.parseColor("#20d6b579");paint.strokeWidth=resources.displayMetrics.density
  var y=32*resources.displayMetrics.density
  while(y<height){canvas.drawLine(0f,y,width.toFloat(),y,paint);y+=32*resources.displayMetrics.density}
  fun draw(stroke:InkStroke){paint.color=color(stroke.color);val pts=stroke.points
   if(pts.size==1){paint.style=Paint.Style.FILL;canvas.drawCircle((pts[0].x*width).toFloat(),(pts[0].y*height).toFloat(),((stroke.width?:.003)*width/2).toFloat(),paint)}
   pts.zipWithNext().forEach{(a,b)->paint.strokeWidth=((stroke.width?:.003)*width*(.55+((a.p?:.5)+(b.p?:.5))*.45)).toFloat();canvas.drawLine((a.x*width).toFloat(),(a.y*height).toFloat(),(b.x*width).toFloat(),(b.y*height).toFloat(),paint)}
  }
  document?.strokes.orEmpty().forEachIndexed{i,s->if(i !in erased)draw(s)}
  if(points.isNotEmpty())draw(InkStroke(color="ivory",width=nib,points=points))
 }
 private fun point(x:Float,y:Float,p:Float)=InkPoint(x=round((x/width.coerceAtLeast(1)).toDouble().coerceIn(0.0,1.0)*10000)/10000,y=round((y/height.coerceAtLeast(1)).toDouble().coerceIn(0.0,1.0)*10000)/10000,p=round(p.toDouble().coerceIn(0.0,1.0)*100)/100)
 private fun sample(p:InkPoint){
  if(tool=="eraser")document?.strokes.orEmpty().forEachIndexed{i,s->
   val hit=s.points.any{hypot(it.x-p.x,(it.y-p.y)*1.4)<.025}||s.points.zipWithNext().any{(a,b)->val dx=b.x-a.x;val dy=(b.y-a.y)*1.4;val px=p.x-a.x;val py=(p.y-a.y)*1.4;val t=((px*dx+py*dy)/(dx*dx+dy*dy).coerceAtLeast(.0000001)).coerceIn(0.0,1.0);hypot(px-t*dx,py-t*dy)<.025}
   if(hit)erased.add(i)
  } else if(points.size<1500)points.add(p)
 }
 override fun onTouchEvent(event:MotionEvent):Boolean {
  if(readOnly)return false
  val index=event.actionIndex
  if(event.actionMasked==MotionEvent.ACTION_DOWN){
   if(event.getToolType(index)==MotionEvent.TOOL_TYPE_FINGER&&!finger)return false
   pointer=event.getPointerId(index);parent?.requestDisallowInterceptTouchEvent(true);points=mutableListOf();erased=mutableSetOf();sample(point(event.x,event.y,event.pressure));invalidate();return true
  }
  val i=event.findPointerIndex(pointer)
  if(pointer<0||i<0)return false
  when(event.actionMasked){
   MotionEvent.ACTION_MOVE->{for(h in 0 until event.historySize)sample(point(event.getHistoricalX(i,h),event.getHistoricalY(i,h),event.getHistoricalPressure(i,h)));sample(point(event.getX(i),event.getY(i),event.getPressure(i)))}
   MotionEvent.ACTION_UP,MotionEvent.ACTION_POINTER_UP->{if(event.getPointerId(event.actionIndex)!=pointer)return true;val old=document?.strokes.orEmpty();val next=if(tool=="eraser")old.filterIndexed{n,_->n !in erased}else old+InkStroke(color="ivory",width=nib,points=points.toList());if(next.size<=500&&next.sumOf{it.points.size}<=5000)changed?.invoke(InkDocument(version=1,strokes=next))else limit?.invoke();points.clear();erased.clear();pointer=-1;parent?.requestDisallowInterceptTouchEvent(false);performClick()}
   MotionEvent.ACTION_CANCEL->{points.clear();erased.clear();pointer=-1;parent?.requestDisallowInterceptTouchEvent(false)}
  };invalidate();return true
 }
 override fun performClick():Boolean{super.performClick();return true}
}
