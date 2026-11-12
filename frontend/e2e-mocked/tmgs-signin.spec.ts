import { expect, test } from "@playwright/test"
import { installMockBackend } from "./mock-backend"

test("TMGS sign-in preserves the password contract on mobile", async ({ browser, context, page }, testInfo) => {
	await installMockBackend(context)
	await page.setViewportSize({ width: 390, height: 844 })
	await page.goto("/login")

	await page.getByPlaceholder("Insert your username").fill("analyst")
	await page.getByPlaceholder("Insert your password").fill("fixture-only")
	const requestPromise = page.waitForRequest(request => new URL(request.url()).pathname === "/api/auth/token")
	await page.getByRole("button", { name: "Sign in with password" }).click()
	const request = await requestPromise
	const url = new URL(request.url())
	const fields = [...(request.postData() || "").matchAll(/^Content-Disposition: form-data; name="([^"]+)"/gim)]
		.map(match => match[1])
		.sort()
	const signature = {
		method: request.method(),
		path: url.pathname,
		query: url.search,
		fields,
		contentType: request.headers()["content-type"]?.split(";")[0],
		authorization: request.headers().authorization ? "present" : "absent"
	}
	await testInfo.attach("password-request", { body: JSON.stringify(signature), contentType: "application/json" })
	expect(signature).toMatchObject({
		method: "POST",
		path: "/api/auth/token",
		query: "",
		fields: ["password", "username"],
		contentType: "multipart/form-data",
		authorization: "absent"
	})

	// Open a fresh guest page, leaving the authenticated fixture session untouched.
	const guest = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: "en-US" })
	try {
		await installMockBackend(guest)
		const login = await guest.newPage()
		await login.goto(new URL("/login", url).href)
		await expect(login.getByRole("heading", { name: "TMGS SOC" })).toBeVisible()
		await login.getByRole("combobox", { name: "Language" }).selectOption("vi")
		await expect(login.getByRole("button", { name: "Đăng nhập bằng mật khẩu" })).toBeVisible()
		await expect(login.getByPlaceholder("Nhập mật khẩu")).toBeVisible()
		expect(await login.locator("body").evaluate(body => body.scrollWidth)).toBeLessThanOrEqual(390)
		await login.reload()
		await expect(login.getByRole("combobox", { name: "Ngôn ngữ" })).toHaveValue("vi")
		await login.getByRole("combobox", { name: "Ngôn ngữ" }).selectOption("en")
		await expect(login.getByPlaceholder("Insert your password")).toBeVisible()
	} finally {
		await guest.close()
	}
})
