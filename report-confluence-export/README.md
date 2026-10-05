# Report Content of `entities.xml` (AI aided)

This is a small, vibe-coded stand-alone tool to quickly check the contents of
a `entities.xml` file as it is provided in Confluence exports.

> *Please note the disclaimer in the [main README](../README.md)*

## Usage

```
report-confluence-export.py <entities.xml> [-v | -vv]

(no flag)  quick summary of the content
-v         + per-space breakdown, content status (draft/deleted/...)
           breakdown, file size by object class -- all as aligned tables
-vv        + deduplicated page/attachment titles (with a version count
           per title), body content size split by the owning page's
           version/state (historical vs. live, and status)
```
