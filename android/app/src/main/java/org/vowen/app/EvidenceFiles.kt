package org.vowen.app

import java.io.ByteArrayOutputStream
import java.io.InputStream

/** Bounded read before base64 encoding. Source URI/name is never persisted or sent. */
internal fun readEvidenceBytes(input:InputStream):ByteArray {
 val result=ByteArrayOutputStream()
 val buffer=ByteArray(8192)
 while(true){
  val count=input.read(buffer)
  if(count<0)break
  require(result.size()+count<=8*1024*1024){"Maximum file size is 8 MiB"}
  result.write(buffer,0,count)
 }
 return result.toByteArray()
}
