<template>
	<main class="page-auth">
		<div v-if="!isLogged" class="auth-layout">
			<div class="form-box">
				<AuthForm :type />
			</div>
			<div class="auth-visual" aria-hidden="true" />
		</div>
	</main>
</template>

<script lang="ts" setup>
import type { FormType } from "@/components/auth/types.d"
import { computed, onBeforeMount, ref, toRefs } from "vue"
import { useRoute } from "vue-router"
import AuthForm from "@/components/auth/AuthForm.vue"
import { useAuthStore } from "@/stores/auth"

const props = defineProps<{
	formType?: FormType
}>()
const { formType } = toRefs(props)

const route = useRoute()
const type = ref<FormType | undefined>(formType.value || undefined)

const authStore = useAuthStore()
const isLogged = computed(() => authStore.isLogged)

onBeforeMount(() => {
	if (route.query.step) {
		const step = route.query.step as FormType
		type.value = step
	}
})
</script>

<style lang="scss" scoped>
.page-auth {
	min-height: 100svh;
	background: var(--bg-body-color);
}

.auth-layout {
	display: grid;
	grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
	min-height: 100svh;
}

.form-box {
	display: grid;
	place-items: center;
	min-width: 0;
	padding: clamp(1.5rem, 5vw, 4rem);
	background: var(--bg-default-color, var(--bg-body-color));
}

.auth-visual {
	position: relative;
	overflow: hidden;
	border-inline-start: 1px solid var(--border-color);
	background: radial-gradient(ellipse at 72% 38%, #234979 0%, transparent 68%), #111c2c;
}

.auth-visual::before {
	position: absolute;
	inset: 0;
	background:
		linear-gradient(to right, #a7c8f21c 1px, transparent 1px),
		linear-gradient(to bottom, #a7c8f21c 1px, transparent 1px);
	background-size: 42px 42px;
	mask-image: radial-gradient(ellipse at 72% 40%, #000 18%, transparent 78%);
	content: "";
}

.auth-visual::after {
	position: absolute;
	inset-inline-start: 12%;
	inset-block-end: 15%;
	width: 4rem;
	height: 3px;
	background: #ed3237;
	content: "";
}

@media (max-width: 820px) {
	.auth-layout {
		grid-template-columns: minmax(0, 1fr);
	}

	.auth-visual {
		display: none;
	}
}
</style>
