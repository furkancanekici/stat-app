import re


def normalize_story(story: str) -> str:
    """
    'Story1', '1.KAT', 'Kat 1', 'ZEMIN' gibi farklı formatları
    normalize eder.
    """
    if not story:
        return ""
    
    s = story.strip().upper()
    
    # Türkçe özel karakterleri dönüştür
    s = s.replace("İ", "I").replace("Ğ", "G").replace("Ü", "U")
    s = s.replace("Ş", "S").replace("Ö", "O").replace("Ç", "C")
    
    # Zemin kat varyasyonları
    if any(x in s for x in ["ZEMIN", "GROUND", "GF", "Z KAT", "Z.KAT"]):
        return "ZEMIN"
    
    # Bodrum varyasyonları
    if any(x in s for x in ["BODRUM", "BASEMENT", "B1", "B2", "-1", "-2"]):
        # Kaçıncı bodrum olduğunu bul
        num = re.search(r'\d+', s)
        return f"BODRUM{num.group() if num else '1'}"
    
    # Sayısal kat: Story1, Kat1, 1.KAT, 1. KAT vb.
    num = re.search(r'\d+', s)
    if num:
        return f"KAT{num.group()}"
    
    return s


def normalize_label(label: str) -> str:
    """
    Eleman label'ını normalize eder.
    'B1', 'b1', 'B 1', 'B-1' → 'B1'
    """
    if not label:
        return ""
    
    s = label.strip().upper()
    s = s.replace(" ", "").replace("-", "").replace("_", "")
    return s


def normalize_section(section: str) -> str:
    """
    Kesit adını normalize eder.
    'W14X48', 'w14x48', 'W 14 X 48' → 'W14X48'
    """
    if not section:
        return ""
    
    s = section.strip().upper()
    s = s.replace(" ", "")
    return s