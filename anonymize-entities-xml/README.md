# Anonymize Content of `entities.xml`

This is a stand-alone tool to anonymize the contents of an
`entities.xml` file as it is provided in Confluence exports.

Sometimes, errors appear only in the context of the structure of
a specific file. However, it is not possible to feed this file into
some tools, especially AI-based ones, due to valid data protection
converns.

This program aids in anonymizing all identifyable data.

> *Please note the disclaimer in the [main README](../README.md)*

> This is a best-effort approach! There is no guarantee that each and
> every user-provided data is anonymized! Take care and check the result,
> especially for constructs that are not yet known to the tool!

## Usage

```
php anonymize-entities-xml.php <entities.xml> > <anonymized.xml>
```

The tool uses XSLT and therefore needs the `php-xml` extension installed.

## Handled Data

### IDs

All IDs are exchanged for an MD5 hash of their value. This way associations keep
intact, but the original value is hidden.

### Timestamps

The tool creates a global random offset between 1000 and 5000 days and applies this
offset globally to all dates (creation, modification, ...). Original dates are not
re-calculable due to the randomness, but relative dates (which version came first?)
remain intact.

### User Data

User names are replaced by fakes. Same user names result in the same fake value.

E-mail addresses are replaced with `hash + "@example.com"`.

### Pages

Page titles are replaced in a stable way: based on a page title hash a number of
random words is chosen.

Body content is completely replaced with dummy text. Empty body content remains
empty, then the length is chosen roughly on the input length.
*To do:* find a way to bring macro information back. This is oftentimes a necessary part of what constitutes a bug.

### Space data

The names of spaces are anonymized in the same way as the titles of pages. Space
keys are hashed.