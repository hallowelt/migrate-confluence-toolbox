# Cross-Space Link List (AI aided)

This small Bash script connects to your Data Center Confluence instance and
fetches a list of all cross-space links between the spaces. The list is then
provided as Excel-compatible CSV file.

> *Please note the disclaimer in the [main README](../README.md)*

This tool was not tested against a live Confluence version! Please review the
code yourself before using it!

## Usage

```
confluence-cross-space-links.sh --db-type TYPE --host HOST --database NAME --user USER [options]

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
  CONFLUENCE_DB_PASSWORD   Database password. If unset, the client falls back to its
                           own mechanisms (~/.pgpass, ~/.my.cnf) or prompts.
```

Set the environment variable `CONFLUENCE_DB_PASSWORD` to access the DB.
