# Minimize Contents of `entities.xml` (AI aided)

This is a small, vibe-coded stand-alone tool to remove data not related to
the currently exported space in a `entities.xml` file as it is provided in
Confluence exports.

> *Please note the disclaimer in the [main README](../README.md)*

> **Attention!** This tool will remove data! It is well possible that it
> will remove too much! Use it only as last resort. In most cases, the
> migration tool itself will do the right thing.

The purpose of the tool is to work around a [Confluence bug](https://confluence.atlassian.com/confkb/a-space-export-contains-multiple-space-objects-and-fails-when-importing-into-another-confluence-instance-949242294.html)
that leads to extremely large exports that contain much more data than needed.

Note that the tool also needs the `exportDescriptor.properties` file to detect
which data to keep.

## Usage

```
minimize-confluence-export.py [--no-history] [--no-deleted] [--no-draft] <input_dir> [output_dir]

Optional flags (independent of the space filtering above, can be combined):
    --no-history  drop every superseded historical page/attachment/...
                  version (anything that is not the most current version of
                  its content), plus that version's own body/properties.
    --no-deleted  drop live content whose contentStatus is "deleted", plus
                  its historical versions, body/properties, comments, labels.
    --no-draft    same as --no-deleted, for contentStatus "draft".
```
