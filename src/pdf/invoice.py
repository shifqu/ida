"""Generate invoice PDFs."""

from dataclasses import dataclass, field
from functools import partial

from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Image, Paragraph, Spacer, Table, TableStyle

from pdf import IMAGES_FOLDER
from pdf._reportlab import PDFDetails, SimpleDocTemplatePaddable


@dataclass
class DetailsFrom:
    """Represent the details from the sender."""

    name: str
    address: str
    city: str
    country: str
    website: str
    email: str
    business_court: str
    vat_number: str
    bank_account: str

    def __str__(self):
        """Return a string representation of the details."""
        return "<br/>".join(
            [
                f"<b>{self.name}</b>",
                self.address,
                self.city,
                self.country,
                self.website,
                self.email,
                "",
                self.business_court,
                self.vat_number,
                self.bank_account,
            ]
        )


@dataclass
class DetailsTo:
    """Represent the details to the recipient."""

    attn: str
    name: str
    address: str
    city: str
    country: str
    vat_number: str

    def __str__(self):
        """Return a string representation of the details."""
        return "<br/>".join(
            [
                f"<b>{self.attn}</b>",
                self.name,
                self.address,
                self.city,
                self.country,
                "",
                self.vat_number,
            ]
        )


@dataclass
class InvoiceDetails:
    """Represent information needed on an invoice."""

    details_from: DetailsFrom
    details_to: DetailsTo
    title: str
    date: dict[str, str] = field(
        metadata={
            "hint": "A mapping of Text:DateStr",
            "example": {"Invoice date": "2021-01-01"},
        }
    )
    due_date: dict[str, str]
    payment_communication: dict[str, str]
    lines: list[dict[str, str]]
    summary: dict[str, str]
    graphic_element = str(IMAGES_FOLDER / "softllama-graphic-element-orange.png")
    logo = str(IMAGES_FOLDER / "softllama-logo-orange.png")


@dataclass
class InvoicePDF:
    """A dataclass containing information about an invoice PDF.

    Methods are provided to generate an actual PDF from these details.
    """

    invoice: InvoiceDetails
    pdf: PDFDetails

    def generate(self) -> None:
        """Generate the PDF."""
        doc = SimpleDocTemplatePaddable(
            self.pdf.name,
            topMargin=self.pdf.margin.top,
            rightMargin=self.pdf.margin.right,
            bottomMargin=self.pdf.margin.bottom,
            leftMargin=self.pdf.margin.left,
            pagesize=self.pdf.pagesize,
        )
        styles = self.pdf.styles
        flowables: list = [Spacer(1, 5 * inch)]

        invoice_keys = list(self.invoice.lines[0].keys())
        invoice_data = [list(line.values()) for line in self.invoice.lines]
        invoice_data.insert(0, invoice_keys)

        # TODO: Make keys and columnwidths configurable
        invoice_column_widths = (
            doc.width * 0.40,
            doc.width * 0.15,
            doc.width * 0.20,
            doc.width * 0.10,
            doc.width * 0.15,
        )
        rowbackgrounds = (
            HexColor("#FFFFFF00", hasAlpha=True),
            HexColor("#654EA326", hasAlpha=True),
        )
        invoice_table_style = TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), rowbackgrounds),
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, -1), styles["normal"].fontName),
                ("FONTNAME", (0, 0), (-1, 0), styles["bold"].fontName),
            ]
        )

        # always show at least 6 (incl headers)
        empty_line = ["" for _ in invoice_keys]
        while len(invoice_data) < 6:
            invoice_data.append(empty_line)

        # TODO: Potentially paragraph some rows to enable wrapping. The problem here is that it will
        # forget all styles applied to it
        invoice_table = Table(
            invoice_data,
            colWidths=invoice_column_widths,
            style=invoice_table_style,
        )
        invoice_table.wrap(doc.width, doc.height)
        flowables.append(invoice_table)

        subtotal_data = [[k, v] for k, v in self.invoice.summary.items()]

        invoice_summary_style = TableStyle(
            [
                (
                    "LINEBELOW",
                    (0, -2),
                    (-1, -2),
                    2,
                    HexColor("#654EA3B0", hasAlpha=True),
                ),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("FONTNAME", (0, 0), (-1, -1), styles["normal"].fontName),
                ("FONTNAME", (0, 0), (0, -1), styles["bold"].fontName),
                ("LEFTPADDING", (0, 0), (0, -1), 0),
            ]
        )

        # add spacebefore exactly the minimum rowHeight of our previous table
        subtotal_table = Table(
            subtotal_data,
            hAlign="RIGHT",
            style=invoice_summary_style,
            spaceBefore=min(invoice_table._rowHeights),  # type: ignore[reportAttributeAccessIssue]
        )
        flowables.append(subtotal_table)

        doc.build(
            flowables,
            onFirstPage=partial(self._static, context=self),
            leftPadding=0,
            rightPadding=0,
        )

    @staticmethod
    def _static(canvas: Canvas, doc: SimpleDocTemplatePaddable, context: "InvoicePDF") -> None:
        """Draw static content."""
        canvas.saveState()

        invoice = context.invoice
        styles = context.pdf.styles

        graphic_element = Image(invoice.graphic_element)
        graphic_element._img._image.putalpha(255 // 6)  # type: ignore[reportAttributeAccessIssue]
        graphic_element.drawHeight = doc.width * graphic_element.drawHeight / graphic_element.drawWidth
        graphic_element.drawWidth = doc.width
        graphic_element.drawOn(canvas, 0, 0)

        from_paragraph = Paragraph(str(invoice.details_from), styles["normal"])
        _, h = from_paragraph.wrap(doc.width, doc.topMargin)
        x = doc.width + doc.rightMargin - max(from_paragraph.getActualLineWidths0())
        y = doc.height + doc.topMargin - h
        from_paragraph.drawOn(canvas, x, y)

        logo = Image(invoice.logo)
        logo.drawHeight = 3 * inch * logo.drawHeight / logo.drawWidth
        logo.drawWidth = 3 * inch
        x = doc.leftMargin
        y = doc.height + doc.topMargin - logo.drawHeight
        logo.drawOn(canvas, x, y)

        to_paragraph = Paragraph(str(invoice.details_to), styles["bodytext"])
        _, h = to_paragraph.wrap(doc.width, doc.topMargin)
        x = doc.leftMargin
        y = y - h - 10
        to_paragraph.drawOn(canvas, x, y)

        invoice_title_paragraph = Paragraph(invoice.title, style=styles["h1"])
        _, h = invoice_title_paragraph.wrap(doc.width, doc.topMargin)
        x = doc.leftMargin
        y = y - 40
        invoice_title_paragraph.drawOn(canvas, x, y)

        invoice_info = {
            **invoice.date,
            **invoice.due_date,
            **invoice.payment_communication,
        }

        # Transform dict to tuple and add a colon (:) to the key
        data = [(f"{key}:", value) for key, value in invoice_info.items()]
        invoice_info_table = Table(
            data,
            style=TableStyle(
                [
                    ("LEFTPADDING", (0, 0), (0, -1), 0),
                    ("FONTNAME", (0, 0), (-1, -1), styles["normal"].fontName),
                    ("LEADING", (0, 0), (-1, -1), styles["normal"].leading),
                ]
            ),
        )
        invoice_info_table.wrap(doc.width, doc.height)
        x = doc.leftMargin
        y = y - 60
        invoice_info_table.drawOn(canvas, x, y)

        canvas.restoreState()
