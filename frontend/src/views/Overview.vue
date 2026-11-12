<template>
	<div ref="page" class="page @container">
		<!-- Add version banner at the top -->
		<div class="section">
			<VersionUpdateBanner />
		</div>

		<h1 class="font-display mb-4 text-2xl font-semibold">{{ t("tmgs.overview") }}</h1>
		<div class="section overview-controls flex flex-wrap items-center justify-between gap-3">
			<div class="flex items-center gap-3">
				<div class="flex items-center gap-2">
					<span id="overview-scope-label" class="text-secondary text-xs">{{ t("tmgs.filter") }}</span>
					<n-switch
						v-model:value="useGlobalCustomerFilterToggle"
						size="small"
						aria-labelledby="overview-scope-label"
					/>
				</div>
			</div>
			<div class="hidden flex-wrap items-center gap-2 @[1100px]:flex">
				<StackProvisioningButton size="small" type="primary" secondary />
				<CloudSecurityAssessmentButton size="small" type="primary" secondary />
				<WebVulnerabilityAssessmentButton size="small" type="primary" secondary />
				<GitHubAuditButton size="small" type="primary" secondary />
				<ActiveResponseWizardButton size="small" type="primary" secondary />
				<ThreatIntelButton size="small" type="primary" secondary />
			</div>
			<div class="mobile-box block @[1100px]:hidden">
				<n-button size="small" type="primary" secondary @click="showQuickActions = true">
					<template #icon>
						<Icon :name="QuickActionsIcon" />
					</template>
					{{ t("tmgs.actions") }}
				</n-button>
			</div>
		</div>
		<div class="section">
			<div class="grid grid-cols-1 gap-4 @[440px]:grid-cols-2 @[720px]:grid-cols-3 @[1040px]:grid-cols-5">
				<div class="min-w-0">
					<AgentsCard class="h-full" :customer-codes="effectiveCustomerCodes" />
				</div>
				<div class="min-w-0">
					<HealthcheckCard class="h-full" />
				</div>
				<div class="min-w-0">
					<CustomersCard class="h-full" />
				</div>
				<div class="min-w-0">
					<IncidentAlerts class="h-full" :customer-codes="effectiveCustomerCodes" />
				</div>
				<div class="min-w-0">
					<IncidentCases class="h-full" :customer-codes="effectiveCustomerCodes" />
				</div>
			</div>
		</div>
		<div class="section">
			<IndicesMarquee @click="routeIndex($event.index).navigate()" />
		</div>
		<div class="section">
			<div class="columns flex-col lg:flex-row">
				<div class="col basis-1/2">
					<ClusterHealth class="stretchy" />
				</div>
				<div class="col basis-1/2">
					<NodeAllocation class="stretchy" />
				</div>
			</div>
		</div>
		<div class="section">
			<PipeList @open-rule="routeGraylogPipelines($event).navigate()" />
		</div>

		<n-drawer
			v-model:show="showQuickActions"
			:width="300"
			style="max-width: 90vw"
			:trap-focus="false"
			display-directive="show"
		>
			<n-drawer-content :title="t('tmgs.actions')" closable :native-scrollbar="false">
				<div class="flex flex-col gap-3">
					<StackProvisioningButton size="small" type="primary" />
					<CloudSecurityAssessmentButton size="small" type="primary" />
					<WebVulnerabilityAssessmentButton size="small" type="primary" />
					<GitHubAuditButton size="small" type="primary" />
					<ActiveResponseWizardButton size="small" type="primary" />
					<ThreatIntelButton size="small" type="primary" />
				</div>
			</n-drawer-content>
		</n-drawer>
	</div>
</template>

<script setup lang="ts">
import { useResizeObserver } from "@vueuse/core"
import { NButton, NDrawer, NDrawerContent, NSwitch } from "naive-ui"
import { computed, defineAsyncComponent, onMounted, ref } from "vue"
import { useI18n } from "vue-i18n"
import ActiveResponseWizardButton from "@/components/activeResponse/ActiveResponseWizardButton.vue"
import CloudSecurityAssessmentButton from "@/components/cloudSecurityAssessment/CloudSecurityAssessmentButton.vue"
import Icon from "@/components/common/Icon.vue"
import VersionUpdateBanner from "@/components/common/VersionUpdateBanner.vue"
import GitHubAuditButton from "@/components/githubAudit/GitHubAuditButton.vue"
import PipeList from "@/components/graylog/Pipelines/PipeList.vue"
import ClusterHealth from "@/components/indices/ClusterHealth.vue"
import IndicesMarquee from "@/components/indices/Marquee.vue"
import NodeAllocation from "@/components/indices/NodeAllocation.vue"
import AgentsCard from "@/components/overview/AgentsCard.vue"
import CustomersCard from "@/components/overview/CustomersCard.vue"
import HealthcheckCard from "@/components/overview/HealthcheckCard.vue"
import IncidentAlerts from "@/components/overview/IncidentAlerts.vue"
import IncidentCases from "@/components/overview/IncidentCases.vue"
import StackProvisioningButton from "@/components/stackProvisioning/StackProvisioningButton.vue"
import WebVulnerabilityAssessmentButton from "@/components/webVulnerabilityAssessment/WebVulnerabilityAssessmentButton.vue"
import { useGlobalCustomerFilter } from "@/composables/useGlobalCustomerFilter"
import { useNavigation } from "@/composables/useNavigation"

const ThreatIntelButton = defineAsyncComponent(() => import("@/components/threatIntel/ThreatIntelButton.vue"))

const { t } = useI18n()
const QuickActionsIcon = "ant-design:thunderbolt-outlined"
const page = ref()
const cardDirection = ref<"horizontal" | "vertical">("horizontal")
const showQuickActions = ref(false)
const { routeIndex, routeGraylogPipelines } = useNavigation()
const { globalCustomerCodes, isFiltering } = useGlobalCustomerFilter()
const useGlobalCustomerFilterToggle = ref(false)

const effectiveCustomerCodes = computed(() => (useGlobalCustomerFilterToggle.value ? globalCustomerCodes.value : []))

useResizeObserver(page, entries => {
	const entry = entries[0]
	if (!entry) return

	const { width } = entry.contentRect

	cardDirection.value = width > 500 ? "horizontal" : "vertical"
})

onMounted(() => {
	if (isFiltering.value) {
		useGlobalCustomerFilterToggle.value = true
	}
})
</script>

<style lang="scss" scoped>
.page {
	.overview-controls {
		padding-block: 0.8rem;
		border-block: 1px solid var(--border-color);
	}

	.section {
		margin-bottom: calc(var(--spacing) * 6);

		.columns {
			display: flex;
			gap: calc(var(--spacing) * 6);

			.stretchy {
				height: 100%;
			}
		}
	}
}
</style>
