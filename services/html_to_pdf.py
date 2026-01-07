"""
HTML → PDF конвертер через wkhtmltopdf
"""
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional

from config import DATA_DIR

KP_OUTPUT_DIR = DATA_DIR / "kp_output"
KP_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def html_to_pdf(html_content: str, filename: str = None) -> Optional[str]:
    """Конвертирует HTML в PDF"""
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"doc_{timestamp}.pdf"
    
    pdf_path = KP_OUTPUT_DIR / filename
    
    try:
        # Создаём временный HTML файл
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html_content)
            html_path = f.name
        
        # Конвертируем
        result = subprocess.run([
            'wkhtmltopdf',
            '--encoding', 'utf-8',
            '--page-size', 'A4',
            '--margin-top', '15mm',
            '--margin-bottom', '15mm',
            '--margin-left', '15mm',
            '--margin-right', '15mm',
            '--enable-local-file-access',
            '--quiet',
            html_path,
            str(pdf_path)
        ], capture_output=True, timeout=30)
        
        # Удаляем временный файл
        Path(html_path).unlink(missing_ok=True)
        
        if pdf_path.exists():
            print(f"[PDF] Created: {pdf_path}")
            return str(pdf_path)
        else:
            print(f"[PDF] Error: {result.stderr.decode()}")
            return None
            
    except subprocess.TimeoutExpired:
        print("[PDF] Timeout")
        return None
    except Exception as e:
        print(f"[PDF] Error: {e}")
        return None


# Базовый HTML шаблон
BASE_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: 'DejaVu Sans', Arial, sans-serif;
            font-size: 14px;
            line-height: 1.5;
            color: #333;
            margin: 0;
            padding: 20px;
        }}
        h1 {{
            color: #1a365d;
            font-size: 24px;
            margin-bottom: 20px;
        }}
        h2 {{
            color: #2d3748;
            font-size: 18px;
            margin-top: 25px;
            margin-bottom: 10px;
        }}
        .header {{
            background: linear-gradient(135deg, #1a365d 0%, #2d4a7c 100%);
            color: white;
            padding: 30px;
            margin: -20px -20px 20px -20px;
            text-align: center;
        }}
        .header h1 {{
            color: white;
            margin: 0;
        }}
        .section {{
            margin-bottom: 20px;
            padding: 15px;
            background: #f7fafc;
            border-radius: 8px;
        }}
        .price {{
            font-size: 22px;
            font-weight: bold;
            color: #2d4a7c;
        }}
        .highlight {{
            background: #ebf8ff;
            padding: 10px 15px;
            border-left: 4px solid #3182ce;
            margin: 10px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }}
        th {{
            background: #edf2f7;
            font-weight: bold;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e2e8f0;
            font-size: 12px;
            color: #718096;
            text-align: center;
        }}
    </style>
</head>
<body>
{content}
</body>
</html>"""


def wrap_html(content: str) -> str:
    """Оборачивает контент в базовый шаблон если нужно"""
    if '<html' in content.lower():
        return content
    return BASE_HTML_TEMPLATE.format(content=content)
