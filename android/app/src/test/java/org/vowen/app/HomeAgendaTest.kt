package org.vowen.app

import org.junit.Assert.*
import org.junit.Test
import java.time.LocalDate

class HomeAgendaTest {
 @Test fun viewerTimezoneAndDst(){
  assertEquals(LocalDate.parse("2026-10-17"),homeDay("2026-10-16T23:30:00Z","Europe/Madrid"))
  assertEquals(LocalDate.parse("2026-10-25"),homeDay("2026-10-25T01:30:00Z","Europe/Madrid"))
 }
 @Test fun switchContextsAreDirected(){
  val r=Relation("fixture",listOf("a","b"),"a","ab","v",listOf("rituals.assign"),"active","b",1)
  assertTrue(homeMatches("a","b",listOf("a"),"a",r))
  assertFalse(homeMatches("b","a",listOf("b"),"a",r))
  assertFalse(homeMatches("b","c",emptyList(),"a",r))
  assertTrue(homeMatches("c","b",listOf("a"),"a",r))
 }
}
