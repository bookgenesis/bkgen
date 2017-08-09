<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.1" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:html="http://www.w3.org/1999/xhtml"
    xmlns:m="http://www.w3.org/1998/Math/MathML"
    xmlns:pub="http://publishingxml.org/ns"
    xmlns:db="http://docbook.org/ns/docbook">

    <xsl:output method="xml" encoding="utf-8"/>

    <!-- DocBook 4 uses the default (no) namespace, whereas DocBook 5 uses the db: namespace. Support both. -->
    
    <xsl:template match="@*|node()"><xsl:copy><xsl:apply-templates select="@*|node()"/></xsl:copy></xsl:template>
    
    <xsl:template match="chapter | db:chapter">
        <html:section class="chapter">
        	<xsl:apply-templates select="@id|node()"/>
        </html:section>
    </xsl:template>

    <xsl:template match="section | db:section | qandaset | db:qandaset | qandaentry | db:qandaentry | question | db:question | answer | db:answer">
    	<html:section>
    		<xsl:attribute name="class">
    		    <xsl:value-of select="name()"/>
    		</xsl:attribute>
    		<xsl:apply-templates select="@id|node()"/>
    	</html:section>
    </xsl:template>

    <xsl:template match="title | db:title">
    	<xsl:param name="level" select="count(ancestor::*[title])"/>
    	<xsl:element name="h{$level}">
            <xsl:apply-templates/>
        </xsl:element>
    </xsl:template>

	 <xsl:template match="para | db:para | equation | db:equation | informalequation | db:informalequation">
	 	<html:p>
    		<xsl:if test="@id">
    		    <xsl:attribute name="id">
    		        <xsl:value-of select="@id"/>
    		    </xsl:attribute>
    		</xsl:if>
	 		<xsl:attribute name="class">
                <xsl:if test="@role">
                    <xsl:value-of select="@role"/>
                </xsl:if>
                <xsl:if test="not(@role)">
                    <xsl:value-of select="name()"/>
                </xsl:if>
	 		</xsl:attribute>
	 		<xsl:apply-templates/>
	 	</html:p> 
	 </xsl:template>

 	<xsl:template match="indexterm | db:indexterm"></xsl:template>
 	<xsl:template match="footnote | db:footnote">
 	    <pub:footnote>
 	    	<xsl:apply-templates/>
 	    </pub:footnote>
 	</xsl:template>    

 	<xsl:template match="xref[@linkend] | db:xref[@linkend]">
        <xsl:if test="//*[@id='{@linkend}']">
            <html:a>
                <xsl:attribute name="href">
                    <xsl:text>#</xsl:text>
                    <xsl:value-of select="@linkend"/>
                </xsl:attribute>
                <xsl:value-of select="@linkend"/>
            </html:a>
        </xsl:if>
        <xsl:if test="not(//*[@id='{@linkend}'])">
            <html:span class="bold">
                <xsl:value-of select="@linkend"/>
            </html:span>
        </xsl:if>

 	</xsl:template>

 	<xsl:template match="inlineequation | db:inlineequation | informalfigure | db:informalfigure">
 	    <html:span>
            <xsl:attribute name="class">
                <xsl:value-of select="name()"/>
            </xsl:attribute>
 	    	<xsl:apply-templates/>
 	    </html:span>
 	</xsl:template>

 	<xsl:template match="m:math">
 	    <html:img>
            <xsl:attribute name="src">
                <xsl:value-of select="@altimg"></xsl:value-of>
            </xsl:attribute>
            <xsl:if test="ancestor::inlineequation | ancestor::db:inlineequation">
                <xsl:attribute name="height">
                    <xsl:text>1em</xsl:text>
                </xsl:attribute>
            </xsl:if>
 	    	<xsl:if test="@altimg-valign">
 	    	    <xsl:attribute name="style">
 	    	        <xsl:text>vertical-align:</xsl:text>
 	    	        <xsl:value-of select="@altimg-valign"/>
 	    	        <xsl:text>pt;</xsl:text>
 	    	    </xsl:attribute>
 	    	</xsl:if>
 	    </html:img>
 	</xsl:template>

    <xsl:template match="table | db:table | informaltable | db:informaltable">
        <html:table class="{name()}">
            <xsl:apply-templates select="@id|node()"></xsl:apply-templates>
        </html:table>
    </xsl:template>

 	<xsl:template match="tgroup | db:tgroup">
 	    <xsl:apply-templates/>
 	</xsl:template>

    <xsl:template match="colspec | db:colspec"></xsl:template>

 	<xsl:template match="row | db:row">
 	    <html:tr>
 	    	<xsl:apply-templates/>
 	    </html:tr>
 	</xsl:template>

    <xsl:template match="entry[ancestor::thead] | db:entry[ancestor::db:thead]">
        <html:th>
            <xsl:apply-templates/>
        </html:th>        
    </xsl:template>

 	<xsl:template match="entry | db:entry">
 	    <html:td>
            <xsl:apply-templates/>
        </html:td>
 	</xsl:template>

    <xsl:template match="orderedlist | db:orderedlist">
        <html:ol>
            <xsl:if test="@numeration">
                <xsl:attribute name="class"><xsl:value-of select="@numeration"/></xsl:attribute>
            </xsl:if>
            <xsl:apply-templates/>
        </html:ol>
    </xsl:template>

    <xsl:template match="listitem | db:listitem">
        <html:li>
            <xsl:apply-templates/>
        </html:li>
    </xsl:template>

    <xsl:template match="mediaobject | db:mediaobject | imageobject | db:imageobject">
        <xsl:apply-templates/>
    </xsl:template>

    <xsl:template match="imagedata | db:imagedata">
        <html:img>
            <xsl:attribute name="src">
                <xsl:value-of select="@fileref"/>
            </xsl:attribute>
            <xsl:apply-templates/>
        </html:img>
    </xsl:template>

    <xsl:template match="emphasis[@role] | db:emphasis[@role]">
        <html:span class="{@role}"><xsl:apply-templates select="@id|node()"/></html:span>
    </xsl:template>

    <xsl:template match="emphasis[not(@role)] | db:emphasis[not(@role)]">
        <html:span class="emphasis"><xsl:apply-templates select="@id|node()"/></html:span>
    </xsl:template>

    <xsl:template match="subscript | db:subscript">
        <html:span class="subscript"><xsl:apply-templates select="@id|node()"></xsl:apply-templates></html:span>
    </xsl:template>

    <xsl:template match="superscript | db:superscript">
        <html:span class="superscript"><xsl:apply-templates select="@id|node()"></xsl:apply-templates></html:span>
    </xsl:template>

</xsl:stylesheet>