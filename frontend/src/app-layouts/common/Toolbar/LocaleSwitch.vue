<template>
	<select v-model="currentLocale" class="locale-switch" :aria-label="t('tmgs.language')">
		<option v-for="locale in localesStore.availableLocales" :key="locale" :value="locale">
			{{ t(`locales.${locale}`, locale) }}
		</option>
	</select>
</template>

<script lang="ts" setup>
import { computed } from "vue"
import { useI18n } from "vue-i18n"
import { useLocalesStore } from "@/stores/i18n"

const { t } = useI18n()
const localesStore = useLocalesStore()
const currentLocale = computed({
	get: () => localesStore.locale,
	set: locale => localesStore.setLocale(locale)
})
</script>

<style scoped>
.locale-switch {
	max-width: 7rem;
	min-height: 2rem;
	padding: 0.2rem 0.35rem;
	border: 1px solid var(--border-color);
	border-radius: 0.35rem;
	background: var(--bg-body-color);
	color: inherit;
	font-size: 0.75rem;
}
</style>
