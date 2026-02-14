import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const transport = new StdioClientTransport({
  command: "node",
  args: ["dist/index.js"],
  cwd: process.cwd(),
});

const client = new Client({ name: "test-client", version: "1.0.0" });
await client.connect(transport);

const testCode = `import cadquery as cq
result = cq.Workplane('XY').box(20, 15, 10).edges('|Z').fillet(2)
`;

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

// Test 1: cadquery_execute
console.log("\n=== cadquery_execute ===");
const r1 = JSON.parse(
  (await client.callTool({ name: "cadquery_execute", arguments: { python_code: testCode } }))
    .content[0].text
);
check("success === true", r1.success === true, `got ${r1.success}, stderr: ${r1.stderr}`);
check("no errors", r1.errors.length === 0, `errors: ${JSON.stringify(r1.errors)}`);

// Test 2: cadquery_validate
console.log("\n=== cadquery_validate ===");
const r2 = JSON.parse(
  (await client.callTool({ name: "cadquery_validate", arguments: { python_code: testCode } }))
    .content[0].text
);
check("valid === true", r2.valid === true, `got ${r2.valid}, errors: ${JSON.stringify(r2.errors)}`);
check("has bounding_box", !!r2.bounding_box, "bounding_box is null");
if (r2.bounding_box) {
  check(
    "size.x ~ 20",
    Math.abs(r2.bounding_box.size.x - 20) < 0.1,
    `got ${r2.bounding_box.size.x}`
  );
  check(
    "size.y ~ 15",
    Math.abs(r2.bounding_box.size.y - 15) < 0.1,
    `got ${r2.bounding_box.size.y}`
  );
  check(
    "size.z ~ 10",
    Math.abs(r2.bounding_box.size.z - 10) < 0.1,
    `got ${r2.bounding_box.size.z}`
  );
}
check("volume > 0", r2.volume_mm3 > 0, `got ${r2.volume_mm3}`);

// Test 3: cadquery_export
console.log("\n=== cadquery_export ===");
const r3 = JSON.parse(
  (
    await client.callTool({
      name: "cadquery_export",
      arguments: { python_code: testCode, formats: ["step", "stl"] },
    })
  ).content[0].text
);
check("success === true", r3.success === true, `got ${r3.success}, errors: ${JSON.stringify(r3.errors)}`);
check("has step file", !!r3.files?.step, "no step file");
check("has stl file", !!r3.files?.stl, "no stl file");
check("has bounding_box", !!r3.bounding_box, "bounding_box is null");
// Cleanup exported files
const fs = await import("fs/promises");
for (const fp of Object.values(r3.files || {})) {
  try { await fs.unlink(fp); } catch {}
}

// Test 4: cadquery_preview
console.log("\n=== cadquery_preview ===");
const r4 = JSON.parse(
  (await client.callTool({ name: "cadquery_preview", arguments: { python_code: testCode } }))
    .content[0].text
);
check("success === true", r4.success === true, `got ${r4.success}, errors: ${JSON.stringify(r4.errors)}`);
check("has svg_path", !!r4.svg_path, "svg_path is null");
if (r4.svg_path) {
  try { await fs.unlink(r4.svg_path); } catch {}
}

// Test 5: cadquery_info
console.log("\n=== cadquery_info ===");
const r5 = JSON.parse(
  (await client.callTool({ name: "cadquery_info", arguments: { python_code: testCode } }))
    .content[0].text
);
check("no errors", !r5.errors || r5.errors.length === 0, `errors: ${JSON.stringify(r5.errors)}`);
check("has bounding_box", !!r5.bounding_box, "bounding_box is null");
check("volume > 0", r5.volume_mm3 > 0, `got ${r5.volume_mm3}`);
check("surface_area > 0", r5.surface_area_mm2 !== null && r5.surface_area_mm2 > 0, `got ${r5.surface_area_mm2}`);

// Summary
console.log(`\n=== RESULT: ${passed} passed, ${failed} failed ===`);
await client.close();
process.exit(failed > 0 ? 1 : 0);
