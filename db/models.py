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
    
    # Локация и особенности
    distance_to_sea: str = ""  # "350 м"
    territory_area: str = ""  # "9 га"
    hotel_operator: str = ""  # "Lee Prime"
    
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
        
        if self.distance_to_sea:
            lines.append(f"🏖 До моря: {self.distance_to_sea}")
        if self.territory_area:
            lines.append(f"🌳 Территория: {self.territory_area}")
        if self.hotel_operator:
            lines.append(f"🏨 Оператор: {self.hotel_operator}")
        
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

    def to_full_info(self) -> str:
        """Полная информация для проверки риэлтором"""
        lines = [f"🏢 <b>{self.name}</b>", ""]
        
        # Локация
        lines.append("📍 <b>Локация:</b>")
        if self.address:
            lines.append(f"   Адрес: {self.address}")
        if self.distance_to_sea:
            lines.append(f"   До моря: {self.distance_to_sea}")
        if self.territory_area:
            lines.append(f"   Территория: {self.territory_area}")
        
        # Застройщик и сроки
        lines.append("")
        lines.append("🏗 <b>Застройщик и сроки:</b>")
        if self.developer:
            lines.append(f"   Застройщик: {self.developer}")
        if self.completion_date:
            lines.append(f"   Сдача: {self.completion_date}")
        if self.hotel_operator:
            lines.append(f"   Оператор: {self.hotel_operator}")
        
        # Цены
        lines.append("")
        lines.append("💰 <b>Цены:</b>")
        if self.price_min and self.price_max:
            lines.append(f"   Диапазон: {self.price_min/1_000_000:.1f} – {self.price_max/1_000_000:.1f} млн ₽")
        elif self.price_min:
            lines.append(f"   От: {self.price_min/1_000_000:.1f} млн ₽")
        if self.price_per_sqm_min and self.price_per_sqm_max:
            lines.append(f"   За м²: {self.price_per_sqm_min:,} – {self.price_per_sqm_max:,} ₽".replace(",", " "))
        elif self.price_per_sqm_min:
            lines.append(f"   За м²: от {self.price_per_sqm_min:,} ₽".replace(",", " "))
        
        # Квартиры
        lines.append("")
        lines.append("🏠 <b>Квартиры:</b>")
        if self.apartment_types:
            lines.append(f"   Типы: {self.apartment_types}")
        if self.area_min and self.area_max:
            lines.append(f"   Площади: {self.area_min:.1f} – {self.area_max:.1f} м²")
        elif self.area_min:
            lines.append(f"   Площадь от: {self.area_min:.1f} м²")
        
        # Условия покупки
        lines.append("")
        lines.append("💳 <b>Условия покупки:</b>")
        if self.payment_options:
            lines.append(f"   Способы: {self.payment_options}")
        if self.installment_min_pv is not None:
            inst = f"   Рассрочка: ПВ от {self.installment_min_pv:.0f}%"
            if self.installment_max_months:
                inst += f", до {self.installment_max_months} мес"
            if self.installment_markup is not None:
                if self.installment_markup == 0:
                    inst += ", 0%"
                else:
                    inst += f", +{self.installment_markup:.0f}%"
            lines.append(inst)
        elif self.installment_terms:
            lines.append(f"   Рассрочка: {self.installment_terms}")
        if self.mortgage_info:
            lines.append(f"   Ипотека: {self.mortgage_info}")
        if self.commission:
            lines.append(f"   Комиссия: {self.commission}")
        else:
            lines.append(f"   Комиссия: не указана")
        
        # Описание
        if self.description:
            lines.append("")
            lines.append("📝 <b>Описание:</b>")
            lines.append(f"   {self.description}")
        
        # Особенности
        if self.features:
            lines.append("")
            lines.append("✨ <b>Особенности:</b>")
            lines.append(f"   {self.features}")
        
        return "\n".join(lines)
