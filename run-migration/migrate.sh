#!/usr/bin/env bash
# migrate.sh - Run the full Confluence migration pipeline sequentially.
# Usage: ./migrate.sh [--config <config-file>] [--wikis <wikis-csv-file>] [--workers <n>] [--quiet] <base-dir>
#   <base-dir> must contain:
#     input/     - the Confluence export (source)
#   <base-dir>/workspace is (re)created on every run: if it exists, it is
#   removed and created empty (owned by the container user, never by root).
#
# Settings read from .env (next to this script, or the file given in $ENV_FILE):
#   CODE_DIR      Optional Docker build context for the migration image. If set,
#                 the image is built from these local files; if empty or unset,
#                 the image is pulled from the registry instead.
#                 Relative paths are resolved against the .env file's directory.
#   TARGET_DIR    Optional deployment directory (e.g. <bluespice>/data/wiki/bluespice).
#                 If set, after a successful migration <base-dir>/workspace/result
#                 is copied into it (via Docker). Created if missing. If empty or
#                 unset, the deploy step is skipped.
#   DOCKER_IMAGE  Name of the migration image that is pulled/built and run
#                 (default: bluespice/migrate-confluence).
#   DOCKER_TAG    Tag of the migration image (default: latest). Ignored if
#                 DOCKER_IMAGE already contains a tag.
#   WORKERS       Number of parallel processes for the analyze, convert and
#                 compose steps (default: 1).
#   DOCKER_USER   uid:gid the migration container runs as (default: current user).
#
# Options:
#   --config <file>  Application config file (mounted as /config.yaml).
#   --wikis <file>   Path to the CSV file mapping Confluence spaces to target wikis
#                    (columns: confluence-space-key;wiki-name;wiki-namespace;wiki-root-page).
#                    See doc/interwiki.sample.csv. When set, the composer produces
#                    a per-wiki result layout and a "manifest.json" deployment
#                    manifest in the workspace root.
#   --workers <n>    Override WORKERS from .env for this run.
#   --quiet          Suppress the tool's own per-page/per-file progress messages
#                    (passed through as --quiet to every step). With many workers,
#                    this avoids output contention and can noticeably speed up
#                    large migrations. The "Step: <name>" headers printed by this
#                    script are unaffected.

set -euo pipefail

# This script is meant to be run by a normal user, never as root.
if [[ "$EUID" -eq 0 ]]; then
  echo "Error: do not run this script as root. Run it as a normal user with Docker access." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"

if [[ -f "$ENV_FILE" ]]; then
  ENV_DIR="$(cd "$(dirname "$ENV_FILE")" && pwd)"
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
else
  ENV_DIR="$SCRIPT_DIR"
  echo "Note: no .env file found at $ENV_FILE, using defaults." >&2
fi

CODE_DIR="${CODE_DIR:-}"
TARGET_DIR="${TARGET_DIR:-}"
DOCKER_IMAGE="${DOCKER_IMAGE:-bluespice/migrate-confluence}"
DOCKER_TAG="${DOCKER_TAG:-latest}"
WORKERS="${WORKERS:-1}"
CONFIG=""
WIKIS=""
QUIET=0

usage() {
  echo "Usage: $0 [--config <config-file>] [--wikis <wikis-csv-file>] [--workers <n>] [--quiet] <base-dir>" >&2
  exit 1
}

# Resolve a path relative to the .env directory unless it is absolute.
resolve_env_path() {
  local p="$1"
  if [[ "$p" == /* ]]; then
    echo "$p"
  else
    echo "$ENV_DIR/$p"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config)
      [[ $# -ge 2 ]] || usage
      CONFIG="$2"
      shift 2
      ;;
    --wikis)
      [[ $# -ge 2 ]] || usage
      WIKIS="$2"
      shift 2
      ;;
    --workers)
      [[ $# -ge 2 ]] || usage
      WORKERS="$2"
      shift 2
      ;;
    --quiet)
      QUIET=1
      shift
      ;;
    -*)
      echo "Error: unknown option: $1" >&2
      usage
      ;;
    *)
      break
      ;;
  esac
done

if [[ $# -ne 1 ]]; then
  usage
fi

# ---------------------------------------------------------------------------
# Validation (all checks happen before anything is deleted or built)
# ---------------------------------------------------------------------------

if [[ ! "$WORKERS" =~ ^[1-9][0-9]*$ ]]; then
  echo "Error: WORKERS must be a positive integer, got: '$WORKERS'" >&2
  exit 1
fi

if [[ ! -d "$1" ]]; then
  echo "Error: base directory not found: $1" >&2
  exit 1
fi
BASE="$(cd "$1" && pwd)"
WORKSPACE="$BASE/workspace"
RESULT_DIR="$WORKSPACE/result"

if [[ -n "$CODE_DIR" ]]; then
  CODE_DIR="$(resolve_env_path "$CODE_DIR")"
  if [[ ! -d "$CODE_DIR" ]]; then
    echo "Error: CODE_DIR not found: $CODE_DIR" >&2
    exit 1
  fi
  CODE_DIR="$(cd "$CODE_DIR" && pwd)"
fi

TARGET=""
if [[ -z "$DOCKER_IMAGE" ]]; then
  echo "Error: DOCKER_IMAGE must not be empty." >&2
  exit 1
fi
# Append DOCKER_TAG unless DOCKER_IMAGE already carries a tag.
if [[ "${DOCKER_IMAGE##*/}" != *:* ]]; then
  if [[ -z "$DOCKER_TAG" ]]; then
    echo "Error: DOCKER_TAG must not be empty." >&2
    exit 1
  fi
  DOCKER_IMAGE="$DOCKER_IMAGE:$DOCKER_TAG"
fi
if [[ -n "$TARGET_DIR" ]]; then
  TARGET_DIR="$(resolve_env_path "$TARGET_DIR")"
  if [[ -e "$TARGET_DIR" && ! -d "$TARGET_DIR" ]]; then
    echo "Error: TARGET_DIR is not a directory: $TARGET_DIR" >&2
    exit 1
  fi
  if ! mkdir -p "$TARGET_DIR"; then
    echo "Error: cannot create TARGET_DIR: $TARGET_DIR" >&2
    exit 1
  fi
  TARGET="$(cd "$TARGET_DIR" && pwd)"
fi

if [[ -n "$CONFIG" ]]; then
  if [[ ! -f "$CONFIG" ]]; then
    echo "Error: config file not found: $CONFIG" >&2
    exit 1
  fi
  CONFIG="$(cd "$(dirname "$CONFIG")" && pwd)/$(basename "$CONFIG")"
fi

if [[ -n "$WIKIS" ]]; then
  if [[ ! -f "$WIKIS" ]]; then
    echo "Error: wikis config file not found: $WIKIS" >&2
    exit 1
  fi
  WIKIS="$(cd "$(dirname "$WIKIS")" && pwd)/$(basename "$WIKIS")"
fi

# Safety guard: never run "rm -rf" on an unexpected path.
if [[ -z "$BASE" || "$BASE" == "/" || "$WORKSPACE" != */workspace ]]; then
  echo "Error: refusing to delete suspicious workspace path: '$WORKSPACE'" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Preparation
# ---------------------------------------------------------------------------

RUN_UID="$(id -u)"
RUN_GID="$(id -g)"

# The image runs as a non-root user (UID 10001 by default). Run the container
# with the real user's UID/GID instead, so it can write to the bind-mounted
# workspace and the results stay owned by that user.
DOCKER_USER="${DOCKER_USER:-$RUN_UID:$RUN_GID}"
DOCKER_UID="${DOCKER_USER%%:*}"
if [[ "$DOCKER_UID" == "0" ]]; then
  echo "Error: DOCKER_USER must not be root (uid 0)." >&2
  exit 1
fi

# An existing workspace needs root to delete only if it contains entries
# owned by someone else (e.g. root-owned files from runs with the old image).
WORKSPACE_NEEDS_ROOT=0
if [[ -e "$WORKSPACE" && -n "$(find "$WORKSPACE" ! -uid "$RUN_UID" -print -quit 2>/dev/null)" ]]; then
  WORKSPACE_NEEDS_ROOT=1
fi

# The new workspace must be owned by the container user.
CHOWN_NEEDED=0
if [[ "$DOCKER_UID" != "$EUID" ]]; then
  CHOWN_NEEDED=1
fi

START_TIME=$(date +%s)

# Run a command as root inside the migration image, for the few operations
# that need root on the host (bind-mounted directories).
docker_root() {
  docker run --rm --user 0:0 --entrypoint "" "$@"
}

if [[ -n "$CODE_DIR" ]]; then
  echo "Building Docker image from: $CODE_DIR"
  docker build -t "$DOCKER_IMAGE" "$CODE_DIR"
else
  echo "Pulling Docker image: $DOCKER_IMAGE"
  docker pull "$DOCKER_IMAGE"
fi

# Recreate the workspace: delete if present, then create it empty.
if [[ -e "$WORKSPACE" ]]; then
  if [[ "$WORKSPACE_NEEDS_ROOT" -eq 1 ]]; then
    echo "Removing existing workspace (contains files of other users, via Docker): $WORKSPACE"
    docker_root -v "$BASE":/data "$DOCKER_IMAGE" rm -rf /data/workspace
  else
    echo "Removing existing workspace: $WORKSPACE"
    rm -rf "$WORKSPACE"
  fi
fi
echo "Creating workspace: $WORKSPACE (owner $DOCKER_USER)"
mkdir -p "$WORKSPACE"
if [[ "$CHOWN_NEEDED" -eq 1 ]]; then
  docker_root -v "$BASE":/data "$DOCKER_IMAGE" chown "$DOCKER_USER" /data/workspace
fi

echo "Base:      $BASE"
[[ -n "$CODE_DIR" ]] && echo "Code:      $CODE_DIR"
echo "Image:     $DOCKER_IMAGE"
if [[ -n "$TARGET" ]]; then
  echo "Target:    $TARGET"
else
  echo "Target:    (none - deploy step will be skipped)"
fi
[[ -n "$CONFIG" ]] && echo "Config:    $CONFIG"
[[ -n "$WIKIS" ]] && echo "Wikis:     $WIKIS"
echo "Workers:   $WORKERS"
[[ "$QUIET" -eq 1 ]] && echo "Quiet:     yes"

DOCKER_VOLUME_ARGS=()
APP_CONFIG_ARGS=()
APP_WIKIS_ARGS=()
APP_QUIET_ARGS=()
if [[ -n "$CONFIG" ]]; then
  DOCKER_VOLUME_ARGS+=(-v "$CONFIG":/config.yaml)
  APP_CONFIG_ARGS=(--config /config.yaml)
fi
if [[ -n "$WIKIS" ]]; then
  DOCKER_VOLUME_ARGS+=(-v "$WIKIS":/wikis.csv)
  APP_WIKIS_ARGS=(--wikis /wikis.csv)
fi
if [[ "$QUIET" -eq 1 ]]; then
  APP_QUIET_ARGS=(--quiet)
fi

run_step() {
  local step="$1"; shift
  echo ""
  echo "=========================================="
  echo " Step: $step"
  echo "=========================================="
  docker run --rm \
    --user "$DOCKER_USER" \
    -v "$BASE":/data \
    "${DOCKER_VOLUME_ARGS[@]}" \
    "$DOCKER_IMAGE" \
    "$step" "${APP_CONFIG_ARGS[@]}" "${APP_QUIET_ARGS[@]}" "$@"
}

# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

# The --wikis option (Confluence space -> target wiki mapping) is only understood
# by the "analyze" step; it is persisted to the workspace database and picked up
# automatically by the later steps (extract, convert, compose).
run_step analyze --src /data/input     --dest /data/workspace --workers "$WORKERS" "${APP_WIKIS_ARGS[@]}"
run_step extract --src /data/input     --dest /data/workspace
run_step convert --src /data/workspace --dest /data/workspace --workers "$WORKERS"
run_step compose --src /data/workspace --dest /data/workspace --workers "$WORKERS"

echo ""
echo "=========================================="
echo " Step: deploy"
echo "=========================================="
if [[ ! -d "$RESULT_DIR" ]]; then
  echo "Error: result directory not found: $RESULT_DIR" >&2
  exit 1
fi
if [[ -n "$TARGET" ]]; then
  echo "Copying $RESULT_DIR -> $TARGET"
  docker_root \
    -v "$RESULT_DIR":/src:ro \
    -v "$TARGET":/target \
    "$DOCKER_IMAGE" \
    cp -r /src/. /target/
else
  echo "TARGET_DIR not set - skipping deployment."
fi

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
ELAPSED_FMT=$(printf '%02d:%02d:%02d' $((ELAPSED/3600)) $(((ELAPSED%3600)/60)) $((ELAPSED%60)))

echo ""
echo "=========================================="
echo " Migration complete."
if [[ -n "$TARGET" ]]; then
  echo " Deployed to: ${TARGET}"
else
  echo " Result:      ${RESULT_DIR} (not deployed)"
fi
echo " Total time: ${ELAPSED_FMT} (${ELAPSED}s)"
echo "=========================================="