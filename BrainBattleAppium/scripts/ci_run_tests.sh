#!/usr/bin/env bash
#
# BioPolymer AI — Mobile Appium CI Runner
# Runs inside the GHA Android Emulator Runner container.
#
# Steps:
#   1. Install APK onto emulator
#   2. Start Appium server
#   3. Inject GITHUB_PATH into PATH
#   4. Execute WDIO test suite
#   5. Run fallback report if WDIO fails
#

set -euo pipefail

echo "📱 BioPolymer Mobile E2E — CI Runner Starting"
echo "================================================"

# ─── Configuration ────────────────────────────────────────────
APK_PATH="${APK_PATH:-apppp/android/app/build/outputs/apk/debug/app-debug.apk}"
WDIO_SPEC="${WDIO_CI_SPEC:-tests/12_e2e/mega_android_1100.test.js}"
APPIUM_PORT=4723
MAX_WAIT=30

# ─── 1. Install APK ──────────────────────────────────────────
echo ""
echo "📦 Installing APK: ${APK_PATH}"
if [ -f "${APK_PATH}" ]; then
  adb install -r "${APK_PATH}" && echo "✅ APK installed" || echo "⚠️ APK install failed"
else
  echo "⚠️ APK not found at ${APK_PATH} — tests will use capabilities"
fi

# ─── 2. Start Appium Server ──────────────────────────────────
echo ""
echo "🚀 Starting Appium server on port ${APPIUM_PORT}..."
appium --log-level warn --port "${APPIUM_PORT}" > /tmp/appium.log 2>&1 &
APPIUM_PID=$!

# Wait for Appium to respond
echo "   Waiting for Appium to be ready..."
ELAPSED=0
while ! curl -sf "http://127.0.0.1:${APPIUM_PORT}/status" > /dev/null 2>&1; do
  sleep 1
  ELAPSED=$((ELAPSED + 1))
  if [ "${ELAPSED}" -ge "${MAX_WAIT}" ]; then
    echo "❌ Appium failed to start within ${MAX_WAIT}s"
    echo "   Last 20 lines of appium.log:"
    tail -20 /tmp/appium.log 2>/dev/null || true
    exit 1
  fi
done
echo "✅ Appium is ready (waited ${ELAPSED}s)"

# ─── 3. Fix PATH for Node.js ─────────────────────────────────
echo ""
echo "🔧 Injecting GITHUB_PATH into session PATH..."
if [ -f "${GITHUB_PATH:-}" ]; then
  while IFS= read -r line; do
    export PATH="${line}:${PATH}"
  done < "${GITHUB_PATH}"
  echo "✅ PATH updated"
else
  echo "⚠️ GITHUB_PATH file not found — using existing PATH"
fi

# Verify node is accessible
echo "   Node.js version: $(node --version 2>/dev/null || echo 'NOT FOUND')"
echo "   npm version: $(npm --version 2>/dev/null || echo 'NOT FOUND')"

# ─── 4. Run WDIO Test Suite ──────────────────────────────────
echo ""
echo "🧪 Executing WDIO test suite: ${WDIO_SPEC}"
echo "================================================"

WDIO_EXIT=0
cd "$(dirname "$0")/.."

export WDIO_CI_SPEC="${WDIO_SPEC}"
node node_modules/@wdio/cli/bin/wdio.js run wdio.conf.js || WDIO_EXIT=$?

echo ""
echo "================================================"

if [ "${WDIO_EXIT}" -ne 0 ]; then
  echo "⚠️ WDIO exited with code ${WDIO_EXIT}"

  # ─── 5. Fallback Report ────────────────────────────────
  echo "📊 Generating fallback report..."
  node utils/generateFallbackReport.js || true
fi

# Generate summary
echo ""
echo "📊 Generating step summary..."
node utils/generateSummary.js || true

echo ""
echo "✅ CI Runner complete (exit: ${WDIO_EXIT})"
exit ${WDIO_EXIT}
