<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0"
    xmlns="http://www.w3.org/1999/xhtml"
    xmlns:html="http://www.w3.org/1999/xhtml"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:pub="http://publishingxml.org/ns">

    <xsl:output method="xml" encoding="utf-8"/>

    <xsl:template match="@*|node()">
        <xsl:copy>
            <xsl:apply-templates select="@*|node()"/>
        </xsl:copy>
    </xsl:template>

    <xsl:template match="html:html">
        <pub:document>
        	<xsl:apply-templates/>
        </pub:document>
    </xsl:template>

    <xsl:template match="html:head">
        <xsl:text>&#xA;&#x9;</xsl:text>
        <xsl:copy>
            <xsl:text>&#xA;&#x9;</xsl:text>
            <xsl:apply-templates select="@*|node()"/>
        </xsl:copy>
    </xsl:template>

    <xsl:template match="html:body">
        <xsl:text>&#xA;&#x9;</xsl:text>
        <xsl:copy>
            <xsl:text>&#xA;</xsl:text>
            <section>
                <xsl:if test="//html:head/html:title">
                    <xsl:attribute name="title">
                        <xsl:value-of select="//html:head/html:title/text()"/>
                    </xsl:attribute>
                </xsl:if>
                <xsl:apply-templates select="@*"/>
                <xsl:text>&#xA;</xsl:text>
                <xsl:apply-templates select="node()"/>
                <xsl:text>&#xA;</xsl:text>
            </section>
            <xsl:text>&#xA;&#x9;</xsl:text>
        </xsl:copy>
    </xsl:template>    

    <xsl:template match="html:head/*">
        <xsl:text>&#x9;</xsl:text>
        <xsl:copy>
            <xsl:apply-templates select="@*|node()"/>
        </xsl:copy>
        <xsl:text>&#xA;&#x9;</xsl:text>
    </xsl:template>

    <xsl:template match="html:meta[@http-equiv='content-type']"/>

</xsl:stylesheet>