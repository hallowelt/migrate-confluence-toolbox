# Print All Users Found in `entities.xml` Files

Comb through all found `entities.xml` files as provided in Confluence exports
and list all users.

The list is in form of a CSV file that is optimized to be read in by
[the Confluence Migration Tool](https://github.com/hallowelt/migrate-confluence/blob/main/doc/how_to_add_author_info.md).

> *Please note the disclaimer in the [main README](../README.md)*

## Usage

```
print-users.php <entities.xml|input-folder>
```

The CSV result is printed to STDOUT. It can be redirect to a file, e.g.

```
print-users.php input/ > users.csv
```