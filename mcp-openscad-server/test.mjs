import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const transport = new StdioClientTransport({
  command: "node",
  args: ["dist/index.js"],
  cwd: process.cwd(),
});

const client = new Client({ name: "test-client", version: "1.0.0" });
await client.connect(transport);

const testCode = 'cube([10, 10, 10]);';
let passed = 0;
let failed = 0;

function check(name, condition, detail) {
  if (condition) {
    console.log(`  PASS  ${name}`);
    passed++;
  } else {
    console.log(`  FAIL  ${name} — ${detail}`);
    failed++;
  }
}

// Test 1: openscad_render
console.log("\n=== openscad_render ===");
const r1 = JSON.parse((await client.callTool({ name: "openscad_render", arguments: { scad_code: testCode } })).content[0].text);
check("success === true", r1.success === true, `got ${r1.success}`);
check("stl_path exists", !!r1.stl_path, "stl_path is null");
check("bounding_box size = [10,10,10]", JSON.stringify(r1.bounding_box?.size) === "[10,10,10]", `got ${JSON.stringify(r1.bounding_box?.size)}`);
check("no errors", r1.errors.length === 0, `errors: ${r1.errors}`);
// cleanup
if (r1.stl_path) { const fs = await import("fs/promises"); try { await fs.unlink(r1.stl_path); } catch {} }

// Test 2: openscad_preview (expected to fail on headless without xvfb)
console.log("\n=== openscad_preview (headless — xvfb needed) ===");
const r2 = JSON.parse((await client.callTool({ name: "openscad_preview", arguments: { scad_code: testCode } })).content[0].text);
if (r2.success) {
  check("success === true", true);
  check("png_path exists", !!r2.png_path, "png_path is null");
  if (r2.png_path) { const fs = await import("fs/promises"); try { await fs.unlink(r2.png_path); } catch {} }
} else {
  console.log("  SKIP  preview not available (no DISPLAY / no xvfb) — expected on headless");
}

// Test 3: openscad_validate
console.log("\n=== openscad_validate ===");
const r3 = JSON.parse((await client.callTool({ name: "openscad_validate", arguments: { scad_code: testCode } })).content[0].text);
check("valid === true", r3.valid === true, `got ${r3.valid}`);
check("compile_success", r3.compile_success === true, `got ${r3.compile_success}`);
check("manifold = likely-manifold", r3.manifold === "likely-manifold", `got ${r3.manifold}`);
check("triangle_count = 12", r3.triangle_count === 12, `got ${r3.triangle_count}`);
check("no errors", r3.errors.length === 0, `errors: ${r3.errors}`);
check("no warnings", r3.warnings.length === 0, `warnings: ${r3.warnings}`);

// Test 4: openscad_export
console.log("\n=== openscad_export (stl) ===");
const r4 = JSON.parse((await client.callTool({ name: "openscad_export", arguments: { scad_code: testCode, format: "stl" } })).content[0].text);
check("success === true", r4.success === true, `got ${r4.success}`);
check("output_path exists", !!r4.output_path, "output_path is null");
check("format = stl", r4.format === "stl", `got ${r4.format}`);
check("file_size > 0", r4.file_size_bytes > 0, `got ${r4.file_size_bytes}`);
check("no errors", r4.errors.length === 0, `errors: ${r4.errors}`);
if (r4.output_path) { const fs = await import("fs/promises"); try { await fs.unlink(r4.output_path); } catch {} }

// Summary
console.log(`\n=== RISULTATO: ${passed} passed, ${failed} failed ===`);
await client.close();
process.exit(failed > 0 ? 1 : 0);
