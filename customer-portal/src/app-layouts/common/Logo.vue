<template>
	<div class="logo">
		<img :src="logoSrc" :alt="portalTitle" :aria-label="portalTitle" class="logo-image" />
	</div>
</template>

<script lang="ts" setup>
import { computed } from "vue"
import { usePortalSettingsStore } from "@/stores/portalSettings"

interface Props {
	maxHeight?: string
}

withDefaults(defineProps<Props>(), {
	maxHeight: "32px"
})

const portalSettingsStore = usePortalSettingsStore()

const portalTitle = computed(() => portalSettingsStore.portalTitle || "Customer Portal")
const portalLogo = computed(() => portalSettingsStore.portalLogo)
const logoSrc = computed(
	() =>
		portalLogo.value ||
		(portalSettingsStore.portalTitle ? portalSettingsStore.portalLogoInitials : "/tmgs/tmgs.svg")
)
</script>

<style lang="scss" scoped>
.logo {
	height: 100%;
	display: flex;
	align-items: center;
	justify-content: center;
	position: relative;

	.logo-image {
		max-height: v-bind(maxHeight);
		height: 100%;
		width: auto;
		display: block;
		object-fit: contain;
	}
}
</style>
