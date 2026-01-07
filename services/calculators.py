"""
Калькуляторы для риэлтора
- Рассрочка
- Ипотека (стандартная, семейная, IT)
- ROI (доходность от аренды)
"""
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timedelta


# === СТАВКИ ИПОТЕКИ (январь 2025) ===

MORTGAGE_PROGRAMS = {
    "standard": {
        "name": "Стандартная",
        "rate": 28.0,
        "min_down_payment": 20,
        "max_years": 30,
        "description": "Базовая программа"
    },
    "family": {
        "name": "Семейная",
        "rate": 6.0,
        "min_down_payment": 20,
        "max_years": 30,
        "description": "Для семей с детьми до 6 лет"
    },
    "it": {
        "name": "IT-ипотека",
        "rate": 5.0,
        "min_down_payment": 20,
        "max_years": 30,
        "description": "Для сотрудников IT-компаний"
    },
    "far_east": {
        "name": "Дальневосточная",
        "rate": 2.0,
        "min_down_payment": 20,
        "max_years": 20,
        "description": "Для ДФО, до 35 лет"
    }
}


@dataclass
class InstallmentResult:
    price: int
    down_payment: int
    down_payment_pct: float
    remainder: int
    months: int
    monthly_payment: int
    total_paid: int
    overpayment: int
    overpayment_pct: float
    schedule: List[dict]


@dataclass
class MortgageResult:
    price: int
    down_payment: int
    down_payment_pct: float
    loan_amount: int
    rate: float
    years: int
    monthly_payment: int
    total_paid: int
    overpayment: int
    overpayment_pct: float
    program_name: str
    program_description: str


@dataclass
class ROIResult:
    price: int
    daily_rent: int
    occupancy_pct: float
    days_occupied: int
    gross_income: int
    expenses: int
    expenses_breakdown: dict
    net_income: int
    roi_pct: float
    payback_years: float
    monthly_net: int


def calc_installment(
    price: int,
    down_payment_pct: float,
    months: int,
    markup_pct: float = 0
) -> InstallmentResult:
    down_payment = int(price * down_payment_pct / 100)
    remainder = price - down_payment
    
    if markup_pct > 0:
        remainder_with_markup = int(remainder * (1 + markup_pct / 100))
    else:
        remainder_with_markup = remainder
    
    monthly_payment = int(remainder_with_markup / months)
    total_paid = down_payment + remainder_with_markup
    overpayment = total_paid - price
    overpayment_pct = (overpayment / price * 100) if price > 0 else 0
    
    schedule = []
    current_date = datetime.now()
    
    schedule.append({
        "month": 0,
        "date": current_date.strftime("%d.%m.%Y"),
        "payment": down_payment,
        "type": "Первоначальный взнос",
        "remaining": remainder_with_markup
    })
    
    remaining = remainder_with_markup
    for i in range(1, months + 1):
        payment_date = current_date + timedelta(days=30 * i)
        payment = monthly_payment if i < months else remaining
        remaining -= payment
        
        schedule.append({
            "month": i,
            "date": payment_date.strftime("%d.%m.%Y"),
            "payment": payment,
            "type": "Ежемесячный платёж",
            "remaining": max(0, remaining)
        })
    
    return InstallmentResult(
        price=price,
        down_payment=down_payment,
        down_payment_pct=down_payment_pct,
        remainder=remainder,
        months=months,
        monthly_payment=monthly_payment,
        total_paid=total_paid,
        overpayment=overpayment,
        overpayment_pct=round(overpayment_pct, 1),
        schedule=schedule
    )


def calc_mortgage(
    price: int,
    down_payment_pct: float,
    years: int,
    program: str = "standard"
) -> MortgageResult:
    prog = MORTGAGE_PROGRAMS.get(program, MORTGAGE_PROGRAMS["standard"])
    rate = prog["rate"]
    
    down_payment = int(price * down_payment_pct / 100)
    loan_amount = price - down_payment
    
    monthly_rate = rate / 100 / 12
    months = years * 12
    
    if monthly_rate > 0:
        monthly_payment = loan_amount * (
            monthly_rate * (1 + monthly_rate) ** months
        ) / (
            (1 + monthly_rate) ** months - 1
        )
    else:
        monthly_payment = loan_amount / months
    
    monthly_payment = int(monthly_payment)
    total_paid = monthly_payment * months + down_payment
    overpayment = total_paid - price
    overpayment_pct = (overpayment / price * 100) if price > 0 else 0
    
    return MortgageResult(
        price=price,
        down_payment=down_payment,
        down_payment_pct=down_payment_pct,
        loan_amount=loan_amount,
        rate=rate,
        years=years,
        monthly_payment=monthly_payment,
        total_paid=total_paid,
        overpayment=overpayment,
        overpayment_pct=round(overpayment_pct, 1),
        program_name=prog["name"],
        program_description=prog["description"]
    )


def calc_mortgage_comparison(
    price: int,
    down_payment_pct: float,
    years: int
) -> List[MortgageResult]:
    results = []
    for program_key in MORTGAGE_PROGRAMS:
        result = calc_mortgage(price, down_payment_pct, years, program_key)
        results.append(result)
    results.sort(key=lambda x: x.monthly_payment)
    return results


def calc_roi(
    price: int,
    daily_rent: int,
    occupancy_pct: float = 70,
    uk_pct: float = 20,
    utilities_monthly: int = 5000,
    tax_pct: float = 4
) -> ROIResult:
    days_occupied = int(365 * occupancy_pct / 100)
    gross_income = daily_rent * days_occupied
    
    uk_fee = int(gross_income * uk_pct / 100)
    utilities_year = utilities_monthly * 12
    tax = int(gross_income * tax_pct / 100)
    
    total_expenses = uk_fee + utilities_year + tax
    
    expenses_breakdown = {
        "uk_fee": uk_fee,
        "utilities": utilities_year,
        "tax": tax
    }
    
    net_income = gross_income - total_expenses
    roi_pct = (net_income / price * 100) if price > 0 else 0
    payback_years = (price / net_income) if net_income > 0 else 999
    monthly_net = int(net_income / 12)
    
    return ROIResult(
        price=price,
        daily_rent=daily_rent,
        occupancy_pct=occupancy_pct,
        days_occupied=days_occupied,
        gross_income=gross_income,
        expenses=total_expenses,
        expenses_breakdown=expenses_breakdown,
        net_income=net_income,
        roi_pct=round(roi_pct, 1),
        payback_years=round(payback_years, 1),
        monthly_net=monthly_net
    )


def format_money(amount: int) -> str:
    return f"{amount:,}".replace(",", " ") + " ₽"


def format_installment_result(result: InstallmentResult) -> str:
    lines = [
        "📊 <b>Расчёт рассрочки</b>",
        "",
        f"🏠 Стоимость: {format_money(result.price)}",
        f"💰 Первый взнос ({result.down_payment_pct}%): {format_money(result.down_payment)}",
        f"📅 Срок: {result.months} мес.",
        "",
        f"📈 <b>Ежемесячный платёж: {format_money(result.monthly_payment)}</b>",
        "",
        f"💵 Всего к оплате: {format_money(result.total_paid)}",
    ]
    
    if result.overpayment > 0:
        lines.append(f"📍 Удорожание: {format_money(result.overpayment)} ({result.overpayment_pct}%)")
    
    return "\n".join(lines)


def format_mortgage_result(result: MortgageResult) -> str:
    lines = [
        f"🏦 <b>Ипотека — {result.program_name}</b>",
        f"<i>{result.program_description}</i>",
        "",
        f"🏠 Стоимость: {format_money(result.price)}",
        f"💰 Первый взнос ({result.down_payment_pct}%): {format_money(result.down_payment)}",
        f"💳 Сумма кредита: {format_money(result.loan_amount)}",
        f"📊 Ставка: {result.rate}%",
        f"📅 Срок: {result.years} лет",
        "",
        f"📈 <b>Ежемесячный платёж: {format_money(result.monthly_payment)}</b>",
        "",
        f"💵 Всего к оплате: {format_money(result.total_paid)}",
        f"📍 Переплата: {format_money(result.overpayment)} ({result.overpayment_pct}%)",
    ]
    
    return "\n".join(lines)


def format_roi_result(result: ROIResult) -> str:
    lines = [
        "📊 <b>Расчёт доходности</b>",
        "",
        f"🏠 Стоимость: {format_money(result.price)}",
        f"🛏 Ставка: {format_money(result.daily_rent)}/сутки",
        f"📅 Загрузка: {result.occupancy_pct}% ({result.days_occupied} дней/год)",
        "",
        f"💰 Валовый доход: {format_money(result.gross_income)}/год",
        f"📉 Расходы: {format_money(result.expenses)}/год",
        f"   • УК: {format_money(result.expenses_breakdown['uk_fee'])}",
        f"   • Коммуналка: {format_money(result.expenses_breakdown['utilities'])}",
        f"   • Налог: {format_money(result.expenses_breakdown['tax'])}",
        "",
        f"✅ <b>Чистый доход: {format_money(result.net_income)}/год</b>",
        f"📈 <b>В месяц: {format_money(result.monthly_net)}</b>",
        "",
        f"💹 ROI: {result.roi_pct}% годовых",
        f"⏱ Окупаемость: {result.payback_years} лет",
    ]
    
    return "\n".join(lines)
