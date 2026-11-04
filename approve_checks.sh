#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || -z "$1" ]]; then
  printf 'Usage: %s <feature-name>\n' "$0" >&2
  exit 2
fi

feature="$1"
if [[ ! "$feature" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
  printf 'Invalid feature name: use letters, numbers, ., _, or - only\n' >&2
  exit 2
fi

source="pending_checks.md"
destination="locked_checks/${feature}.md"

[[ -f "$source" ]] || { printf 'Missing %s\n' "$source" >&2; exit 1; }
[[ ! -e "$destination" ]] || { printf 'Refusing to overwrite %s\n' "$destination" >&2; exit 1; }

mv -- "$source" "$destination"
chmod 0444 -- "$destination" 2>/dev/null || printf 'Warning: could not set read-only permissions on %s\n' "$destination" >&2
printf 'Locked checks: %s\n' "$destination"
