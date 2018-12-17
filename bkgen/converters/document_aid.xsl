<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.1" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns="http://www.w3.org/1999/xhtml"
    xmlns:html="http://www.w3.org/1999/xhtml"
    xmlns:m="http://www.w3.org/1998/Math/MathML"
    xmlns:aid="http://ns.adobe.com/AdobeInDesign/4.0/"
    xmlns:aid5="http://ns.adobe.com/AdobeInDesign/5.0/"
    xmlns:pub="http://publishingxml.org/ns"
    xmlns:epub="http://www.idpf.org/2007/ops"
    exclude-result-prefixes="html"
>

    <xsl:output method="xml" encoding="utf-8" indent="no"/>

	<xsl:template match="@*|node()"><xsl:copy><xsl:apply-templates select="@*|node()"/></xsl:copy></xsl:template>

    <xsl:template match="pub:document">
        <pub:document 
                xmlns="http://www.w3.org/1999/xhtml" 
                xmlns:aid="http://ns.adobe.com/AdobeInDesign/4.0/" 
                xmlns:aid5="http://ns.adobe.com/AdobeInDesign/5.0/" 
                xmlns:pub="http://publishingxml.org/ns">
            <xsl:apply-templates select="@*|*"/>
        </pub:document>
    </xsl:template>

    <xsl:template match="html:html">
        <html 
                xmlns="http://www.w3.org/1999/xhtml"
                xmlns:epub="http://www.idpf.org/2007/ops"
                xmlns:aid="http://ns.adobe.com/AdobeInDesign/4.0/" 
                xmlns:aid5="http://ns.adobe.com/AdobeInDesign/5.0/">
            <xsl:apply-templates select="@*|*"/>
        </html>
    </xsl:template>

    <xsl:template match="pub:include">
        <xsl:apply-templates/>
    </xsl:template>

    <xsl:template match="html:section">
        <xsl:apply-templates></xsl:apply-templates>
    </xsl:template>

	<xsl:template match="html:p[@class] | html:h1[@class] | html:h2[@class] | html:h3[@class] | html:h4[@class] | html:h5[@class] | html:h6[@class] | html:h7[@class] | html:h8[@class] | html:h9[@class] ">
		<xsl:copy>
			<xsl:attribute name="aid:pstyle">
                <!-- <xsl:if test="ancestor::html:section[last()][@class]">
                    <xsl:value-of select="ancestor::html:section[last()]/@class"/>
                    <xsl:text> </xsl:text>
                </xsl:if> -->
			    <xsl:value-of select="@class"/>
			</xsl:attribute>
			<xsl:apply-templates select="@*|node()"/>
			<!-- <xsl:if test="not(ancestor::html:td) and following::*">
                <xsl:text>&#xA;</xsl:text>
            </xsl:if> -->
		</xsl:copy>
		<!-- <xsl:if test="ancestor::html:td and (following-sibling::*)">
		    <pub:x000A/>
		</xsl:if> -->
    </xsl:template>

    <xsl:template match="html:span[@class] | html:a[@class]">
        <xsl:copy>
        	<xsl:attribute name="aid:cstyle">
                <!-- <xsl:if test="ancestor::html:section[last()][@class]">
                    <xsl:value-of select="ancestor::html:section[last()]/@class"/>
                    <xsl:text> </xsl:text>
                </xsl:if> -->
                <xsl:value-of select="@class"/>
            </xsl:attribute>
        	<xsl:apply-templates select="@*|node()"/>
        </xsl:copy>
    </xsl:template>

    <xsl:template match="html:table">
        <p>            
            <xsl:if test="@class">
                <xsl:attribute name="aid:pstyle"><xsl:value-of select="@class"/></xsl:attribute>
            </xsl:if>
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
                    <xsl:attribute name="aid5:tablestyle"><xsl:value-of select="@class"/></xsl:attribute>
            	</xsl:if>
                <xsl:if test="not(@class)">
                    <xsl:attribute name="aid5:tablestyle">table</xsl:attribute>
                </xsl:if>
            	<xsl:if test="@data-cols">
    	        	<xsl:attribute name="aid:tcols"><xsl:value-of select="@data-cols"/></xsl:attribute>
            	</xsl:if>
            	<xsl:apply-templates/>
            </xsl:copy>
        </p>
    </xsl:template>    

    <xsl:template match="html:tr">
        <xsl:apply-templates/>
    </xsl:template>

    <xsl:template match="html:td">
        <xsl:copy>
        	<xsl:attribute name="aid:table">cell</xsl:attribute>
        	<xsl:if test="@id">
        	    <xsl:attribute name="id"><xsl:value-of select="@id"/></xsl:attribute>
        	</xsl:if>
        	<xsl:if test="@class">
        	    <xsl:attribute name="aid5:cellstyle"><xsl:value-of select="@class"/></xsl:attribute>
        	</xsl:if>
            <xsl:if test="not(@class)">
                <xsl:attribute name="aid5:cellstyle">cell</xsl:attribute>
            </xsl:if>
        	<xsl:if test="@width">
        	    <xsl:attribute name="aid:ccolwidth"><xsl:value-of select="@width"/></xsl:attribute>
        	</xsl:if>
        	<xsl:if test="@colspan">
        	    <xsl:attribute name="aid:ccols"><xsl:value-of select="@colspan"/></xsl:attribute>
        	</xsl:if>
        	<xsl:apply-templates/>
        </xsl:copy>
    </xsl:template>

    <xsl:template match="html:i | i">
    	<xsl:copy>
    		<xsl:attribute name="aid:cstyle">italic</xsl:attribute>
    		<xsl:apply-templates select="@*|node()"/>
    	</xsl:copy>
    </xsl:template>

    <xsl:template match="html:li[not(descendant::html:p)]">
        <xsl:copy>
            <xsl:attribute name="aid:pstyle">
                <xsl:if test="ancestor::html:section[last()][@class]">
                    <xsl:value-of select="ancestor::html:section[last()]/@class"/>
                </xsl:if>
                <xsl:if test="ancestor::html:section[last()][@class] and @class">
                    <xsl:text> </xsl:text>
                </xsl:if>
                <xsl:if test="@class">
                    <xsl:value-of select="@class"/>
                </xsl:if>
            </xsl:attribute>
            <xsl:apply-templates select="@*|node()"/>
            <!-- <xsl:text>&#xA;</xsl:text> -->
        </xsl:copy>        
    </xsl:template>

    <!-- DEFINITION LISTS -->

    <xsl:template match="html:dl">
        <xsl:copy>
            <xsl:attribute name="aid:pstyle">
                <xsl:if test="ancestor::html:section[last()][@class]">
                    <xsl:value-of select="ancestor::html:section[last()]/@class"/>
                </xsl:if>
                <xsl:if test="ancestor::html:section[last()][@class] and @class">
                    <xsl:text> </xsl:text>
                </xsl:if>
                <xsl:if test="@class">
                    <xsl:value-of select="@class"/>
                </xsl:if>
            </xsl:attribute>            
            <xsl:apply-templates select="@*|node()"/>
        </xsl:copy>
    </xsl:template>

    <xsl:template match="html:dt">
        <xsl:copy>
            <xsl:attribute name="aid:pstyle">
                <xsl:if test="ancestor::html:section[last()][@class]">
                    <xsl:value-of select="ancestor::html:section[last()]/@class"/>
                </xsl:if>
                <xsl:if test="ancestor::html:section[last()][@class] and ancestor::html:dl[last()][@class]">
                    <xsl:text> </xsl:text>
                </xsl:if>
                <xsl:if test="ancestor::html:dl[last()][@class]">
                    <xsl:value-of select="ancestor::html:dl[last()]/@class"/>
                </xsl:if>
            </xsl:attribute>
            <xsl:attribute name="aid:cstyle">
                <xsl:if test="ancestor::html:section[last()][@class]">
                    <xsl:value-of select="ancestor::html:section[last()]/@class"/>
                </xsl:if>    
                <xsl:if test="ancestor::html:section[last()][@class] and @class">
                    <xsl:text> </xsl:text>
                </xsl:if>
                <xsl:if test="@class">
                    <xsl:value-of select="@class"/>
                </xsl:if>
            </xsl:attribute>
            <xsl:apply-templates select="@*|node()"/>
            <xsl:choose>
                <xsl:when test="not(contains(@class, 'nobreak'))">
                    <br/>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:text> </xsl:text>
                </xsl:otherwise>
            </xsl:choose>
        </xsl:copy>
    </xsl:template>

    <xsl:template match="html:dd">
        <xsl:copy>
            <xsl:attribute name="aid:pstyle">
                <xsl:if test="ancestor::html:section[last()][@class]">
                    <xsl:value-of select="ancestor::html:section[last()]/@class"/>
                    <xsl:text> </xsl:text>
                </xsl:if>
                <xsl:if test="ancestor::html:section[last()][@class] and ancestor::html:dl[last()][@class]">
                    <xsl:text> </xsl:text>
                </xsl:if>
                <xsl:if test="ancestor::html:dl[last()][@class]">
                    <xsl:value-of select="ancestor::html:dl[last()]/@class"/>
                </xsl:if>
            </xsl:attribute>
            <xsl:apply-templates select="@*|node()"/>
        </xsl:copy>
    </xsl:template>

    <!-- UNSTYLED TEXT -->

    <xsl:template match="text()[(ancestor::html:p or ancestor::html:td or ancestor::html:th or ancestor::html:li or ancestor::html:dt or ancestor::html:dd) and string-length(normalize-space(.)) > 0 and not(ancestor::html:span[@class] or ancestor::html:dt[@class] or ancestor::html:dd[@class] or ancestor::m:math)]">
        <span aid:cstyle='default'>
            <xsl:copy>
                <xsl:apply-templates select="@*|node()"/>
            </xsl:copy>
        </span>
    </xsl:template>

</xsl:stylesheet>