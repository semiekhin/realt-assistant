"""
Модели данных для Realt Assistant
"""
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
import json


@dataclass
class Property:
    """ЖК / Объект недвижимости"""
    id: Optional[int] = None
    user_id: int = 0  # Telegram ID владельца
    
    # Основная информация
    name: str = ""  # Название ЖК
    address: str = ""
    developer: str = ""  # Застройщик
    
    # Сроки
    completion_date: str = ""  # "Q4 2025", "Сдан", и т.д.
    
    # Цены
    price_min: Optional[int] = None  # минимальная цена в рублях
    price_max: Optional[int] = None
    price_per_sqm_min: Optional[int] = None  # цена за м²
    price_per_sqm_max: Optional[int] = None
    
    # Квартиры
    apartment_types: str = ""  # "студии, 1к, 2к, 3к"
    area_min: Optional[float] = None  # минимальная площадь
    area_max: Optional[float] = None
    
    # Условия покупки (текстовые — legacy)
    payment_options: str = ""  # "100%, рассрочка, ипотека"
    installment_terms: str = ""  # "30% + 24 мес" (текстовое описание)
    mortgage_info: str = ""
    
    # Условия рассрочки (структурированные — для калькулятора)
    installment_min_pv: Optional[float] = None  # Мин. ПВ в % (10, 20, 30)
    installment_max_months: Optional[int] = None  # Макс. срок в месяцах (18, 24, 36)
    installment_markup: Optional[float] = None  # Удорожание в % (0, 5, 10)
    
    # Комиссия риэлтора
    commission: str = ""  # "3%", "150 000 ₽"
    
    # Дополнительно
    description: str = ""  # Общее описание
    features: str = ""  # Особенности, инфраструктура
    raw_data: str = ""  # Сырые данные из LLM (JSON)
    
    # Мета
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_summary(self) -> str:
        """Краткая сводка для отображения"""
        lines = [f"🏢 <b>{self.name}</b>"]
        
        if self.address:
            lines.append(f"📍 {self.address}")
        if self.developer:
            lines.append(f"🏗 Застройщик: {self.developer}")
        if self.completion_date:
            lines.append(f"📅 Сдача: {self.completion_date}")
        
        if self.price_min and self.price_max:
            lines.append(f"💰 Цены: {self.price_min/1_000_000:.1f} – {self.price_max/1_000_000:.1f} млн ₽")
        elif self.price_min:
            lines.append(f"💰 Цены: от {self.price_min/1_000_000:.1f} млн ₽")
        
        if self.apartment_types:
            lines.append(f"🏠 Квартиры: {self.apartment_types}")
        
        # Условия рассрочки — структурированные
        if self.installment_min_pv is not None:
            installment_line = f"💳 Рассрочка: ПВ от {self.installment_min_pv:.0f}%"
            if self.installment_max_months:
                installment_line += f", до {self.installment_max_months} мес"
            if self.installment_markup is not None and self.installment_markup > 0:
                installment_line += f", +{self.installment_markup:.0f}%"
            elif self.installment_markup == 0:
                installment_line += ", без удорожания"
            lines.append(installment_line)
        elif self.installment_terms:
            lines.append(f"💳 Рассрочка: {self.installment_terms}")
        
        if self.commission:
            lines.append(f"💵 Комиссия: {self.commission}")
        
        return "\n".join(lines)


@dataclass
class PropertyFile:
    """Загруженный файл ЖК"""
    id: Optional[int] = None
    property_id: int = 0
    user_id: int = 0
    
    file_id: str = ""  # Telegram file_id
    file_name: str = ""
    file_type: str = ""  # document, photo, spreadsheet
    file_path: str = ""  # локальный путь
    
    extracted_text: str = ""  # извлечённый текст
    
    created_at: Optional[datetime] = None


@dataclass 
class User:
    """Пользователь (риэлтор)"""
    id: Optional[int] = None
    telegram_id: int = 0
    username: str = ""
    first_name: str = ""
    last_name: str = ""
    
    # Состояние диалога
    state: str = ""  # текущее состояние FSM
    state_data: str = ""  # JSON с данными состояния
    
    created_at: Optional[datetime] = None
    
    def get_state_data(self) -> dict:
        if self.state_data:
            return json.loads(self.state_data)
        return {}
    
    def set_state_data(self, data: dict):
        self.state_data = json.dumps(data, ensure_ascii=False)
