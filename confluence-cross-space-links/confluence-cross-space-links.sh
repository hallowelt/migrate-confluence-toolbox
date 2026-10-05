#!/usr/bin/env bash
#
# confluence-cross-space-links.sh
#
# Export the number of links from each Confluence Data Center space to every
# other space as CSV, read directly from the Confluence database.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
PASSWORD_ENV="CONFLUENCE_DB_PASSWORD"

usage() {
  cat <<EOF
Usage: $SCRIPT_NAME --db-type TYPE --host HOST --database NAME --user USER [options]

Counts links between Confluence Data Center spaces (from the LINKS table) and
writes one CSV row per (source space, target space) pair.

Required:
  -t, --db-type TYPE     Database type: postgres | mysql
  -H, --host HOST        Database host
  -d, --database NAME    Confluence database name
  -u, --user USER        Database user (read-only access is enough)

Optional:
  -p, --port PORT        Database port (default: 5432 for postgres, 3306 for mysql)
  -o, --output FILE      CSV output file (default: cross-space-links.csv, "-" for stdout)
  -s, --include-same-space
                         Also count links within the same space
  -h, --help             Show this help and exit

Environment:
  $PASSWORD_ENV   Database password. If unset, the client falls back to its
                           own mechanisms (~/.pgpass, ~/.my.cnf) or prompts.

Required client: psql (postgres, v12 or newer) or mysql (mysql/mariadb) on PATH.

CSV format: comma-separated, UTF-8 with BOM (Excel-compatible).
CSV columns:
  source_space_key, source_space_name, target_space_key, target_space_name, link_count

Notes:
  * Only current versions of current pages and blog posts are counted
    (no page history, drafts, trash or comments).
  * Only page references with a space key are counted. Cross-space links pasted
    as full URLs are stored as http links and are not included.

Example:
  export $PASSWORD_ENV='secret'
  $SCRIPT_NAME -t postgres -H db.example.com -d confluence -u confluence -o links.csv
EOF
}

die() {
  echo "Error: $*" >&2
  echo "Run '$SCRIPT_NAME --help' for usage." >&2
  exit 1
}

# --- Parse arguments ---------------------------------------------------------
DB_TYPE="" HOST="" PORT="" DATABASE="" DB_USER=""
OUTPUT="cross-space-links.csv"
INCLUDE_SAME_SPACE=0

[[ $# -eq 0 ]] && { usage; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)               usage; exit 0 ;;
    -t|--db-type)            DB_TYPE="${2:-}";  shift 2 || die "$1 needs a value" ;;
    -H|--host)               HOST="${2:-}";     shift 2 || die "$1 needs a value" ;;
    -p|--port)               PORT="${2:-}";     shift 2 || die "$1 needs a value" ;;
    -d|--database)           DATABASE="${2:-}"; shift 2 || die "$1 needs a value" ;;
    -u|--user)               DB_USER="${2:-}";  shift 2 || die "$1 needs a value" ;;
    -o|--output)             OUTPUT="${2:-}";   shift 2 || die "$1 needs a value" ;;
    -s|--include-same-space) INCLUDE_SAME_SPACE=1; shift ;;
    *)                       die "Unknown argument: $1" ;;
  esac
done

missing=()
[[ -z "$DB_TYPE"  ]] && missing+=("--db-type")
[[ -z "$HOST"     ]] && missing+=("--host")
[[ -z "$DATABASE" ]] && missing+=("--database")
[[ -z "$DB_USER"  ]] && missing+=("--user")
if [[ ${#missing[@]} -gt 0 ]]; then
  usage >&2
  echo >&2
  die "Missing required argument(s): ${missing[*]}"
fi

case "$DB_TYPE" in
  postgres|postgresql) DB_TYPE="postgres"; PORT="${PORT:-5432}"; CLIENT="psql" ;;
  mysql|mariadb)       DB_TYPE="mysql";    PORT="${PORT:-3306}"; CLIENT="mysql" ;;
  *) die "Unsupported --db-type '$DB_TYPE' (use postgres or mysql)" ;;
esac

[[ "$PORT" =~ ^[0-9]+$ ]] || die "--port must be a number"
command -v "$CLIENT" >/dev/null 2>&1 || die "'$CLIENT' not found on PATH"

# --- Query -------------------------------------------------------------------
# Upper-case unquoted identifiers work on both PostgreSQL (folded to lower case)
# and MySQL (where Confluence tables are upper case).
SAME_SPACE_FILTER="AND l.DESTSPACEKEY <> s.SPACEKEY"
[[ $INCLUDE_SAME_SPACE -eq 1 ]] && SAME_SPACE_FILTER=""

read -r -d '' QUERY <<SQL || true
SELECT s.SPACEKEY       AS source_space_key,
       s.SPACENAME      AS source_space_name,
       t.SPACEKEY       AS target_space_key,
       t.SPACENAME      AS target_space_name,
       COUNT(*)         AS link_count
FROM LINKS l
JOIN CONTENT c ON c.CONTENTID = l.CONTENTID
JOIN SPACES  s ON s.SPACEID   = c.SPACEID
JOIN SPACES  t ON t.SPACEKEY  = l.DESTSPACEKEY
WHERE c.PREVVER IS NULL
  AND c.CONTENT_STATUS = 'current'
  AND c.CONTENTTYPE IN ('PAGE', 'BLOGPOST')
  $SAME_SPACE_FILTER
GROUP BY s.SPACEKEY, s.SPACENAME, t.SPACEKEY, t.SPACENAME
ORDER BY link_count DESC, source_space_key, target_space_key
SQL

# --- Run ---------------------------------------------------------------------
run_postgres() {
  # --csv needs psql 12+; it writes the header and quotes fields correctly.
  if [[ -n "${!PASSWORD_ENV:-}" ]]; then
    export PGPASSWORD="${!PASSWORD_ENV}"
  fi
  psql -X -q -v ON_ERROR_STOP=1 --csv \
       -h "$HOST" -p "$PORT" -U "$DB_USER" -d "$DATABASE" \
       -c "$QUERY"
}

run_mysql() {
  local -a auth=()
  # Pass the password through a temporary option file, not the command line.
  if [[ -n "${!PASSWORD_ENV:-}" ]]; then
    auth=(--defaults-extra-file=<(printf '[client]\npassword="%s"\n' "${!PASSWORD_ENV}"))
  fi
  # Batch mode prints tab-separated rows (tabs/newlines escaped as \t, \n);
  # awk turns them into RFC 4180 CSV.
  mysql "${auth[@]}" --batch --default-character-set=utf8mb4 \
        -h "$HOST" -P "$PORT" -u "$DB_USER" "$DATABASE" \
        -e "$QUERY" |
    awk -F'\t' -v OFS="," '{
        for (i = 1; i <= NF; i++) {
          gsub(/"/, "\"\"", $i)
          $i = "\"" $i "\""
        }
        print
      }'
}

run() {
  printf '\xEF\xBB\xBF'   # UTF-8 BOM for Excel
  "run_$DB_TYPE"
}

if [[ "$OUTPUT" == "-" ]]; then
  run
else
  tmp="$(mktemp "${OUTPUT}.XXXXXX")"
  trap 'rm -f "$tmp"' EXIT
  run > "$tmp"
  mv "$tmp" "$OUTPUT"
  trap - EXIT
  rows=$(( $(wc -l < "$OUTPUT") - 1 ))
  echo "Wrote $rows space pair(s) to $OUTPUT" >&2
fi
