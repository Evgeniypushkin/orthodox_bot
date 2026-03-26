import os
import json
import xml.etree.ElementTree as ET
from datetime import datetime

def convert_lives():
    # Папка, куда вы склонировали репозиторий
    source_dir = "orthodox-typikon-feasts-xml/lives-of-the-saints-ru"
    output_file = "data/lives.json"
    
    result = {}
    
    for month in range(1, 13):
        month_str = f"{month:02d}"
        xml_file = os.path.join(source_dir, f"{month_str}.xml")
        if not os.path.exists(xml_file):
            continue
        
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        for feast in root.findall("feast"):
            date_elem = feast.find("date/julian")
            if date_elem is None:
                continue
            date_str = date_elem.text  # формат "01-12" (месяц-день)
            # Преобразуем в "12-01" (день-месяц) для удобства поиска
            month_day = date_str.split("-")
            if len(month_day) != 2:
                continue
            day_key = f"{month_day[1]}-{month_day[0]}"  # день-месяц
            
            # Извлекаем имя святого
            title_elem = feast.find("title/ru")
            name = title_elem.text if title_elem is not None else "Святой"
            
            # Извлекаем текст жития (все <p> под <text>)
            content_parts = []
            for p in feast.findall("content/text/p"):
                if p.text:
                    content_parts.append(p.text.strip())
            life = "\n\n".join(content_parts)
            
            if day_key not in result:
                result[day_key] = []
            result[day_key].append({"name": name, "life": life})
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"Сохранено {len(result)} дней")

if __name__ == "__main__":
    convert_lives()
