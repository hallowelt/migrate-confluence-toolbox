#!/usr/bin/env php
<?php

/**
 * Recursively searches `$inputDir` for `entities.xml` files and prints a single,
 * deduplicated CSV of Confluence spaces to stdout. The CSV is usable as the
 * `--wikis` input of the `analyze` command.
 */
function execute( string $inputDir ): int {
	$out = fopen( 'php://stdout', 'w' );
	fputcsv( $out, ['confluence-space-key', 'wiki-name', 'wiki-namespace', 'wiki-root-page'] );


	try {
		foreach ( makeFileList( $inputDir ) as $file ) {
			processFile( $file, $out );
		}
	} catch ( Throwable $e ) {
		fwrite( STDERR, "Error: " . $e->getMessage() . "\n" );
		return 1;
	} finally {
		fclose( $out );
	}
	return 0;
}

/**
 * Filter to entities.xml files only, like Analyze::makeFileList does.
 *
 * @return array<SplFileInfo>
 */
function makeFileList( string $inputDir ): array {
	$files = [];

	// An input file was specified
	if ( is_file( $inputDir ) ) {
		$files[$inputDir] = new SplFileInfo( $inputDir );
		return $files;
	}

	// An input directory was specified
	$filesIterator = new RecursiveIteratorIterator(
		new RecursiveDirectoryIterator( $inputDir ),
		RecursiveIteratorIterator::SELF_FIRST
	);

	foreach ( $filesIterator as $path => $file ) {
		if ( $file->isDir() ) {
			continue;
		}
		if ( $file->getFilename() === 'entities.xml' ) {
			$files[$file->getPathname()] = new SplFileInfo( $file->getPathname() );
		}
	}

	ksort( $files, SORT_NATURAL );

	return $files;
}

/**
 * @param SplFileInfo $file
 * @param resource $out The output stream to write the CSV to
 *
 * @return bool
 */
function processFile( SplFileInfo $file, $out ): bool {
	$xmlReader = new XMLReader();
	$xmlReader->open( $file->getPathname() );

	while ( $xmlReader->read() ) {
		if ( $xmlReader->nodeType !== XMLReader::ELEMENT || $xmlReader->name !== 'object' ) {
			continue;
		}
		if ( $xmlReader->getAttribute( 'class' ) !== 'Space' ) {
			continue;
		}

		printSpace( $xmlReader, $out );
	}

	$xmlReader->close();

	return true;
}

/**
 * @param XMLReader $xmlReader Positioned on a `Space` object element
 * @param resource $out The output stream to write the CSV to
 *
 * @return void
 */
function printSpace( XMLReader $xmlReader, $out ): void {
	static $seen = [];
	$spaceKey = '';
	$node = $xmlReader->expand();
	foreach ( $node->childNodes as $child ) {
		if ( $child->nodeType !== XML_ELEMENT_NODE ) {
			continue;
		}
		/** @var DOMElement $child */
		if ( $child->nodeName === 'property' && $child->getAttribute( 'name' ) === 'key' ) {
			$spaceKey = trim( $child->textContent );
		}
	}

	if ( $spaceKey === '' || isset( $seen[$spaceKey] ) ) {
		return;
	}
	$seen[$spaceKey] = true;

	fputcsv( $out, [ $spaceKey, spaceKeyToWikiName( $spaceKey ), '', '' ] );
}

/**
 * Convert a Confluence space key to a valid wiki name.
 *
 * @param string $spaceKey
 * @return string
 */
function spaceKeyToWikiName( string $spaceKey ): string {
	if ( str_starts_with( $spaceKey, '~' ) ) {
		$spaceKey = 'User' . ucfirst( substr( $spaceKey, 1 ) );
	}
	return $spaceKey;
}


exit( execute( $argv[1] ?? '' ) );