from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QCheckBox,
    QPushButton,
    QMessageBox
)

from modules.core.telegram_notifier import TelegramNotifier


class TelegramSettingsPanel(QWidget):
    """
    Telegram bot token / chat id ve hangi olaylarda bildirim
    gönderileceği burada ayarlanır. "Test Et" ile kayıtlı ayarlarla
    gerçek bir mesaj gönderilip kurulumun çalıştığı doğrulanabilir.
    Ayarlar penceresi içine gömülür - bkz. SettingsDialog.
    """

    def __init__(self, settings_manager, parent=None):

        super().__init__(parent)

        self.settings_manager = settings_manager

        layout = QVBoxLayout(self)

        title = QLabel("Telegram Bildirimleri")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        info_label = QLabel(
            "Bot token'ı almak için Telegram'da @BotFather ile "
            "konuşup /newbot yapın. Chat ID'yi öğrenmek için botu "
            "sohbete ekleyip @userinfobot gibi bir bot kullanabilir "
            "ya da https://api.telegram.org/bot<TOKEN>/getUpdates "
            "adresine bakabilirsiniz."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray;")
        layout.addWidget(info_label)

        token_row = QHBoxLayout()
        token_row.addWidget(QLabel("Bot Token:"))
        self.token_input = QLineEdit()
        token_row.addWidget(self.token_input)
        layout.addLayout(token_row)

        chat_row = QHBoxLayout()
        chat_row.addWidget(QLabel("Chat ID:"))
        self.chat_id_input = QLineEdit()
        chat_row.addWidget(self.chat_id_input)
        layout.addLayout(chat_row)

        self.notify_ng_checkbox = QCheckBox(
            "HATA tespit edildiğinde bildir (fotoğrafla birlikte)"
        )
        layout.addWidget(self.notify_ng_checkbox)

        self.notify_disconnect_checkbox = QCheckBox(
            "Kamera/Arduino bağlantısı koptuğunda bildir"
        )
        layout.addWidget(self.notify_disconnect_checkbox)

        self.react_to_confirm_checkbox = QCheckBox(
            "HATA mesajına emoji ile tepki verilince otomatik UYGUN'a çevir "
            "(bu sırada İnceleme uygulaması açık olmalı)"
        )
        layout.addWidget(self.react_to_confirm_checkbox)

        self.daily_report_checkbox = QCheckBox(
            "Her 24 saatte bir özet rapor gönder (toplam/UYGUN/HATA, "
            "model ve göz bazlı dağılım - Excel dosyası olarak)"
        )
        layout.addWidget(self.daily_report_checkbox)

        emoji_row = QHBoxLayout()
        emoji_row.addWidget(QLabel("Onay Emojisi:"))
        self.confirm_emoji_input = QLineEdit()
        self.confirm_emoji_input.setMaxLength(8)
        self.confirm_emoji_input.setFixedWidth(60)
        emoji_row.addWidget(self.confirm_emoji_input)
        emoji_row.addWidget(
            QLabel("(sadece bu emoji ile yapılan tepkiler sayılır)")
        )
        emoji_row.addStretch()
        layout.addLayout(emoji_row)

        button_row = QHBoxLayout()

        self.test_button = QPushButton("&Test Et")
        self.test_button.clicked.connect(self._on_test_clicked)
        button_row.addWidget(self.test_button)

        self.save_button = QPushButton("&Kaydet")
        self.save_button.clicked.connect(self._on_save_clicked)
        button_row.addWidget(self.save_button)

        button_row.addStretch()

        layout.addLayout(button_row)

        layout.addStretch()

        self._load_current_settings()

    # -------------------------------------------------

    def _load_current_settings(self):

        settings = self.settings_manager.load()

        self.token_input.setText(settings.bot_token)
        self.chat_id_input.setText(settings.chat_id)
        self.notify_ng_checkbox.setChecked(settings.notify_on_ng)
        self.notify_disconnect_checkbox.setChecked(
            settings.notify_on_disconnect
        )
        self.react_to_confirm_checkbox.setChecked(
            settings.react_to_confirm
        )
        self.confirm_emoji_input.setText(settings.confirm_emoji)
        self.daily_report_checkbox.setChecked(
            settings.daily_report_enabled
        )

    def _current_notifier(self) -> TelegramNotifier:

        return TelegramNotifier(
            self.token_input.text().strip(),
            self.chat_id_input.text().strip()
        )

    # -------------------------------------------------

    def _on_test_clicked(self):

        notifier = self._current_notifier()

        if not notifier.is_configured():

            QMessageBox.warning(
                self,
                "Uyarı",
                "Önce Bot Token ve Chat ID girin."
            )

            return

        success = notifier.send_message(
            "Kasa İnceleme: test mesajı. Bu mesajı görüyorsanız "
            "Telegram bildirimleri doğru yapılandırılmış."
        )

        if success:

            QMessageBox.information(
                self,
                "Başarılı",
                "Test mesajı gönderildi. Telegram'ı kontrol edin."
            )

        else:

            QMessageBox.critical(
                self,
                "Hata",
                "Test mesajı gönderilemedi. Token/Chat ID'yi ve "
                "internet bağlantısını kontrol edin (ayrıntı için "
                "logs/app.log)."
            )

    # -------------------------------------------------

    def _on_save_clicked(self):

        settings = self.settings_manager.load()

        settings.bot_token = self.token_input.text().strip()
        settings.chat_id = self.chat_id_input.text().strip()
        settings.notify_on_ng = self.notify_ng_checkbox.isChecked()
        settings.notify_on_disconnect = (
            self.notify_disconnect_checkbox.isChecked()
        )
        settings.react_to_confirm = (
            self.react_to_confirm_checkbox.isChecked()
        )
        settings.daily_report_enabled = (
            self.daily_report_checkbox.isChecked()
        )

        emoji = self.confirm_emoji_input.text().strip()
        settings.confirm_emoji = emoji or "✅"

        self.settings_manager.save(settings)
