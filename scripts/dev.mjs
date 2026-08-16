/**
 * npm run dev — start FastAPI + Next.js together (cross-platform).
 *
 * Uses the `concurrently` package so Ctrl+C stops both processes.
 * Requires: backend/.venv (run `npm run setup` first).
 */
import path from "node:path";
import { concurrently } from "concurrently";

import { ROOT, backendPython } from "./paths.mjs";

const py = backendPython();
if (!py) {
  console.error(
    "backend/.venv not found. Run `npm run setup` first (or create the venv manually).",
  );
  process.exit(1);
}

console.log("[backend]  http://127.0.0.1:8000");
console.log("[frontend] http://127.0.0.1:3000");
console.log("Press Ctrl+C to stop both.\n");

const { result } = concurrently(
  [
    {
      command: `"${py}" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`,
      name: "backend",
      cwd: path.join(ROOT, "backend"),
      prefixColor: "cyan",
    },
    {
      command: "npm run dev -- --port 3000 --hostname 127.0.0.1",
      name: "frontend",
      cwd: path.join(ROOT, "frontend"),
      prefixColor: "magenta",
    },
  ],
  {
    killOthersOn: ["failure", "success"],
    restartTries: 0,
    raw: false,
  },
);

try {
  await result;
  process.exit(0);
} catch {
  process.exit(1);
}
