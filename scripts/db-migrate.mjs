/**
 * npm run db:migrate — alembic upgrade head (explicit; never run silently from setup).
 */
import { spawnSync } from "node:child_process";
import path from "node:path";

import { ROOT, backendPython, isWindows } from "./paths.mjs";

const py = backendPython();
if (!py) {
  console.error("backend/.venv not found. Run `npm run setup` first.");
  process.exit(1);
}

const result = spawnSync(py, ["-m", "alembic", "upgrade", "head"], {
  cwd: path.join(ROOT, "backend"),
  stdio: "inherit",
  shell: isWindows(),
});
process.exit(result.status ?? 1);
