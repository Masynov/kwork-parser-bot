import logging
import json
import os
from bs4 import BeautifulSoup
from config import KWORK_URL

logger = logging.getLogger(__name__)

async def fetch_kwork_orders(session) -> list:
    try:
        from curl_cffi.requests import AsyncSession
        
        async with AsyncSession() as s:
            response = await s.get(KWORK_URL, impersonate="chrome", timeout=15)
            html = response.text
            
            # Сохраняем слепок для непредвиденных ситуаций
            with open("debug.html", "w", encoding="utf-8") as f:
                f.write(html)
    except Exception as e:
        logger.error(f"❌ Ошибка сети при запросе к Kwork: {e}")
        # Резервный режим: если сеть временно недоступна, работаем по локальному кэшу
        if os.path.exists("debug.html"):
            logger.info("♻️ Сеть недоступна. Используем сохраненный debug.html...")
            with open("debug.html", "r", encoding="utf-8") as f:
                html = f.read()
        else:
            return []

    soup = BeautifulSoup(html, "lxml")
    scripts = soup.find_all("script")
    
    # Сканируем тяжелые скрипты инициализации страницы
    for script in scripts:
        script_text = script.string or script.text or ""
        if len(script_text) < 50000:  # Игнорируем мелкие системные скрипты
            continue
            
        if "wants" in script_text or "projects" in script_text:
            logger.info(f"🚀 [ПАРСЕР] Препарируем массивный JS-контекст ({len(script_text)} симв.)...")
            
            # Перебираем ключевые маркеры, за которыми может скрываться JSON-массив проектов
            for marker in ["\"wants\"", "'wants'", "wants", "\"items\"", "projects"]:
                start_pos = 0
                while True:
                    pos = script_text.find(marker, start_pos)
                    if pos == -1:
                        break
                    
                    # Пробуем нарезать валидную JSON структуру, идущую после маркера
                    json_str = extract_json_by_bracket(script_text, pos)
                    if json_str:
                        try:
                            data = json.loads(json_str)
                            orders = process_extracted_json(data)
                            if orders:
                                logger.info(f"✨ [УСПЕХ] Алгоритм извлек {len(orders)} чистых заказов из JS-стейта!")
                                return orders
                        except:
                            pass
                    start_pos = pos + len(marker)
                    
    logger.warning("⚠️ [ПАРСЕР] JS-структура проанализирована, но активных заказов внутри не обнаружено.")
    return []

def extract_json_by_bracket(text, start_idx):
    """Находит первую открывающую скобку ({ или [) после start_idx и вырезает сбалансированный JSON"""
    first_bracket_idx = -1
    bracket_type = None
    
    for i in range(start_idx, len(text)):
        if text[i] == '{':
            first_bracket_idx = i
            bracket_type = ('{', '}')
            break
        elif text[i] == '[':
            first_bracket_idx = i
            bracket_type = ('[', ']')
            break
            
    if first_bracket_idx == -1:
        return None
        
    open_br, close_br = bracket_type
    count = 0
    in_string = False
    escape = False
    
    for i in range(first_bracket_idx, len(text)):
        char = text[i]
        
        if escape:
            escape = False
            continue
        if char == '\\':
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
            
        if not in_string:
            if char == open_br:
                count += 1
            elif char == close_br:
                count -= 1
                if count == 0:
                    return text[first_bracket_idx:i+1]
    return None

def process_extracted_json(data) -> list:
    """Адаптивно обрабатывает извлеченный JSON независимо от вложенности (Nuxt / Vue State)"""
    if isinstance(data, list):
        return parse_list(data)
        
    if isinstance(data, dict):
        # Проверяем прямые классические ключи
        for key in ["wants", "items", "projects", "data"]:
            if key in data and isinstance(data[key], list):
                res = parse_list(data[key])
                if res: return res
                
        # Если структура мудреная, запускаем рекурсивный поиск массивов с маркерами проектов
        for key, value in data.items():
            if isinstance(value, list) and len(value) > 0:
                first = value[0]
                if isinstance(first, dict) and ('id' in first or 'want_id' in first) and ('title' in first or 'name' in first):
                    return parse_list(value)
            elif isinstance(value, dict):
                res = process_extracted_json(value)
                if res: return res
    return []

def parse_list(wants_list) -> list:
    """Парсит нормализованные поля объектов биржи"""
    orders = []
    for item in wants_list:
        if not isinstance(item, dict): 
            continue
            
        order_id = item.get("id") or item.get("want_id") or item.get("projectId")
        if not order_id: 
            continue
        
        title = item.get("title") or item.get("name") or item.get("subject") or "Без названия"
        
        price = "Не указана"
        if item.get("priceLimit"): price = f"{item['priceLimit']} руб."
        elif item.get("price"): price = f"{item['price']} руб."
        elif item.get("cost"): price = f"{item['cost']} руб."
        
        desc = item.get("description") or item.get("text") or item.get("shortDescription") or ""
        
        orders.append({
            "id": str(order_id),
            "title": str(title).strip(),
            "price": str(price).strip(),
            "description": str(desc).strip()[:400],
            "url": f"https://kwork.ru/projects?project={order_id}"
        })
    return orders