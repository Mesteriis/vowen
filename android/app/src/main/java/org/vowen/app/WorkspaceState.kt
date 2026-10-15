package org.vowen.app

data class WorkspaceState(
 val relations:List<Relation> = emptyList(),
 val participants:List<Participant> = emptyList(),
 val sessions:List<DeviceSession> = emptyList()
)

suspend fun Api.workspace():WorkspaceState = WorkspaceState(relations(),participants(),sessions())
