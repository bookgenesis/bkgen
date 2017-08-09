<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.1" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:html="http://www.w3.org/1999/xhtml"
    xmlns:aid="http://ns.adobe.com/AdobeInDesign/4.0/"
    xmlns:aid5="http://ns.adobe.com/AdobeInDesign/5.0/"
    xmlns:pub="http://publishingxml.org/ns">

    <xsl:output method="xml" encoding="utf-8"/>

	<xsl:template match="@*|node()"><xsl:copy><xsl:apply-templates select="@*|node()"/></xsl:copy></xsl:template>

    <xsl:template match="text()[(ancestor::html:p or ancestor::html:td or ancestor::html:th or ancestor::html:li) and string-length(normalize-space(.)) > 0 and not(ancestor::*[@aid:cstyle] or ancestor::*[@aid-cstyle])]">
        <html:span aid:cstyle='default'>
            <xsl:copy>
                <xsl:apply-templates select="@*"/>
            </xsl:copy>
        </html:span>
    </xsl:template>

</xsl:stylesheet>