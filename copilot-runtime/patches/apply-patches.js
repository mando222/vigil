#!/usr/bin/env node
/**
 * Post-install patch script for CopilotKit runtime dependencies.
 *
 * Fixes two issues in @copilotkitnext/agent and @ag-ui/client:
 *
 * 1. AGUI Verifier Race Condition:
 *    The @ag-ui/client verifier throws "Cannot send 'RUN_FINISHED' while tool
 *    calls are still active" when frontend tools (which have no server-side
 *    execute function) are mixed with MCP tools. This can also happen during
 *    request aborts. The patch converts the error into a warning + auto-close.
 *
 * 2. Frontend Tool Execute Stubs:
 *    CopilotKit frontend tools (useFrontendTool) don't have server-side execute
 *    functions. When mixed with MCP tools in Vercel AI SDK's streamText, this
 *    causes timing issues. The patch adds stub execute functions that return a
 *    "frontend_action" marker, allowing the stream to process uniformly.
 *
 * Run: node patches/apply-patches.js
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
let patchCount = 0;

function patchFile(relPath, findFn, replaceFn, description) {
  const fullPath = path.join(ROOT, relPath);
  if (!fs.existsSync(fullPath)) {
    console.log(`  SKIP (not found): ${relPath}`);
    return false;
  }

  let content = fs.readFileSync(fullPath, 'utf8');
  const needle = findFn(content);
  if (needle === null) {
    console.log(`  SKIP (already patched): ${relPath}`);
    return false;
  }

  content = replaceFn(content, needle);
  fs.writeFileSync(fullPath, content);
  console.log(`  PATCHED: ${relPath} — ${description}`);
  patchCount++;
  return true;
}

// ─── Patch 1: AGUI Verifier — auto-close tool calls instead of throwing ──────

console.log('\n[Patch 1] AGUI Verifier: auto-close tool calls before RUN_FINISHED');

const verifierFiles = [
  'node_modules/@ag-ui/client/dist/index.mjs',
  'node_modules/@ag-ui/client/dist/index.js',
  'node_modules/@copilotkitnext/agent/node_modules/@ag-ui/client/dist/index.mjs',
  'node_modules/@copilotkitnext/agent/node_modules/@ag-ui/client/dist/index.js',
  'node_modules/@copilotkitnext/runtime/node_modules/@ag-ui/client/dist/index.mjs',
  'node_modules/@copilotkitnext/runtime/node_modules/@ag-ui/client/dist/index.js',
];

for (const f of verifierFiles) {
  patchFile(
    f,
    (content) => {
      const needle = "Cannot send 'RUN_FINISHED' while tool calls are still active";
      return content.includes(needle) ? needle : null;
    },
    (content) => {
      const needle = "Cannot send 'RUN_FINISHED' while tool calls are still active";
      const idx = content.indexOf(needle);
      // Find enclosing if(n.size>0){...}
      const start = content.lastIndexOf('if(n.size>0)', idx);
      let braceCount = 0;
      let end = start;
      for (let i = start; i < content.length; i++) {
        if (content[i] === '{') braceCount++;
        if (content[i] === '}') {
          braceCount--;
          if (braceCount === 0) { end = i + 1; break; }
        }
      }
      const replacement = 'if(n.size>0){console.warn("[PATCH] Closing tool calls before RUN_FINISHED");n.clear()}';
      return content.substring(0, start) + replacement + content.substring(end);
    },
    'verifier auto-close'
  );
}

// ─── Patch 2: Frontend tool execute stubs ────────────────────────────────────

console.log('\n[Patch 2] BuiltInAgent: add execute stubs to convertToolsToVercelAITools');

const agentFiles = [
  'node_modules/@copilotkitnext/agent/dist/index.mjs',
  'node_modules/@copilotkitnext/agent/dist/index.js',
];

for (const f of agentFiles) {
  patchFile(
    f,
    (content) => {
      // Check if already patched (has our execute stub)
      if (content.includes('frontend_action')) return null;
      // Find the convertToolsToVercelAITools function
      if (!content.includes('convertToolsToVercelAITools')) return null;
      return 'needs-patch';
    },
    (content) => {
      // Find the tool creation line that doesn't have execute
      // Pattern: result[tool.name] = createVercelAISDKTool({ description: ..., inputSchema: zodSchema });
      // We need to add execute before the closing });
      const funcStart = content.indexOf('function convertToolsToVercelAITools');
      if (funcStart === -1) return content;

      // Find the createVercelAISDKTool call within this function
      const searchArea = content.substring(funcStart, funcStart + 500);
      const createToolIdx = searchArea.indexOf('createVercelAISDKTool({');
      if (createToolIdx === -1) return content;

      // Find the closing }); of the createVercelAISDKTool call
      const absIdx = funcStart + createToolIdx;
      let depth = 0;
      let closeIdx = absIdx;
      for (let i = absIdx; i < content.length; i++) {
        if (content[i] === '(') depth++;
        if (content[i] === ')') {
          depth--;
          if (depth === 0) { closeIdx = i; break; }
        }
      }

      // Find the last } before closeIdx (end of the options object)
      let lastBrace = closeIdx;
      for (let i = closeIdx - 1; i > absIdx; i--) {
        if (content[i] === '}') { lastBrace = i; break; }
      }

      // Insert execute function before the closing brace
      const insertText = `,\n      execute: async (args) => {\n        return JSON.stringify({ status: "frontend_action", tool: tool.name, message: "This action will be handled by the frontend UI.", args });\n      }`;

      return content.substring(0, lastBrace) + insertText + content.substring(lastBrace);
    },
    'frontend tool execute stubs'
  );
}

// ─── Patch 3: BuiltInAgent — auto-close tool calls before RUN_FINISHED ──────

console.log('\n[Patch 3] BuiltInAgent: auto-close tool calls in finish handler');

for (const f of agentFiles) {
  patchFile(
    f,
    (content) => {
      if (content.includes('Auto-closing un-ended tool call')) return null;
      if (!content.includes('case "finish"')) return null;
      return 'needs-patch';
    },
    (content) => {
      // Find case "finish": and add tool-call cleanup before RUN_FINISHED
      const finishIdx = content.indexOf('case "finish":');
      if (finishIdx === -1) return content;

      // Insert after 'case "finish":'
      const insertAfter = 'case "finish":';
      const insertText = `\n                // [PATCH] Close any un-ended tool calls before RUN_FINISHED\n                for (const [tcId, tcState] of toolCallStates.entries()) {\n                  if (tcState.started && !tcState.ended) {\n                    console.log("[PATCH] Auto-closing un-ended tool call:", tcId);\n                    tcState.ended = true;\n                    subscriber.next({ type: ${content.includes('import_client.EventType') ? 'import_client.EventType' : 'EventType'}.TOOL_CALL_END, toolCallId: tcId });\n                  }\n                }`;

      return content.substring(0, finishIdx + insertAfter.length) + insertText + content.substring(finishIdx + insertAfter.length);
    },
    'finish handler auto-close'
  );
}

console.log(`\n✅ Applied ${patchCount} patches total.\n`);
