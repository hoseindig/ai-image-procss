/**
 * npm run test:all — run backend + frontend automated checks.
 *
 * Backend (in backend/.venv): pytest, ruff check, ruff format --check, mypy
 * Frontend: npm test, lint, typecheck, build
 * Playwright: run if Chromium binary exists; otherwise report BLOCKED (not PASS).
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

import { ROOT, backendPython, isWindows } from "./paths.mjs";

function npmBin() {
  return isWindows() ? "npm.cmd" : "npm";
}

function run(label, command, args, cwd) {
  console.log(`\n======== ${label} ========`);
  console.log(`> ${command} ${args.join(" ")}`);
  const result = spawnSync(command, args, {
    cwd,
    stdio: "inherit",
    env: process.env,
  });
  if (result.status !== 0) {
    console.error(`\nFAILED: ${label}`);
    process.exit(result.status ?? 1);
  }
  console.log(`OK: ${label}`);
}

async function chromiumAvailable(frontendDir) {
  try {
    const require = createRequire(path.join(frontendDir, "package.json"));
    const playwrightEntry = require.resolve("@playwright/test");
    const mod = await import(pathToFileURL(playwrightEntry).href);
    const exe = mod.chromium.executablePath();
    return { ok: fs.existsSync(exe), path: exe };
  } catch (err) {
    return { ok: false, path: null, error: String(err) };
  }
}

const py = backendPython();
if (!py) {
  console.error("backend/.venv not found. Run `npm run setup` first.");
  process.exit(1);
}

const backend = path.join(ROOT, "backend");
const frontend = path.join(ROOT, "frontend");

run("backend pytest", py, ["-m", "pytest", "-q"], backend);
run("backend ruff check", py, ["-m", "ruff", "check", "."], backend);
run("backend ruff format --check", py, ["-m", "ruff", "format", "--check", "."], backend);
run("backend mypy", py, ["-m", "mypy", "."], backend);

const npm = npmBin();
run("frontend test", npm, ["test"], frontend);
run("frontend lint", npm, ["run", "lint"], frontend);
run("frontend typecheck", npm, ["run", "typecheck"], frontend);
run("frontend build", npm, ["run", "build"], frontend);

console.log("\n======== frontend Playwright E2E ========");
const browser = await chromiumAvailable(frontend);
let e2eStatus = "PASS";

if (!browser.ok) {
  e2eStatus = "BLOCKED";
  console.warn(
    "Browser E2E BLOCKED: Playwright Chromium is not installed (or download failed).",
  );
  if (browser.path) {
    console.warn(`Expected binary: ${browser.path}`);
  }
  console.warn("Install once with: npm run frontend:e2e:install");
  console.warn("Automated unit/lint/build checks above still passed.");
} else {
  const e2e = spawnSync(npm, ["run", "test:e2e"], {
    cwd: frontend,
    encoding: "utf8",
    env: process.env,
  });
  const combined = `${e2e.stdout || ""}\n${e2e.stderr || ""}`;
  if (e2e.stdout) process.stdout.write(e2e.stdout);
  if (e2e.stderr) process.stderr.write(e2e.stderr);

  if (e2e.status !== 0) {
    const blocked =
      /Executable doesn't exist|browserType\.launch|Please run the following command to download|Failed to download|Timed out waiting for|chromium/i.test(
        combined,
      ) &&
      /install|download|Executable doesn't exist|browserType\.launch/i.test(combined);
    if (
      blocked ||
      /Executable doesn't exist|Failed to download Chrome for Testing/i.test(combined)
    ) {
      e2eStatus = "BLOCKED";
      console.warn(
        "\nBrowser E2E BLOCKED: Playwright Chromium is unavailable (not installed or CDN download failed).",
      );
      console.warn("Install once with: npm run frontend:e2e:install");
      console.warn("Automated unit/lint/build checks above still passed.");
    } else {
      console.error("\nFAILED: frontend Playwright E2E");
      process.exit(e2e.status ?? 1);
    }
  }
}

console.log(`
================ Summary ================
Automated backend/frontend: PASS
Browser E2E: ${e2eStatus}
`);
