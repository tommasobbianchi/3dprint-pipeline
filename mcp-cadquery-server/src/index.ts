#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { execFile } from "child_process";
import { promisify } from "util";
import * as fs from "fs/promises";
import * as path from "path";
import * as crypto from "crypto";

const execFileAsync = promisify(execFile);

// --- Configuration ---

const PYTHON_PATH = process.env.PYTHON_PATH || "python3";
const TEMP_DIR = "/tmp/cadquery-mcp";
const EXEC_TIMEOUT_MS = 60_000; // 60 seconds

// --- Helpers ---

async function ensureTempDir(): Promise<void> {
  await fs.mkdir(TEMP_DIR, { recursive: true });
}

function uniqueId(): string {
  return crypto.randomBytes(8).toString("hex");
}

function tempPath(prefix: string, ext: string): string {
  const id = uniqueId();
  return path.join(TEMP_DIR, `${prefix}_${id}${ext}`);
}

async function cleanup(...paths: string[]): Promise<void> {
  for (const p of paths) {
    try {
      await fs.unlink(p);
    } catch {
      // ignore missing files
    }
  }
}

interface PythonResult {
  exitCode: number;
  stdout: string;
  stderr: string;
}

async function runPython(scriptPath: string): Promise<PythonResult> {
  try {
    const { stdout, stderr } = await execFileAsync(PYTHON_PATH, [scriptPath], {
      timeout: EXEC_TIMEOUT_MS,
      maxBuffer: 10 * 1024 * 1024, // 10 MB
    });
    return { exitCode: 0, stdout, stderr };
  } catch (err: unknown) {
    const e = err as { code?: number; stdout?: string; stderr?: string };
    return {
      exitCode: e.code ?? 1,
      stdout: e.stdout ?? "",
      stderr: e.stderr ?? String(err),
    };
  }
}

function parseStderr(stderr: string): {
  errors: string[];
  warnings: string[];
} {
  const lines = stderr.split("\n").filter((l) => l.trim());
  const errors: string[] = [];
  const warnings: string[] = [];
  for (const line of lines) {
    if (
      /Traceback/i.test(line) ||
      /Error:/i.test(line) ||
      /Exception:/i.test(line) ||
      /^  File "/i.test(line)
    ) {
      errors.push(line.trim());
    } else if (/warning/i.test(line) || /deprecat/i.test(line)) {
      warnings.push(line.trim());
    }
  }
  return { errors, warnings };
}

interface BoundingBox {
  min: { x: number; y: number; z: number };
  max: { x: number; y: number; z: number };
  size: { x: number; y: number; z: number };
}

function parseBoundingBox(stdout: string): BoundingBox | null {
  const bboxMatch = stdout.match(
    /BBOX:([-\d.]+),([-\d.]+),([-\d.]+),([-\d.]+),([-\d.]+),([-\d.]+)/
  );
  const sizeMatch = stdout.match(
    /SIZE:([-\d.]+)x([-\d.]+)x([-\d.]+)/
  );

  if (!bboxMatch || !sizeMatch) return null;

  return {
    min: {
      x: parseFloat(bboxMatch[1]),
      y: parseFloat(bboxMatch[2]),
      z: parseFloat(bboxMatch[3]),
    },
    max: {
      x: parseFloat(bboxMatch[4]),
      y: parseFloat(bboxMatch[5]),
      z: parseFloat(bboxMatch[6]),
    },
    size: {
      x: parseFloat(sizeMatch[1]),
      y: parseFloat(sizeMatch[2]),
      z: parseFloat(sizeMatch[3]),
    },
  };
}

function parseVolume(stdout: string): number | null {
  const match = stdout.match(/VOLUME:([-\d.]+)/);
  return match ? parseFloat(match[1]) : null;
}

function parseSurfaceArea(stdout: string): number | null {
  const match = stdout.match(/AREA:([-\d.]+)/);
  if (!match) return null;
  const val = parseFloat(match[1]);
  return val >= 0 ? val : null;
}

// --- Measurement code snippets ---

const MEASUREMENT_CODE = `
_r = result
_bb = _r.val().BoundingBox()
_vol = _r.val().Volume()
print(f"BBOX:{_bb.xmin:.2f},{_bb.ymin:.2f},{_bb.zmin:.2f},{_bb.xmax:.2f},{_bb.ymax:.2f},{_bb.zmax:.2f}")
print(f"SIZE:{_bb.xlen:.2f}x{_bb.ylen:.2f}x{_bb.zlen:.2f}")
print(f"VOLUME:{_vol:.2f}")
`;

const INFO_CODE = `
_r = result
_bb = _r.val().BoundingBox()
_vol = _r.val().Volume()
try:
    _area = sum(f.Area() for f in _r.val().Faces())
except:
    _area = -1
print(f"BBOX:{_bb.xmin:.2f},{_bb.ymin:.2f},{_bb.zmin:.2f},{_bb.xmax:.2f},{_bb.ymax:.2f},{_bb.zmax:.2f}")
print(f"SIZE:{_bb.xlen:.2f}x{_bb.ylen:.2f}x{_bb.zlen:.2f}")
print(f"VOLUME:{_vol:.2f}")
print(f"AREA:{_area:.2f}")
`;

// --- MCP Server ---

const server = new McpServer({
  name: "cadquery-mcp",
  version: "1.0.0",
});

// Tool 1: cadquery_execute
server.tool(
  "cadquery_execute",
  "Execute CadQuery Python code. The code must define a `result` variable as a CadQuery Workplane object. Returns stdout, stderr, and success status.",
  {
    python_code: z
      .string()
      .describe(
        "CadQuery Python code to execute. Must define a `result` variable."
      ),
  },
  async ({ python_code }) => {
    await ensureTempDir();
    const scriptPath = tempPath("script", ".py");

    try {
      await fs.writeFile(scriptPath, python_code, "utf-8");

      const result = await runPython(scriptPath);
      const { errors, warnings } = parseStderr(result.stderr);
      const success = result.exitCode === 0;

      const response = {
        success,
        stdout: result.stdout,
        stderr: result.stderr,
        errors,
        warnings,
      };

      return {
        content: [
          { type: "text" as const, text: JSON.stringify(response, null, 2) },
        ],
      };
    } finally {
      await cleanup(scriptPath);
    }
  }
);

// Tool 2: cadquery_validate
server.tool(
  "cadquery_validate",
  "Validate CadQuery Python code: execute it, measure bounding box and volume. The code must define a `result` variable as a CadQuery Workplane object. Returns validation status, bounding box, volume, and any errors.",
  {
    python_code: z
      .string()
      .describe(
        "CadQuery Python code to validate. Must define a `result` variable."
      ),
  },
  async ({ python_code }) => {
    await ensureTempDir();
    const scriptPath = tempPath("script", ".py");

    try {
      const fullCode = python_code + "\n" + MEASUREMENT_CODE;
      await fs.writeFile(scriptPath, fullCode, "utf-8");

      const result = await runPython(scriptPath);
      const { errors, warnings } = parseStderr(result.stderr);
      const boundingBox = parseBoundingBox(result.stdout);
      const volume = parseVolume(result.stdout);

      // valid = no errors AND bounding_box size > 0 on all axes
      const valid =
        result.exitCode === 0 &&
        errors.length === 0 &&
        boundingBox !== null &&
        boundingBox.size.x > 0 &&
        boundingBox.size.y > 0 &&
        boundingBox.size.z > 0;

      const response = {
        valid,
        errors,
        warnings,
        bounding_box: boundingBox,
        volume_mm3: volume,
      };

      return {
        content: [
          { type: "text" as const, text: JSON.stringify(response, null, 2) },
        ],
      };
    } finally {
      await cleanup(scriptPath);
    }
  }
);

// Tool 3: cadquery_export
server.tool(
  "cadquery_export",
  "Export CadQuery model to STEP, STL, and/or SVG formats. The code must define a `result` variable as a CadQuery Workplane object. Returns file paths and bounding box.",
  {
    python_code: z
      .string()
      .describe(
        "CadQuery Python code to export. Must define a `result` variable."
      ),
    formats: z
      .array(z.enum(["step", "stl", "svg"]))
      .default(["step", "stl"])
      .describe('Export formats (default: ["step", "stl"])'),
    output_dir: z
      .string()
      .optional()
      .describe(
        "Output directory for exported files (default: /tmp/cadquery-mcp/)"
      ),
  },
  async ({ python_code, formats, output_dir }) => {
    await ensureTempDir();
    const scriptPath = tempPath("script", ".py");
    const outDir = output_dir ?? TEMP_DIR;
    const id = uniqueId();

    // Ensure output directory exists
    await fs.mkdir(outDir, { recursive: true });

    const filePaths: Record<string, string> = {};
    for (const fmt of formats) {
      const ext = fmt === "step" ? ".step" : fmt === "stl" ? ".stl" : ".svg";
      filePaths[fmt] = path.join(outDir, `export_${id}${ext}`);
    }

    try {
      let exportCode = "\nimport cadquery as cq\n";

      for (const fmt of formats) {
        const outPath = filePaths[fmt];
        if (fmt === "step") {
          exportCode += `cq.exporters.export(result, "${outPath}")\n`;
        } else if (fmt === "stl") {
          exportCode += `cq.exporters.export(result, "${outPath}")\n`;
        } else if (fmt === "svg") {
          exportCode += `try:\n`;
          exportCode += `    cq.exporters.export(result, "${outPath}", exportType="SVG")\n`;
          exportCode += `except Exception as _svg_err:\n`;
          exportCode += `    print(f"SVG_EXPORT_ERROR:{_svg_err}", flush=True)\n`;
        }
      }

      // Also append bounding box measurement
      exportCode += MEASUREMENT_CODE;

      const fullCode = python_code + "\n" + exportCode;
      await fs.writeFile(scriptPath, fullCode, "utf-8");

      const result = await runPython(scriptPath);
      const { errors, warnings } = parseStderr(result.stderr);
      const boundingBox = parseBoundingBox(result.stdout);
      const success = result.exitCode === 0 && errors.length === 0;

      // Verify which files were actually created
      const files: Record<string, string> = {};
      for (const fmt of formats) {
        try {
          await fs.access(filePaths[fmt]);
          files[fmt] = filePaths[fmt];
        } catch {
          // file was not created
        }
      }

      const response = {
        success,
        files,
        bounding_box: boundingBox,
        errors,
        warnings,
        stderr: result.stderr,
      };

      return {
        content: [
          { type: "text" as const, text: JSON.stringify(response, null, 2) },
        ],
      };
    } finally {
      await cleanup(scriptPath);
      // Keep exported files
    }
  }
);

// Tool 4: cadquery_preview
server.tool(
  "cadquery_preview",
  "Generate an SVG preview of a CadQuery model. The code must define a `result` variable as a CadQuery Workplane object. Returns the SVG file path.",
  {
    python_code: z
      .string()
      .describe(
        "CadQuery Python code to preview. Must define a `result` variable."
      ),
    output_path: z
      .string()
      .optional()
      .describe("Optional output SVG path"),
  },
  async ({ python_code, output_path }) => {
    await ensureTempDir();
    const scriptPath = tempPath("script", ".py");
    const svgPath = output_path ?? tempPath("preview", ".svg");

    // Ensure output directory exists
    await fs.mkdir(path.dirname(svgPath), { recursive: true });

    try {
      const previewCode = `
import cadquery as cq
cq.exporters.export(result, "${svgPath}", exportType="SVG")
print("SVG_OK")
`;

      const fullCode = python_code + "\n" + previewCode;
      await fs.writeFile(scriptPath, fullCode, "utf-8");

      const result = await runPython(scriptPath);
      const { errors, warnings } = parseStderr(result.stderr);

      let exists = false;
      try {
        await fs.access(svgPath);
        exists = true;
      } catch {
        // file doesn't exist
      }

      const success = result.exitCode === 0 && errors.length === 0 && exists;

      const response = {
        success,
        svg_path: exists ? svgPath : null,
        errors,
        warnings,
        stderr: result.stderr,
      };

      return {
        content: [
          { type: "text" as const, text: JSON.stringify(response, null, 2) },
        ],
      };
    } finally {
      await cleanup(scriptPath);
      // Keep SVG file
    }
  }
);

// Tool 5: cadquery_info
server.tool(
  "cadquery_info",
  "Get detailed information about a CadQuery model: bounding box, volume, and surface area. The code must define a `result` variable as a CadQuery Workplane object.",
  {
    python_code: z
      .string()
      .describe(
        "CadQuery Python code to analyze. Must define a `result` variable."
      ),
  },
  async ({ python_code }) => {
    await ensureTempDir();
    const scriptPath = tempPath("script", ".py");

    try {
      const fullCode = python_code + "\n" + INFO_CODE;
      await fs.writeFile(scriptPath, fullCode, "utf-8");

      const result = await runPython(scriptPath);
      const { errors, warnings } = parseStderr(result.stderr);
      const boundingBox = parseBoundingBox(result.stdout);
      const volume = parseVolume(result.stdout);
      const surfaceArea = parseSurfaceArea(result.stdout);

      const response = {
        bounding_box: boundingBox,
        volume_mm3: volume,
        surface_area_mm2: surfaceArea,
        errors,
        warnings,
        stderr: result.stderr,
      };

      return {
        content: [
          { type: "text" as const, text: JSON.stringify(response, null, 2) },
        ],
      };
    } finally {
      await cleanup(scriptPath);
    }
  }
);

// --- Start server ---

async function main() {
  await ensureTempDir();
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  console.error("Fatal error starting MCP server:", err);
  process.exit(1);
});
