# Route CoPilot v0.1.96

Trích từ route records TypeScript. Cột auth và role kế thừa meta của route cha nếu có. Kiểm tra quyền tại component, điều kiện feature/license và quyền API được nêu theo nhóm trong [bảng chức năng](feature-parity.md).

## Core (172 records)

| Route | Name / redirect | Auth meta | Role meta | View |
| --- | --- | --- | --- | --- |
| `/` | `redirect` | — | — | — |
| `/:pathMatch(.*)*` | `NotFound` | — | — | `@/views/NotFound.vue` |
| `/active-response` | `ActiveResponse` | `true` | `All` | `@/views/ActiveResponse.vue` |
| `/agents` | — | `true` | `All` | — |
| `/agents` | `Agents` | `true` | `All` | `@/views/agents/Agents.vue` |
| `/agents/:id` | `Agent` | `true` | `All` | `@/views/agents/Overview.vue` |
| `/agents/:id/data-store` | `redirect` | `true` | `All` | — |
| `/agents/:id/data-store/:artifactId` | `AgentArtifact` | `true` | `All` | `@/views/agents/AgentArtifact.vue` |
| `/agents/:id/sca` | `redirect` | `true` | `All` | — |
| `/agents/:id/sca/:policyId` | `AgentSca` | `true` | `All` | `@/views/agents/AgentSca.vue` |
| `/agents/:id/sca/:policyId/checks` | `redirect` | `true` | `All` | — |
| `/agents/:id/sca/:policyId/checks/:checkId` | `AgentScaCheck` | `true` | `All` | `@/views/agents/AgentScaCheck.vue` |
| `/agents/:id/vulnerabilities` | `redirect` | `true` | `All` | — |
| `/agents/:id/vulnerabilities/:cve` | `AgentVulnerability` | `true` | `All` | `@/views/agents/AgentVulnerability.vue` |
| `/agents/copilot-actions` | `CopilotActions` | `true` | `All` | `@/views/agents/CopilotActions.vue` |
| `/agents/copilot-actions/:name(.*)` | `CopilotAction` | `true` | `All` | `@/views/agents/CopilotAction.vue` |
| `/agents/detection-rules` | `DetectionRules` | `true` | `All` | `@/views/agents/DetectionRules.vue` |
| `/agents/groups` | `Groups` | `true` | `All` | `@/views/agents/Groups.vue` |
| `/agents/sca-overview` | `ScaOverview` | `true` | `All` | `@/views/agents/ScaOverview.vue` |
| `/agents/sca-policies` | `ScaPolicies` | `true` | `All` | `@/views/agents/ScaPolicies.vue` |
| `/agents/sca-policies/:policyId` | `ScaPolicy` | `true` | `All` | `@/views/agents/ScaPolicy.vue` |
| `/agents/sysmon-config` | `SysmonConfig` | `true` | `All` | `@/views/agents/SysmonConfig.vue` |
| `/agents/vulnerability-overview` | `VulnerabilityOverview` | `true` | `All` | `@/views/agents/VulnerabilityOverview.vue` |
| `/agents/vulnerability-overview/:agentName` | `redirect` | `true` | `All` | — |
| `/agents/vulnerability-overview/:agentName/:cve` | `VulnerabilityOverviewItem` | `true` | `All` | `@/views/agents/VulnerabilityOverviewItem.vue` |
| `/ai-analyst` | `AiAnalyst` | `true` | `All` | `@/views/aiAnalyst/AiAnalyst.vue` |
| `/ai-analyst/feedback` | `redirect` | — | — | — |
| `/ai-analyst/feedback/:id` | `AiAnalystFeedbackReview` | `true` | `All` | `@/views/aiAnalyst/AiAnalystFeedbackReview.vue` |
| `/ai-analyst/iocs` | `redirect` | — | — | — |
| `/ai-analyst/iocs/:id` | `AiAnalystIoc` | `true` | `All` | `@/views/aiAnalyst/AiAnalystIoc.vue` |
| `/ai-analyst/jobs` | `redirect` | — | — | — |
| `/ai-analyst/jobs/:id` | `AiAnalystJob` | `true` | `All` | `@/views/aiAnalyst/AiAnalystJob.vue` |
| `/ai-analyst/reports` | `redirect` | — | — | — |
| `/ai-analyst/reports/:id` | `AiAnalystReport` | `true` | `All` | `@/views/aiAnalyst/AiAnalystReport.vue` |
| `/alerts` | `redirect` | `true` | `All` | — |
| `/alerts/atomic-red-team` | `Alerts-AtomicRedTeam` | `true` | `All` | `@/views/alerts/AtomicRedTeam.vue` |
| `/alerts/atomic-red-team/:techniqueId` | `Alerts-AtomicRedTeam-Technique` | `true` | `All` | `@/views/alerts/AtomicRedTeamTechnique.vue` |
| `/alerts/mitre` | `Alerts-Mitre` | `true` | `All` | `@/views/alerts/Mitre.vue` |
| `/alerts/mitre/:techniqueId` | `Alerts-Mitre-Technique` | `true` | `All` | `@/views/alerts/MitreTechniqueAlert.vue` |
| `/alerts/mitre/:techniqueId/events` | `redirect` | `true` | `All` | — |
| `/alerts/mitre/:techniqueId/events/:eventId` | `Alerts-Mitre-Technique-Event` | `true` | `All` | `@/views/alerts/MitreTechniqueEvent.vue` |
| `/alerts/mitre/groups` | `redirect` | `true` | `All` | — |
| `/alerts/mitre/groups/:groupId` | `Alerts-Mitre-Group` | `true` | `All` | `@/views/alerts/MitreGroup.vue` |
| `/alerts/mitre/mitigations` | `redirect` | `true` | `All` | — |
| `/alerts/mitre/mitigations/:mitigationId` | `Alerts-Mitre-Mitigation` | `true` | `All` | `@/views/alerts/MitreMitigation.vue` |
| `/alerts/mitre/software` | `redirect` | `true` | `All` | — |
| `/alerts/mitre/software/:softwareId` | `Alerts-Mitre-Software` | `true` | `All` | `@/views/alerts/MitreSoftware.vue` |
| `/alerts/mitre/tactics` | `redirect` | `true` | `All` | — |
| `/alerts/mitre/tactics/:tacticId` | `Alerts-Mitre-Tactic` | `true` | `All` | `@/views/alerts/MitreTactic.vue` |
| `/alerts/mitre/techniques` | `redirect` | `true` | `All` | — |
| `/alerts/mitre/techniques/:techniqueId` | `Alerts-Mitre-Techniques` | `true` | `All` | `@/views/alerts/MitreTechniques.vue` |
| `/alerts/siem` | `Alerts-SIEM` | `true` | `All` | `@/views/alerts/AlertsGraylog.vue` |
| `/alerts/siem/:indexName` | `Alerts-SIEM-Summary` | `true` | `All` | `@/views/alerts/AlertsSiemSummary.vue` |
| `/alerts/siem/alert` | `redirect` | `true` | `All` | — |
| `/alerts/siem/alert/:indexName` | `redirect` | `true` | `All` | — |
| `/alerts/siem/alert/:indexName/:alertId` | `Alerts-SIEM-Alert` | `true` | `All` | `@/views/alerts/AlertsSiemAlert.vue` |
| `/artifacts` | `Artifacts` | `true` | `All` | `@/views/Artifacts.vue` |
| `/audit` | `Audit` | `true` | `All` | `@/views/Audit.vue` |
| `/audit/:id` | `AuditEntry` | `true` | `All` | `@/views/AuditEntry.vue` |
| `/cloud-security-assessment` | `CloudSecurityAssessment` | `true` | `All` | `@/views/CloudSecurityAssessment.vue` |
| `/connectors` | `Connectors` | `true` | `All` | `@/views/Connectors.vue` |
| `/copilot-searches` | `CopilotSearches` | `true` | `All` | `@/views/agents/CopilotSearches.vue` |
| `/copilot-searches/:ruleId` | `CopilotSearchRule` | `true` | `All` | `@/views/agents/CopilotSearchRule.vue` |
| `/copilot-searches/editor` | `CopilotSearchEditor` | `true` | `All` | `@/views/agents/CopilotSearchEditor.vue` |
| `/customer-portal` | `CustomerPortal` | `true` | `All` | `@/views/customers/CustomerPortal.vue` |
| `/customers` | `Customers` | `true` | `All` | `@/views/customers/Customers.vue` |
| `/customers/:code` | `Customer` | `true` | `All` | `@/views/customers/Customer.vue` |
| `/customers/:code/healthcheck` | `redirect` | — | — | — |
| `/customers/:code/healthcheck/:source` | `redirect` | — | — | — |
| `/customers/:code/healthcheck/:source/:agentId` | `CustomerHealthcheckAgent` | `true` | `All` | `@/views/customers/CustomerHealthcheckAgent.vue` |
| `/customers/new` | `CustomerNew` | `true` | `All` | `@/views/customers/CustomerNew.vue` |
| `/dashboards` | `Dashboards` | `true` | `All` | `@/views/dashboards/Dashboards.vue` |
| `/dashboards/:id` | `DashboardView` | `true` | `All` | `@/views/dashboards/DashboardView.vue` |
| `/detection-catalog` | `DetectionCatalog` | `true` | `All` | `@/views/detectionCatalog/DetectionCatalog.vue` |
| `/detection-catalog/compliance` | `redirect` | — | — | — |
| `/detection-catalog/compliance/:framework` | `redirect` | — | — | — |
| `/detection-catalog/compliance/:framework/:control` | `DetectionCatalogComplianceGroup` | `true` | `All` | `@/views/detectionCatalog/DetectionCatalogComplianceGroup.vue` |
| `/detection-catalog/coverage-gaps` | `redirect` | — | — | — |
| `/detection-catalog/coverage-gaps/:techniqueId` | `DetectionCatalogCoverageGap` | `true` | `All` | `@/views/detectionCatalog/DetectionCatalogCoverageGap.vue` |
| `/detection-catalog/detections` | `redirect` | — | — | — |
| `/detection-catalog/detections/:id` | `DetectionCatalogDetection` | `true` | `All` | `@/views/detectionCatalog/DetectionCatalogDetection.vue` |
| `/detection-catalog/stories` | `redirect` | — | — | — |
| `/detection-catalog/stories/:name` | `DetectionCatalogStory` | `true` | `All` | `@/views/detectionCatalog/DetectionCatalogStory.vue` |
| `/detection-catalog/wazuh-rules` | `redirect` | — | — | — |
| `/detection-catalog/wazuh-rules/:id` | `DetectionCatalogWazuhRule` | `true` | `All` | `@/views/detectionCatalog/DetectionCatalogWazuhRule.vue` |
| `/event-search` | `EventSearch` | `true` | `All` | `@/views/events/EventSearch.vue` |
| `/event-search/:customerCode` | `redirect` | — | — | — |
| `/event-search/:customerCode/:sourceName` | `redirect` | — | — | — |
| `/event-search/:customerCode/:sourceName/:indexName` | `redirect` | — | — | — |
| `/event-search/:customerCode/:sourceName/:indexName/:eventId` | `EventSearch-Event` | `true` | `All` | `@/views/events/Event.vue` |
| `/external-services` | `redirect` | `true` | `All` | — |
| `/external-services/network-connectors` | `ExternalServices-NetworkConnectors` | `true` | `All` | `@/views/externalServices/NetworkConnectors.vue` |
| `/external-services/network-connectors/:id` | `ExternalServices-NetworkConnector` | `true` | `All` | `@/views/externalServices/NetworkConnector.vue` |
| `/external-services/shuffle-app-auth` | `ExternalServices-ShuffleAppAuth` | `true` | `All` | `@/views/externalServices/ShuffleAppAuth.vue` |
| `/external-services/third-party-integrations` | `ExternalServices-ThirdPartyIntegrations` | `true` | `All` | `@/views/externalServices/ThirdPartyIntegrations.vue` |
| `/external-services/third-party-integrations/:id` | `ExternalServices-ThirdPartyIntegration` | `true` | `All` | `@/views/externalServices/ThirdPartyIntegration.vue` |
| `/file-analysis` | `FileAnalysis` | `true` | `[Admin, Analyst]` | `@/views/NewFileAnalysis.vue` |
| `/file-analysis/:jobId` | `FileAnalysisDetails` | `true` | `[Admin, Analyst]` | `@/views/FileAnalysisDetails.vue` |
| `/github-audit` | `GitHubAudit` | `true` | `All` | `@/views/GitHubAuditOverview.vue` |
| `/github-audit/:configId` | `GitHubAuditConfig` | `true` | `All` | `@/views/GitHubAuditConfig.vue` |
| `/github-audit/new` | `GitHubAuditConfigNew` | `true` | `All` | `@/views/GitHubAuditConfigNew.vue` |
| `/graylog` | `redirect` | `true` | `All` | — |
| `/graylog/management` | `Graylog-Management` | `true` | `All` | `@/views/graylog/Management.vue` |
| `/graylog/metrics` | `Graylog-Metrics` | `true` | `All` | `@/views/graylog/Metrics.vue` |
| `/graylog/pipelines` | `Graylog-Pipelines` | `true` | `All` | `@/views/graylog/Pipelines.vue` |
| `/healthcheck` | `redirect` | `true` | `All` | — |
| `/healthcheck/alerts` | `Healthcheck` | `true` | `All` | `@/views/Healthcheck.vue` |
| `/healthcheck/metrics` | `Metrics` | `true` | `All` | `@/views/Metrics.vue` |
| `/incident-management` | `redirect` | `true` | `All` | — |
| `/incident-management/alerts` | `IncidentManagement-Alerts` | `true` | `All` | `@/views/incidentManagement/Alerts.vue` |
| `/incident-management/alerts/:alertId/assets` | `redirect` | `true` | `All` | — |
| `/incident-management/alerts/:alertId/assets/:assetId` | `IncidentManagement-AlertAsset` | `true` | `All` | `@/views/incidentManagement/AlertLinkedAsset.vue` |
| `/incident-management/alerts/:alertId/iocs` | `redirect` | `true` | `All` | — |
| `/incident-management/alerts/:alertId/iocs/:iocId` | `IncidentManagement-AlertIoc` | `true` | `All` | `@/views/incidentManagement/AlertLinkedIoc.vue` |
| `/incident-management/alerts/:alertId/iocs/new` | `IncidentManagement-AlertIocNew` | `true` | `All` | `@/views/incidentManagement/AlertLinkedIocNew.vue` |
| `/incident-management/alerts/:id` | `IncidentManagement-Alert` | `true` | `All` | `@/views/incidentManagement/Alert.vue` |
| `/incident-management/case-templates` | `IncidentManagement-CaseTemplates` | `true` | `[Admin, Analyst]` | `@/views/incidentManagement/CaseTemplates.vue` |
| `/incident-management/case-templates/:id` | `IncidentManagement-CaseTemplate` | `true` | `[Admin, Analyst]` | `@/views/incidentManagement/CaseTemplate.vue` |
| `/incident-management/case-templates/library/:key` | `IncidentManagement-CaseTemplateLibraryEntry` | `true` | `[Admin, Analyst]` | `@/views/incidentManagement/CaseTemplateLibraryEntry.vue` |
| `/incident-management/case-templates/new` | `IncidentManagement-CaseTemplateNew` | `true` | `[Admin, Analyst]` | `@/views/incidentManagement/CaseTemplateNew.vue` |
| `/incident-management/cases` | `IncidentManagement-Cases` | `true` | `All` | `@/views/incidentManagement/Cases.vue` |
| `/incident-management/cases/:id` | `IncidentManagement-Case` | `true` | `All` | `@/views/incidentManagement/Case.vue` |
| `/incident-management/cases/new` | `IncidentManagement-CaseNew` | `true` | `All` | `@/views/incidentManagement/CaseNew.vue` |
| `/incident-management/exclusion-rules/:id` | `IncidentManagement-ExclusionRule` | `true` | `All` | `@/views/incidentManagement/ExclusionRule.vue` |
| `/incident-management/exclusion-rules/new` | `IncidentManagement-ExclusionRuleNew` | `true` | `All` | `@/views/incidentManagement/ExclusionRuleNew.vue` |
| `/incident-management/sigma` | `IncidentManagement-Sigma` | `true` | `All` | `@/views/incidentManagement/Sigma.vue` |
| `/incident-management/sources` | `IncidentManagement-Sources` | `true` | `All` | `@/views/incidentManagement/Sources.vue` |
| `/incident-management/sources/:source` | `IncidentManagement-Source` | `true` | `All` | `@/views/incidentManagement/ConfiguredSource.vue` |
| `/incident-management/sources/new` | `IncidentManagement-SourceNew` | `true` | `All` | `@/views/incidentManagement/ConfiguredSourceNew.vue` |
| `/indices` | `redirect` | `true` | `All` | — |
| `/indices/management` | `Indices` | `true` | `All` | `@/views/Indices.vue` |
| `/indices/snapshots` | `Snapshots` | `true` | `All` | `@/views/Snapshots.vue` |
| `/internal-notifications` | `InternalNotifications` | `true` | `Admin` | `@/views/notification/InternalNotificationRoutes.vue` |
| `/internal-notifications/:id` | `InternalNotification` | `true` | `Admin` | `@/views/notification/InternalNotificationRoute.vue` |
| `/internal-notifications/new` | `InternalNotificationNew` | `true` | `Admin` | `@/views/notification/InternalNotificationRouteNew.vue` |
| `/license` | — | `true` | `All` | — |
| `/license` | `License` | `true` | `All` | `@/views/license/License.vue` |
| `/license/cancel` | `LicenseCancel` | `true` | `All` | `@/views/license/Cancel.vue` |
| `/license/success` | `LicenseSuccess` | `true` | `All` | `@/views/license/Success.vue` |
| `/login` | `Login` | — | — | — |
| `/logout` | `Logout` | — | — | — |
| `/logs` | `Logs` | `true` | `All` | `@/views/Logs.vue` |
| `/message-templates` | `MessageTemplates` | `true` | `Admin` | `@/views/notification/MessageTemplates.vue` |
| `/message-templates/:id` | `MessageTemplate` | `true` | `Admin` | `@/views/notification/MessageTemplate.vue` |
| `/message-templates/new` | `MessageTemplateNew` | `true` | `Admin` | `@/views/notification/MessageTemplateNew.vue` |
| `/opencti` | `OpenCTI` | — | — | — |
| `/overview` | `Overview` | `true` | `All` | — |
| `/patch-tuesday` | `PatchTuesday` | `true` | `All` | `@/views/agents/PatchTuesdayOverview.vue` |
| `/patch-tuesday/:cycle` | `redirect` | `true` | `All` | — |
| `/patch-tuesday/:cycle/:cve` | `PatchTuesdayItem` | `true` | `All` | `@/views/agents/PatchTuesdayItem.vue` |
| `/profile` | `Profile` | `true` | `All` | `@/views/Profile.vue` |
| `/report-creation` | `redirect` | `true` | `All` | — |
| `/report-creation/general` | `ReportCreation` | `true` | `All` | `@/views/ReportCreation.vue` |
| `/report-creation/sca-reports` | `SCAReports` | `true` | `All` | `@/components/sca/SCAReports.vue` |
| `/report-creation/vulnerability-reports` | `VulnerabilityReports` | `true` | `All` | `@/components/vulnerabilities/VulnerabilityReports.vue` |
| `/scheduler` | `Scheduler` | `true` | `All` | `@/views/scheduler/Scheduler.vue` |
| `/scheduler/:id` | `SchedulerJob` | `true` | `All` | `@/views/scheduler/SchedulerJob.vue` |
| `/soc-management` | `SocManagement` | `true` | `[Admin, Analyst]` | `@/views/SocManagement.vue` |
| `/sso-callback` | `SSOCallback` | — | — | — |
| `/sso-config` | `SSOConfig` | `true` | `All` | `@/views/SSOConfig.vue` |
| `/stack-provisioning` | `StackProvisioning` | `true` | `All` | `@/views/StackProvisioning.vue` |
| `/threat-intel` | `ThreatIntel` | `true` | `[Admin, Analyst]` | `@/views/ThreatIntel.vue` |
| `/uba` | `Uba` | `true` | `[Admin, Analyst]` | `@/views/Uba.vue` |
| `/uba/:customerCode` | `redirect` | — | — | — |
| `/uba/:customerCode/:tab(alerts\|entities)` | `redirect` | — | — | — |
| `/uba/:customerCode/alerts/:alertId` | `UbaAlert` | `true` | `[Admin, Analyst]` | `@/views/UbaAlert.vue` |
| `/uba/:customerCode/entities/:entityKey` | `UbaEntity` | `true` | `[Admin, Analyst]` | `@/views/UbaEntity.vue` |
| `/users` | `Users` | `true` | `All` | `@/views/users/Users.vue` |
| `/users/:id` | `UserView` | `true` | `All` | `@/views/users/UserView.vue` |
| `/users/new` | `UserNew` | `true` | `All` | `@/views/users/UserNew.vue` |
| `/waf` | `Waf` | `true` | `[Admin, Analyst]` | `@/views/Waf.vue` |
| `/web-vulnerability-assessment` | `WebVulnerabilityAssessment` | `true` | `All` | `@/views/WebVulnerabilityAssessment.vue` |

## Customer Portal (22 records)

| Route | Name / redirect | Auth meta | Role meta | View |
| --- | --- | --- | --- | --- |
| `/` | `redirect` | — | — | — |
| `/overview` | `Overview` | `true` | `All` | `@/views/Overview.vue` |
| `/alerts` | — | `true` | `All` | — |
| `/alerts` | `AlertsList` | `true` | `All` | `@/views/Alerts/List.vue` |
| `/alerts/:id` | `AlertDetails` | `true` | `All` | `@/views/Alerts/Details.vue` |
| `/cases` | — | `true` | `All` | — |
| `/cases` | `CasesList` | `true` | `All` | `@/views/Cases/List.vue` |
| `/cases/:id` | `CaseDetails` | `true` | `All` | `@/views/Cases/Details.vue` |
| `/agents` | — | `true` | `All` | — |
| `/agents` | `AgentsList` | `true` | `All` | `@/views/Agents/List.vue` |
| `/agents/:id` | `AgentDetails` | `true` | `All` | `@/views/Agents/Details.vue` |
| `/reports` | — | `true` | `All` | — |
| `/reports` | `ReportsList` | `true` | `All` | `@/views/Reports/List.vue` |
| `/event-search` | `EventSearch` | `true` | `All` | `@/views/EventSearch.vue` |
| `/dashboards` | — | `true` | `All` | — |
| `/dashboards` | `DashboardsList` | `true` | `All` | `@/views/Dashboards/List.vue` |
| `/dashboards/:id` | `DashboardView` | `true` | `All` | `@/views/Dashboards/Overview.vue` |
| `/sla` | `Sla` | `true` | `All` | `@/views/Sla.vue` |
| `/profile` | `Profile` | `true` | `All` | `@/views/Profile.vue` |
| `/login` | `Login` | — | — | — |
| `/logout` | `Logout` | — | — | — |
| `/:pathMatch(.*)*` | `NotFound` | — | — | `@/views/NotFound.vue` |
