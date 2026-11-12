<template>
	<div class="logo" :class="{ compact: type === 'small' }">
		<img :src="tmgsLogo" :alt="type === 'small' ? 'TMGS' : ''" />
		<span v-if="type !== 'small'">TMGS SOC</span>
	</div>
</template>

<script lang="ts" setup>
withDefaults(defineProps<{ type?: "default" | "small" | "large"; maxHeight?: string }>(), {
	type: "default",
	maxHeight: "32px"
})

const tmgsLogo = "/tmgs/tmgs.svg"
</script>

<style scoped>
.logo {
	display: inline-flex;
	align-items: center;
	gap: 0.65rem;
	color: var(--fg-default-color);
	font-size: 1rem;
	font-weight: 600;
	white-space: nowrap;
}

.logo img {
	display: block;
	width: auto;
	height: v-bind(maxHeight);
	max-width: 4.2rem;
	object-fit: contain;
}

.logo.compact img {
	max-width: 2.75rem;
}
</style>
