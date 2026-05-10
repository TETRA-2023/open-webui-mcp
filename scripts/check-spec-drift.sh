#!/usr/bin/env bash
# check-spec-drift.sh — diff the wrapper's OpenAPI snapshot against a live OpenWebUI's /openapi.json.
#
# Usage:
#   WEBUI_API_KEY=... ./scripts/check-spec-drift.sh [--source <path>] https://owui.example.com
#
# Effective-spec resolution (highest priority first):
#   1. --source <path>            explicit override
#   2. patches/specs/open-webui.openapi.json   TETRA-side -N spec patch (when present)
#   3. src/openwebui_mcp/specs/open-webui.openapi.json   upstream-pinned snapshot
#
# Reports:
#   - operations present in the wrapper spec but missing from live OWUI (removed)
#   - operations present in live OWUI but missing from the wrapper spec (added)
#   - operations present in both with operationId renames
#   - operations present in both with body / parameter / response schema drift
#     (delegated to scripts/check-body-schema-drift.py)
#
# Exit code: 0 if no drift, 1 if any drift detected, 2 on usage / fetch error.
#
# Requires: bash, curl, jq, python3 (for body-schema drift).

set -euo pipefail

SOURCE_OVERRIDE=""
WEBUI_URL=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      sed -n '2,21p' "$0"
      exit 2
      ;;
    --source)
      [[ $# -ge 2 ]] || { echo "ERROR: --source requires a path" >&2; exit 2; }
      SOURCE_OVERRIDE="$2"
      shift 2
      ;;
    --source=*)
      SOURCE_OVERRIDE="${1#--source=}"
      shift
      ;;
    -*)
      echo "ERROR: unknown flag: $1" >&2
      exit 2
      ;;
    *)
      [[ -z "$WEBUI_URL" ]] || { echo "ERROR: too many positional args" >&2; exit 2; }
      WEBUI_URL="${1%/}"
      shift
      ;;
  esac
done

[[ -n "$WEBUI_URL" ]] || { sed -n '2,21p' "$0"; exit 2; }

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PATCHES_SPEC="$REPO_ROOT/patches/specs/open-webui.openapi.json"
PINNED_SPEC="$REPO_ROOT/src/openwebui_mcp/specs/open-webui.openapi.json"
BODY_DRIFT_SCRIPT="$REPO_ROOT/scripts/check-body-schema-drift.py"

if [[ -n "$SOURCE_OVERRIDE" ]]; then
  WRAPPER_SPEC="$SOURCE_OVERRIDE"
  WRAPPER_SOURCE="override"
elif [[ -f "$PATCHES_SPEC" ]]; then
  WRAPPER_SPEC="$PATCHES_SPEC"
  WRAPPER_SOURCE="patches/ (TETRA-side -N patch)"
else
  WRAPPER_SPEC="$PINNED_SPEC"
  WRAPPER_SOURCE="src/ (upstream pin)"
fi

if [[ ! -f "$WRAPPER_SPEC" ]]; then
  echo "ERROR: wrapper spec not found at $WRAPPER_SPEC" >&2
  exit 2
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq is required" >&2
  exit 2
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required (for body-schema drift)" >&2
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

WRAPPER_OPS=$(inventory "$WRAPPER_SPEC")
LIVE_OPS=$(inventory "$LIVE_SPEC")

# Key on path+method for set diff (operationId may rename without semantic change).
WRAPPER_KEYS=$(echo "$WRAPPER_OPS" | awk -F'\t' '{print $1"\t"$2}' | sort -u)
LIVE_KEYS=$(echo "$LIVE_OPS"    | awk -F'\t' '{print $1"\t"$2}' | sort -u)

REMOVED=$(comm -23 <(echo "$WRAPPER_KEYS") <(echo "$LIVE_KEYS"))
ADDED=$(  comm -13 <(echo "$WRAPPER_KEYS") <(echo "$LIVE_KEYS"))

# operationId-rename detection on the path+method intersection
COMMON=$(comm -12 <(echo "$WRAPPER_KEYS") <(echo "$LIVE_KEYS"))
RENAMED=""
if [[ -n "$COMMON" ]]; then
  while IFS=$'\t' read -r p m ; do
    bid=$(awk -F'\t' -v p="$p" -v m="$m" '$1==p && $2==m {print $3}' <<<"$WRAPPER_OPS")
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
echo "Wrapper spec: $WRAPPER_SPEC"
echo "  source:     $WRAPPER_SOURCE ($(jq -r '.info.version // "?"' "$WRAPPER_SPEC"))"
echo "Live spec:    $WEBUI_URL/openapi.json ($(jq -r '.info.version // "?"' "$LIVE_SPEC"))"
echo ""
echo "Wrapper ops: $(count "$WRAPPER_KEYS")    Live ops: $(count "$LIVE_KEYS")"
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

# Body / parameter / response schema drift on the operations present in both.
echo "--- body-schema drift (requestBody / parameters / responses) ---"
set +e
python3 "$BODY_DRIFT_SCRIPT" "$WRAPPER_SPEC" "$LIVE_SPEC"
BODY_RC=$?
set -e
if [[ "$BODY_RC" -eq 1 ]]; then
  DRIFT=1
elif [[ "$BODY_RC" -ne 0 ]]; then
  echo "ERROR: body-schema drift script exited $BODY_RC" >&2
  exit 2
fi
echo ""

if [[ "$DRIFT" -eq 0 ]]; then
  echo "No drift detected. Wrapper spec matches live OWUI's path+method inventory and body schemas."
  exit 0
else
  echo "Drift detected. Either re-vendor upstream + bump the SHA pin, or apply a -N spec patch (see CONTRIBUTING.md)."
  exit 1
fi
