from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QMessageBox
)
from PySide6.QtCore import Qt, Signal

from modules.core.telegram_notifier import TelegramNotifier
from modules.core.telegram_reaction_poller import TelegramReactionPoller

from ..window_utils import restore_or_center, save_geometry

SETTINGS_KEY = "telegram_recipients_dialog"

PAIRING_PROMPT = (
    "Kasa İnceleme bildirimlerine kaydolmak için aşağıdaki "
    "\"Numaramı Paylaş\" butonuna basın."
)

PAIRING_CONFIRMATION = (
    "Kaydınız alındı, teşekkürler. Artık HATA/bağlantı bildirimlerini "
    "alabilirsiniz (yönetici sizi aktif hale getirdiğinde)."
)


class TelegramRecipientsDialog(QDialog):
    """
    Telefon numarası ile Telegram bildirim alıcısı ekleme/yönetme
    penceresi.

    "Eşleştirme Modu" açıkken bota mesaj atan herkese otomatik olarak
    "Numaramı Paylaş" butonu gönderilir; kişi butona basınca telefon
    numarası + chat id otomatik kaydedilir ve tabloya düşer. Yönetici
    her kayıt için bildirim alıp almayacağını (Aktif) seçer.
    """

    _contact_received = Signal(str, str, str)

    def __init__(self, settings_manager, recipients_manager, parent=None):

        super().__init__(parent)

        self.settings_manager = settings_manager
        self.recipients_manager = recipients_manager
        self.poller = None

        self.setWindowTitle("Bildirim Alıcıları (Telefon Numarası)")
        self.setModal(True)
        restore_or_center(self, SETTINGS_KEY, 560, 420)

        layout = QVBoxLayout(self)

        info_label = QLabel(
            "Telegram bir telefon numarasına doğrudan mesaj gönderemez; "
            "kişinin önce botla konuşup numarasını paylaşması gerekir. "
            "\"Eşleştirme Modunu Başlat\"a basıp ilgili kişiden bota "
            "herhangi bir mesaj atmasını isteyin."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray;")
        layout.addWidget(info_label)

        self.pairing_button = QPushButton("&Eşleştirme Modunu Başlat")
        self.pairing_button.setCheckable(True)
        self.pairing_button.clicked.connect(self._on_pairing_toggled)
        layout.addWidget(self.pairing_button)

        self.pairing_status_label = QLabel("")
        self.pairing_status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.pairing_status_label)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Aktif", "Ad", "Telefon"])
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        self.table.verticalHeader().setVisible(False)
        self.table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.table)

        button_row = QHBoxLayout()

        self.delete_button = QPushButton("&Sil")
        self.delete_button.clicked.connect(self._on_delete_clicked)
        button_row.addWidget(self.delete_button)

        button_row.addStretch()

        self.close_button = QPushButton("&Kapat")
        self.close_button.clicked.connect(self.reject)
        button_row.addWidget(self.close_button)

        layout.addLayout(button_row)

        self._contact_received.connect(self._on_contact_received_main_thread)

        self._reload_table()

    # -------------------------------------------------

    def closeEvent(self, event):

        self._stop_pairing()

        save_geometry(self, SETTINGS_KEY)

        super().closeEvent(event)

    def reject(self):

        self._stop_pairing()

        super().reject()

    # -------------------------------------------------
    # Tablo
    # -------------------------------------------------

    def _reload_table(self):

        recipients = self.recipients_manager.load()

        self.table.blockSignals(True)

        self.table.setRowCount(len(recipients))

        for row, recipient in enumerate(recipients):

            active_item = QTableWidgetItem()
            active_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            active_item.setCheckState(
                Qt.Checked if recipient.active else Qt.Unchecked
            )
            active_item.setData(Qt.UserRole, recipient.phone_number)
            self.table.setItem(row, 0, active_item)

            name_item = QTableWidgetItem(recipient.display_name or "-")
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 1, name_item)

            phone_item = QTableWidgetItem(recipient.phone_number)
            phone_item.setFlags(phone_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 2, phone_item)

        self.table.blockSignals(False)

    def _on_item_changed(self, item: QTableWidgetItem):

        if item.column() != 0:
            return

        phone_number = item.data(Qt.UserRole)

        if not phone_number:
            return

        self.recipients_manager.set_active(
            phone_number, item.checkState() == Qt.Checked
        )

    def _on_delete_clicked(self):

        row = self.table.currentRow()

        if row < 0:
            return

        item = self.table.item(row, 0)
        phone_number = item.data(Qt.UserRole) if item else None

        if not phone_number:
            return

        answer = QMessageBox.question(
            self,
            "Emin misiniz?",
            f"{phone_number} numaralı alıcı silinecek. Devam edilsin mi?"
        )

        if answer != QMessageBox.Yes:
            return

        self.recipients_manager.remove(phone_number)

        self._reload_table()

    # -------------------------------------------------
    # Eşleştirme Modu
    # -------------------------------------------------

    def _on_pairing_toggled(self, checked: bool):

        if checked:
            self._start_pairing()
        else:
            self._stop_pairing()

    def _start_pairing(self):

        settings = self.settings_manager.load()

        if not settings.bot_token.strip():

            QMessageBox.warning(
                self,
                "Uyarı",
                "Önce Telegram Bildirimleri penceresinden Bot Token girin."
            )

            self.pairing_button.setChecked(False)

            return

        self.poller = TelegramReactionPoller(
            settings.bot_token,
            on_message=self._on_message_background_thread
        )
        self.poller.start()

        self.pairing_button.setText("&Eşleştirme Modunu Durdur")
        self.pairing_status_label.setText(
            "Eşleştirme modu açık - kişinin bota mesaj atmasını bekleyin..."
        )

    def _stop_pairing(self):

        if self.poller is not None:
            self.poller.stop()
            self.poller = None

        self.pairing_button.setChecked(False)
        self.pairing_button.setText("&Eşleştirme Modunu Başlat")
        self.pairing_status_label.setText("")

    # -------------------------------------------------
    # Gelen Mesajlar (arka plan thread'i)
    # -------------------------------------------------

    def _on_message_background_thread(self, message: dict):
        """
        TelegramReactionPoller'ın arka plan thread'inden çağrılır.
        Qt widget'larına DOKUNMAZ - sadece ağ isteği atar ve (varsa)
        contact bilgisini sinyal ile ana thread'e iletir.
        """

        settings = self.settings_manager.load()

        chat_id = str(message.get("chat", {}).get("id", ""))

        if not chat_id:
            return

        contact = message.get("contact")

        notifier = TelegramNotifier(settings.bot_token, chat_id)

        if contact is not None:

            phone_number = contact.get("phone_number", "")

            if not phone_number:
                return

            name = " ".join(
                part for part in [
                    contact.get("first_name", ""),
                    contact.get("last_name", "")
                ] if part
            ).strip()

            notifier.send_message(PAIRING_CONFIRMATION)

            self._contact_received.emit(phone_number, chat_id, name)

        else:

            notifier.send_contact_request(PAIRING_PROMPT)

    def _on_contact_received_main_thread(
        self, phone_number: str, chat_id: str, display_name: str
    ):

        self.recipients_manager.register(phone_number, chat_id, display_name)

        self._reload_table()

        self.pairing_status_label.setText(
            f"Kaydedildi: {display_name or '?'} ({phone_number})"
        )
