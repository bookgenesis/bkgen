<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.1" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns="http://www.w3.org/1999/xhtml"
    xmlns:pub="http://publishingxml.org/ns"
    xmlns:m="http://www.w3.org/1998/Math/MathML"
    exclude-result-prefixes="m pub">

    <xsl:output method="xml" encoding="utf-8" indent="yes"
	    doctype-system="http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd" 
	    doctype-public="-//W3C//DTD XHTML 1.1//EN" />

    <xsl:template match="@*|node()">
    	<xsl:copy><xsl:apply-templates select="@*|node()"/></xsl:copy>
	</xsl:template>
    
	<xsl:template match="pub:document">
		<html xmlns:epub="http://www.idpf.org/2007/ops">
			<head></head>
			<xsl:apply-templates/>
		</html>
	</xsl:template>

	<xsl:template match="pub:metadata"/>

<!-- 	<xsl:template match="pub:field[@class='REF' and @anchor]">
		<a>
			<xsl:attribute name='class'>
				<xsl:value-of select="@class"></xsl:value-of>
			</xsl:attribute>
			<xsl:attribute name="href">
				<xsl:text>#</xsl:text>
				<xsl:value-of select="@anchor"></xsl:value-of>
			</xsl:attribute>
			<xsl:apply-templates></xsl:apply-templates>
		</a>
	</xsl:template> -->

	<xsl:template match="pub:field">
	    <xsl:apply-templates/>
	</xsl:template>

	<xsl:template match="pub:field_end">
	    <xsl:apply-templates/>
	</xsl:template>
	
	<xsl:template match="pub:tab">
		<!-- four spaces are a good substitute for a tab in HTML -->
	    <xsl:text> &#x00a0;&#x00a0; </xsl:text>
	</xsl:template>

	<xsl:template match="pub:anchor_start">
	    <a>
	    	<xsl:attribute name="id">
	    	    <xsl:value-of select="@name"/>
	    	</xsl:attribute>
	    </a>
	</xsl:template>

	<xsl:template match="pub:anchor_end">
	    <a>
	    	<xsl:attribute name="id">
	    	    <xsl:value-of select="@name"/>
	    	    <xsl:text>_end</xsl:text>
	    	</xsl:attribute>
	    </a>
	</xsl:template>

	<xsl:template match="pub:hyperlink">
	    <a>
	    	<xsl:attribute name="href">
	    	    <xsl:value-of select="@filename"/>
	    	    <xsl:if test="@anchor">
	    	        <xsl:text>#</xsl:text>
	    	        <xsl:value-of select="@anchor"/>
	    	    </xsl:if>
	    	</xsl:attribute>
	    	<xsl:apply-templates/>
	    </a>
	</xsl:template>

	<xsl:template match="pub:modified">
	    <xsl:apply-templates/>
	</xsl:template>

	<xsl:template match="pub:include">
	    <xsl:apply-templates/>
	</xsl:template>

	<xsl:template match="pub:image[@filename]">
		<img>
			<xsl:attribute name="src">
			    <xsl:value-of select="@filename"/>
			</xsl:attribute>
		</img>	    
		<br></br>
	</xsl:template>

	<!-- MathML: If an altimg is available, use it; otherwise, leave the MathML alone -->
	<xsl:template match="m:math[@altimg] | math[@altimg]">
	    <img>
	    	<xsl:attribute name="src">
	    	    <xsl:value-of select="@altimg"/>
	    	</xsl:attribute>
<!-- 	    	<xsl:if test="@altimg-valign">
	    	    <xsl:attribute name="style">
	    	        <xsl:text>vertical-align:</xsl:text>
	    	        <xsl:value-of select="@altimg-valign"/>
	    	        <xsl:text>px</xsl:text>
	    	    </xsl:attribute>
	    	</xsl:if>
 -->
	    </img>
	</xsl:template>

    <xsl:template match="m:math[not(@altimg)] | math[not(@altimg)]">
    	<xsl:copy><xsl:apply-templates select="@*|node()"/></xsl:copy>
	</xsl:template>


</xsl:stylesheet>
