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
 val ruleHistory:List<RuleTemplate> = emptyList()
)

suspend fun Api.workspace():WorkspaceState = WorkspaceState(relations(),participants(),sessions(),forms(),formInvitations(),formResults(),rules(),ruleAssignments())
