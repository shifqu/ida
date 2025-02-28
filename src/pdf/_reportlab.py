"""Improvements and overrides on Reportlab module."""

from dataclasses import dataclass, field

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, StyleSheet1
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import registerFont, registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus.doctemplate import (
    BaseDocTemplate,
    PageTemplate,
    SimpleDocTemplate,
    _doNothing,
)
from reportlab.platypus.frames import Frame

from pdf import FONTS_FOLDER


class SimpleDocTemplatePaddable(SimpleDocTemplate):
    """A SimpleDocTemplate where we can adjust the padding applied to the frames."""

    def build(
        self,
        flowables,
        onFirstPage=_doNothing,
        onLaterPages=_doNothing,
        canvasmaker=Canvas,
        leftPadding=6,
        bottomPadding=6,
        rightPadding=6,
        topPadding=6,
    ):
        """Build the document in the same way as `SimpleDocTemplate`.

        The difference is that we accept and pass paddings to the initialization of the frames.
        The rest of this function is the same as reportlab:3.6.5's SimpleDocTemplate.build and is
        therefore not further documented here.
        """
        self._calc()  # in case we changed margins sizes etc
        frameT = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="normal",
            leftPadding=leftPadding,
            bottomPadding=bottomPadding,
            rightPadding=rightPadding,
            topPadding=topPadding,
        )
        self.addPageTemplates(
            [
                PageTemplate(
                    id="First",
                    frames=frameT,
                    onPage=onFirstPage,
                    pagesize=self.pagesize,
                ),
                PageTemplate(
                    id="Later",
                    frames=frameT,
                    onPage=onLaterPages,
                    pagesize=self.pagesize,
                ),
            ]
        )
        if onFirstPage is _doNothing and hasattr(self, "onFirstPage"):
            self.pageTemplates[0].beforeDrawPage = self.onFirstPage
        if onLaterPages is _doNothing and hasattr(self, "onLaterPages"):
            self.pageTemplates[1].beforeDrawPage = self.onLaterPages
        BaseDocTemplate.build(self, flowables, canvasmaker=canvasmaker)


def get_default_stylesheet() -> StyleSheet1:
    """Return a stylesheet object using PT Mono for text and AnonymiceNerd for code.

    All styles are aliased to their lowercase or hN in case of Heading.
    """
    _base_font_name = "PTMono"
    _base_font_name_bold = "PTMono-bold"
    PTMONO_FONT_LOCATION = FONTS_FOLDER / "PTMono.ttc"
    registerFont(TTFont(_base_font_name, PTMONO_FONT_LOCATION, subfontIndex=1))
    registerFont(TTFont(_base_font_name_bold, PTMONO_FONT_LOCATION, subfontIndex=0))
    registerFontFamily(
        _base_font_name,
        normal=_base_font_name,
        bold=_base_font_name_bold,
    )
    _base_code_font_name = "AnonymiceNerd"
    ANONYMICE_NERD_LOCATION = FONTS_FOLDER / "AnonymiceNerdMono.ttf"
    registerFont(TTFont(_base_code_font_name, ANONYMICE_NERD_LOCATION))
    stylesheet = StyleSheet1()
    stylesheet.add(
        ParagraphStyle(name="Normal", fontName=_base_font_name, fontSize=10, leading=12),
        alias="normal",
    )
    stylesheet.add(
        ParagraphStyle(name="BodyText", fontName=_base_font_name, fontSize=12, leading=16),
        alias="bodytext",
    )
    stylesheet.add(
        ParagraphStyle(name="Bold", parent=stylesheet["Normal"], fontName=_base_font_name_bold),
        alias="bold",
    )
    stylesheet.add(
        ParagraphStyle(
            name="Heading1",
            parent=stylesheet["Normal"],
            fontName=_base_font_name_bold,
            fontSize=18,
            leading=22,
            spaceAfter=6,
            textColor=HexColor("#654EA3"),
        ),
        alias="h1",
    )
    stylesheet.add(
        ParagraphStyle(
            name="Title",
            parent=stylesheet["Heading1"],
            alignment=TA_CENTER,
        ),
        alias="title",
    )
    stylesheet.add(
        ParagraphStyle(
            name="Heading2",
            parent=stylesheet["Normal"],
            fontName=_base_font_name_bold,
            fontSize=14,
            leading=18,
            spaceBefore=12,
            spaceAfter=6,
        ),
        alias="h2",
    )
    stylesheet.add(
        ParagraphStyle(
            name="Heading3",
            parent=stylesheet["Normal"],
            fontName=_base_font_name_bold,
            fontSize=12,
            leading=14,
            spaceBefore=12,
            spaceAfter=6,
        ),
        alias="h3",
    )
    stylesheet.add(
        ParagraphStyle(
            name="Heading4",
            parent=stylesheet["Normal"],
            fontName=_base_font_name_bold,
            fontSize=10,
            leading=12,
            spaceBefore=10,
            spaceAfter=4,
        ),
        alias="h4",
    )
    stylesheet.add(
        ParagraphStyle(
            name="Heading5",
            parent=stylesheet["Normal"],
            fontName=_base_font_name_bold,
            fontSize=9,
            leading=10.8,
            spaceBefore=8,
            spaceAfter=4,
        ),
        alias="h5",
    )
    stylesheet.add(
        ParagraphStyle(
            name="Heading6",
            parent=stylesheet["Normal"],
            fontName=_base_font_name_bold,
            fontSize=7,
            leading=8.4,
            spaceBefore=6,
            spaceAfter=2,
        ),
        alias="h6",
    )
    stylesheet.add(
        ParagraphStyle(
            name="Code",
            parent=stylesheet["Normal"],
            fontName=_base_code_font_name,
            fontSize=8,
            leading=8.8,
            firstLineIndent=0,
            leftIndent=36,
            hyphenationLang="",
        ),
        alias="code",
    )
    return stylesheet


@dataclass
class Margin:
    """A dataclass which represents margins.

    They default to 2/3 of an inch which seems like a fitting margin for an A4 document.
    """

    top: float = 0.66 * inch
    right: float = 0.66 * inch
    bottom: float = 0.66 * inch
    left: float = 0.66 * inch


@dataclass
class PDFDetails:
    """A dataclass which represents PDF details."""

    name: str
    pagesize: tuple[float, float] = A4
    styles: StyleSheet1 = field(default_factory=get_default_stylesheet)
    margin: Margin = field(default_factory=Margin)
