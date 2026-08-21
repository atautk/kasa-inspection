"""
Arayüzde gösterilecek İngilizce iç değerler için Türkçe karşılıklar.

"OK"/"NG" (InspectionLogger.overall_result, SQLite'ta saklanan
değer) ve "NORMAL"/"RECOVERY"/"ESTIMATE"/"FAIL" (LocalizationEngine
modu) gibi değerler kod içinde ve Arduino seri protokolünde
DEĞİŞMEDEN kalır - sadece kullanıcıya gösterilirken bu eşlemeden
geçirilir. Böylece veritabanı şeması, karşılaştırmalar
(`== "OK"`/`== "NORMAL"`) ve donanım protokolüne dokunmadan arayüz
tamamen Türkçe gösterilebilir.
"""

RESULT_LABELS_TR = {
    "OK": "UYGUN",
    "NG": "HATA",
}

STATE_LABELS_TR = {
    "FULL": "DOLU",
    "EMPTY": "BOŞ",
}

MODE_LABELS_TR = {
    "NORMAL": "NORMAL",
    "RECOVERY": "TOPARLANIYOR",
    "ESTIMATE": "TAHMİN",
    "FAIL": "BAŞARISIZ",
}


def result_label(value: str) -> str:

    return RESULT_LABELS_TR.get(value, value)


def state_label(value: str) -> str:

    return STATE_LABELS_TR.get(value, value)


def mode_label(value: str) -> str:

    return MODE_LABELS_TR.get(value, value)
