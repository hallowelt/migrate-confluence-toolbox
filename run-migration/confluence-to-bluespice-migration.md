# Confluence → BlueSpice Migration

## Setup

```bash
git clone https://github.com/hallowelt/migrate-confluence-toolbox
cp migrate-confluence-toolbox/run-migration/.env.sample migrate-confluence-toolbox/run-migration/.env
```

Edit `.env`:
- Set `TARGET_DIR` to your BlueSpice data migration directory. The result will be copied there automatically.
- Increase `WORKERS` depending on available CPU cores.

## Run migration

```bash
migrate-confluence-toolbox/run-migration/migrate.sh --config path/to/config.yaml --wikis path/to/wikis.csv path/to/confluence_export
```

## Pre-import

1. Read `result/<wiki instance>/deployment.txt`
2. Adjust the config (e.g. `post-init-settings.php`):

```php
$wgAllowExternalImages = true;
$wgFileExtensions = array_merge( $wgFileExtensions, [ 'svg', 'docx' ] );
```

## Import

First without files:

```bash
result/<wiki instance>/wikiimport.sh --wiki-root=/app/bluespice/w --add-default --mode=no-files
```

Then only files:

```bash
result/<wiki instance>/wikiimport.sh --wiki-root=/app/bluespice/w --mode=files-only
```

## Post-import

Run the maintenance scripts:

```bash
php /app/bluespice/w/maintenance/rebuildall.php
php /app/bluespice/w/extensions/BlueSpiceExtendedSearch/maintenance/rebuildIndex.php
php /app/bluespice/w/extensions/SemanticMediaWiki/maintenance/rebuildData.php
php /app/bluespice/w/maintenance/runJobs.php
```
