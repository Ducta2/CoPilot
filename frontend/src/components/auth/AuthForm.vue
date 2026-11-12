<template>
	<div class="w-full max-w-96">
		<div>
			<div class="mb-6 flex items-center justify-between gap-3">
				<Logo type="small" max-height="42px" class="login-logo" />
				<LocaleSwitch />
			</div>
			<h1 class="font-display mb-5 text-3xl font-semibold" data-test="login-title">{{ title }}</h1>
		</div>

		<transition name="transition-fade-move" mode="out-in" appear class="my-10">
			<SignIn v-if="type === 'signin'" key="signin" />
		</transition>
	</div>
</template>

<script lang="ts" setup>
import type { FormType } from "./types.d"
import { computed, onBeforeMount, ref } from "vue"
import { useI18n } from "vue-i18n"
import Logo from "@/app-layouts/common/Logo.vue"
import LocaleSwitch from "@/app-layouts/common/Toolbar/LocaleSwitch.vue"
import SignIn from "./SignIn.vue"

const props = defineProps<{
	type?: FormType
}>()

const type = ref<FormType>("signin")
const { t } = useI18n()
const title = computed(() => (type.value === "signin" || type.value === "signup" ? "TMGS SOC" : t("tmgs.forgot")))

onBeforeMount(() => {
	if (props.type) {
		type.value = props.type
	}
})
</script>

<style scoped>
.login-logo :deep(img) {
	max-width: 6rem;
}
</style>
