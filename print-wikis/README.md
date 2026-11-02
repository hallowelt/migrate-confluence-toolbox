# Print All Spaces Found in `entities.xml` Files

Comb through all found `entities.xml` files as provided in Confluence exports
and list all spaces.

The list is in form of a CSV file that is optimized to be read in by
[the Confluence Migration Tool](https://github.com/hallowelt/migrate-confluence/blob/main/doc/configuration.md#wikis-config-csv-file---wikis).

> *Please note the disclaimer in the [main README](../README.md)*

## Usage

```
print-wikis.php <entities.xml|input-folder>
```

The CSV result is printed to STDOUT. It can be redirect to a file, e.g.

```
print-wikis.php input/ > wikis.csv
```