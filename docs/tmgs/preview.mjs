import { createReadStream } from "node:fs"
import { realpath, stat } from "node:fs/promises"
import { createServer } from "node:http"
import { extname, isAbsolute, relative, resolve } from "node:path"

const [directory, portArg = "4173"] = process.argv.slice(2)
const port = Number(portArg)
if (!directory || !Number.isInteger(port) || port < 1024 || port > 65535) {
	throw new Error("Usage: node docs/tmgs/preview.mjs <dist-directory> [port]")
}

const root = await realpath(resolve(directory))
const index = resolve(root, "index.html")
await stat(index)

const mimeTypes = {
	".css": "text/css; charset=utf-8",
	".html": "text/html; charset=utf-8",
	".ico": "image/x-icon",
	".jpeg": "image/jpeg",
	".jpg": "image/jpeg",
	".js": "text/javascript; charset=utf-8",
	".json": "application/json",
	".mp4": "video/mp4",
	".png": "image/png",
	".svg": "image/svg+xml",
	".webp": "image/webp",
	".woff2": "font/woff2"
}

function finish(res, status, body) {
	res.writeHead(status, { "Content-Type": "application/json", "Cache-Control": "no-store" })
	res.end(JSON.stringify(body))
}

const server = createServer(async (req, res) => {
	try {
		const path = decodeURIComponent(new URL(req.url, "http://127.0.0.1").pathname)
		if (path === "/api" || path.startsWith("/api/")) {
			return finish(res, 503, { success: false, message: "Local preview has no backend connection." })
		}
		if (req.method !== "GET" && req.method !== "HEAD") {
			return finish(res, 405, { success: false })
		}
		if (path.includes("\\") || path.split("/").some(part => part.startsWith("."))) {
			return finish(res, 404, { success: false })
		}
		let file = await realpath(resolve(root, `.${path}`)).catch(() => null)
		if (file) {
			const relativeFile = relative(root, file)
			if (relativeFile.startsWith("..") || isAbsolute(relativeFile)) {
				return finish(res, 404, { success: false })
			}
			if (!(await stat(file)).isFile()) file = null
		}
		if (!file && !extname(path)) file = index
		if (!file) return finish(res, 404, { success: false })
		res.writeHead(200, {
			"Content-Type": mimeTypes[extname(file)] || "application/octet-stream",
			"Cache-Control": "no-store",
			"X-Content-Type-Options": "nosniff"
		})
		if (req.method === "HEAD") return res.end()
		createReadStream(file).on("error", () => res.destroy()).pipe(res)
	} catch {
		finish(res, 400, { success: false })
	}
})

server.listen(port, "127.0.0.1", () => {
	console.log(`Frontend preview: http://127.0.0.1:${port}/login`)
})
