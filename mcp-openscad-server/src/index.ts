#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { execFile } from "child_process";
import { promisify } from "util";
import * as fs from "fs/promises";
import * as path from "path";
import * as os from "os";
import * as crypto from "crypto";

const execFileAsync = promisify(execFile);

// --- Configuration ---

const OPENSCAD_PATH = process.env.OPENSCAD_PATH || "openscad";
const TEMP_DIR = "/tmp/openscad-mcp";
const RENDER_TIMEOUT_MS = 120_000; // 2 minutes

// --- Helpers ---

async function ensureTempDir(): Promise<void> {
  await fs.mkdir(TEMP_DIR, { recursive: true });
}

function tempPath(ext: string): string {
  const id = crypto.randomBytes(8).toString("hex");
  return path.join(TEMP_DIR, `openscad-${id}${ext}`);
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

interface OpenscadResult {
  exitCode: number;
  stdout: string;
  stderr: string;
}

async function runOpenscad(
  args: string[],
  needsDisplay = false
): Promise<OpenscadResult> {
  try {
    let command = OPENSCAD_PATH;
    let finalArgs = args;

    // For preview (PNG), try xvfb-run if no DISPLAY is set
    if (needsDisplay && !process.env.DISPLAY) {
      command = "xvfb-run";
      finalArgs = ["-a", OPENSCAD_PATH, ...args];
    }

    const { stdout, stderr } = await execFileAsync(command, finalArgs, {
      timeout: RENDER_TIMEOUT_MS,
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
    if (/error/i.test(line) || /^ERROR/i.test(line)) {
      errors.push(line.trim());
    } else if (/warning/i.test(line) || /^WARNING/i.test(line)) {
      warnings.push(line.trim());
    } else if (/^Parser error/i.test(line) || /syntax error/i.test(line)) {
      errors.push(line.trim());
    }
  }
  return { errors, warnings };
}

async function getBoundingBox(
  stlPath: string
): Promise<{ min: number[]; max: number[]; size: number[] } | null> {
  try {
    const data = await fs.readFile(stlPath);
    // Binary STL: 80-byte header, 4-byte triangle count, then 50 bytes per triangle
    if (data.length < 84) return null;
    const triangleCount = data.readUInt32LE(80);
    if (triangleCount === 0) return null;

    let minX = Infinity,
      minY = Infinity,
      minZ = Infinity;
    let maxX = -Infinity,
      maxY = -Infinity,
      maxZ = -Infinity;

    for (let i = 0; i < triangleCount; i++) {
      const offset = 84 + i * 50;
      // Skip normal vector (12 bytes), read 3 vertices (each 12 bytes = 3 floats)
      for (let v = 0; v < 3; v++) {
        const vOffset = offset + 12 + v * 12;
        const x = data.readFloatLE(vOffset);
        const y = data.readFloatLE(vOffset + 4);
        const z = data.readFloatLE(vOffset + 8);
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        minZ = Math.min(minZ, z);
        maxX = Math.max(maxX, x);
        maxY = Math.max(maxY, y);
        maxZ = Math.max(maxZ, z);
      }
    }

    const round2 = (n: number) => Math.round(n * 100) / 100;
    return {
      min: [round2(minX), round2(minY), round2(minZ)],
      max: [round2(maxX), round2(maxY), round2(maxZ)],
      size: [round2(maxX - minX), round2(maxY - minY), round2(maxZ - minZ)],
    };
  } catch {
    return null;
  }
}

// --- MCP Server ---

const server = new McpServer({
  name: "openscad-mcp",
  version: "1.0.0",
});

// Tool 1: openscad_render
server.tool(
  "openscad_render",
  "Compile OpenSCAD code to STL. Returns success status, stderr output, STL file path, and bounding box.",
  {
    scad_code: z.string().describe("OpenSCAD source code to compile"),
    output_path: z
      .string()
      .optional()
      .describe(
        "Optional output STL path. If omitted, uses a temp file in /tmp/openscad-mcp/"
      ),
  },
  async ({ scad_code, output_path }) => {
    await ensureTempDir();
    const inputPath = tempPath(".scad");
    const stlPath = output_path ?? tempPath(".stl");

    try {
      await fs.writeFile(inputPath, scad_code, "utf-8");

      const result = await runOpenscad([
        "-o",
        stlPath,
        "--export-format",
        "binstl",
        inputPath,
      ]);

      const { errors, warnings } = parseStderr(result.stderr);
      const success = errors.length === 0 && result.exitCode === 0;

      let boundingBox = null;
      let fileSize = 0;
      if (success) {
        try {
          const stat = await fs.stat(stlPath);
          fileSize = stat.size;
          boundingBox = await getBoundingBox(stlPath);
        } catch {
          // STL file might not exist if render produced no geometry
        }
      }

      const response = {
        success,
        stl_path: success ? stlPath : null,
        file_size_bytes: fileSize,
        bounding_box: boundingBox,
        errors,
        warnings,
        stderr: result.stderr,
      };

      return {
        content: [{ type: "text" as const, text: JSON.stringify(response, null, 2) }],
      };
    } finally {
      await cleanup(inputPath);
      // Keep STL — caller decides when to clean up
    }
  }
);

// Tool 2: openscad_preview
server.tool(
  "openscad_preview",
  "Generate a PNG preview image of OpenSCAD code. Returns the PNG file path.",
  {
    scad_code: z.string().describe("OpenSCAD source code to preview"),
    size: z
      .string()
      .optional()
      .default("800,600")
      .describe("Image size as 'width,height' (default: 800,600)"),
    camera: z
      .string()
      .optional()
      .describe(
        "Camera position as 'translateX,translateY,translateZ,rotX,rotY,rotZ,dist' (optional)"
      ),
    output_path: z
      .string()
      .optional()
      .describe("Optional output PNG path"),
  },
  async ({ scad_code, size, camera, output_path }) => {
    await ensureTempDir();
    const inputPath = tempPath(".scad");
    const pngPath = output_path ?? tempPath(".png");

    try {
      await fs.writeFile(inputPath, scad_code, "utf-8");

      const args = ["-o", pngPath, "--imgsize", size!.replace(",", ",")];
      if (camera) {
        args.push("--camera", camera);
      }
      args.push(inputPath);

      const result = await runOpenscad(args, true); // needs display for PNG
      const { errors } = parseStderr(result.stderr);
      const success = errors.length === 0 && result.exitCode === 0;

      let exists = false;
      try {
        await fs.access(pngPath);
        exists = true;
      } catch {
        // file doesn't exist
      }

      const response = {
        success: success && exists,
        png_path: exists ? pngPath : null,
        errors,
        stderr: result.stderr,
      };

      return {
        content: [{ type: "text" as const, text: JSON.stringify(response, null, 2) }],
      };
    } finally {
      await cleanup(inputPath);
    }
  }
);

// Tool 3: openscad_validate
server.tool(
  "openscad_validate",
  "Validate OpenSCAD code: compile, check for errors/warnings, verify manifold geometry, and report bounding box.",
  {
    scad_code: z.string().describe("OpenSCAD source code to validate"),
  },
  async ({ scad_code }) => {
    await ensureTempDir();
    const inputPath = tempPath(".scad");
    const stlPath = tempPath(".stl");

    try {
      await fs.writeFile(inputPath, scad_code, "utf-8");

      // Compile to binary STL (binary format helps detect manifold issues)
      const result = await runOpenscad([
        "-o",
        stlPath,
        "--export-format",
        "binstl",
        inputPath,
      ]);

      const { errors, warnings } = parseStderr(result.stderr);
      const compileSuccess = errors.length === 0 && result.exitCode === 0;

      let boundingBox = null;
      let fileSize = 0;
      let triangleCount = 0;
      let manifoldCheck = "unknown";

      if (compileSuccess) {
        try {
          const stat = await fs.stat(stlPath);
          fileSize = stat.size;
          boundingBox = await getBoundingBox(stlPath);

          // Read triangle count from binary STL header
          const header = Buffer.alloc(84);
          const fd = await fs.open(stlPath, "r");
          await fd.read(header, 0, 84, 0);
          await fd.close();
          triangleCount = header.readUInt32LE(80);

          // Check for manifold issues in stderr
          const hasManifoldWarning =
            /not.*manifold/i.test(result.stderr) ||
            /self.intersect/i.test(result.stderr);
          manifoldCheck = hasManifoldWarning ? "non-manifold" : "likely-manifold";
        } catch {
          manifoldCheck = "check-failed";
        }
      }

      // Check for suspicious dimensions (bounding box sanity)
      let dimensionWarnings: string[] = [];
      if (boundingBox) {
        const [sx, sy, sz] = boundingBox.size;
        if (sx > 500 || sy > 500 || sz > 500) {
          dimensionWarnings.push(
            `Large dimension detected: ${sx}x${sy}x${sz}mm — verify this is intentional`
          );
        }
        if (sx < 0.5 || sy < 0.5 || sz < 0.5) {
          dimensionWarnings.push(
            `Very small dimension detected: ${sx}x${sy}x${sz}mm — may be too small to print`
          );
        }
        if (sx === 0 || sy === 0 || sz === 0) {
          dimensionWarnings.push("Zero-thickness geometry detected — model may be 2D");
        }
      }

      const valid =
        compileSuccess &&
        manifoldCheck === "likely-manifold" &&
        dimensionWarnings.length === 0;

      const response = {
        valid,
        compile_success: compileSuccess,
        manifold: manifoldCheck,
        triangle_count: triangleCount,
        bounding_box: boundingBox,
        file_size_bytes: fileSize,
        errors,
        warnings: [...warnings, ...dimensionWarnings],
        stderr: result.stderr,
      };

      return {
        content: [{ type: "text" as const, text: JSON.stringify(response, null, 2) }],
      };
    } finally {
      await cleanup(inputPath, stlPath);
    }
  }
);

// Tool 4: openscad_export
server.tool(
  "openscad_export",
  "Export OpenSCAD code to a specified format (stl, 3mf, amf, off, dxf, svg, csg).",
  {
    scad_code: z.string().describe("OpenSCAD source code to export"),
    format: z
      .enum(["stl", "binstl", "3mf", "amf", "off", "dxf", "svg", "csg"])
      .default("stl")
      .describe("Output format (default: stl)"),
    output_path: z
      .string()
      .optional()
      .describe("Optional output file path. If omitted, uses a temp file."),
  },
  async ({ scad_code, format, output_path }) => {
    await ensureTempDir();
    const inputPath = tempPath(".scad");

    const extMap: Record<string, string> = {
      stl: ".stl",
      binstl: ".stl",
      "3mf": ".3mf",
      amf: ".amf",
      off: ".off",
      dxf: ".dxf",
      svg: ".svg",
      csg: ".csg",
    };
    const outPath = output_path ?? tempPath(extMap[format] || ".stl");

    try {
      await fs.writeFile(inputPath, scad_code, "utf-8");

      const args = ["-o", outPath];
      if (format === "binstl") {
        args.push("--export-format", "binstl");
      }
      args.push(inputPath);

      const result = await runOpenscad(args);
      const { errors, warnings } = parseStderr(result.stderr);
      const success = errors.length === 0 && result.exitCode === 0;

      let fileSize = 0;
      let exists = false;
      if (success) {
        try {
          const stat = await fs.stat(outPath);
          fileSize = stat.size;
          exists = true;
        } catch {
          // file doesn't exist
        }
      }

      const response = {
        success: success && exists,
        output_path: exists ? outPath : null,
        format,
        file_size_bytes: fileSize,
        errors,
        warnings,
        stderr: result.stderr,
      };

      return {
        content: [{ type: "text" as const, text: JSON.stringify(response, null, 2) }],
      };
    } finally {
      await cleanup(inputPath);
      // Keep output file — caller decides when to clean up
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
