package org.vowen.app

data class WorkspaceState(
 val economyRelationId:String? = null,
 val wallet:RelationWallet? = null,
 val shop:List<ShopListing> = emptyList(),
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
 val rewards:List<RewardDefinition> = emptyList(),
 val rewardNotices:List<RewardNotice> = emptyList(),
 val rewardGrants:List<RewardGrant> = emptyList(),
 val ritualHistory:List<RitualTemplate> = emptyList(),
 val discipline:List<DisciplineRecord> = emptyList(),
 val journal:List<JournalEntry> = emptyList(),
 val surveys:List<SurveyPlan> = emptyList(),
 val notificationSettings:NotificationSettings? = null
)

suspend fun Api.workspace():WorkspaceState = WorkspaceState(relations=relations(),participants=participants(),sessions=sessions(),forms=forms(),formInvitations=formInvitations(),formResults=formResults(),rules=rules(),ruleAssignments=ruleAssignments(),rituals=rituals(),ritualAssignments=ritualAssignments(),ritualOccurrences=ritualOccurrences(),ritualNotices=ritualNotices(),rewards=rewards(),rewardGrants=rewardGrants(),rewardNotices=rewardNotices(),discipline=discipline(),journal=journal(),surveys=surveys(),notificationSettings=notificationSettings())
