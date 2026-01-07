"""
Генератор КП v2 — рендерит контент от Content Composer
"""
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    HRFlowable, KeepTogether
)
from reportlab.lib.colors import HexColor, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.flowables import Flowable

from config import DATA_DIR
from services.pdf_styles import get_style, PDFStyle

KP_OUTPUT_DIR = DATA_DIR / "kp_output"
KP_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_PATH = Path(__file__).parent / "fonts" / "DejaVuSans.ttf"
FONT_BOLD_PATH = Path(__file__).parent / "fonts" / "DejaVuSans-Bold.ttf"


def register_fonts() -> str:
    try:
        if FONT_PATH.exists():
            pdfmetrics.registerFont(TTFont('DejaVuSans', str(FONT_PATH)))
        if FONT_BOLD_PATH.exists():
            pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', str(FONT_BOLD_PATH)))
        return 'DejaVuSans'
    except:
        return 'Helvetica'


class ColorBlock(Flowable):
    """Цветной блок с автоподбором размера текста"""
    def __init__(self, width, height, color, text="", text_color=white, 
                 font_name="DejaVuSans-Bold", font_size=16, align="center",
                 min_font_size=10, padding=4*mm):
        Flowable.__init__(self)
        self.width = width
        self.base_height = height
        self.color = color
        self.text = text
        self.text_color = text_color
        self.font_name = font_name
        self.font_size = font_size
        self.min_font_size = min_font_size
        self.align = align
        self.padding = padding
        
        # Вычисляем оптимальный размер шрифта
        self._calc_font_size()
        
        # Динамическая высота
        self.height = max(self.base_height, self.font_size + 8*mm)
    
    def _calc_font_size(self):
        """Уменьшаем шрифт если текст не влезает"""
        from reportlab.pdfbase.pdfmetrics import stringWidth
        
        max_width = self.width - self.padding * 2
        
        while self.font_size > self.min_font_size:
            text_width = stringWidth(self.text, self.font_name, self.font_size)
            if text_width <= max_width:
                break
            self.font_size -= 1
    
    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.roundRect(0, 0, self.width, self.height, 2*mm, fill=1, stroke=0)
        
        if self.text:
            self.canv.setFillColor(self.text_color)
            self.canv.setFont(self.font_name, self.font_size)
            
            text_width = self.canv.stringWidth(self.text, self.font_name, self.font_size)
            if self.align == "center":
                x = (self.width - text_width) / 2
            else:
                x = self.padding
            
            y = self.height/2 - self.font_size/3
            self.canv.drawString(x, y, self.text)


class FeatureCard(Flowable):
    """Карточка преимущества"""
    def __init__(self, title: str, description: str, style: PDFStyle, width: float):
        Flowable.__init__(self)
        self.title = title
        self.description = description
        self.style = style
        self.width = width
        self.height = 22*mm
    
    def draw(self):
        # Фон
        self.canv.setFillColor(self.style.background)
        self.canv.roundRect(0, 0, self.width, self.height, 2*mm, fill=1, stroke=0)
        
        # Акцент слева
        self.canv.setFillColor(self.style.accent)
        self.canv.rect(0, 0, 1.5*mm, self.height, fill=1, stroke=0)
        
        # Заголовок
        self.canv.setFillColor(self.style.primary)
        self.canv.setFont("DejaVuSans-Bold", 10)
        self.canv.drawString(5*mm, self.height - 7*mm, self.title[:35])
        
        # Описание
        self.canv.setFillColor(self.style.text_light)
        self.canv.setFont("DejaVuSans", 8)
        
        # Переносим длинный текст
        desc = self.description[:80]
        if len(desc) > 45:
            self.canv.drawString(5*mm, self.height - 13*mm, desc[:45])
            self.canv.drawString(5*mm, self.height - 18*mm, desc[45:])
        else:
            self.canv.drawString(5*mm, self.height - 14*mm, desc)


class QuickFact(Flowable):
    """Быстрый факт"""
    def __init__(self, label: str, value: str, style: PDFStyle, width: float):
        Flowable.__init__(self)
        self.label = label
        self.value = value
        self.style = style
        self.width = width
        self.height = 14*mm
    
    def draw(self):
        # Лейбл
        self.canv.setFillColor(self.style.text_light)
        self.canv.setFont("DejaVuSans", 8)
        self.canv.drawString(2*mm, self.height - 5*mm, self.label)
        
        # Значение
        self.canv.setFillColor(self.style.text)
        self.canv.setFont("DejaVuSans-Bold", 11)
        self.canv.drawString(2*mm, 2*mm, self.value[:25])


def create_styles(style: PDFStyle, font: str) -> Dict[str, ParagraphStyle]:
    """Создать стили параграфов"""
    bold = f"{font}-Bold" if font == "DejaVuSans" else "Helvetica-Bold"
    
    return {
        "headline": ParagraphStyle(
            "Headline", fontName=bold, fontSize=22,
            textColor=style.primary, spaceAfter=2*mm, leading=26
        ),
        "subheadline": ParagraphStyle(
            "Subheadline", fontName=font, fontSize=12,
            textColor=style.secondary, spaceAfter=5*mm, leading=16
        ),
        "heading": ParagraphStyle(
            "Heading", fontName=bold, fontSize=13,
            textColor=style.primary, spaceBefore=6*mm, spaceAfter=3*mm
        ),
        "body": ParagraphStyle(
            "Body", fontName=font, fontSize=10,
            textColor=style.text, leading=15, spaceAfter=2*mm
        ),
        "body_light": ParagraphStyle(
            "BodyLight", fontName=font, fontSize=10,
            textColor=style.text_light, leading=15
        ),
        "accent": ParagraphStyle(
            "Accent", fontName=bold, fontSize=11,
            textColor=style.accent, spaceAfter=2*mm
        ),
        "caption": ParagraphStyle(
            "Caption", fontName=font, fontSize=9,
            textColor=style.text_light, leading=12
        ),
        "cta": ParagraphStyle(
            "CTA", fontName=bold, fontSize=11,
            textColor=style.accent, alignment=TA_CENTER,
            spaceBefore=5*mm
        ),
        "footer": ParagraphStyle(
            "Footer", fontName=font, fontSize=8,
            textColor=style.text_light, alignment=TA_CENTER
        ),
    }


async def render_kp_from_content(
    content: Dict[str, Any],
    property_name: str,
    realtor_name: str = "",
    realtor_phone: str = ""
) -> Optional[str]:
    """
    Рендерит PDF из контента, созданного Content Composer
    """
    
    font = register_fonts()
    style_name = content.get("style_recommendation", "modern")
    style = get_style(style_name)
    styles = create_styles(style, font)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c for c in property_name if c.isalnum() or c in " _-")[:30]
    filepath = KP_OUTPUT_DIR / f"KP_{safe_name}_{timestamp}.pdf"
    
    try:
        doc = SimpleDocTemplate(
            str(filepath), pagesize=A4,
            rightMargin=20*mm, leftMargin=20*mm,
            topMargin=20*mm, bottomMargin=15*mm
        )
        
        elements = []
        page_width = A4[0] - 40*mm
        
        # === ЗАГОЛОВОК ===
        if content.get("headline"):
            elements.append(Paragraph(content["headline"], styles["headline"]))
        
        if content.get("subheadline"):
            elements.append(Paragraph(content["subheadline"], styles["subheadline"]))
        
        # === HERO — ЦЕНА ===
        hero = content.get("hero_section", {})
        
        if hero.get("price"):
            elements.append(ColorBlock(
                page_width, 16*mm, style.accent,
                hero["price"], white, "DejaVuSans-Bold", 18, "center"
            ))
            elements.append(Spacer(1, 2*mm))
        
        if hero.get("key_fact"):
            elements.append(Paragraph(hero["key_fact"], styles["body"]))
        
        if hero.get("price_per_sqm"):
            elements.append(Paragraph(hero["price_per_sqm"], styles["body_light"]))
        
        # === ОПИСАНИЕ КВАРТИРЫ ===
        if content.get("apartment_description"):
            elements.append(Spacer(1, 3*mm))
            elements.append(Paragraph(content["apartment_description"], styles["body"]))
        
        # === ПРЕИМУЩЕСТВА ===
        features = content.get("features", [])
        
        if features:
            elements.append(Paragraph("Преимущества", styles["heading"]))
            
            # По 2 в ряд
            card_width = (page_width - 5*mm) / 2
            rows = []
            
            for i in range(0, len(features[:6]), 2):
                row = []
                for j in range(2):
                    if i + j < len(features):
                        f = features[i + j]
                        row.append(FeatureCard(
                            f.get("title", ""),
                            f.get("description", ""),
                            style, card_width - 2*mm
                        ))
                    else:
                        row.append(Spacer(card_width, 1))
                rows.append(row)
            
            if rows:
                table = Table(rows, colWidths=[card_width, card_width])
                table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
                ]))
                elements.append(table)
        
        # === ЛОКАЦИЯ ===
        if content.get("location_description"):
            elements.append(Paragraph("Расположение", styles["heading"]))
            elements.append(Paragraph(content["location_description"], styles["body"]))
        
        # === УСЛОВИЯ ===
        terms = content.get("terms", {})
        
        if terms.get("payment") or terms.get("deadline"):
            elements.append(Paragraph("Условия покупки", styles["heading"]))
            
            if terms.get("payment"):
                elements.append(Paragraph(f"💳 {terms['payment']}" if style.show_icons else terms["payment"], styles["body"]))
            
            if terms.get("deadline"):
                elements.append(Paragraph(f"📅 {terms['deadline']}" if style.show_icons else terms["deadline"], styles["body"]))
        
        # === CTA ===
        if content.get("call_to_action"):
            elements.append(Spacer(1, 5*mm))
            elements.append(HRFlowable(width="40%", thickness=1, color=style.accent, hAlign="CENTER"))
            elements.append(Paragraph(content["call_to_action"], styles["cta"]))
        
        # === КОНТАКТЫ ===
        if realtor_name or realtor_phone:
            elements.append(Spacer(1, 8*mm))
            
            contact_text = []
            if realtor_name:
                contact_text.append(f"<b>{realtor_name}</b>")
            if realtor_phone:
                contact_text.append(realtor_phone)
            
            elements.append(Paragraph("<br/>".join(contact_text), styles["body"]))
        
        # === ФУТЕР ===
        elements.append(Spacer(1, 10*mm))
        elements.append(Paragraph(
            f"Предложение от {datetime.now().strftime('%d.%m.%Y')}",
            styles["footer"]
        ))
        
        doc.build(elements)
        print(f"[KP2] Rendered: {filepath}")
        return str(filepath)
        
    except Exception as e:
        print(f"[KP2] Render error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def render_summary_from_content(
    content: Dict[str, Any],
    property_name: str
) -> Optional[str]:
    """
    Рендерит информационную выжимку из контента Composer
    """
    
    font = register_fonts()
    style_name = content.get("style_recommendation", "minimal")
    style = get_style(style_name)
    styles = create_styles(style, font)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c for c in property_name if c.isalnum() or c in " _-")[:30]
    filepath = KP_OUTPUT_DIR / f"Info_{safe_name}_{timestamp}.pdf"
    
    try:
        doc = SimpleDocTemplate(
            str(filepath), pagesize=A4,
            rightMargin=20*mm, leftMargin=20*mm,
            topMargin=20*mm, bottomMargin=15*mm
        )
        
        elements = []
        page_width = A4[0] - 40*mm
        
        # Заголовок
        elements.append(Paragraph(content.get("title", property_name), styles["headline"]))
        
        if content.get("subtitle"):
            elements.append(Paragraph(content["subtitle"], styles["subheadline"]))
        
        # Быстрые факты
        quick_facts = content.get("quick_facts", [])
        if quick_facts:
            fact_width = page_width / min(len(quick_facts), 4)
            fact_cards = [
                QuickFact(f["label"], f["value"], style, fact_width - 2*mm)
                for f in quick_facts[:4]
            ]
            
            table = Table([fact_cards], colWidths=[fact_width] * len(fact_cards))
            table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BACKGROUND', (0, 0), (-1, -1), style.background),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 5*mm))
        
        # Описание
        if content.get("description"):
            elements.append(Paragraph(content["description"], styles["body"]))
        
        # Квартиры
        apartments = content.get("apartments", {})
        if apartments:
            elements.append(Paragraph("Квартиры", styles["heading"]))
            if apartments.get("types"):
                elements.append(Paragraph(f"Типы: {apartments['types']}", styles["body"]))
            if apartments.get("areas"):
                elements.append(Paragraph(f"Площади: {apartments['areas']}", styles["body"]))
            if apartments.get("price_analysis"):
                elements.append(Paragraph(apartments["price_analysis"], styles["accent"]))
        
        # Плюсы и минусы
        pros = content.get("pros", [])
        cons = content.get("cons", [])
        
        if pros:
            elements.append(Paragraph("Плюсы", styles["heading"]))
            for p in pros:
                elements.append(Paragraph(f"✓ {p}", styles["body"]))
        
        if cons:
            elements.append(Paragraph("Нюансы", styles["heading"]))
            for c in cons:
                elements.append(Paragraph(f"• {c}", styles["body_light"]))
        
        # Условия
        if content.get("buying_conditions"):
            elements.append(Paragraph("Условия покупки", styles["heading"]))
            elements.append(Paragraph(content["buying_conditions"], styles["body"]))
        
        # Вывод
        if content.get("conclusion"):
            elements.append(Spacer(1, 5*mm))
            elements.append(ColorBlock(
                page_width, 14*mm, style.background,
                "", style.text, "DejaVuSans", 10
            ))
            elements.append(Paragraph(f"<b>Вывод:</b> {content['conclusion']}", styles["body"]))
        
        # Футер
        elements.append(Spacer(1, 10*mm))
        elements.append(Paragraph(
            f"Сформировано {datetime.now().strftime('%d.%m.%Y')}",
            styles["footer"]
        ))
        
        doc.build(elements)
        print(f"[KP2] Summary rendered: {filepath}")
        return str(filepath)
        
    except Exception as e:
        print(f"[KP2] Summary render error: {e}")
        return None
