#!/bin/bash
set -e

FRONTEND_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$FRONTEND_DIR/.." && pwd)"
ANALYZE_SCRIPT="$FRONTEND_DIR/.claude/skills/find-impacted-routes/analyze_diff.py"
REPORT_JSON="$FRONTEND_DIR/impacted-routes-report.json"
REPORT_MD="$FRONTEND_DIR/impacted-routes-report.md"

BRANCH=$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)
LOCAL_SHA=$(git -C "$REPO_ROOT" rev-parse HEAD)
REMOTE_SHA=$(git -C "$REPO_ROOT" rev-parse "origin/$BRANCH" 2>/dev/null || echo "")

if [ -z "$REMOTE_SHA" ]; then
  COMMIT1=$(git -C "$REPO_ROOT" merge-base main "$LOCAL_SHA" 2>/dev/null || git -C "$REPO_ROOT" rev-parse main)
else
  COMMIT1="$REMOTE_SHA"
fi
COMMIT2="$LOCAL_SHA"

# ── Step 1: Run impacted routes analysis ──────────────────────────────────────
echo ""
echo "Step 1/4: Running impacted routes analysis..."
echo ""

if [ ! -f "$ANALYZE_SCRIPT" ]; then
  echo "  find-impacted-routes script not found — skipping analysis."
else
  python3 "$ANALYZE_SCRIPT" \
    --project-path "$FRONTEND_DIR" \
    --commit1 "$COMMIT1" \
    --commit2 "$COMMIT2" \
    --output "$FRONTEND_DIR"
fi

# ── Step 2: Map impacted routes to test files ─────────────────────────────────
echo ""
echo "Step 2/4: Mapping impacted routes to test files..."
echo ""

map_route_to_test() {
  case "$1" in
    /auth/login)          echo "e2e/auth/login.spec.ts" ;;
    /auth/signup)         echo "e2e/auth/signup.spec.ts" ;;
    /home)                echo "e2e/dashboard/home.spec.ts" ;;
    /agents)              echo "e2e/dashboard/agents.spec.ts" ;;
    /agents/create/inbound)  echo "e2e/dashboard/agents-create-inbound.spec.ts" ;;
    /agents/create/outbound) echo "e2e/dashboard/agents-create-outbound.spec.ts" ;;
    /agents/edit/*)       echo "e2e/dashboard/agents-edit.spec.ts" ;;
    *)                    echo "" ;;
  esac
}

TEST_FILES=""
if [ -f "$REPORT_JSON" ]; then
  ROUTES=$(node -e "
    const r = require('$REPORT_JSON');
    (r.impacted_routes || []).forEach(i => console.log(i.route));
  " 2>/dev/null || echo "")

  SEEN=""
  for route in $ROUTES; do
    spec=$(map_route_to_test "$route")
    if [ -n "$spec" ] && [ -f "$FRONTEND_DIR/$spec" ]; then
      case "$SEEN" in
        *"$spec"*) ;;
        *)
          SEEN="$SEEN $spec"
          TEST_FILES="$TEST_FILES $spec"
          echo "  $route -> $spec"
          ;;
      esac
    else
      if [ -n "$route" ]; then
        echo "  $route -> (no spec file)"
      fi
    fi
  done
fi

if [ -z "$TEST_FILES" ]; then
  echo "  No impacted test files found."
fi

# ── Step 3: Run impacted tests ────────────────────────────────────────────────
if [ -n "$TEST_FILES" ]; then
  echo ""
  echo "Step 3/4: Running impacted tests..."
  echo ""

  if curl -s -o /dev/null -w '' http://localhost:3000 2>/dev/null; then
    cd "$FRONTEND_DIR"
    if npx playwright test $TEST_FILES --reporter=list; then
      echo ""
      echo "  All impacted tests passed."
    else
      echo ""
      echo "  Some tests failed. Fix them before pushing."
      exit 1
    fi
  else
    echo "  Dev server not running on localhost:3000 — skipping test run."
    echo "  Start it with 'yarn dev' to enable automatic test execution."
  fi
else
  echo ""
  echo "Step 3/4: No tests to run — skipping."
fi

# ── Step 4: Commit report and push ────────────────────────────────────────────
echo ""
echo "Step 4/4: Committing report and pushing..."
echo ""

NEEDS_COMMIT=false
if ! git -C "$REPO_ROOT" diff --quiet -- "$REPORT_JSON" "$REPORT_MD" 2>/dev/null; then
  NEEDS_COMMIT=true
fi
if git -C "$REPO_ROOT" ls-files --others --exclude-standard -- "$REPORT_JSON" "$REPORT_MD" | grep -q .; then
  NEEDS_COMMIT=true
fi

if [ "$NEEDS_COMMIT" = true ]; then
  git -C "$REPO_ROOT" add "$REPORT_JSON" "$REPORT_MD"
  git -C "$REPO_ROOT" commit -m "Update impacted routes report"
  echo "  Committed updated impacted routes report."
fi

HUSKY=0 git -C "$REPO_ROOT" push origin "$BRANCH"

echo ""
echo "Pushed $BRANCH to origin."
