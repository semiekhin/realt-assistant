"""
Стили для PDF документов
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
from reportlab.lib.colors import HexColor, Color


@dataclass
class PDFStyle:
    """Конфигурация стиля PDF"""
    name: str
    
    # Цвета
    primary: Color          # Основной цвет (заголовки, акценты)
    secondary: Color        # Вторичный цвет (подзаголовки)
    accent: Color           # Акцентный цвет (цены, важное)
    background: Color       # Фон блоков
    text: Color             # Основной текст
    text_light: Color       # Второстепенный текст
    
    # Типографика
    font_family: str        # Основной шрифт
    title_size: int         # Размер заголовка
    heading_size: int       # Размер подзаголовков
    body_size: int          # Размер текста
    caption_size: int       # Размер подписей
    
    # Отступы (в mm)
    margin_top: int
    margin_bottom: int
    margin_left: int
    margin_right: int
    block_padding: int      # Внутренний отступ блоков
    
    # Декор
    use_lines: bool         # Использовать разделительные линии
    use_blocks: bool        # Использовать цветные блоки
    rounded_corners: bool   # Скруглённые углы
    show_icons: bool        # Показывать иконки (emoji)


# === ПРЕДУСТАНОВЛЕННЫЕ СТИЛИ ===

STYLES: Dict[str, PDFStyle] = {
    
    "premium": PDFStyle(
        name="premium",
        primary=HexColor("#1a1a2e"),       # Тёмно-синий
        secondary=HexColor("#16213e"),      # Глубокий синий
        accent=HexColor("#d4af37"),         # Золотой
        background=HexColor("#f8f9fa"),     # Светло-серый
        text=HexColor("#1a1a2e"),           # Тёмный
        text_light=HexColor("#6c757d"),     # Серый
        font_family="DejaVuSans",
        title_size=24,
        heading_size=14,
        body_size=11,
        caption_size=9,
        margin_top=25,
        margin_bottom=20,
        margin_left=25,
        margin_right=25,
        block_padding=12,
        use_lines=False,
        use_blocks=True,
        rounded_corners=False,
        show_icons=False
    ),
    
    "business": PDFStyle(
        name="business",
        primary=HexColor("#2c3e50"),        # Тёмно-серый синий
        secondary=HexColor("#34495e"),      # Серо-синий
        accent=HexColor("#27ae60"),         # Зелёный (деньги)
        background=HexColor("#ecf0f1"),     # Светлый
        text=HexColor("#2c3e50"),           # Тёмный
        text_light=HexColor("#7f8c8d"),     # Серый
        font_family="DejaVuSans",
        title_size=20,
        heading_size=13,
        body_size=10,
        caption_size=8,
        margin_top=20,
        margin_bottom=15,
        margin_left=20,
        margin_right=20,
        block_padding=10,
        use_lines=True,
        use_blocks=False,
        rounded_corners=False,
        show_icons=False
    ),
    
    "modern": PDFStyle(
        name="modern",
        primary=HexColor("#6366f1"),        # Индиго
        secondary=HexColor("#8b5cf6"),      # Фиолетовый
        accent=HexColor("#f59e0b"),         # Оранжевый
        background=HexColor("#f1f5f9"),     # Slate-100
        text=HexColor("#1e293b"),           # Slate-800
        text_light=HexColor("#64748b"),     # Slate-500
        font_family="DejaVuSans",
        title_size=22,
        heading_size=13,
        body_size=10,
        caption_size=9,
        margin_top=20,
        margin_bottom=20,
        margin_left=20,
        margin_right=20,
        block_padding=12,
        use_lines=False,
        use_blocks=True,
        rounded_corners=True,
        show_icons=True
    ),
    
    "minimal": PDFStyle(
        name="minimal",
        primary=HexColor("#111827"),        # Почти чёрный
        secondary=HexColor("#374151"),      # Тёмно-серый
        accent=HexColor("#111827"),         # Чёрный
        background=HexColor("#ffffff"),     # Белый
        text=HexColor("#111827"),           # Тёмный
        text_light=HexColor("#9ca3af"),     # Серый
        font_family="DejaVuSans",
        title_size=18,
        heading_size=12,
        body_size=10,
        caption_size=8,
        margin_top=20,
        margin_bottom=15,
        margin_left=25,
        margin_right=25,
        block_padding=8,
        use_lines=True,
        use_blocks=False,
        rounded_corners=False,
        show_icons=False
    ),
    
    "warm": PDFStyle(
        name="warm",
        primary=HexColor("#92400e"),        # Янтарный тёмный
        secondary=HexColor("#b45309"),      # Янтарный
        accent=HexColor("#dc2626"),         # Красный
        background=HexColor("#fef3c7"),     # Кремовый
        text=HexColor("#451a03"),           # Коричневый
        text_light=HexColor("#78716c"),     # Stone
        font_family="DejaVuSans",
        title_size=22,
        heading_size=14,
        body_size=11,
        caption_size=9,
        margin_top=20,
        margin_bottom=20,
        margin_left=20,
        margin_right=20,
        block_padding=12,
        use_lines=False,
        use_blocks=True,
        rounded_corners=True,
        show_icons=True
    ),
    
    "corporate": PDFStyle(
        name="corporate",
        primary=HexColor("#1e3a5f"),        # Тёмно-синий
        secondary=HexColor("#2d5a87"),      # Синий
        accent=HexColor("#1e3a5f"),         # Тёмно-синий (без ярких)
        background=HexColor("#f0f4f8"),     # Светло-серый с синевой
        text=HexColor("#1a202c"),           # Почти чёрный
        text_light=HexColor("#718096"),     # Серый
        font_family="DejaVuSans",
        title_size=20,
        heading_size=13,
        body_size=10,
        caption_size=8,
        margin_top=20,
        margin_bottom=15,
        margin_left=20,
        margin_right=20,
        block_padding=10,
        use_lines=True,
        use_blocks=False,
        rounded_corners=False,
        show_icons=False
    ),
}


def get_style(style_name: str) -> PDFStyle:
    """Получить стиль по имени"""
    return STYLES.get(style_name, STYLES["modern"])


# === МАППИНГ КОНТЕКСТА НА СТИЛИ ===

CONTEXT_STYLE_MAP = {
    # Класс ЖК
    "премиум": "premium",
    "бизнес": "business",
    "бизнес-класс": "business",
    "элитный": "premium",
    "luxury": "premium",
    "комфорт": "modern",
    "комфорт-класс": "modern",
    "эконом": "minimal",
    "стандарт": "minimal",
    
    # Аудитория
    "инвестор": "business",
    "инвестиция": "business",
    "семья": "warm",
    "молодая семья": "warm",
    "молодые": "modern",
    "студент": "minimal",
}


def suggest_style_from_context(text: str) -> str:
    """Предложить стиль на основе контекста"""
    text_lower = text.lower()
    
    for keyword, style in CONTEXT_STYLE_MAP.items():
        if keyword in text_lower:
            return style
    
    return "modern"  # По умолчанию
