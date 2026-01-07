"""
Генератор коммерческих предложений (КП) в PDF
"""
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from config import DATA_DIR

# Папка для сгенерированных КП
KP_OUTPUT_DIR = DATA_DIR / "kp_output"
KP_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Регистрируем шрифт с поддержкой кириллицы
FONT_PATH = Path(__file__).parent / "fonts" / "DejaVuSans.ttf"
FONT_BOLD_PATH = Path(__file__).parent / "fonts" / "DejaVuSans-Bold.ttf"

def register_fonts():
    """Регистрация шрифтов"""
    try:
        if FONT_PATH.exists():
            pdfmetrics.registerFont(TTFont('DejaVuSans', str(FONT_PATH)))
            pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', str(FONT_BOLD_PATH)))
            return 'DejaVuSans'
    except Exception as e:
        print(f"[KP] Font registration error: {e}")
    return 'Helvetica'


def format_price(price: int) -> str:
    """Форматирование цены: 15000000 -> 15 000 000 ₽"""
    if not price:
        return "—"
    return f"{price:,}".replace(",", " ") + " ₽"


def format_area(area: float) -> str:
    """Форматирование площади"""
    if not area:
        return "—"
    return f"{area:.1f} м²"


async def generate_kp_pdf(
    property_name: str,
    apartment_info: Dict[str, Any],
    realtor_name: str = "",
    realtor_phone: str = "",
    realtor_company: str = ""
) -> Optional[str]:
    """
    Генерация PDF с коммерческим предложением
    
    Args:
        property_name: Название ЖК
        apartment_info: Данные о квартире {
            "type": "2-комнатная",
            "area": 54.5,
            "floor": 7,
            "price": 8500000,
            "price_per_sqm": 155963,
            "rooms": "кухня-гостиная 18м², спальня 14м², ...",
            "features": "балкон, гардеробная",
            "completion_date": "Q4 2025",
            "payment_options": "100%, рассрочка, ипотека",
            "installment": "30% + 24 мес"
        }
        realtor_name: Имя риэлтора
        realtor_phone: Телефон
        realtor_company: Компания
    
    Returns:
        Путь к сгенерированному PDF или None
    """
    
    font_name = register_fonts()
    
    # Генерируем имя файла
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c for c in property_name if c.isalnum() or c in " _-")[:30]
    filename = f"KP_{safe_name}_{timestamp}.pdf"
    filepath = KP_OUTPUT_DIR / filename
    
    try:
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )
        
        # Стили
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontName=f'{font_name}-Bold' if font_name == 'DejaVuSans' else 'Helvetica-Bold',
            fontSize=18,
            spaceAfter=10*mm,
            textColor=colors.HexColor('#1a365d')
        )
        
        heading_style = ParagraphStyle(
            'Heading',
            parent=styles['Heading2'],
            fontName=f'{font_name}-Bold' if font_name == 'DejaVuSans' else 'Helvetica-Bold',
            fontSize=14,
            spaceBefore=8*mm,
            spaceAfter=4*mm,
            textColor=colors.HexColor('#2c5282')
        )
        
        normal_style = ParagraphStyle(
            'Normal',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=11,
            leading=14
        )
        
        price_style = ParagraphStyle(
            'Price',
            parent=styles['Normal'],
            fontName=f'{font_name}-Bold' if font_name == 'DejaVuSans' else 'Helvetica-Bold',
            fontSize=16,
            textColor=colors.HexColor('#276749')
        )
        
        # Элементы документа
        elements = []
        
        # Заголовок
        elements.append(Paragraph(f"Коммерческое предложение", title_style))
        elements.append(Paragraph(f"<b>{property_name}</b>", heading_style))
        elements.append(Spacer(1, 5*mm))
        
        # Основная информация о квартире
        apt = apartment_info
        
        elements.append(Paragraph("Параметры квартиры", heading_style))
        
        # Таблица с данными
        data = []
        
        if apt.get("type"):
            data.append(["Тип:", apt["type"]])
        if apt.get("area"):
            data.append(["Площадь:", format_area(apt["area"])])
        if apt.get("floor"):
            data.append(["Этаж:", str(apt["floor"])])
        if apt.get("rooms"):
            data.append(["Комнаты:", apt["rooms"]])
        if apt.get("features"):
            data.append(["Особенности:", apt["features"]])
        
        if data:
            table = Table(data, colWidths=[50*mm, 100*mm])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('FONTNAME', (0, 0), (0, -1), f'{font_name}-Bold' if font_name == 'DejaVuSans' else 'Helvetica-Bold'),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#4a5568')),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
            ]))
            elements.append(table)
        
        elements.append(Spacer(1, 5*mm))
        
        # Цена
        elements.append(Paragraph("Стоимость", heading_style))
        
        if apt.get("price"):
            elements.append(Paragraph(format_price(apt["price"]), price_style))
        
        if apt.get("price_per_sqm"):
            elements.append(Paragraph(
                f"Цена за м²: {format_price(apt['price_per_sqm'])}",
                normal_style
            ))
        
        elements.append(Spacer(1, 5*mm))
        
        # Условия покупки
        if apt.get("payment_options") or apt.get("installment"):
            elements.append(Paragraph("Условия покупки", heading_style))
            
            if apt.get("payment_options"):
                elements.append(Paragraph(f"Варианты оплаты: {apt['payment_options']}", normal_style))
            
            if apt.get("installment"):
                elements.append(Paragraph(f"Рассрочка: {apt['installment']}", normal_style))
        
        # Сроки
        if apt.get("completion_date"):
            elements.append(Spacer(1, 3*mm))
            elements.append(Paragraph(f"Срок сдачи: {apt['completion_date']}", normal_style))
        
        # Контакты риэлтора
        if realtor_name or realtor_phone:
            elements.append(Spacer(1, 10*mm))
            elements.append(Paragraph("Контакты", heading_style))
            
            if realtor_name:
                elements.append(Paragraph(f"<b>{realtor_name}</b>", normal_style))
            if realtor_company:
                elements.append(Paragraph(realtor_company, normal_style))
            if realtor_phone:
                elements.append(Paragraph(f"Тел: {realtor_phone}", normal_style))
        
        # Дата
        elements.append(Spacer(1, 10*mm))
        date_str = datetime.now().strftime("%d.%m.%Y")
        elements.append(Paragraph(
            f"<i>Предложение действительно на {date_str}</i>",
            ParagraphStyle('Date', parent=normal_style, textColor=colors.gray, fontSize=9)
        ))
        
        # Генерируем PDF
        doc.build(elements)
        
        print(f"[KP] Generated: {filepath}")
        return str(filepath)
        
    except Exception as e:
        print(f"[KP] Generation error: {e}")
        return None


async def generate_kp_from_query(
    property_data: Dict,
    query: str,
    realtor_info: Dict = None
) -> Optional[str]:
    """
    Генерация КП на основе запроса пользователя
    
    Args:
        property_data: Данные ЖК из базы
        query: Запрос пользователя ("КП на двушку 54 метра")
        realtor_info: Информация о риэлторе
    
    Returns:
        Путь к PDF
    """
    from services.llm import quick_chat
    
    # Просим LLM извлечь параметры квартиры из запроса и данных ЖК
    prompt = f"""Из запроса "{query}" и данных ЖК извлеки параметры квартиры.

Данные ЖК:
{property_data.get('raw_data', '')}

Верни JSON:
{{
    "type": "тип квартиры",
    "area": площадь_число,
    "floor": этаж_число_или_null,
    "price": цена_число,
    "rooms": "описание комнат",
    "features": "особенности"
}}"""
    
    # Пока простая заглушка — берём данные из property_data
    apartment_info = {
        "type": query,
        "area": property_data.get("area_min"),
        "price": property_data.get("price_min"),
        "completion_date": property_data.get("completion_date"),
        "payment_options": property_data.get("payment_options"),
        "installment": property_data.get("installment_terms")
    }
    
    realtor = realtor_info or {}
    
    return await generate_kp_pdf(
        property_name=property_data.get("name", "ЖК"),
        apartment_info=apartment_info,
        realtor_name=realtor.get("name", ""),
        realtor_phone=realtor.get("phone", ""),
        realtor_company=realtor.get("company", "")
    )


async def generate_property_info_pdf(property_data, extracted_info: str = "") -> Optional[str]:
    """
    Генерация информационного PDF о ЖК (выжимка)
    
    Args:
        property_data: Объект Property из базы
        extracted_info: Извлечённая информация из файлов
    
    Returns:
        Путь к PDF
    """
    font_name = register_fonts()
    
    # Генерируем имя файла
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c for c in property_data.name if c.isalnum() or c in " _-")[:30]
    filename = f"Info_{safe_name}_{timestamp}.pdf"
    filepath = KP_OUTPUT_DIR / filename
    
    try:
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )
        
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontName=f'{font_name}-Bold' if font_name == 'DejaVuSans' else 'Helvetica-Bold',
            fontSize=18,
            spaceAfter=10*mm,
            textColor=colors.HexColor('#1a365d')
        )
        
        heading_style = ParagraphStyle(
            'Heading',
            parent=styles['Heading2'],
            fontName=f'{font_name}-Bold' if font_name == 'DejaVuSans' else 'Helvetica-Bold',
            fontSize=14,
            spaceBefore=6*mm,
            spaceAfter=3*mm,
            textColor=colors.HexColor('#2c5282')
        )
        
        normal_style = ParagraphStyle(
            'Normal',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=10,
            leading=14
        )
        
        elements = []
        
        # Заголовок
        elements.append(Paragraph(f"<b>{property_data.name}</b>", title_style))
        
        # Основная информация
        if property_data.address:
            elements.append(Paragraph(f"Адрес: {property_data.address}", normal_style))
        if property_data.developer:
            elements.append(Paragraph(f"Застройщик: Застройщик: {property_data.developer}", normal_style))
        if property_data.completion_date:
            elements.append(Paragraph(f"Сдача: Сдача: {property_data.completion_date}", normal_style))
        
        elements.append(Spacer(1, 5*mm))
        
        # Цены
        if property_data.price_min or property_data.price_max:
            elements.append(Paragraph("Цены", heading_style))
            if property_data.price_min and property_data.price_max:
                elements.append(Paragraph(
                    f"От {format_price(property_data.price_min)} до {format_price(property_data.price_max)}",
                    normal_style
                ))
            elif property_data.price_min:
                elements.append(Paragraph(f"От {format_price(property_data.price_min)}", normal_style))
        
        # Квартиры
        if property_data.apartment_types:
            elements.append(Paragraph("Типы квартир", heading_style))
            elements.append(Paragraph(property_data.apartment_types, normal_style))
        
        if property_data.area_min and property_data.area_max:
            elements.append(Paragraph(
                f"Площади: от {property_data.area_min} до {property_data.area_max} м²",
                normal_style
            ))
        
        # Условия
        if property_data.payment_options or property_data.installment_terms:
            elements.append(Paragraph("Условия покупки", heading_style))
            if property_data.payment_options:
                elements.append(Paragraph(f"Варианты: {property_data.payment_options}", normal_style))
            if property_data.installment_terms:
                elements.append(Paragraph(f"Рассрочка: {property_data.installment_terms}", normal_style))
        
        # Описание
        if property_data.description:
            elements.append(Paragraph("О проекте", heading_style))
            elements.append(Paragraph(property_data.description, normal_style))
        
        # Особенности
        if property_data.features:
            elements.append(Paragraph("Особенности", heading_style))
            elements.append(Paragraph(property_data.features, normal_style))
        
        # Детальная информация из файлов (первые 3000 символов)
        if extracted_info:
            elements.append(Spacer(1, 5*mm))
            elements.append(Paragraph("Детальная информация", heading_style))
            # Ограничиваем и очищаем текст
            clean_info = extracted_info[:3000].replace('\n', '<br/>')
            elements.append(Paragraph(clean_info, normal_style))
        
        # Дата
        elements.append(Spacer(1, 10*mm))
        date_str = datetime.now().strftime("%d.%m.%Y")
        elements.append(Paragraph(
            f"<i>Сформировано: {date_str}</i>",
            ParagraphStyle('Date', parent=normal_style, textColor=colors.gray, fontSize=9)
        ))
        
        doc.build(elements)
        
        print(f"[KP] Generated info PDF: {filepath}")
        return str(filepath)
        
    except Exception as e:
        print(f"[KP] Info PDF generation error: {e}")
        return None
