package org.vowen.app

import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId

fun homeDay(instant:String,zone:String):LocalDate=Instant.parse(instant).atZone(ZoneId.of(zone)).toLocalDate()
fun homeMatches(issuer:String,recipient:String,reviewers:List<String>,member:String,relation:Relation?):Boolean {
 if(relation==null)return true
 val partner=if(relation.dominant_user_id==member)relation.submissive_user_id else if(relation.submissive_user_id==member)relation.dominant_user_id else return false
 return issuer==relation.dominant_user_id&&recipient==relation.submissive_user_id || recipient==partner&&member in reviewers
}
data class HomeAgenda(val today:List<RitualOccurrence>,val reviews:List<RitualOccurrence>,val upcoming:List<RitualOccurrence>)
fun homeAgenda(member:Member,data:WorkspaceState,relation:Relation?,now:Instant=Instant.now()):HomeAgenda {
 val day=now.atZone(ZoneId.of(member.timezone)).toLocalDate()
 val rows=data.ritualOccurrences.filter{o->data.ritualAssignments.any{a->a.id==o.assignment_id&&homeMatches(a.issuer_id,a.recipient_id,a.reviewer_ids,member.id,relation)}}.sortedBy{it.due_at}
 return HomeAgenda(rows.filter{homeDay(it.due_at,member.timezone)==day&&it.status!="cancelled"},rows.filter{it.can_review&&it.status=="submitted"&&!member.paused},rows.filter{it.status=="scheduled"&&homeDay(it.due_at,member.timezone)>day}.take(4))
}
