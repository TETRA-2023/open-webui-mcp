#!/usr/bin/env bash
# check-spec-drift.sh — diff the bundled OpenAPI snapshot against a live OpenWebUI's /openapi.json.
#
# Usage:
#   WEBUI_API_KEY=... ./scripts/check-spec-drift.sh https://owui.example.com
#
# Reports:
#   - operations present in the bundled spec but missing from live OWUI (removed)
#   - operations present in live OWUI but missing from the bundled spec (added)
#   - operations present in both with method-level differences (changed)
#
# Exit code: 0 if no drift, 1 if any drift detected, 2 on usage / fetch error.
#
# Requires: bash, curl, jq.

set -euo pipefail

if [[ $# -lt 1 || "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  sed -n '2,15p' "$0"
  exit 2
fi

WEBUI_URL="${1%/}"
BUNDLED_SPEC="$(dirname "$0")/../src/openwebui_mcp/specs/open-webui.openapi.json"

if [[ ! -f "$BUNDLED_SPEC" ]]; then
  echo "ERROR: bundled spec not found at $BUNDLED_SPEC" >&2
  exit 2
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq is required" >&2
  exit 2
fi

LIVE_SPEC=$(mktemp)
trap 'rm -f "$LIVE_SPEC"' EXIT

AUTH=()
if [[ -n "${WEBUI_API_KEY:-}" ]]; then
  AUTH=(-H "Authorization: Bearer $WEBUI_API_KEY")
fi

echo "Fetching $WEBUI_URL/openapi.json ..."
if ! curl -fsSL "${AUTH[@]}" "$WEBUI_URL/openapi.json" -o "$LIVE_SPEC" ; then
  echo "ERROR: failed to fetch live OpenAPI spec from $WEBUI_URL/openapi.json" >&2
  exit 2
fi

# Build "path|METHOD|operationId" inventories for both specs.
inventory() {
  jq -r '
    .paths | to_entries[] | .key as $p
    | .value | to_entries[]
    | select(.key | IN("get","post","put","patch","delete"))
    | [$p, (.key|ascii_upcase), (.value.operationId // "?")] | @tsv
  ' "$1" | sort
}

BUNDLED_OPS=$(inventory "$BUNDLED_SPEC")
LIVE_OPS=$(inventory "$LIVE_SPEC")

# Key on path+method for set diff (operationId may rename without semantic change).
BUNDLED_KEYS=$(echo "$BUNDLED_OPS" | awk -F'\t' '{print $1"\t"$2}' | sort -u)
LIVE_KEYS=$(echo "$LIVE_OPS"    | awk -F'\t' '{print $1"\t"$2}' | sort -u)

REMOVED=$(comm -23 <(echo "$BUNDLED_KEYS") <(echo "$LIVE_KEYS"))
ADDED=$(  comm -13 <(echo "$BUNDLED_KEYS") <(echo "$LIVE_KEYS"))

# operationId-rename detection on the path+method intersection
COMMON=$(comm -12 <(echo "$BUNDLED_KEYS") <(echo "$LIVE_KEYS"))
RENAMED=""
if [[ -n "$COMMON" ]]; then
  while IFS=$'\t' read -r p m ; do
    bid=$(awk -F'\t' -v p="$p" -v m="$m" '$1==p && $2==m {print $3}' <<<"$BUNDLED_OPS")
    lid=$(awk -F'\t' -v p="$p" -v m="$m" '$1==p && $2==m {print $3}' <<<"$LIVE_OPS")
    if [[ "$bid" != "$lid" ]]; then
      RENAMED+=$'\n'"$p"$'\t'"$m"$'\t'"$bid -> $lid"
    fi
  done <<<"$COMMON"
fi

count() {
  if [[ -z "$1" ]]; then
    echo 0
  else
    echo "$1" | wc -l
  fi
}

# Indent each line of a string by two spaces. Empty input yields no output.
indent() {
  [[ -z "$1" ]] && return
  echo "  ${1//$'\n'/$'\n  '}"
}

echo ""
echo "=== Spec drift report ==="
echo "Bundled spec: $BUNDLED_SPEC ($(jq -r '.info.version // "?"' "$BUNDLED_SPEC"))"
echo "Live spec:    $WEBUI_URL/openapi.json ($(jq -r '.info.version // "?"' "$LIVE_SPEC"))"
echo ""
echo "Bundled ops: $(count "$BUNDLED_KEYS")    Live ops: $(count "$LIVE_KEYS")"
echo ""

DRIFT=0

if [[ -n "$REMOVED" ]]; then
  DRIFT=1
  echo "--- REMOVED in live OWUI ($(count "$REMOVED")) — wrapper would advertise tools that 404 ---"
  indent "$REMOVED"
  echo ""
fi

if [[ -n "$ADDED" ]]; then
  DRIFT=1
  echo "--- ADDED in live OWUI ($(count "$ADDED")) — wrapper would not expose these tools ---"
  indent "$ADDED"
  echo ""
fi

RENAMED_TRIM="${RENAMED#$'\n'}"
if [[ -n "$RENAMED_TRIM" ]]; then
  DRIFT=1
  echo "--- operationId renames (path+method match) ---"
  indent "$RENAMED_TRIM"
  echo ""
fi

if [[ "$DRIFT" -eq 0 ]]; then
  echo "No drift detected. Bundled snapshot matches live OWUI's path+method inventory."
  exit 0
else
  echo "Drift detected. Re-pin upstream SHA + re-audit before bumping the wrapper."
  echo "(Schema-level drift inside operation request/response bodies is NOT detected by this script —"
  echo " add manual smoke for any tool you depend on heavily.)"
  exit 1
fi
