/**
 * aoc-sensor extension — pi tools backed by the aoc MCP (stdio).
 *
 * Ported from /content/pi-extension/content-sensor.ts. Same shape:
 * spawn the MCP once per session, expose verbs to the model.
 * The MCP owns skins + gates + receipts; pi just drives it.
 *
 * Differences from content-sensor: 14 aoc tools instead of 6, review
 * queue + signoff verbs included, paths point at /root/aoc.
 */
import { spawn, type ChildProcess } from "node:child_process";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

const MCP_CMD = process.env.AOC_MCP_PY || "python3";
const MCP_ARG = process.env.AOC_MCP_PATH || "/root/aoc/mcp_server.py";

let proc: ChildProcess | null = null;
let nextId = 0;
const pending = new Map<number, (v: unknown) => void>();
let buf = "";

function ensureProc(): ChildProcess {
	if (proc && proc.exitCode === null) return proc;
	proc = spawn(MCP_CMD, [MCP_ARG], { stdio: ["pipe", "pipe", "ignore"] });
	proc.stdout!.on("data", (chunk: Buffer) => {
		buf += chunk.toString();
		let nl: number;
		while ((nl = buf.indexOf("\n")) >= 0) {
			const line = buf.slice(0, nl).trim();
			buf = buf.slice(nl + 1);
			if (!line) continue;
			try {
				const msg = JSON.parse(line) as { id?: number; result?: unknown; error?: unknown };
				if (typeof msg.id === "number" && pending.has(msg.id)) {
					const res = pending.get(msg.id)!;
					pending.delete(msg.id);
					res(msg.error ? { error: msg.error } : msg.result);
				}
			} catch { /* keep going */ }
		}
	});
	return proc;
}

function mcpCall(tool: string, args: Record<string, unknown>): Promise<unknown> {
	const p = ensureProc();
	return new Promise((resolve) => {
		const id = ++nextId;
		pending.set(id, resolve);
		p.stdin!.write(JSON.stringify({ jsonrpc: "2.0", id, method: "tools/call", params: { name: tool, arguments: args } }) + "\n");
		setTimeout(() => {
			if (pending.has(id)) { pending.delete(id); resolve({ error: "mcp timeout" }); }
		}, 120000);
	});
}

async function toolText(tool: string, args: Record<string, unknown>): Promise<string> {
	const res = (await mcpCall(tool, args)) as {
		content?: Array<{ type?: string; text?: string }>;
		error?: unknown;
	};
	if (res && typeof res === "object" && "error" in res) return `ERROR: ${JSON.stringify(res.error).slice(0, 500)}`;
	const parts = res?.content ?? [];
	return parts.map((c) => String(c.text ?? "")).join("\n").slice(0, 8000) || "(empty result)";
}

const SEGMENT = Type.String({ description: "Segment: electrician|beautician|nails|lashes|hair|cleaners|dog_groomers|gardeners|car_detailers|driving_instructors|weddings|plumber|sole_trader", default: "electrician" });

export default function aocSensor(pi: ExtensionAPI) {
	pi.on("session_shutdown", () => {
		try { proc?.kill(); } catch { /* already gone */ }
		proc = null;
	});
	pi.registerTool({
		name: "aoc_hooks",
		label: "AOC Hooks",
		description: "Hook bank for a trade segment. Start here.",
		parameters: Type.Object({ segment: SEGMENT }),
		async execute(_id, params) {
			const text = await toolText("aoc_hooks", { segment: params.segment });
			return { content: [{ type: "text", text }], details: { tool: "aoc_hooks" } };
		},
	});
	pi.registerTool({
		name: "aoc_build",
		label: "AOC Build",
		description: "Build a gated carousel locally (PNGs+ZIP, no publish).",
		parameters: Type.Object({
			hook: Type.String({ description: "Slide-1 hook" }),
			template: Type.String({ description: "Template", default: "opportunity" }),
			segment: SEGMENT,
		}),
		async execute(_id, params) {
			const text = await toolText("aoc_build", { hook: params.hook, template: params.template, segment: params.segment });
			return { content: [{ type: "text", text }], details: { tool: "aoc_build" } };
		},
	});
	pi.registerTool({
		name: "aoc_validate",
		label: "AOC Validate",
		description: "Run proof+gates without rendering. Cheap quality check before building.",
		parameters: Type.Object({
			hook: Type.String(),
			template: Type.String({ default: "opportunity" }),
			segment: SEGMENT,
		}),
		async execute(_id, params) {
			const text = await toolText("aoc_validate", { hook: params.hook, template: params.template, segment: params.segment });
			return { content: [{ type: "text", text }], details: { tool: "aoc_validate" } };
		},
	});
	pi.registerTool({
		name: "aoc_queue",
		label: "AOC Queue",
		description: "Review queue: built carousels awaiting human verdict.",
		parameters: Type.Object({}),
		async execute(_id) {
			const text = await toolText("aoc_lineage", { limit: 20 });
			return { content: [{ type: "text", text }], details: { tool: "aoc_lineage" } };
		},
	});
	pi.registerTool({
		name: "aoc_signoff",
		label: "AOC Sign-off",
		description: "Record human verdict: approved|revise|rejected with reason.",
		parameters: Type.Object({
			content_id: Type.String(),
			decision: Type.String({ description: "approved|revise|rejected" }),
			reason: Type.String(),
		}),
		async execute(_id, params) {
			const text = await toolText("aoc_signoff", { content_id: params.content_id, decision: params.decision, reason: params.reason });
			return { content: [{ type: "text", text }], details: { tool: "aoc_signoff" } };
		},
	});
	pi.registerTool({
		name: "aoc_status",
		label: "AOC Status",
		description: "What the factory can do: templates, segments, hooks, receipts.",
		parameters: Type.Object({}),
		async execute(_id) {
			const text = await toolText("aoc_status", {});
			return { content: [{ type: "text", text }], details: { tool: "aoc_status" } };
		},
	});
}
