<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.1" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns="http://www.w3.org/1999/xhtml"
    xmlns:aid="http://ns.adobe.com/AdobeInDesign/4.0/"
    xmlns:aid5="http://ns.adobe.com/AdobeInDesign/5.0/"
    xmlns:pub="http://publishingxml.org/ns"
>

    <xsl:output method="xml" encoding="utf-8"/>

	<xsl:template match="@*|node()"><xsl:copy><xsl:apply-templates select="@*|node()"/></xsl:copy></xsl:template>

    <!-- DOCUMENT STRUCTURE -->

	<xsl:template match="section"><xsl:apply-templates/></xsl:template>
    <xsl:template match="div"><xsl:apply-templates/></xsl:template>
    <xsl:template match="pub:include"><xsl:apply-templates/></xsl:template>

    <!-- PARAGRAPHS -->

	<xsl:template match="p[@class] | h1[@class] | h2[@class] | h3[@class] | h4[@class] | h5[@class] | h6[@class] | h7[@class] | h8[@class] | h9[@class] ">
		<xsl:copy>
        	<xsl:if test="@id">
        	    <xsl:attribute name="id"><xsl:value-of select="@id"/></xsl:attribute>
        	</xsl:if>
			<xsl:attribute name="aid:pstyle">
			    <xsl:value-of select="@class"/>
			</xsl:attribute>
			<xsl:apply-templates/>
		</xsl:copy>
		<xsl:if test="ancestor::td and (following-sibling::*)">
		    <pub:x000D/>
		</xsl:if>
    </xsl:template>

    <!-- put every range of text in <p> into default spans -->
    <xsl:template match="p[not(table)]//text()[not(ancestor::span)]">
        <span aid:cstyle="default"><xsl:copy><xsl:apply-templates select="@*|node()"/></xsl:copy></span>
    </xsl:template>

    <!-- Put a paragraph return at the end of every paragraph/heading that is not in a table and has following content.
        The paragraph return goes at the end of the last text in the paragraph, in case there is a span or other element
        at the end of the paragraph (which would cause InDesign to ignore the paragraph return if it were after that element). -->
        
<!--     <xsl:template match="*[(name()='p' or name()='h1' or name()='h2' or name()='h3' or name()='h4' or name()='h5' or name()='h6' or name()='h7' or name()='h8' or name()='h9') and not(ancestor::td) and following::*]//text()[last()]">
        <xsl:copy><xsl:apply-templates select="@*|node()"/></xsl:copy>
        <xsl:text>&#xA;</xsl:text>
    </xsl:template>
 -->
    <!-- SPANS -->

    <xsl:template match="span[@class] | a[@class]">
        <span>
        	<xsl:if test="@id">
        	    <xsl:attribute name="id"><xsl:value-of select="@id"/></xsl:attribute>
        	</xsl:if>
        	<xsl:attribute name="aid:cstyle"><xsl:value-of select="@class"/></xsl:attribute>
        	<xsl:apply-templates/>
        </span>
    </xsl:template>

    <!-- TABLES -->

    <xsl:template match="table">
        <table>
        	<xsl:if test="@id">
        	    <xsl:attribute name="id"><xsl:value-of select="@id"/></xsl:attribute>
        	</xsl:if>
        	<xsl:attribute name="aid:table">table</xsl:attribute>
        	<xsl:if test="@class">
        	    <xsl:attribute name="aid5-tablestyle"><xsl:value-of select="@class"/></xsl:attribute>
                <xsl:attribute name="aid5:tablestyle"><xsl:value-of select="@class"/></xsl:attribute>
        	</xsl:if>
            <xsl:if test="not(@class)">
                <xsl:attribute name="aid5:tablestyle">table</xsl:attribute>
                <xsl:attribute name="aid5-tablestyle">table</xsl:attribute>
            </xsl:if>
        	<xsl:if test="@data-cols">
	        	<xsl:attribute name="aid:tcols"><xsl:value-of select="@data-cols"/></xsl:attribute>
        	</xsl:if>
            <xsl:if test="not(@data-cols)">
                <xsl:attribute name="aid:tcols"><xsl:value-of select="count(tr[1]/*)"/></xsl:attribute>                
            </xsl:if>
            <xsl:if test="@data-rows">
                <xsl:attribute name="aid:trows"><xsl:value-of select="@data-rows"/></xsl:attribute>
            </xsl:if>
            <xsl:if test="not(@data-rows)">
                <xsl:attribute name="aid:trows"><xsl:value-of select="count(tr)"/></xsl:attribute>
            </xsl:if>
        	<xsl:apply-templates/>
        </table>
    </xsl:template>    

    <xsl:template match="tr">
        <xsl:apply-templates/>
    </xsl:template>

    <xsl:template match="td">
        <td>
        	<xsl:attribute name="aid:table">cell</xsl:attribute>
            <xsl:attribute name="aid-table">cell</xsl:attribute>
        	<xsl:if test="@id">
        	    <xsl:attribute name="id"><xsl:value-of select="@id"/></xsl:attribute>
        	</xsl:if>
        	<xsl:if test="@class">
                <xsl:attribute name="aid5-cellstyle"><xsl:value-of select="@class"/></xsl:attribute>
        	    <xsl:attribute name="aid5:cellstyle"><xsl:value-of select="@class"/></xsl:attribute>
        	</xsl:if>
            <xsl:if test="not(@class)">
                <xsl:attribute name="aid5-cellstyle">cell</xsl:attribute>
                <xsl:attribute name="aid5:cellstyle">cell</xsl:attribute>
            </xsl:if>
        	<xsl:if test="@width">
                <xsl:attribute name="aid-ccolwidth"><xsl:value-of select="@width"/></xsl:attribute>
        	    <xsl:attribute name="aid:ccolwidth"><xsl:value-of select="@width"/></xsl:attribute>
        	</xsl:if>
        	<xsl:if test="@colspan">
                <xsl:attribute name="aid-ccols"><xsl:value-of select="@colspan"/></xsl:attribute>
        	    <xsl:attribute name="aid:ccols"><xsl:value-of select="@colspan"/></xsl:attribute>
        	</xsl:if>
        	<xsl:apply-templates/>
        </td>
    </xsl:template>

    <!-- FONT FORMATTING -->

    <xsl:template match="i | i">
    	<i>
        	<xsl:if test="@id">
        	    <xsl:attribute name="id"><xsl:value-of select="@id"/></xsl:attribute>
        	</xsl:if>
    		<xsl:attribute name="aid:cstyle">italic</xsl:attribute>
    		<xsl:apply-templates/>
    	</i>
    </xsl:template>

    <xsl:template match="b | b">
        <b>
            <xsl:if test="@id">
                <xsl:attribute name="id"><xsl:value-of select="@id"/></xsl:attribute>
            </xsl:if>
            <xsl:attribute name="aid:cstyle">bold</xsl:attribute>
            <xsl:apply-templates/>
        </b>
    </xsl:template>

</xsl:stylesheet>