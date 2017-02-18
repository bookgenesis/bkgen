<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns="http://www.w3.org/1999/xhtml"
    xmlns:pub="http://publishingxml.org/ns"
    xmlns:opf="http://www.idpf.org/2007/opf"

    xmlns:container="urn:oasis:names:tc:opendocument:xmlns:container" 
    xmlns:dc="http://purl.org/dc/elements/1.1/" 
    xmlns:dcterms="http://purl.org/dc/terms/" 
    xmlns:dcmitype="http://purl.org/dc/dcmitype/" 
    xmlns:epub="http://www.idpf.org/2007/ops" 
    xmlns:ncx="http://www.daisy.org/z3986/2005/ncx/" 
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"

    xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" 
    xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" 
    xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" 
    xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" 
    xmlns:mo="http://schemas.microsoft.com/office/mac/office/2008/main" 
    xmlns:mv="urn:schemas-microsoft-com:mac:vml" 
    xmlns:o="urn:schemas-microsoft-com:office:office" 
    xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture" 
    xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" 
    xmlns:v="urn:schemas-microsoft-com:vml" 
    xmlns:w10="urn:schemas-microsoft-com:office:word" 
    xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" 
    xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml" 
    xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" 
    xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml" 
    xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing" 
    xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" 
    xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" 
    xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" 
    xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" 
    xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"

    exclude-result-prefixes="a aml dt m mc mo mv o pic r sl v ve w w10 w14 w15 wne wp wp14 wpc wpg wpi wps wsp wx"
    >

    <xsl:output method="xml" encoding="utf-8"/>

    <xsl:param name="source"/>

    <!-- This default template matches everything and passes it through unchanged. -->
    <xsl:template match="@*|node()">
        <xsl:copy>
            <xsl:apply-templates select="@*|node()"/>
        </xsl:copy>
    </xsl:template>

    <xsl:template match="w:document">
        <pub:document>
            <xsl:attribute name="src">
                <xsl:value-of select="$source"/>
            </xsl:attribute>
            <xsl:text>&#xA;</xsl:text>
        	<xsl:apply-templates/>
        	<xsl:text>&#xA;</xsl:text>
        </pub:document>
    </xsl:template>

    <xsl:template match="w:body">
        <xsl:text>&#x9;</xsl:text>
        <body>
            <xsl:text>&#xA;</xsl:text>
        	<xsl:apply-templates/>
        <xsl:text>&#x9;</xsl:text>
        </body>
    </xsl:template>

    <xsl:template match="w:p">
        <xsl:choose>
            <xsl:when test=".//w:sectPr">
                <xsl:apply-templates/>
            </xsl:when>
            <xsl:otherwise>
                <p>
                    <xsl:if test="w:pPr/w:pStyle">
                        <xsl:attribute name="class">
                            <xsl:value-of select="w:pPr/w:pStyle/@w:val"/>
                        </xsl:attribute>    
                    </xsl:if>
                    <xsl:if test="w:pPr/w:jc[@w:val='left' or @w:val='right' or @w:val='center']">
                        <xsl:attribute name="text-align"><xsl:value-of select="w:pPr/w:jc/@w:val"/></xsl:attribute>
                    </xsl:if>
                    <xsl:if test="w:pPr/w:jc[@w:val='both']">
                        <xsl:attribute name="text-align">justify</xsl:attribute>
                    </xsl:if>
                    <xsl:apply-templates/>
                </p>                    
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <xsl:template match="w:sectPr">
    	<pub:section_end>
        	<xsl:if test="w:type[@w:val]">
        	    <xsl:attribute name="class">
        	        <xsl:value-of select="w:type/@w:val"/>
        	    </xsl:attribute>
        	</xsl:if>
        	<!-- <xsl:apply-templates/> -->
        </pub:section_end>
    </xsl:template>

    <xsl:template match="w:footnote">
        <pub:footnote>
            <xsl:attribute name="name">
                <xsl:value-of select="@w:id"/>
            </xsl:attribute>
            <xsl:apply-templates/>
            <xsl:text></xsl:text>
        </pub:footnote>        
    </xsl:template>

    <xsl:template match="w:footnoteRef">
        <!-- <pub:footnote-ref><xsl:apply-templates/></pub:footnote-ref> -->
    </xsl:template>

    <xsl:template match="w:endnote">
        <pub:endnote>
            <xsl:attribute name="name">
                <xsl:value-of select="@w:id"/>
            </xsl:attribute>
            <xsl:apply-templates/>
            <xsl:text></xsl:text>
        </pub:endnote>        
    </xsl:template>

    <xsl:template match="w:endnoteRef">
        <!-- <pub:endnote-ref><xsl:apply-templates/></pub:endnote-ref> -->
    </xsl:template>

    <!-- COMMENTS -->
    <xsl:template match="w:comment">
        <pub:comment>
            <xsl:attribute name="name">
                <xsl:value-of select="@w:id"/>
            </xsl:attribute>
            <xsl:attribute name="datetime">
                <xsl:value-of select="@w:date"/>
            </xsl:attribute>
            <xsl:attribute name="author">
                <xsl:value-of select="@w:author"/>
            </xsl:attribute>
            <xsl:apply-templates select="node()"/>
            <xsl:text></xsl:text>  
        </pub:comment>
    </xsl:template>

    <!-- w:annotationRef = text marker for comment metadata, not needed -->
    <xsl:template match="w:annotationRef"/> 

    <xsl:template match="w:commentRangeStart">
        <a class="comment-range">
            <xsl:attribute name="id">
                <xsl:text>start_comment_</xsl:text>
                <xsl:value-of select="@w:id"/>
            </xsl:attribute>
        </a>
    </xsl:template>

    <xsl:template match="w:commentRangeEnd">
        <a class="comment-range">
            <xsl:attribute name="id">
                <xsl:text>end_comment_</xsl:text>
                <xsl:value-of select="@w:id"/>
            </xsl:attribute>
        </a>
    </xsl:template>

    <!-- SPAN -->

    <xsl:template match="w:r[w:rPr]">
        <span>
            <!-- class name -->
            <!-- omit when style in "CommentReference", "FootnoteReference", "EndnoteReference" because it wraps a comment/footnote/endnote or its reference -->
            <xsl:if test="w:rPr/w:rStyle[@w:val!='CommentReference' and @w:val!='FootnoteReference' and @w:val!='EndnoteReference']">
                <xsl:attribute name="class">
                    <xsl:value-of select="w:rPr/w:rStyle/@w:val"/>
                </xsl:attribute>
            </xsl:if>

            <!-- font formatting: TOGGLE PROPERTIES. They will need post-processing -->
            <!-- italic -->
            <xsl:if test="w:rPr/w:i | w:rPr/w:iCs">
                <xsl:attribute name="ital">
                    <xsl:call-template name="toggle-property-value">
                        <xsl:with-param name="val" select="w:rPr/w:i/@w:val | w:rPr/w:iCs/@w:val"/>
                    </xsl:call-template>
                </xsl:attribute>
            </xsl:if>
            <!-- bold -->
            <xsl:if test="w:rPr/w:b | w:rPr/w:bCs">
                <xsl:attribute name="bold">
                    <xsl:call-template name="toggle-property-value">
                        <xsl:with-param name="val" select="w:rPr/w:b/@w:val | w:rPr/w:bCs/@w:val"/>
                    </xsl:call-template>
                </xsl:attribute>
            </xsl:if>
            <!-- caps -->
            <xsl:if test="w:rPr/w:caps">
                <xsl:attribute name="caps">
                    <xsl:call-template name="toggle-property-value">
                        <xsl:with-param name="val" select="w:rPr/w:caps/@w:val"/>
                    </xsl:call-template>
                </xsl:attribute>
            </xsl:if>
            <!-- small caps -->
            <xsl:if test="w:rPr/w:smallCaps">
                <xsl:attribute name="smallcaps">
                    <xsl:call-template name="toggle-property-value">
                        <xsl:with-param name="val" select="w:rPr/w:smallCaps/@w:val"/>
                    </xsl:call-template>
                </xsl:attribute>
            </xsl:if>
            <!-- strikethrough -->
            <xsl:if test="w:rPr/w:strike">
                <xsl:attribute name="strike">
                    <xsl:call-template name="toggle-property-value">
                        <xsl:with-param name="val" select="w:rPr/w:strike/@w:val"/>
                    </xsl:call-template>
                </xsl:attribute>
            </xsl:if>
            <!-- double strikethrough -->
            <xsl:if test="w:rPr/w:dstrike">
                <xsl:attribute name="dstrike">
                    <xsl:call-template name="toggle-property-value">
                        <xsl:with-param name="val" select="w:rPr/w:dstrike/@w:val"/>
                    </xsl:call-template>
                </xsl:attribute>
            </xsl:if>
            <!-- hidden text -->
            <xsl:if test="w:rPr/w:vanish">
                <xsl:attribute name="hidden">
                    <xsl:call-template name="toggle-property-value">
                        <xsl:with-param name="val" select="w:rPr/w:vanish/@w:val"/>
                    </xsl:call-template>
                </xsl:attribute>
            </xsl:if>            

            <!-- font formatting: NON-TOGGLE PROPERTIES. -->
            <!-- vertical alignment: superscript, subscript, baseline -->
            <xsl:if test="w:rPr/w:vertAlign">
                <xsl:attribute name="valign">
                    <xsl:value-of select="w:rPr/w:vertAlign/@w:val"/>
                </xsl:attribute>
            </xsl:if>
            <!-- underline: single, double, ... -->
            <xsl:if test="w:rPr/w:u">
                <xsl:attribute name="u">
                    <xsl:value-of select="w:rPr/w:u/@w:val"/>
                </xsl:attribute>
            </xsl:if>
            <!-- highlight -->
            <xsl:if test="w:rPr/w:highlight">
                <xsl:attribute name="highlight">
                    <xsl:value-of select="w:rPr/w:highlight/@w:val"/>
                </xsl:attribute>
            </xsl:if>
            <!-- color -->
            <xsl:if test="w:rPr/w:color">
                <xsl:attribute name="color">
                    <xsl:value-of select="w:rPr/w:color/@w:val"/>
                </xsl:attribute>
            </xsl:if>

            <!-- finally, recurse -->
            <xsl:apply-templates/>
        </span>
    </xsl:template>

    <xsl:template name="toggle-property-value">
        <xsl:param name="val"/>
        <xsl:choose>
            <xsl:when test="$val='true' or $val='1' or $val='on'">
                <xsl:value-of select="true"/>
            </xsl:when>
            <xsl:when test="$val='false' or $val='0' or $val='off'">
                <xsl:value-of select="false"/>
            </xsl:when>
            <xsl:otherwise>
                <xsl:text>toggle</xsl:text>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <xsl:template match="w:r[not(w:rPr[w:rStyle or w:i or w:iCs or w:b or w:bCs or w:caps or w:smallCaps or w:strike or w:dstrike or w:vertAlign or w:u or w:vanish or w:highlight or w:color])]">
        <xsl:apply-templates/>
    </xsl:template>

    <xsl:template match="w:rPr"><xsl:apply-templates/></xsl:template>
    <xsl:template match="w:rStyle"><xsl:apply-templates/></xsl:template>
    <xsl:template match="w:i|w:iCs"><xsl:apply-templates/></xsl:template>
    <xsl:template match="w:b|w:bCs"><xsl:apply-templates/></xsl:template>
    <xsl:template match="w:caps"><xsl:apply-templates/></xsl:template>
    <xsl:template match="w:smallCaps"><xsl:apply-templates/></xsl:template>
    <xsl:template match="w:strike|w:dstrike"><xsl:apply-templates/></xsl:template>
    <xsl:template match="w:vertAlign"><xsl:apply-templates/></xsl:template>
    <xsl:template match="w:u"><xsl:apply-templates/></xsl:template>
    <xsl:template match="w:vanish"><xsl:apply-templates/></xsl:template>
    <xsl:template match="w:highlight"><xsl:apply-templates/></xsl:template>
    <xsl:template match="w:color"><xsl:apply-templates/></xsl:template>

    <xsl:template match="w:hyperlink">
        <a>
        	<xsl:if test="@r:id">
        	    <xsl:copy-of select="@r:id"/>
        	</xsl:if>
        	<xsl:if test="@w:anchor">
        	    <xsl:copy-of select="@w:anchor"/>
        	</xsl:if>
        	<xsl:apply-templates/>
        </a>
    </xsl:template>

    <xsl:template match="w:br">
        <br>
        	<xsl:if test="@w:type">
        	    <xsl:attribute name="class">
        	        <xsl:value-of select="@w:type"/>
        	    </xsl:attribute>
        	</xsl:if>
        	<xsl:apply-templates/>
        </br>
    </xsl:template>

    <xsl:template match="w:tab">
        <xsl:text>&#x9;</xsl:text>
    </xsl:template>

    <xsl:template match="w:t">
        <xsl:if test="not(following::w:r[1]/w:fldChar[@w:fldCharType='end'])">
            <xsl:apply-templates/>
        </xsl:if>
    </xsl:template>

    <xsl:template match="w:bookmarkStart">
        <xsl:if test="not(contains(@w:name,'_GoBack'))">
            <a class="anchor">
                <xsl:attribute name="id">
                    <xsl:value-of select="@w:name"/>
                </xsl:attribute>
                <xsl:apply-templates/>
            </a>
        </xsl:if>
    </xsl:template>

    <xsl:template match="w:bookmarkEnd">
    	<xsl:param name="id" select="@w:id"/>
        <xsl:param name="anchor" select="//w:bookmarkStart[@w:id=$id]/@w:name"/>
        <xsl:if test="not(contains($anchor, '_GoBack'))">
            <a class="anchor">
                <xsl:attribute name="id">
                    <xsl:value-of select="$anchor"/><xsl:text>_end</xsl:text>
                </xsl:attribute>
            </a>
        </xsl:if>
    </xsl:template>

    <!-- TABLES -->

    <xsl:template match="w:tbl">
        <xsl:text>&#xA;</xsl:text>
        <table>
            <xsl:apply-templates/>
            <xsl:text>&#xA;</xsl:text>
        </table>
        <xsl:text>&#xA;</xsl:text>
    </xsl:template>

    <xsl:template match="w:tr">
        <xsl:text>&#xA;&#x9;</xsl:text>
        <tr>
            <xsl:apply-templates/>
            <xsl:text>&#xA;&#x9;</xsl:text>
        </tr>
    </xsl:template>

    <xsl:template match="w:tc">
        <xsl:text>&#xA;&#x9;&#x9;</xsl:text>
        <td>
            <xsl:apply-templates/>
            <!-- <xsl:text>&#xA;&#x9;&#x9;</xsl:text> -->
        </td>
    </xsl:template>

    <!-- FIELDS -->

    <xsl:template match="w:fldSimple">
        <pub:field>
        	<xsl:attribute name="instr">
        	    <xsl:value-of select="@w:instr"/>
        	</xsl:attribute>
        	<xsl:apply-templates/>
        </pub:field>
    </xsl:template>

    <xsl:template match="w:fldChar[@w:fldCharType='begin']">
        <pub:field_start>
            <xsl:attribute name="instr">
                <xsl:value-of select="normalize-space(following::w:instrText[1])"/>
            </xsl:attribute>
        	<xsl:apply-templates/>
        </pub:field_start>
    </xsl:template>

    <!-- remove the w:instrText because it is captured by the preceding w:fldChar @instr -->
    <xsl:template match="w:instrText"/>

    <xsl:template match="w:fldChar[@w:fldCharType='separate']">
        <!-- <pub:field_sep/> -->
    </xsl:template>

    <xsl:template match="w:fldChar[@w:fldCharType='end']">
        <pub:field_end/>
    </xsl:template>

    <!-- DRAWINGS AND IMAGES -->

    <xsl:template match="w:drawing">
        <xsl:apply-templates/>
    </xsl:template>

    <xsl:template match="wp:inline">
        <xsl:apply-templates/>
    </xsl:template>

    <xsl:template match="wp:extent"/>
    <xsl:template match="wp:effectExtent"/>
    <xsl:template match="wp:docPr"/>
    <xsl:template match="wp:cNvGraphicFramePr"/>
    <xsl:template match="a:graphicFrameLocks"/>
    <xsl:template match="a:graphic">
        <xsl:apply-templates/>
    </xsl:template>
    <xsl:template match="a:graphicData">
        <xsl:apply-templates/>
    </xsl:template>

    <xsl:template match="pic:pic">
        <img>
            <xsl:attribute name="name">
                <xsl:value-of select="pic:nvPicPr/pic:cNvPr/@name"/>
            </xsl:attribute>
            <xsl:if test=".//a:blip/@r:embed">
                <xsl:attribute name="data-embed-id">
                    <xsl:value-of select=".//a:blip/@r:embed"/>
                </xsl:attribute>    
            </xsl:if>
            <xsl:if test=".//a:blip/@r:link">
                <xsl:attribute name="data-link-id">
                    <xsl:value-of select=".//a:blip/@r:link"/>
                </xsl:attribute>    
            </xsl:if>
        </img>
    </xsl:template>

    <!-- REVISIONS -->
    <xsl:template match="w:del|w:moveFrom">
        <del>
            <xsl:attribute name="id">
                <xsl:text>del_</xsl:text>
                <xsl:value-of select="@w:id"/>
            </xsl:attribute>
            <xsl:attribute name="datetime">
                <xsl:value-of select="@w:date"/>
            </xsl:attribute>
            <xsl:attribute name="title">
                <xsl:text>author:</xsl:text>
                <xsl:value-of select="@w:author"/>
            </xsl:attribute>

            <xsl:apply-templates/>
        </del>
    </xsl:template>

    <xsl:template match="w:delText">
        <xsl:apply-templates/>
    </xsl:template>
    
    <xsl:template match="w:ins|w:moveTo">
        <ins>
            <xsl:attribute name="id">
                <xsl:text>ins_</xsl:text>
                <xsl:value-of select="@w:id"/>
            </xsl:attribute>
            <xsl:attribute name="datetime">
                <xsl:value-of select="@w:date"/>
            </xsl:attribute>
            <xsl:attribute name="title">
                <xsl:text>author:</xsl:text>
                <xsl:value-of select="@w:author"/>
            </xsl:attribute>

            <xsl:apply-templates/>
        </ins>
    </xsl:template>

    <xsl:template match="w:moveFromRangeStart|w:moveFromRangeEnd|w:moveToRangeStart|w:moveToRangeEnd"/>

    <!-- OTHER -->

    <xsl:template match="w:highlight"><xsl:apply-templates/></xsl:template>
    <xsl:template match="w:pPr"><xsl:apply-templates/></xsl:template>
    <xsl:template match="w:pStyle"><xsl:apply-templates/></xsl:template>
    <xsl:template match="w:rFonts"><xsl:apply-templates/></xsl:template>
    <xsl:template match="w:lastRenderedPageBreak"><xsl:apply-templates/></xsl:template>
    <xsl:template match="w:noProof"><xsl:apply-templates/></xsl:template>
    <xsl:template match="w:sz"><xsl:apply-templates/></xsl:template>
    <xsl:template match="w:szCs"><xsl:apply-templates/></xsl:template>
    <xsl:template match="w:lang"><xsl:apply-templates/></xsl:template>
    <xsl:template match="w:t"><xsl:apply-templates/></xsl:template>
    <xsl:template match="w:sdtContent"><xsl:apply-templates/></xsl:template>
    <xsl:template match="w:sdt"><xsl:apply-templates/></xsl:template>
    <xsl:template match="w:sdtPr"><xsl:apply-templates/></xsl:template>
    <xsl:template match="w:sdtEndPr"><xsl:apply-templates/></xsl:template>
    <xsl:template match="w:docPart"><xsl:apply-templates/></xsl:template>
    <xsl:template match="w:placeholder"><xsl:apply-templates/></xsl:template>


    <xsl:template match="w:divId"/>
    <xsl:template match="w:ind"/>
    <xsl:template match="w:tblPr"/>
    <xsl:template match="w:tblGrid"/>
    <xsl:template match="w:trPr"/>
    <xsl:template match="w:tcPr"/>
    <xsl:template match="w:tcW"/>
    <xsl:template match="w:spacing"/>
        
    <xsl:template match="w:kern"/>
    <xsl:template match="w:widowControl"/>
    <xsl:template match="w:autoSpaceDE"/>
    <xsl:template match="w:autoSpaceDN"/>
    <xsl:template match="w:adjustRightInd"/>
    <xsl:template match="w:shd"/>
    <xsl:template match="w:proofErr"/>
    <xsl:template match="w:id"/>

    
<!-- 
    <xsl:template match="w:pPrChange"/>
    <xsl:template match="w:ins"/>
    <xsl:template match="w:tabs"/>
    <xsl:template match="w:proofErr"/>
    <xsl:template match="w:del"/>
    <xsl:template match="w:rPrChange"/>
    <xsl:template match="w:shd"/>
    <xsl:template match="w:vertAlign"/>
    <xsl:template match="w:softHyphen"/>
 -->    
    <xsl:template match="w:jc"/>


</xsl:stylesheet>