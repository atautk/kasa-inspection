from dataclasses import dataclass


@dataclass(slots=True)
class TelegramRecipient:
    """
    Botla konuşup "Kişimi Paylaş" ile numarasını gönderen bir kişi.
    chat_id, Telegram'ın kendisine mesaj gönderebilmemiz için verdiği
    gerçek kimliktir; phone_number sadece kimin kaydolduğunu insan
    tarafından okunabilir şekilde göstermek içindir.
    """

    phone_number: str
    chat_id: str
    display_name: str = ""
    active: bool = True
