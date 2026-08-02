#!/bin/bash
# Refuse to commit anything that looks like real company material.
# This repo is PUBLIC (github.com/vodinhphuc/rag). The real EDR corpus is
# local-only; see docs/superpowers/specs/ section 6 for the two-corpus design.
#
# Install:  ln -sf ../../scripts/check-no-private.sh .git/hooks/pre-commit
set -euo pipefail

staged=$(git diff --cached --name-only --diff-filter=ACM)
[[ -z "$staged" ]] && exit 0

fail=0

# 1. Paths that must never be tracked
while IFS= read -r f; do
  case "$f" in
    corpus/private/*|corpus/real/*|private/*|*.private.*)
      echo "BLOCKED: $f is a private-corpus path" >&2
      fail=1
      ;;
  esac
done <<< "$staged"

# 2. Binary document formats outside the generated corpus. The generated corpus
#    is produced by scripts/render_corpus.sh into corpus/rendered/ and may be
#    committed; anything else is presumed to be a real document.
while IFS= read -r f; do
  case "$f" in
    corpus/rendered/*) continue ;;
    *.pdf|*.docx|*.doc|*.xlsx|*.xls|*.pptx|*.msg|*.eml)
      echo "BLOCKED: $f is a document binary outside corpus/rendered/" >&2
      fail=1
      ;;
  esac
done <<< "$staged"

# 3. Content markers that suggest real internal material.
#    Case-SENSITIVE and anchored: real document banners are uppercase, and
#    matching prose like "confidentiality markers" would make this hook noisy
#    enough that people bypass it with --no-verify, which is worse than nothing.
#    This script is skipped because it necessarily contains the patterns.
markers='(^|[[:space:]])(CONFIDENTIAL|INTERNAL ONLY|RESTRICTED)([[:space:]]|$)|Proprietary and Confidential|BEGIN [A-Z ]*PRIVATE KEY'
for f in $staged; do
  [[ -f "$f" ]] || continue
  [[ "$f" == "scripts/check-no-private.sh" ]] && continue
  if grep -lqE "$markers" "$f" 2>/dev/null; then
    echo "BLOCKED: $f contains a confidentiality banner" >&2
    fail=1
  fi
done

if [[ $fail -ne 0 ]]; then
  cat >&2 <<'EOF'

Commit refused. This repository is PUBLIC.
Real EDR documentation must stay in corpus/private/ (gitignored) and is
never committed. If this is a false positive, override deliberately:
    git commit --no-verify
EOF
  exit 1
fi
