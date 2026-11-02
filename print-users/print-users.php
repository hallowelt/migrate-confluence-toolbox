#!/usr/bin/env php
<?php

/**
 * Recursively searches `$inputDir` for `entities.xml` files and prints a single,
 * deduplicated CSV of Confluence users to stdout. The CSV is usable as the
 * `--usermap` input of the `analyze` command.
 */
function execute( string $inputDir ): int {
	$out = fopen( 'php://stdout', 'w' );
	fputcsv( $out, [ 'confluence-userkey', 'confluence-username', 'wiki-username' ] );

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
		if ( $xmlReader->getAttribute( 'class' ) !== 'ConfluenceUserImpl' ) {
			continue;
		}

		printUser( $xmlReader, $out );
	}

	$xmlReader->close();

	return true;
}

/**
 * @param XMLReader $xmlReader Positioned on a `ConfluenceUserImpl` object element
 *
 * @return void
 */
function printUser( XMLReader $xmlReader, $out ): void {
	static $seen = [];
	$userKey = '';
	$lowerName = '';
	$node = $xmlReader->expand();
	foreach ( $node->childNodes as $child ) {
		if ( $child->nodeType !== XML_ELEMENT_NODE ) {
			continue;
		}
		/** @var DOMElement $child */
		if ( $child->nodeName === 'id' && $child->getAttribute( 'name' ) === 'key' ) {
			$userKey = trim( $child->textContent );
		} elseif ( $child->nodeName === 'property' && $child->getAttribute( 'name' ) === 'lowerName' ) {
			$lowerName = trim( $child->textContent );
		}
	}

	if ( $userKey === '' || isset( $seen[$userKey] ) ) {
		return;
	}
	$seen[$userKey] = true;

	fputcsv( $out, [ $userKey, $lowerName, makeMWUserName( $lowerName ) ] );
}

/**
 * make a username a valid MW username
 */
function makeMWUserName( string $userName ): string {
	// Email adresses are no valid MW usernames. We just use the first part
	// While this could lead to collisions it is very unlikly
	$usernameParts = explode( '@', $userName, 2 );
	$newUsername = $usernameParts[0];
	$newUsername = ucfirst( strtolower( $newUsername ) );

	// A MW username must always be a valid page title. Use the code from
	// mediawiki-lib-migration, HalloWelt\MediaWiki\Lib\Migration\TitleBuilder,
	// for sanitizing
	$segmentParts = explode( '/', $newUsername );
	$segmentParts = array_map( 'trim', $segmentParts );
	$segment = implode( ', ', $segmentParts );
	$segment = str_replace( ' ', '_', $segment );
	$segment = preg_replace( '/' .
				# Any character not allowed is forbidden...
				"[^ %!\"$&'()*,\\-.\\/0-9:;=?@A-Z\\\\^_`a-z~\\x80-\\xFF+]" .
				# URL percent encoding sequences interfere with the ability
				# to round-trip titles -- you can't link to them consistently.
				'|%[0-9A-Fa-f]{2}' .
				# XML/HTML character references produce similar issues.
				'|&[A-Za-z0-9\x80-\xff]+;' .
				'|&#[0-9]+;' .
				'|&#x[0-9A-Fa-f]+;' .
				'/S', '_', $segment );
	// Slash is usually a legal char, but not in the segment
	$segment = preg_replace( '/\\//', '_', $segment );
	// Remove additional segments that caused issues during tests
	$segment = str_replace(
		[ ':', '%', '?', '#', '<', '>', '+', '[', ']', '{', '}', '|', '~', '&' ],
		'_',
		$segment
	);
	// MediaWiki normalizes multiple spaces/undescores into one single underscore
	$segment = preg_replace( '#_+#si', '_', $segment );
	$segment = trim( $segment, " _\t" );

	return trim( $segment );
}


exit( execute( $argv[1] ?? '' ) );