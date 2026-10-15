package org.vowen.app

import org.junit.Assert.*
import org.junit.Test

class InstanceSessionTest {
 @Test fun changingInstanceDeletesTokensAndCannotSendOldBearer() {
  val state = InstanceSession()
  state.select("https://first.example")
  state.accessToken = "old-access"
  state.select("https://second.example/")
  assertNull(state.accessToken)
  assertEquals("https://second.example", state.origin)
 }
 @Test fun invalidOriginsAreRejected() {
  for (origin in listOf("http://host.example", "https://user:pass@host.example", "https://host.example/path", "https://host.example?token=x", "https://host.example#fragment")) {
   try { InstanceSession().select(origin); fail(origin) } catch (_: IllegalArgumentException) { }
  }
 }
}
