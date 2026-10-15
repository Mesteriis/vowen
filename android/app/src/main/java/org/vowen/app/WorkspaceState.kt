package org.vowen.app

data class WorkspaceState(
 val relations:List<Relation> = emptyList(),
 val participants:List<Participant> = emptyList(),
 val sessions:List<DeviceSession> = emptyList(),
 val forms:List<FormTemplate> = emptyList(),
 val formInvitations:List<FormAccess> = emptyList(),
 val formResults:List<FormResult> = emptyList(),
 val rules:List<RuleTemplate> = emptyList(),
 val ruleAssignments:List<RuleAssignment> = emptyList(),
 val ruleHistory:List<RuleTemplate> = emptyList(),
 val rituals:List<RitualTemplate> = emptyList(),
 val ritualAssignments:List<RitualAssignment> = emptyList(),
 val ritualOccurrences:List<RitualOccurrence> = emptyList(),
 val ritualNotices:List<RitualNotice> = emptyList(),
 val ritualHistory:List<RitualTemplate> = emptyList()
)

suspend fun Api.workspace():WorkspaceState = WorkspaceState(relations(),participants(),sessions(),forms(),formInvitations(),formResults(),rules(),ruleAssignments(),rituals=rituals(),ritualAssignments=ritualAssignments(),ritualOccurrences=ritualOccurrences(),ritualNotices=ritualNotices())
