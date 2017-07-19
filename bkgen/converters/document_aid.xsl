<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.1" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:html="http://www.w3.org/1999/xhtml"
    xmlns:aid="http://ns.adobe.com/AdobeInDesign/4.0/"
    xmlns:aid5="http://ns.adobe.com/AdobeInDesign/5.0/"
    xmlns:pub="http://publishingxml.org/ns">

    <xsl:output method="xml" encoding="utf-8"/>

	<xsl:template match="@*|node()"><xsl:copy><xsl:apply-templates select="@*|node()"/></xsl:copy></xsl:template>

	<xsl:template match="html:section"><xsl:apply-templates/></xsl:template>
    <xsl:template match="html:div"><xsl:apply-templates/></xsl:template>
    <xsl:template match="pub:include"><xsl:apply-templates/></xsl:template>

	<xsl:template match="html:p[@class] | html:h1[@class] | html:h2[@class] | html:h3[@class] | html:h4[@class] | html:h5[@class] | html:h6[@class] | html:h7[@class] | html:h8[@class] | html:h9[@class] ">
		<xsl:copy>
        	<xsl:if test="@id">
        	    <xsl:attribute name="id"><xsl:value-of select="@id"/></xsl:attribute>
        	</xsl:if>
			<xsl:attribute name="aid:pstyle">
			    <xsl:value-of select="@class"/>
			</xsl:attribute>
			<xsl:apply-templates/>
			<xsl:if test="not(ancestor::html:td) and following::*">
                <xsl:text>&#xA;</xsl:text>
            </xsl:if>
		</xsl:copy>
		<xsl:if test="ancestor::html:td and (following-sibling::*)">
		    <pub:x000D/>
		</xsl:if>
    </xsl:template>

    <!-- Put a paragraph return at the end of every paragraph/heading that is not in a table and has following content.
        The paragraph return goes at the end of the last text in the paragraph, in case there is a span or other element
        at the end of the paragraph (which would cause InDesign to ignore the paragraph return if it were after that element). -->
<!--     <xsl:template match="text()">
        <xsl:copy><xsl:apply-templates select="@*|node()"/></xsl:copy>
        <xsl:if test="(ancestor::html:p[following::*] or ancestor::html:h1[following::*] or ancestor::html:h2[following::*] or ancestor::html:h3[following::*] or ancestor::html:h4[following::*] or ancestor::html:h5[following::*] or ancestor::html:h6[following::*] or ancestor::html:h7[following::*] or ancestor::html:h8[following::*] or ancestor::html:h9[following::*]) and not(ancestor::html:td)">
            <xsl:text>&#xA;</xsl:text>
        </xsl:if>
    </xsl:template>
 -->
    <xsl:template match="html:span[@class] | html:a[@class]">
        <xsl:copy>
        	<xsl:if test="@id">
        	    <xsl:attribute name="id"><xsl:value-of select="@id"/></xsl:attribute>
        	</xsl:if>
        	<xsl:attribute name="aid:cstyle"><xsl:value-of select="@class"/></xsl:attribute>
        	<xsl:apply-templates/>
        </xsl:copy>
    </xsl:template>

    <xsl:template match="html:table">
        <xsl:copy>
        	<xsl:if test="@id">
        	    <xsl:attribute name="id"><xsl:value-of select="@id"/></xsl:attribute>
        	</xsl:if>
        	<xsl:attribute name="aid:table">table</xsl:attribute>
        	<xsl:attribute name="aid:trows">
        	    <xsl:value-of select="count(html:tr)"/>
        	</xsl:attribute>
            <xsl:attribute name="aid:tcols">
                <xsl:value-of select="count(html:tr[1]/*)"/>
            </xsl:attribute>
        	<xsl:if test="@class">
        	    <xsl:attribute name="aid5-tablestyle"><xsl:value-of select="@class"/></xsl:attribute>
                <xsl:attribute name="aid5:tablestyle"><xsl:value-of select="@class"/></xsl:attribute>
        	</xsl:if>
            <xsl:if test="not(@class)">
                <xsl:attribute name="aid5:tablestyle">table</xsl:attribute>
                <xsl:attribute name="aid5-tablestyle">table</xsl:attribute>
            </xsl:if>
        	<xsl:if test="@data-cols">
                <xsl:attribute name="aid-tcols"><xsl:value-of select="@data-cols"/></xsl:attribute>
	        	<xsl:attribute name="aid:tcols"><xsl:value-of select="@data-cols"/></xsl:attribute>
        	</xsl:if>
        	<xsl:apply-templates/>
        </xsl:copy>
    </xsl:template>    

    <xsl:template match="html:tr">
        <xsl:apply-templates/>
    </xsl:template>

    <xsl:template match="html:td">
        <xsl:copy>
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
        </xsl:copy>
    </xsl:template>

    <xsl:template match="html:i | i">
    	<xsl:copy>
        	<xsl:if test="@id">
        	    <xsl:attribute name="id"><xsl:value-of select="@id"/></xsl:attribute>
        	</xsl:if>
    		<xsl:attribute name="aid:cstyle">italic</xsl:attribute>
    		<xsl:apply-templates/>
    	</xsl:copy>
    </xsl:template>

</xsl:stylesheet>