"""
ETABS API ile model tablolarını otomatik çekme modülü.

Üretilen Excel dosyası, ETABS'ın kendi "File → Export → Tables to Excel"
çıktısıyla BİREBİR AYNI formatta olur. Böylece STAT'ın mevcut reader'ları
hiçbir değişiklik olmadan çalışır.

Format:
  - Her sheet'te satır 0: "TABLE:  <tam_tablo_adı>"
  - Satır 1: Sütun başlıkları (boşluklu isimler — "Output Case")
  - Satır 2+: Veri satırları (ondalık ayırıcı: nokta)
  - Sheet isimleri: ETABS'ın kendi kısaltmaları (max 31 karakter)
"""

import os
import logging
from io import BytesIO

import pandas as pd

logger = logging.getLogger(__name__)

# ─── STAT'ın ihtiyaç duyduğu tablolar ───
# (ETABS API tablo key'i, sheet kısa adı)
# Sheet kısa adı ETABS'ın elle export'ta kullandığı isimle aynı olmalı.
# Reader'lar bu kısa isimlere göre sheet buluyor.
STAT_TABLE_MAP = [
    ("Program Control",                                          "Program Control"),
    ("Material Properties - General",                            "Mat Prop - General"),
    ("Frame Section Property Definitions - Summary",             "Frame Prop - Summary"),
    ("Story Definitions",                                        "Story Definitions"),
    ("Load Pattern Definitions",                                 "Load Pattern Definitions"),
    ("Point Object Connectivity",                                "Point Object Connectivity"),
    ("Point Bays",                                               "Point Bays"),
    ("Column Object Connectivity",                               "Column Object Connectivity"),
    ("Column Bays",                                              "Column Bays"),
    ("Beam Object Connectivity",                                 "Beam Object Connectivity"),
    ("Beam Bays",                                                "Beam Bays"),
    ("Floor Object Connectivity",                                "Floor Object Connectivity"),
    ("Floor Bays",                                               "Floor Bays"),
    ("Dimension Line Object Geometry",                           "Dimension Line Object Geome"),
    ("Element Forces - Columns",                                 "Element Forces - Columns"),
    ("Element Forces - Beams",                                   "Element Forces - Beams"),
    ("Story Drifts",                                             "Story Drifts"),
    ("Diaphragm Max Over Avg Drifts",                            "Diaphragm Max Over Avg Drif"),
    ("Modal Participating Mass Ratios",                          "Modal Participating Mass Rat"),
    ("Modal Periods And Frequencies",                            "Modal Periods And Frequencie"),
    ("Base Reactions",                                           "Base Reactions"),
]

# Beton tasarım tabloları — isim ETABS sürümüne göre değişir.
# Keyword ile eşleştirip doğru ismi bulacağız.
CONCRETE_DESIGN_KEYWORDS = [
    (["Concrete Column Design Summary"], "Conc Col Sum"),
    (["Concrete Beam Design Summary"],   "Conc Bm Sum"),
    (["Concrete Joint Design Summary"],  "Conc Jt Sum"),
]

# Auto Seismic — isim deprem koduna göre değişir
AUTO_SEISMIC_KEYWORDS = ["Auto Seismic"]

# ─── Sütun ismi normalleştirme ───
# ETABS API bazen boşluksuz isim veriyor, elle export'ta boşluklu.
COLUMN_RENAMES = {
    "OutputCase":  "Output Case",
    "CaseType":    "Case Type",
    "DesignSect":  "DesignSect",   # bu zaten aynı
    "UniqueName":  "UniqueName",   # bu zaten aynı
}


def check_etabs_available() -> dict:
    """ETABS API erişilebilirliğini kontrol eder."""
    try:
        import comtypes.client
    except ImportError:
        return {
            "available": False,
            "message": "comtypes kütüphanesi yüklü değil. pip install comtypes",
            "model_open": False, "model_name": "",
        }

    try:
        import comtypes.gen.ETABSv1 as _
    except ImportError:
        pass

    try:
        helper = comtypes.client.CreateObject('ETABSv1.Helper')
        helper = helper.QueryInterface(comtypes.gen.ETABSv1.cHelper)
    except Exception:
        return {
            "available": False,
            "message": "ETABS kurulu değil veya API erişilemiyor.",
            "model_open": False, "model_name": "",
        }

    try:
        EtabsObject = helper.GetObject("CSI.ETABS.API.ETABSObject")
        SapModel = EtabsObject.SapModel
        filename = SapModel.GetModelFilename() or ""
        model_name = os.path.basename(filename) if filename else ""
        return {
            "available": True,
            "message": f"ETABS bağlantısı hazır. Model: {model_name}" if model_name else "ETABS açık ama model yüklü değil.",
            "model_open": bool(model_name), "model_name": model_name,
        }
    except Exception:
        return {
            "available": True,
            "message": "ETABS API erişilebilir. Açık bir model yok.",
            "model_open": False, "model_name": "",
        }


def _connect_etabs(model_path: str | None = None):
    """ETABS'a bağlan veya yeni instance başlat."""
    import comtypes.client
    try:
        import comtypes.gen.ETABSv1 as _
    except ImportError:
        pass

    helper = comtypes.client.CreateObject('ETABSv1.Helper')
    helper = helper.QueryInterface(comtypes.gen.ETABSv1.cHelper)

    if model_path:
        EtabsObject = helper.CreateObjectProgID("CSI.ETABS.API.ETABSObject")
        EtabsObject.ApplicationStart()
        SapModel = EtabsObject.SapModel
        SapModel.InitializeNewModel()
        ret = SapModel.File.OpenFile(model_path)
        if ret != 0:
            raise RuntimeError(f"Model açılamadı: {model_path} (hata kodu: {ret})")
    else:
        try:
            EtabsObject = helper.GetObject("CSI.ETABS.API.ETABSObject")
        except Exception:
            raise RuntimeError("Açık bir ETABS bulunamadı.")
        SapModel = EtabsObject.SapModel

    return EtabsObject, SapModel


def _run_analysis_and_design(SapModel, run_analysis: bool, run_design: bool):
    """Analiz ve Concrete Frame Design çalıştır."""
    if run_analysis:
        logger.info("Analiz çalıştırılıyor...")
        SapModel.File.Save()
        ret = SapModel.Analyze.RunAnalysis()
        if ret != 0:
            logger.warning(f"Analiz uyarı/hata döndürdü (kod: {ret})")

    if run_design:
        logger.info("Concrete Frame Design çalıştırılıyor...")
        try:
            ret = SapModel.DesignConcrete.StartDesign()
            if ret != 0:
                logger.warning(f"Design uyarı/hata döndürdü (kod: {ret})")
        except Exception as e:
            logger.warning(f"Design çalıştırılamadı: {e}")


def _get_available_tables(SapModel) -> list[str]:
    """ETABS'taki tüm mevcut tablo isimlerini döndürür."""
    try:
        result = SapModel.DatabaseTables.GetAvailableTables()
        table_keys = result[1]
        if table_keys:
            return list(table_keys)
    except Exception:
        pass
    return []


def _get_table_dataframe(SapModel, table_key: str) -> pd.DataFrame | None:
    """ETABS'tan tek bir tabloyu DataFrame olarak çek."""
    try:
        # Yöntem 1
        try:
            result = SapModel.DatabaseTables.GetTableForDisplayArray(
                table_key, '', '',
            )
        except Exception:
            result = None

        # Yöntem 2
        if result is None or result[-1] != 0:
            try:
                result = SapModel.DatabaseTables.GetTableForDisplayArray(
                    table_key, [], '', 0, [], 0, []
                )
            except Exception:
                pass

        if result is None or result[-1] != 0:
            return None

        # Sonuç parse
        fields_keys = None
        table_data = None

        for item in result[:-1]:
            if isinstance(item, (tuple, list)) and len(item) > 0:
                if fields_keys is None and all(isinstance(x, str) for x in item):
                    fields_keys = list(item)
                elif fields_keys is not None and table_data is None:
                    table_data = list(item)

        if not fields_keys or not table_data:
            return None

        num_fields = len(fields_keys)
        num_records = len(table_data) // num_fields if num_fields > 0 else 0

        if num_records == 0:
            return None

        rows = []
        for i in range(num_records):
            start = i * num_fields
            end = start + num_fields
            if end <= len(table_data):
                rows.append(list(table_data[start:end]))

        df = pd.DataFrame(rows, columns=fields_keys)

        # ─── Sütun ismi normalleştirme ───
        rename_map = {}
        for col in df.columns:
            clean = col.strip()
            if clean in COLUMN_RENAMES:
                rename_map[col] = COLUMN_RENAMES[clean]
        if rename_map:
            df = df.rename(columns=rename_map)

        # ─── Türkçe ondalık ayırıcı düzeltme (virgül → nokta) ───
        for col in df.columns:
            df[col] = df[col].apply(
                lambda x: str(x).replace(",", ".") if isinstance(x, str) and "," in str(x) else x
            )

        # Koordinat tablolarında mm → m dönüşümü
        if any(kw in table_key for kw in ["Point Bays", "Story Drifts", "Diaphragm"]):
            for col in ["X", "Y", "Z", "DZBelow"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce") / 1000

        # Element Forces tablolarında N → kN dönüşümü
        if "Element Forces" in table_key:
            for col in ["P", "V2", "V3", "T", "M2", "M3"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce") / 1000

        # Kesme donatısı m²/m → mm²/m dönüşümü (Concrete Design tabloları)
        if any(kw in table_key for kw in ["Concrete Column", "Concrete Beam", "Concrete Joint"]):
            for col in ["VMajRebar", "VMinRebar", "VRebar", "TTrnRebar"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce") * 1000

        return df

    except Exception as e:
        logger.debug(f"Tablo okunamadı [{table_key}]: {e}")
        return None


def _find_table_key(available: list[str], keywords: list[str]) -> str | None:
    """Mevcut tablolar arasında keyword'lerle eşleşen ilk tabloyu bul."""
    for table_name in available:
        if all(kw.lower() in table_name.lower() for kw in keywords):
            return table_name
    return None


def _write_table_to_excel(writer, SapModel, table_key: str, sheet_name: str) -> bool:
    """
    Tek bir tabloyu Excel'e ETABS elle export formatında yazar.

    Format:
      Satır 0: TABLE:  <tam_tablo_adı>
      Satır 1: Sütun başlıkları
      Satır 2+: Veri
    """
    df = _get_table_dataframe(SapModel, table_key)
    if df is None or df.empty:
        return False

    # Excel satır limiti kontrolü
    MAX_ROWS = 1048570
    if len(df) > MAX_ROWS:
        logger.warning(
            f"  ⚠ {table_key}: {len(df)} satır > Excel limiti, ilk {MAX_ROWS} satır alınıyor"
        )
        df = df.head(MAX_ROWS)

    # Sheet ismi max 31 karakter
    safe_sheet = sheet_name[:31]

    num_cols = len(df.columns)

    # Satır 0: TABLE header
    table_row = [f"TABLE:  {table_key}"] + [""] * (num_cols - 1)

    # Satır 1: Sütun başlıkları
    col_row = list(df.columns)

    # Tüm satırları birleştir
    all_rows = [table_row, col_row] + df.values.tolist()

    out_df = pd.DataFrame(all_rows)
    out_df.to_excel(writer, sheet_name=safe_sheet, index=False, header=False)

    logger.info(f"  ✓ {sheet_name} ← {table_key} ({len(df)} satır)")
    return True


def export_from_etabs(
    model_path: str | None = None,
    run_analysis: bool = True,
    run_design: bool = True,
) -> bytes:
    """
    ETABS'tan tabloları çekip, elle export formatında Excel bytes döner.

    Bu bytes doğrudan STAT'ın mevcut reader'larına verilebilir.
    Ayrıca kullanıcının bilgisayarına kaydedilip tekrar yüklenebilir.
    """
    EtabsObject, SapModel = _connect_etabs(model_path)
    _run_analysis_and_design(SapModel, run_analysis, run_design)

    # Birimleri ETABS birim seti 9 (kN-mm-C; koordinat tablolarında mm→m _get_table_dataframe'de)
    SapModel.SetPresentUnits(9)

    available = _get_available_tables(SapModel)
    logger.info(f"ETABS'ta {len(available)} tablo mevcut")

    if not available:
        raise RuntimeError("ETABS'tan tablo listesi alınamadı.")

    buffer = BytesIO()
    exported = 0

    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:

        # 1) Sabit tablolar
        for table_key, sheet_name in STAT_TABLE_MAP:
            # Tam eşleşme dene, yoksa keyword ile bul
            actual_key = table_key if table_key in available else None
            if not actual_key:
                # Keyword ile ara
                keywords = table_key.split(" - ")[0].split()  # ilk kısmı keyword yap
                actual_key = _find_table_key(available, [table_key.split(" - ")[0]])
            if not actual_key:
                actual_key = _find_table_key(available, table_key.split())

            if actual_key:
                if _write_table_to_excel(writer, SapModel, actual_key, sheet_name):
                    exported += 1
            else:
                logger.debug(f"  - Tablo bulunamadı: {table_key}")

        # 2) Beton tasarım tabloları (isim sürüme göre değişir)
        for keywords, sheet_prefix in CONCRETE_DESIGN_KEYWORDS:
            actual_key = _find_table_key(available, keywords)
            if actual_key:
                # Sheet ismini ETABS'ın kullandığı formata yakınlaştır
                # Ör: "Concrete Column Design Summary - TS 500-2000(R2018)"
                #   → "Conc Col Sum - TS 500-2000R2018"
                suffix = ""
                if "TS 500" in actual_key:
                    # "TS 500-2000(R2018)" → "TS 500-2000R2018"
                    import re
                    m = re.search(r"(TS \d+-\d+.*)", actual_key)
                    if m:
                        suffix = " - " + m.group(1).replace("(", "").replace(")", "")

                sheet_name = (sheet_prefix + suffix)[:31]
                if _write_table_to_excel(writer, SapModel, actual_key, sheet_name):
                    exported += 1

        # 3) Auto Seismic tablosu (deprem koduna göre isim değişir)
        auto_key = _find_table_key(available, AUTO_SEISMIC_KEYWORDS)
        if auto_key:
            # Sheet ismi: "Auto Seismic - TSC 2018" gibi
            short = auto_key.replace("Load Pattern Definitions - ", "")[:31]
            if _write_table_to_excel(writer, SapModel, auto_key, short):
                exported += 1

        # Hiç tablo yoksa hata sheet'i ekle
        if exported == 0:
            pd.DataFrame({"Hata": [
                "Hiçbir tablo veri döndürmedi.",
                f"Modelde {len(available)} tablo mevcut.",
                "Analiz ve Design çalıştırıldığından emin olun.",
            ]}).to_excel(writer, sheet_name="_HATA", index=False)

    if exported == 0:
        raise RuntimeError(
            f"Hiçbir tablo export edilemedi. "
            f"Modelde {len(available)} tablo var ama hiçbiri veri döndürmedi."
        )

    logger.info(f"Export tamamlandı: {exported} tablo")

    buffer.seek(0)
    return buffer.read()