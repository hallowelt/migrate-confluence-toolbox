# migrate.sh — Confluence → BlueSpice migration pipeline

`migrate.sh` runs the complete [migrate-confluence](https://github.com/hallowelt/migrate-confluence) pipeline in Docker: it builds the image, recreates a clean workspace, runs the `analyze`, `extract`, `convert` and `compose` steps, and optionally deploys the result into a BlueSpice installation.

# Conventions



## Directory layout

```
<base-dir>/
├── input/       Confluence export (source), must exist
└── workspace/   intermediate and final results, recreated on every run
    └── result/  final migration result (deployed to TARGET_DIR if set)
```

## Configuration (`.env`)

The script reads a `.env` file from its own directory. Use `ENV_FILE=/path/to/file ./migrate.sh ...` to load a different one. Copy `.env.sample` to get started:

```bash
cp .env.sample .env
```

| Variable       | Default        | Description |
|----------------|----------------|-------------|
| `CODE_DIR`     | `code`         | Docker build context (the migrate-confluence source). |
| `TARGET_DIR`   | *(empty)*      | BlueSpice installation directory. If set, `workspace/result` is copied to `$TARGET_DIR/data/wiki/bluespice` after a successful run. If empty, deployment is skipped. |
| `WORKERS`      | `1`            | Parallel processes for `analyze`, `convert` and `compose`. Set to the number of CPU cores for best performance. |

Relative paths in `.env` are resolved against the directory containing the `.env` file.

Example:

```bash
CODE_DIR=../migrate-confluence
TARGET_DIR=/opt/bluespice
WORKERS=8
```

## Usage

```bash
./migrate.sh [--config <config-file>] [--wikis <wikis-csv-file>] [--workers <n>] [--quiet] <base-dir>
```

| Option              | Description |
|---------------------|-------------|
| `--config <file>`   | Application config file, mounted into the container as `/config.yaml`. |
| `--wikis <file>`    | CSV mapping Confluence spaces to target wikis (columns: `confluence-space-key;wiki-name;wiki-namespace;wiki-root-page`, see `doc/interwiki.sample.csv`). Enables the per-wiki result layout and a `manifest.json` in the workspace root. |
| `--workers <n>`     | Overrides `WORKERS` from `.env` for this run. |
| `--quiet`           | Suppresses per-page/per-file progress output of the tool. Recommended with many workers on large migrations. |

Examples:

```bash
# Simple run, settings from .env
./migrate.sh /srv/migration

# With config and space-to-wiki mapping, quiet output
./migrate.sh --config config.yaml --wikis wikis.csv --quiet /srv/migration
```

## What the script does

1. Loads `.env` and validates all paths and options before anything is changed.
2. Builds the image `bluespice/migrate-confluence:latest` from `CODE_DIR`.
3. Recreates `<base-dir>/workspace`: deletes it if present and creates it empty, owned by the container user.
4. Runs the pipeline steps in order: `analyze` → `extract` → `convert` → `compose`. The `--wikis` mapping is passed to `analyze` only; it is stored in the workspace database and used by the later steps automatically.
5. Deploys `workspace/result` to `$TARGET_DIR/data/wiki/bluespice` if `TARGET_DIR` is set.
6. Prints the total runtime.