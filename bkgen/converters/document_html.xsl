<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.1" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns="http://www.w3.org/1999/xhtml"
    xmlns:pub="http://publishingxml.org/ns"
    xmlns:epub="http://www.idpf.org/2007/ops"
    xmlns:m="http://www.w3.org/1998/Math/MathML"
    exclude-result-prefixes="pub">

    <xsl:output method="xml" encoding="utf-8" indent="yes"
	    doctype-system="http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd" 
	    doctype-public="-//W3C//DTD XHTML 1.1//EN" />

	<!-- If the element is not otherwise dealt with, copy it as-is. -->
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

	<!-- omit PAGEREF in TOC -->
	<xsl:template match="pub:field[@class='PAGEREF' and ancestor::pub:field[@class='TOC']]">
		<span pub:cond="print">
			<xsl:apply-templates/>
		</span>
	</xsl:template>

	<xsl:template match="pub:field">
	    <xsl:apply-templates/>
	</xsl:template>

	<xsl:template match="pub:field_end">
	    <xsl:apply-templates/>
	</xsl:template>
	
	<xsl:template match="pub:tab">
		<!-- four spaces are a good substitute for a tab in HTML -->
	    <!-- <xsl:text> &#x00a0;&#x00a0; </xsl:text> -->
	    <xsl:text> </xsl:text>
	</xsl:template>

	<xsl:template match="pub:page[@n]">
		<span epub:type="pagebreak" role="doc-pagebreak">
			<xsl:attribute name="title">
				<xsl:value-of select="@n"></xsl:value-of>
			</xsl:attribute>
			<xsl:attribute name="id">
				<xsl:text>page-</xsl:text>
				<xsl:value-of select="@n"></xsl:value-of>
			</xsl:attribute>
		</span>
	</xsl:template>

	<xsl:template match="pub:colbreak"/>

	<xsl:template match="pub:anchor[@id]">
	    <span class="anchor">
	    	<xsl:attribute name="id">
	    	    <xsl:value-of select="@id"/>
	    	</xsl:attribute>
	    </span>
	</xsl:template>

	<!-- DEPRECATED: Switching to pub:anchor id="..." in pub:document -->
	<xsl:template match="pub:anchor_start[@name]">
	    <span class="anchor">
	    	<xsl:attribute name="id">
	    	    <xsl:value-of select="@name"/>
	    	</xsl:attribute>
	    </span>
	</xsl:template>

	<!-- DEPRECATED: To be removed -->
	<xsl:template match="pub:anchor_end"/>

	<xsl:template match="pub:hyperlink">
	    <a>
	    	<xsl:attribute name="href">
	    	    <xsl:value-of select="@filename"/>
	    	    <!-- @anchor is deprecated, new documents use @idref instead -->
	    	    <xsl:if test="@anchor or @idref">
	    	        <xsl:text>#</xsl:text>
	    	        <xsl:value-of select="@anchor or @idref"/>
	    	    </xsl:if>
	    	</xsl:attribute>
	    	<xsl:apply-templates/>
	    </a>
	</xsl:template>

	<!-- Assume that all pub:include elements have been pre-processed. -->
	<xsl:template match="pub:include">
	    <xsl:apply-templates/>
	</xsl:template>

	<!-- DEPRECATED: We're using html:img src in pub:document. -->
	<xsl:template match="pub:image[@filename]">
		<img>
			<xsl:attribute name="src">
			    <xsl:value-of select="@filename"/>
			</xsl:attribute>
		</img>	    
		<br></br>
	</xsl:template>

	<!-- pub:x* special characters: make sure they are represented -->
	<xsl:template match="pub:x202F"><xsl:text>&#x202F;</xsl:text></xsl:template>
	<xsl:template match="pub:x00A0"><xsl:text>&#x00A0;</xsl:text></xsl:template>
	<xsl:template match="pub:x2002"><xsl:text>&#x2002;</xsl:text></xsl:template>

	<!-- NOT YET IMPLEMENTED and therefore ignored (stripped, leaving content) -->
	<xsl:template match="pub:field"><xsl:apply-templates/></xsl:template>
	<xsl:template match="pub:cref"><xsl:apply-templates/></xsl:template>
	<!-- <xsl:template match="pub:xe"><xsl:apply-templates/></xsl:template> -->
	<xsl:template match="pub:index"><xsl:apply-templates/></xsl:template>
	<xsl:template match="pub:toc"><xsl:apply-templates/></xsl:template>
	<xsl:template match="pub:modified"><xsl:apply-templates/></xsl:template>

	<!-- MathML: If an altimg is available, use it; otherwise, leave the MathML alone -->

	<xsl:template match="m:math[@altimg] | math[@altimg]">
	    <img class="mathml">
	    	<xsl:attribute name="src">
	    	    <xsl:value-of select="@altimg"/>
	    	</xsl:attribute>
	    	<xsl:if test="@alttext">
	    		<xsl:attribute name="alt">
	    			<xsl:value-of select="@alttext"></xsl:value-of>
	    		</xsl:attribute>
	    	</xsl:if>
	    	<xsl:if test="@altimg-width or @altimg-height or @altimg-valign">
	    	    <xsl:attribute name="style">
	    	    	<!-- either height or width, not both (avoid distorting the image) -->
	    	    	<xsl:choose>
	    	    		<xsl:when test="@altimg-height">
				    		<xsl:text>height:</xsl:text>
			    	        <xsl:value-of select="@altimg-height"/>
			    	        <xsl:text>;</xsl:text>
				    	</xsl:when>
	    	    		<xsl:when test="@altimg-width">
				    		<xsl:text>width:</xsl:text>
			    	        <xsl:value-of select="@altimg-width"/>
			    	        <xsl:text>;</xsl:text>
				    	</xsl:when>	
	    	    	</xsl:choose>			    	
			    	<xsl:if test="@altimg-valign">
			    		<xsl:text>vertical-align:</xsl:text>
		    	        <xsl:value-of select="@altimg-valign"/>
		    	        <xsl:text>;</xsl:text>
			    	</xsl:if>
	    	    </xsl:attribute>
	    	</xsl:if>
	    </img>
	</xsl:template>

	<!-- altimg attribute (such as on tables) to be removed -->
	<xsl:template match="@altimg"></xsl:template>

    <xsl:template match="m:math[not(@altimg)] | math[not(@altimg)]">
    	<xsl:copy><xsl:apply-templates select="@*|node()"/></xsl:copy>
	</xsl:template>

</xsl:stylesheet>
