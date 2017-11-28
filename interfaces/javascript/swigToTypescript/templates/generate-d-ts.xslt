<?xml version="1.0" encoding="UTF-8"?>

<xsl:stylesheet version="1.0" 
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform" 
    xmlns:fo="http://www.w3.org/1999/XSL/Format"
    xmlns:user="urn:my-scripts">

    <xsl:output method="text" omit-xml-declaration="yes" indent="no"/>
    <xsl:strip-space elements="*" />

    <!--

    SWIG's XML describes the interface in a highly structured way, 
    *except* for types, which are encoded as mysterious strings like this
    "q(const).model::OutputPort&lt;(double)>" 

    -->

    <xsl:template match="/">

<!-- 

We start the output file with a standard header that includes any types
that ELL uses but doesn't define itself. Hopefully this list will be
short, perhaps even empty once ELL has a nice white-listed API.

-->

<!-- TODO: import this text via <xsl:import href=.../> -->
        <xsl:text>
/*
  THIS FILE IS AUTOMATICALLY GENERATED. DO NOT EDIT.
*/

//----------------------------------------------------------------------------------
// Definitions from utility libraries that are not in the SWIG XML file.
//----------------------------------------------------------------------------------

export class StdVector&lt;T&gt; {
    constructor();
    constructor(count: number);
    size(): number;
    capacity(): number;
    reserve(count: number): void;
    empty(): boolean;
    clear(): void;
    add(val: T): void;
    get(index: number): T;
    set(index: number, val: T): void;
}

type vector&lt;T&gt; = StdVector&lt;T&gt;


//----------------------------------------------------------------------------------
// Translated definitions below. 
// (The id comments allow traceability back to the SWIG XML file.)
//----------------------------------------------------------------------------------
&#10;&#10;&#10;
        </xsl:text>

        <xsl:apply-templates/>
    </xsl:template>

    <!--

     The translation rules start here.  

     -->

    <xsl:template match="namespace">
        <!-- Keep track of when we're inside namespaces, to recognize top-level functions. -->
        <xsl:apply-templates mode="inside-namespace" />
    </xsl:template>


    <!-- type aliases in classes -->
    <xsl:key name="aliases" 
        match="cdecl/attributelist/attribute[@name='typealias']" 
        use="../attribute[@name='sym_name']/@value" />


    <!-- classes -->
    <xsl:template match="class" mode="inside-namespace">
        <xsl:if test="attributelist/attribute[@name='sym_name'] and
            not(attributelist/attribute[@name='sym_name' and starts-with(@value, '__')])">
            <xsl:text>export class </xsl:text>
            <xsl:value-of select="attributelist/attribute[@name='sym_name']/@value"/>
            <xsl:text> { // class id:</xsl:text>
            <xsl:value-of select='@id'/>
            <xsl:text>&#10;</xsl:text>
            <xsl:apply-templates mode="inside-class"/>
            <xsl:text>}&#10;&#10;&#10;</xsl:text>
        </xsl:if>
    </xsl:template>


    <!-- templates -->
    <xsl:template match="template" mode="inside-namespace">
        <xsl:if test="attributelist/attribute[@name='templatetype']/@value='class'">
            <xsl:text>export class </xsl:text>
            <xsl:value-of select="attributelist/attribute[@name='sym_name']/@value"/>
            <xsl:text>&lt;</xsl:text>
            <xsl:for-each select="attributelist/templateparms/parm">
                <xsl:if test="position() != 1"><xsl:text>, </xsl:text></xsl:if>
                <xsl:value-of select="attributelist/attribute[@name='name']/@value"/>
            </xsl:for-each>
            <xsl:text>&gt; { // class id:</xsl:text>
            <xsl:value-of select='@id'/>
            <xsl:text>&#10;</xsl:text>
            <xsl:apply-templates mode="inside-class"/>
            <xsl:text>}&#10;&#10;&#10;</xsl:text>
        </xsl:if>
    </xsl:template>


    <!-- constructors -->
    <xsl:template match="constructor/attributelist" mode="inside-class">
        <xsl:text>&#9;constructor(</xsl:text>
        <xsl:for-each select="parmlist/parm">
            <xsl:if test="position() != 1"><xsl:text>, </xsl:text></xsl:if>
            <xsl:choose>
                <xsl:when test="attributelist/attribute[@name='name']">
                    <xsl:value-of select="attributelist/attribute[@name='name']/@value"/>
                </xsl:when>
                <xsl:otherwise><xsl:text>parameter</xsl:text></xsl:otherwise>
            </xsl:choose>
            <xsl:text>: </xsl:text>
            <xsl:call-template name="TranslateType">
                <xsl:with-param name="value">
                    <xsl:value-of select="attributelist/attribute[@name='type']/@value"/>
                </xsl:with-param>
            </xsl:call-template>
        </xsl:for-each>
        <xsl:text>); // ctor id:</xsl:text>
        <xsl:value-of select="@id"/>
        <xsl:text>&#10;</xsl:text>
    </xsl:template>


    <!-- methods and fields -->
    <xsl:template match="cdecl/attributelist[attribute[@name='kind' and (@value='variable' or @value='function')]]" mode="inside-class">
        <!-- translate every cdel with 
        (1) an attribute name 'access' and value 'public' 
        (2) a 'name' attribute that does not contain 'operator ' -->
        <xsl:if test="attribute[@name='access' and @value='public'] and 
                      not(attribute[@name='name' and contains(@value, 'operator ')])">
            <xsl:text>&#9;</xsl:text>
            <xsl:value-of select="attribute[@name='name']/@value"/>
            <xsl:if test="not(attribute[@name='kind' and @value='variable'])">
                <xsl:text>(</xsl:text>
                <xsl:for-each select="parmlist/parm">
                    <xsl:if test="position() != 1"><xsl:text>, </xsl:text></xsl:if>
                    <xsl:value-of select="attributelist/attribute[@name='name']/@value"/>
                    <xsl:text>: </xsl:text>
                    <xsl:call-template name="TranslateType">
                        <xsl:with-param name="value">
                            <xsl:value-of select="attributelist/attribute[@name='type']/@value"/>
                        </xsl:with-param>
                    </xsl:call-template>

                </xsl:for-each>
                <xsl:text>)</xsl:text>
            </xsl:if>
            <xsl:text>: </xsl:text>

            <xsl:call-template name="TranslateType">
                <xsl:with-param name="value">
                    <xsl:value-of select="attribute[@name='type']/@value"/>
                </xsl:with-param>
            </xsl:call-template>

            <xsl:text>; // member id:</xsl:text>
            <xsl:value-of select="@id"/>
            <xsl:text>&#10;</xsl:text>
        </xsl:if>
    </xsl:template>


    <!-- typedefs -->
    <xsl:template match="cdecl/attributelist[attribute[@name='kind' and @value='typedef']]" mode="inside-namespace">
        <xsl:if test="attribute[@name='sym_name']">
            <xsl:text>export class </xsl:text>
            <xsl:value-of select="attribute[@name='sym_name']/@value"/>
            <xsl:if test="not(contains(attribute[@name='type']/@value, concat('::', attribute[@name='sym_name']/@value)))">
                <xsl:text> extends </xsl:text>
                <xsl:call-template name="TranslateType">
                    <xsl:with-param name="value">
                        <xsl:value-of select="attribute[@name='type']/@value"/>
                    </xsl:with-param>
                </xsl:call-template>
            </xsl:if>
            <xsl:text> { } // typedef id:</xsl:text>
            <xsl:value-of select="@id"/>
            <xsl:text>&#10;&#10;&#10;</xsl:text>
        </xsl:if>
    </xsl:template>


    <!-- top-level functions -->
    <xsl:template match="cdecl/attributelist[attribute[@name='kind' and @value='function']]" mode="inside-namespace" >
        <xsl:if test="not(attribute[@name='access' and @value='private']) and 
            not(attribute[@name='name' and contains(@value, 'operator ')])">
            <xsl:text>export function </xsl:text>
            <xsl:choose>
                <xsl:when test="contains(attribute[@name='name']/@value, '::')">
                    <xsl:value-of select="substring-after(attribute[@name='name']/@value, '::')"/>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:value-of select="attribute[@name='name']/@value"/>
                </xsl:otherwise>
            </xsl:choose>            
            <xsl:text>(</xsl:text>
            <xsl:for-each select="parmlist/parm">
                <xsl:if test="position() != 1"><xsl:text>, </xsl:text></xsl:if>
                <xsl:value-of select="attributelist/attribute[@name='name']/@value"/>
                <xsl:text>: </xsl:text>
                <xsl:call-template name="TranslateType">
                    <xsl:with-param name="value">
                        <xsl:value-of select="attributelist/attribute[@name='type']/@value"/>
                    </xsl:with-param>
                </xsl:call-template>
            </xsl:for-each>
            <xsl:text>): </xsl:text>
            <xsl:call-template name="TranslateType">
                <xsl:with-param name="value">
                    <xsl:value-of select="attribute[@name='type']/@value"/>
                </xsl:with-param>
            </xsl:call-template>
            <xsl:text>; // function id:</xsl:text>
            <xsl:value-of select="../@id"/>
            <xsl:text>&#10;&#10;</xsl:text>
        </xsl:if>
    </xsl:template>


    <!-- enums -->
    <xsl:template match="enum" mode="inside-namespace">
        <xsl:if test="not(attributelist/attribute[@name='access' and @value='private'])">
        <xsl:text>export enum </xsl:text>
        <xsl:value-of select="attributelist/attribute[@name='sym_name']/@value"/>
        <xsl:text> { </xsl:text>
        <xsl:for-each select="enumitem/attributelist">
            <xsl:value-of select="attribute[@name='sym_name']/@value" />
            <xsl:text>, </xsl:text>
        </xsl:for-each>
        <xsl:text>}&#10;&#10;&#10;</xsl:text>
        </xsl:if>
    </xsl:template>

    <!-- simple types -->
    <xsl:template name="TranslateSimpleType">
        <xsl:param name="value"/>
        <xsl:choose>
            <xsl:when test="$value='bool'">
                <xsl:text>boolean</xsl:text>
            </xsl:when>
            <xsl:when test="$value='char'">
                <xsl:text>number</xsl:text>
            </xsl:when>
            <xsl:when test="$value='short'">
                <xsl:text>number</xsl:text>
            </xsl:when>
            <xsl:when test="$value='int'">
                <xsl:text>number</xsl:text>
            </xsl:when>
            <xsl:when test="$value='float'">
                <xsl:text>number</xsl:text>
            </xsl:when>
            <xsl:when test="$value='double'">
                <xsl:text>number</xsl:text>
            </xsl:when>
            <xsl:when test="$value='uint64_t'">
                <xsl:text>number</xsl:text>
            </xsl:when>
            <xsl:when test="$value='size_t'">
                <xsl:text>number</xsl:text>
            </xsl:when>
            <xsl:when test="$value='nullptr_t'">
                <xsl:text>any</xsl:text>
            </xsl:when>
            <xsl:when test="key('aliases', $value)"> <!-- use of a type alias -->
                <xsl:call-template name="StripDecoration">
                    <xsl:with-param name="value">
                        <xsl:value-of select="key('aliases', $value)/../attribute[@name='type']/@value"/>
                    </xsl:with-param>
                </xsl:call-template>
            </xsl:when>
            <xsl:otherwise>
                <xsl:value-of select="$value"/>
                <xsl:apply-templates/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <!-- strip the weird SWIG decorations and namespace qualifiers from type names -->
    <xsl:template name="StripDecoration">
        <xsl:param name="value"/>
        <xsl:variable name="result">
            <xsl:choose>
                <!-- encoding of const ref -->
                <xsl:when test="starts-with($value, 'r.q(const).')">
                    <xsl:value-of select="substring-after($value, 'r.q(const).')"/>
                </xsl:when>
                <!-- encoding of const -->
                <xsl:when test="starts-with($value, 'q(const).')">
                    <xsl:value-of select="substring-after($value, 'q(const).')"/>
                </xsl:when>
                <!-- encoding of ref -->
                <xsl:when test="starts-with($value, 'r.')">
                    <xsl:value-of select="substring-after($value, 'r.')"/>
                </xsl:when>
                <!-- encoding of pointer -->
                <xsl:when test="starts-with($value, 'p.')">
                    <xsl:value-of select="substring-after($value, 'p.')"/>
                </xsl:when>
                <!-- encoding of namespaces -->
                <xsl:when test="contains($value, '::')">
                    <xsl:value-of select="substring-after($value, '::')"/>
                </xsl:when>
            </xsl:choose>
        </xsl:variable>

        <xsl:choose>
            <xsl:when test="string-length($result) &gt; 0">
                <!-- call template recursively -->
                <xsl:call-template name="StripDecoration">
                    <xsl:with-param name="value">
                        <xsl:value-of select="$result"/>
                    </xsl:with-param>
                </xsl:call-template>
            </xsl:when>
            <xsl:otherwise>
                <xsl:value-of select="$value"/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <!-- template parameter lists -->
    <xsl:template name="TransformTemplateContents">
        <xsl:param name="value"/>

        <xsl:choose>
            <xsl:when test="contains($value, ',')">
                <xsl:call-template name="TranslateType">
                    <xsl:with-param name="value">
                        <xsl:value-of select="substring-before($value, ',')"/>
                    </xsl:with-param>
                </xsl:call-template>
                <xsl:text>, </xsl:text>
                <xsl:call-template name="TransformTemplateContents">
                    <xsl:with-param name="value">
                        <xsl:value-of select="substring-after($value, ',')"/>
                    </xsl:with-param>
                </xsl:call-template>
            </xsl:when>
            <xsl:otherwise>
                <xsl:call-template name="TranslateType">
                    <xsl:with-param name="value">
                        <xsl:value-of select="$value"/>
                    </xsl:with-param>
                </xsl:call-template>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <!-- XSL template to convert SWIG-formatted types to typescript -->
    <xsl:template name="TranslateType">
        <xsl:param name="value"/>

        <xsl:variable name="templateBase">
            <xsl:value-of select="substring-before($value, '&lt;(')"/>
        </xsl:variable>
        <xsl:variable name="templateContents">
            <xsl:value-of select="substring-after(substring-before($value, ')&gt;'), '&lt;(')"/>
        </xsl:variable>

        <xsl:variable name="result">
            <xsl:choose>
                <xsl:when test="string-length($templateContents) &gt; 0">
                    <!-- it's a template -->
                    <xsl:call-template name="StripDecoration">
                        <xsl:with-param name="value">
                            <xsl:value-of select="$templateBase"/>
                        </xsl:with-param>
                    </xsl:call-template>
                    <xsl:text>&lt;</xsl:text> 
                        <xsl:call-template name="TransformTemplateContents">
                            <xsl:with-param name="value">
                                <xsl:value-of select="$templateContents"/>
                            </xsl:with-param>
                        </xsl:call-template>
                    <xsl:text>&gt;</xsl:text> 
                </xsl:when>
                <xsl:otherwise>
                    <xsl:call-template name="StripDecoration">
                        <xsl:with-param name="value">
                            <xsl:value-of select="$value"/>
                        </xsl:with-param>
                    </xsl:call-template>
                </xsl:otherwise>
            </xsl:choose>
        </xsl:variable>

        <xsl:call-template name="TranslateSimpleType">
            <xsl:with-param name="value">
                <xsl:value-of select="$result"/>
            </xsl:with-param>
        </xsl:call-template>
    </xsl:template>

</xsl:stylesheet>