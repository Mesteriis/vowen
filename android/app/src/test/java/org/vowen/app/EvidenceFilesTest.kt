package org.vowen.app

import java.io.ByteArrayInputStream
import org.junit.Assert.*
import org.junit.Test

class EvidenceFilesTest {
 @Test fun pickerReadRejectsOversizeStreamsBeforeEncoding() {
  val small=byteArrayOf(1,2,3)
  assertArrayEquals(small,readEvidenceBytes(ByteArrayInputStream(small)))
  try{readEvidenceBytes(ByteArrayInputStream(ByteArray(8*1024*1024+1)));fail("Oversized content accepted")}catch(expected:IllegalArgumentException){assertTrue(expected.message!!.contains("8 MiB"))}
 }
}
