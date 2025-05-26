#!/usr/bin/env node
/**
 * npm launcher for Knowledge Assistant.
 *
 * The app is a Python service; this script finds a Python >= 3.10, creates a private
 * virtualenv under ~/.knowledge-assistant/venv, installs the bundled wheel (or the pinned
 * PyPI release), and execs `ka <args>`. Re-running is fast: the venv is reused.
 *
 * No native Node modules, no network beyond pip. Works on macOS, Linux, Windows.
 */
"use strict";
const { spawnSync, spawn } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const PKG = require("../package.json");
const HOME = process.env.KA_DATA_DIR || path.join(os.homedir(), ".knowledge-assistant");
const VENV = path.join(HOME, "venv");
const WIN = process.platform === "win32";
const VENV_PY = WIN ? path.join(VENV, "Scripts", "python.exe") : path.join(VENV, "bin", "python");
const STAMP = path.join(VENV, ".ka-version");

function log(msg) { process.stderr.write(`[knowledge-assistant] ${msg}\n`); }

function pythonVersion(bin) {
  const r = spawnSync(bin, ["-c", "import sys;print('%d.%d'%sys.version_info[:2])"], { encoding: "utf8" });
  if (r.status !== 0) return null;
  const [maj, min] = r.stdout.trim().split(".").map(Number);
  return maj > 3 || (maj === 3 && min >= 10) ? `${maj}.${min}` : null;
}

function findPython() {
  const candidates = [process.env.KA_PYTHON, "python3.12", "python3.11", "python3.13", "python3.10", "python3", "python", WIN ? "py" : null].filter(Boolean);
  for (const c of candidates) {
    const args = c === "py" ? ["-3"] : [];
    const r = spawnSync(c, [...args, "-c", "import sys;print('%d.%d'%sys.version_info[:2])"], { encoding: "utf8" });
    if (r.status === 0) {
      const [maj, min] = r.stdout.trim().split(".").map(Number);
      if (maj === 3 && min >= 10) return c === "py" ? ["py", "-3"] : [c];
    }
  }
  return null;
}

function ensureVenv() {
  const upToDate = fs.existsSync(VENV_PY) && fs.existsSync(STAMP) && fs.readFileSync(STAMP, "utf8").trim() === PKG.version;
  if (upToDate) return;
  const py = findPython();
  if (!py) {
    log("Python 3.10+ is required but was not found. Install it from https://python.org and re-run.");
    process.exit(1);
  }
  fs.mkdirSync(HOME, { recursive: true });
  if (!fs.existsSync(VENV_PY)) {
    log(`creating virtualenv in ${VENV} (one-time)`);
    const r = spawnSync(py[0], [...py.slice(1), "-m", "venv", VENV], { stdio: "inherit" });
    if (r.status !== 0) process.exit(r.status ?? 1);
  }
  const wheelDir = path.join(__dirname, "..", "python");
  const wheel = fs.existsSync(wheelDir) ? fs.readdirSync(wheelDir).find((f) => f.endsWith(".whl")) : null;
  const target = wheel ? path.join(wheelDir, wheel) : `knowledge-assistant==${PKG.version}`;
  log(`installing ${wheel || target} (this downloads the embedding runtime; a few minutes the first time)`);
  const r = spawnSync(VENV_PY, ["-m", "pip", "install", "--quiet", "--upgrade", "pip", target], { stdio: "inherit" });
  if (r.status !== 0) process.exit(r.status ?? 1);
  fs.writeFileSync(STAMP, PKG.version);
}

function main() {
  ensureVenv();
  const args = process.argv.slice(2);
  const finalArgs = args.length ? args : ["serve", "--open"];
  const child = spawn(VENV_PY, ["-m", "knowledge_assistant.cli", ...finalArgs], { stdio: "inherit", env: { ...process.env, KA_DATA_DIR: HOME } });
  for (const sig of ["SIGINT", "SIGTERM"]) process.on(sig, () => child.kill(sig));
  child.on("exit", (code) => process.exit(code ?? 0));
}

main();
