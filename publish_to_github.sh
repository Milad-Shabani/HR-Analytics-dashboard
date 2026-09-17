#!/usr/bin/env bash
# =============================================================================
# HR Analytics Dashboard (TelNova Communications) — Direct GitHub Publish Script
# -----------------------------------------------------------------------------
# One-shot script to initialize this project as a git repository and push it
# straight to a new (or existing empty) GitHub repository.
#
# Usage:
#   1. Create an empty repository on GitHub first (no README/license/.gitignore
#      so there is nothing to conflict with) — e.g.:
#      https://github.com/new  ->  name it:  hr-analytics-dashboard
#   2. Run this script from the project root:
#        chmod +x publish_to_github.sh
#        ./publish_to_github.sh https://github.com/<your-username>/hr-analytics-dashboard.git
#
# After pushing, enable GitHub Pages: Settings -> Pages -> Source: "GitHub
# Actions" (the included workflow at .github/workflows/deploy-pages.yml will
# then build and publish the live dashboard automatically on every push).
# =============================================================================
set -euo pipefail

REMOTE_URL="${1:-}"
BRANCH="main"

if [[ -z "$REMOTE_URL" ]]; then
  echo "Usage: ./publish_to_github.sh <git-remote-url>"
  echo "Example: ./publish_to_github.sh https://github.com/milad-shabani/hr-analytics-dashboard.git"
  exit 1
fi

echo "==> Initializing git repository (if not already one)"
if [[ ! -d .git ]]; then
  git init -b "$BRANCH"
else
  git checkout -B "$BRANCH"
fi

echo "==> Staging files"
git add .

echo "==> Creating commit"
git commit -m "Initial commit: HR Analytics Dashboard (TelNova Communications)" || echo "(nothing new to commit)"

echo "==> Setting remote 'origin' to $REMOTE_URL"
if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REMOTE_URL"
else
  git remote add origin "$REMOTE_URL"
fi

echo "==> Pushing to $REMOTE_URL ($BRANCH)"
git push -u origin "$BRANCH"

echo ""
echo "Done. Next steps on GitHub:"
echo "  1. Go to Settings -> Pages -> Source -> 'GitHub Actions'"
echo "  2. Wait for the 'Deploy dashboard to GitHub Pages' workflow to finish"
echo "  3. Your live dashboard will be at: https://<your-username>.github.io/<repo-name>/"
