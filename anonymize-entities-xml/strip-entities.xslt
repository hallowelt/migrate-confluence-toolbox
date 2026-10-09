<?xml version="1.0" encoding="UTF-8"?>
<!--
  strip-entities.xslt

  Reduces a Confluence `entities.xml` export to the minimum needed to
  reproduce behaviour of this tool's Analyzer/Extractor, while removing
  the bulk of page/comment content and any object types the tool never
  reads.

  What it does:
  - Drops entire <object> elements whose @class is never read by
    ConfluenceAnalyzer::getProcessors() (see src/Analyzer/ConfluenceAnalyzer.php).
    These are purely informational Confluence-internal bookkeeping objects
    (relations, notifications, permissions, bandana records, likes, ...).
  - Replaces the CDATA body of every BodyContent object's "body" property
    (the actual page/comment/space-description storage-format content)
    with a short placeholder. BodyContent objects themselves are kept
    because Page/BlogPost/Comment/SpaceDescription objects reference them
    by id via a "bodyContents" collection.
  - Leaves everything else (Page, BlogPost, Attachment, Comment, Space,
    SpaceDescription, PageTemplate, ConfluenceUserImpl, Label, Labelling,
    ContentProperty and all their properties/ids/collections) untouched,
    since titles, parent/child relations, versions and space assignments
    are exactly what is needed to reproduce title-collision issues.

  Usage:
    xsltproc strip-entities.xslt entities.xml > entities.min.xml

  Note: this does not touch files under attachments/ on disk. Missing
  attachment binaries only produce non-fatal log entries during
  `analyze`/`extract`, they do not need to be included for this purpose.
-->
  <xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
       xmlns:php="http://php.net/xsl"
    xsl:extension-element-prefixes="php"
  >
	  <xsl:namespace-alias stylesheet-prefix="php" result-prefix="xsl" />

  <xsl:output method="xml" encoding="UTF-8" indent="no"/>

  <!-- identity transform -->
  <xsl:template match="@*|node()">
    <xsl:copy>
      <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
  </xsl:template>

  <!-- Drop object types that no processor in ConfluenceAnalyzer reads -->
  <xsl:template match="object[
      @class='Content2ContentRelationEntity' or
      @class='User2ContentRelationEntity' or
      @class='Notification' or
      @class='OutgoingLink' or
      @class='SpacePermission' or
      @class='CustomContentEntityObject' or
      @class='BucketPropertySetItem' or
      @class='ConfluenceBandanaRecord' or
      @class='LikeEntity' or
      @class='ContentProperty' or
      @class='TemplateProperty'
    ]"/>

  <!-- Redact the actual page/comment/space-description content -->
  <xsl:template match="object[@class='ConfluenceUserImpl']/id">
	  <id name="key">
		  <xsl:value-of select="php:functionString('md5', .)" />
	  </id>
  </xsl:template>
  <xsl:template match="object[@class='ConfluenceUserImpl']/property" />

  <xsl:template match="object/property[@name='creator']/id">
    <id name="key">[REDACTED]</id>
  </xsl:template>
  <xsl:template match="object/property[@name='versionComment']"/>
  <xsl:template match="object/property[@name='title' or @name='lowerTitle']">
	  <property>
		  <xsl:attribute name="name">
			<xsl:value-of select="@name" />
		  </xsl:attribute>
		  <xsl:value-of select="php:functionString('md5', .)" />
	  </property>
  </xsl:template>

  <!-- Redact the actual page/comment/space-description content -->
  <xsl:template match="object[@class='BodyContent']/property[@name='body']">
    <property name="body">[REDACTED]</property>
  </xsl:template>

</xsl:stylesheet>
