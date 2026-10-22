package org.vowen.app

import androidx.compose.foundation.Image
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.CancellationException

fun wikiLocalThumbnail(path:String):Boolean =
 Regex("^/references/[A-Za-z0-9_./-]+\\.(png|jpe?g|webp|avif)$").matches(path)&&".." !in path.split('/')

@Composable internal fun WikiThumbnail(api:WikiApi,path:String?,modifier:Modifier=Modifier){
 var bitmap by remember(path){mutableStateOf<ImageBitmap?>(null)}
 LaunchedEffect(path){if(path!=null&&wikiLocalThumbnail(path))try{
  bitmap=withContext(Dispatchers.IO){
   val bytes=api.thumbnail(path)
   val bounds=android.graphics.BitmapFactory.Options().apply{inJustDecodeBounds=true}
   android.graphics.BitmapFactory.decodeByteArray(bytes,0,bytes.size,bounds)
   require(bounds.outWidth in 1..16000&&bounds.outHeight in 1..16000)
   var sample=1;while(maxOf(bounds.outWidth,bounds.outHeight)/sample>1024)sample*=2
   android.graphics.BitmapFactory.decodeByteArray(bytes,0,bytes.size,android.graphics.BitmapFactory.Options().apply{inSampleSize=sample})?.asImageBitmap()
  }
 }catch(e:CancellationException){throw e}catch(_:Exception){bitmap=null}}
 bitmap?.let{Image(it,null,modifier,contentScale=ContentScale.Fit)}
}
