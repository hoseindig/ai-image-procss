/**
 * npm run setup — safe, documented project bootstrap.
 *
 * Does:
 *  - npm install (root + frontend)
 *  - create backend/.venv if missing
 *  - pip install -e ".[dev]" into that venv
 *  - copy .env.example → .env and frontend/.env.example → frontend/.env.local if missing
 *
 * Does NOT:
 *  - download ONNX models
 *  - run alembic migrations
 *  - delete databases or virtualenvs
 *  - start servers
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import {
  ROOT,
  backendPython,
  backendPythonCandidates,
  ensureCopied,
  isWindows,
} from "./paths.mjs";

function run(command, args, opts = {}) {
  console.log(`\n> ${command} ${args.join(" ")}`);
  const result = spawnSync(command, args, {
    cwd: opts.cwd ?? ROOT,
    stdio: "inherit",
    shell: isWindows(),
    env: process.env,
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function findSystemPython() {
  for (const candidate of backendPythonCandidates()) {
    const probe = spawnSync(candidate, ["--version"], {
      encoding: "utf8",
      shell: isWindows(),
    });
    if (probe.status === 0) {
      return candidate;
    }
  }
  return null;
}

console.log("Local Face Camera — setup");
console.log("=========================");
console.log("This will install Node + Python deps.");
console.log("It will NOT download models or migrate/delete the database.\n");

run("npm", ["install"], { cwd: ROOT });
run("npm", ["install"], { cwd: path.join(ROOT, "frontend") });

const envRoot = ensureCopied(".env.example", ".env");
console.log(
  envRoot.created
    ? `Created ${envRoot.target}`
    : `Skipped .env (${envRoot.reason})`,
);
const envFront = ensureCopied("frontend/.env.example", "frontend/.env.local");
console.log(
  envFront.created
    ? `Created ${envFront.target}`
    : `Skipped frontend/.env.local (${envFront.reason})`,
);

let py = backendPython();
if (!py) {
  const systemPy = findSystemPython();
  if (!systemPy) {
    console.error("No Python 3.13+ interpreter found. Install Python 3.13 and re-run.");
    process.exit(1);
  }
  const venvDir = path.join(ROOT, "backend", ".venv");
  console.log(`\nCreating virtualenv at ${venvDir} with ${systemPy}…`);
  run(systemPy, ["-m", "venv", venvDir]);
  py = backendPython();
  if (!py) {
    console.error("Virtualenv was created but python executable was not found.");
    process.exit(1);
  }
} else {
  console.log(`\nUsing existing venv: ${py}`);
}

run(py, ["-m", "pip", "install", "--upgrade", "pip"], {
  cwd: path.join(ROOT, "backend"),
});
run(py, ["-m", "pip", "install", "-e", ".[dev]"], {
  cwd: path.join(ROOT, "backend"),
});

console.log(`
Setup finished.

Next steps (manual / explicit):
  1. Models (once, needs network):
       ${isWindows() ? "python" : "python3"} scripts/download_models.py
  2. Database migration:
       npm run db:migrate
  3. Start backend + frontend:
       npm run dev

Open:
  Frontend  http://127.0.0.1:3000
  Backend   http://127.0.0.1:8000/api/health
`);
