from dataclasses import dataclass


@dataclass(slots=True)
class TelegramSettings:

    bot_token: str = ""
    chat_id: str = ""

    notify_on_ng: bool = True
    notify_on_disconnect: bool = True

    # NG bildirimine bu emoji ile tepki verilirse kayıt otomatik
    # olarak "incelendi/OK" yapılır (yanlış tespit düzeltmesiyle
    # aynı mantık, orijinal sonuç korunur).
    confirm_emoji: str = "✅"
    react_to_confirm: bool = False

    # Günlük özet rapor: toplam kontrol/OK/NG ve model/ROI bazlı
    # dağılımı özetleyen bir Excel dosyası her 24 saatte bir gönderilir
    # (bkz. InspectionUIController._maybe_send_periodic_report).
    daily_report_enabled: bool = False

    # ISO zaman damgası (UTC) - son rapor ne zaman gönderildi. Boşsa
    # hiç gönderilmemiş demektir, bir sonraki tick'te gönderilir.
    last_daily_report_sent_at: str = ""

    def is_configured(self) -> bool:

        return bool(self.bot_token.strip()) and bool(self.chat_id.strip())
