<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:php="http://php.net/xsl"
    xsl:extension-element-prefixes="php"
  >

  <xsl:namespace-alias stylesheet-prefix="php" result-prefix="xsl" />

  <!-- indent: this tool is for introspection, therefore make it easier
       for the introspectors. -->
  <xsl:output method="xml" encoding="UTF-8" indent="yes"/>

  <!-- identity transform -->
  <xsl:template match="@*|node()">
    <xsl:copy>
      <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
  </xsl:template>

  <!-- IDs -->

  <xsl:template match="//id |
      //property[@name='originalVersionId'] |
      //property[@name='labelableId'] |
      //property[@name='spaceId']
      ">
    <xsl:copy>
      <xsl:apply-templates select="@*"/>
      <!-- hashing the ID keeps it unique and resolvable but unrecognizable -->
      <xsl:value-of select="php:functionString('fakeId', .)" />
    </xsl:copy>
  </xsl:template>

  <!-- Timestamps -->

  <xsl:template match="
      object/property[@name='creationDate' or @name='lastModificationDate'] |
      object[@class='ContentProperty']/property[@name='dateValue'] |
      object[@class='BucketPropertySetItem']/property[@name='dateVal']">
    <xsl:copy>
      <xsl:apply-templates select="@*"/>
      <xsl:value-of select="php:functionString('fakeDate', .)" />
    </xsl:copy>
  </xsl:template>

  <!-- Users -->

  <xsl:template match="object[@class='ConfluenceUserImpl']/property[@name='name' or @name='lowerName']">
    <xsl:copy>
      <xsl:apply-templates select="@*"/>
      <xsl:value-of select="php:functionString('fakeUsername', ., @name, ../property[@name='name'])" />
    </xsl:copy>
  </xsl:template>

  <xsl:template match="object[@class='ConfluenceUserImpl']/property[@name='email']">
    <xsl:copy>
      <xsl:apply-templates select="@*"/>
      <xsl:value-of select="php:functionString('fakeEmail', .)" />
    </xsl:copy>
  </xsl:template>

  <xsl:template match="
      object[@class='ConfluenceUserImpl']/property[@name='atlassianAccountId'] |
      object[@class='Page' or @class='BlogPost' or @class='Attachment' or @class='Comment' or @class='SpaceDescription' or @class='CustomContentEntityObject']/property[@name='agentCreatorAaid' or @name='agentLastModifierAaid']">
    <xsl:copy>
      <xsl:apply-templates select="@*"/>
      <xsl:value-of select="php:functionString('fakeId', .)" />
    </xsl:copy>
  </xsl:template>

  <!-- Pages -->

  <xsl:template match="
      object[@class='Page' or
             @class='BlogPost' or
             @class='Attachment' or
             @class='CustomContentEntityObject' or
             @class='Comment' or
             @class='SpaceDescription']/property[@name='title' or
                                                 @name='lowerTitle' or
                                                 @name='versionComment']
      ">
    <xsl:copy>
      <xsl:apply-templates select="@*"/>
      <xsl:value-of select="php:functionString('fakeTitle', ., @name, ../property[@name='title'])" />
    </xsl:copy>
  </xsl:template>

  <!-- Body Content -->

  <xsl:template match="
      object[@class='BodyContent']/property[@name='body'] |
      object[@class='PageTemplate']/property[@name='content']
      ">
    <xsl:copy>
      <xsl:apply-templates select="@*"/>
      <xsl:value-of select="php:functionString('fakeContent', ., ../@class)" />
    </xsl:copy>
  </xsl:template>

  <xsl:template match="
      object[@class='PageTemplate']/property[@name='name' or @name='description'] |
      object[@class='TemplateProperty']/property[@name='name' or @name='value'] |
      object[@class='ContentProperty']/property[@name='stringValue'] |
      object[@class='ContentProperty']/property[@name='name'] |
      object[@class='ConfluenceBandanaRecord']/property[@name='context' or @name='key' or @name='value'] |
      object[@class='BucketPropertySetItem']/property[@name='textVal' or @name='stringVal']
      ">
    <xsl:copy>
      <!-- other metadata for content: hash it.
      
        "ContentProperty/@name" and "stringValue" mix macro names, page properties and user content.
      -->
      <xsl:apply-templates select="@*"/>
      <xsl:value-of select="php:functionString('md5', .)" />
    </xsl:copy>
  </xsl:template>

  <!-- Space data -->

  <xsl:template match="
      object[@class='Space']/property[@name='name'] |
      object[@class='OutgoingLink']/property[@name='destinationPageTitle' or @name='lowerDestinationPageTitle'] |
      object[@class='Label']/property[@name='name']
      ">
    <xsl:copy>
      <xsl:apply-templates select="@*"/>
      <xsl:value-of select="php:functionString('fakeTitle', .)" />
    </xsl:copy>
  </xsl:template>

  <xsl:template match="
      object[@class='Space']/property[@name='key' or @name='lowerKey'] |
      object[@class='OutgoingLink']/property[@name='destinationSpaceKey' or @name='lowerDestinationSpaceKey'] |
      object[@class='Label']/property[@name='namespace'] |
      object[@class='SpacePermission']/property[@name='group']
      ">
    <xsl:copy>
      <xsl:apply-templates select="@*"/>
      <xsl:value-of select="php:functionString('md5', .)" />
    </xsl:copy>
  </xsl:template>

</xsl:stylesheet>
