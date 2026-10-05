# Workspace DB Inspector (AI aided)

This is a small, vibe-coded stand-alone tool to quickly check the contents of
a `workspace.sqlite` as created from the Confluence migration tool. It spawns
a web server (default port `8765`) and renders data as clickable SVG diagrams.

> *Please note the disclaimer in the [main README](../README.md)*

## Usage

```
python3 inspector.py <PATH_TO_WORKSPACE_DB>
```

Then open [localhost:8765](http://localhost:8765) and browse the contents. Add
a `?id=<ID>` query parameter to start with a specific item (page, user, space,
body content, ...).

The inspector will never change the content of the DB, it connects in read-only
mode.
