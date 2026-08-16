/**
 * Cross-platform path helpers for monorepo scripts.
 * Works on Windows PowerShell and Linux bash (Node.js only).
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const ROOT = path.resolve(__dirname, "..");

export function isWindows() {
  return process.platform === "win32";
}

export function backendPython() {
  const win = path.join(ROOT, "backend", ".venv", "Scripts", "python.exe");
  const nix = path.join(ROOT, "backend", ".venv", "bin", "python");
  if (fs.existsSync(win)) return win;
  if (fs.existsSync(nix)) return nix;
  return null;
}

export function backendPythonCandidates() {
  return isWindows()
    ? ["python", "py"]
    : ["python3.13", "python3", "python"];
}

export function pathExists(p) {
  return fs.existsSync(p);
}

export function ensureCopied(exampleRel, targetRel) {
  const example = path.join(ROOT, exampleRel);
  const target = path.join(ROOT, targetRel);
  if (!fs.existsSync(example)) {
    return { skipped: true, reason: `missing ${exampleRel}` };
  }
  if (fs.existsSync(target)) {
    return { skipped: true, reason: `${targetRel} already exists` };
  }
  fs.copyFileSync(example, target);
  return { created: true, target: targetRel };
}
