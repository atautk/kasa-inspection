from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QPushButton,
    QMessageBox
)
from PySide6.QtCore import Qt

from ..window_utils import restore_or_center, save_geometry

from .operator_management_panel import OperatorManagementPanel
from .telegram_settings_panel import TelegramSettingsPanel
from .telegram_recipients_panel import TelegramRecipientsPanel
from .camera_channels_panel import CameraChannelsPanel
from .arduino_settings_panel import ArduinoSettingsPanel
from .shift_settings_panel import ShiftSettingsPanel
from .reference_reminder_panel import ReferenceReminderPanel
from .training_data_settings_panel import TrainingDataSettingsPanel
from .auto_backup_settings_panel import AutoBackupSettingsPanel
from .data_retention_settings_panel import DataRetentionSettingsPanel

SETTINGS_KEY = "settings_dialog"


class SettingsDialog(QDialog):
    """
    Tek bir kategori listesi + panel yapısında birleştirilmiş ayarlar
    penceresi. Eskiden "Yönetim" menüsünde 9 ayrı pencere olarak
    açılan ayarlar (Operatörler, Telegram, Kamera Kanalları, Arduino,
    Vardiya, Referans Hatırlatıcı, Model Eğitimi, Otomatik Yedekleme)
    burada tek pencerede, soldaki listeden seçilerek gösterilir.

    "Doğrula", "Dışa/İçe Aktar" (tek seferlik işlemler) ve "Giriş/
    Çıkış ve Değişiklik Logu" (salt okunur geçmiş görüntüleyici) bu
    pencerenin kapsamı DIŞINDA bırakıldı - bunlar birer "ayar" değil,
    "Yönetim" menüsünde ayrı maddeler olarak kalmaya devam ediyor.

    Operatör/Telegram kategorileri yönetici yetkisi ister (tıklanınca
    kontrol edilir); band'e özel kategoriler (Kamera Kanalları,
    Arduino, Vardiya, Referans Hatırlatıcı, Model Eğitimi, Otomatik
    Yedekleme, Veri Saklama) hiç band açılmamışsa listede devre dışı
    görünür.
    """

    def __init__(
        self,
        band_manager,
        band,
        operator_manager,
        operator_name,
        telegram_settings_manager,
        telegram_recipients_manager,
        on_channels_changed=None,
        parent=None
    ):

        super().__init__(parent)

        self.band_manager = band_manager
        self.band = band
        self.operator_manager = operator_manager
        self.operator_name = operator_name

        self.setWindowTitle("Ayarlar")
        self.setModal(True)
        restore_or_center(self, SETTINGS_KEY, 900, 600)

        outer_layout = QVBoxLayout(self)

        if self.band is None:

            band_hint_label = QLabel(
                "Band'e özel ayarlar (Kamera Kanalları, Arduino, "
                "Vardiya, Referans Hatırlatıcı, Model Eğitimi, "
                "Otomatik Yedekleme, Veri Saklama) soldaki listede "
                "soluk görünür - kullanmak için önce ana ekrandan "
                "bir band açın."
            )
            band_hint_label.setWordWrap(True)
            band_hint_label.setStyleSheet("color: gray; font-style: italic;")
            outer_layout.addWidget(band_hint_label)

        content_row = QHBoxLayout()

        self.category_list = QListWidget()
        self.category_list.setFixedWidth(220)
        content_row.addWidget(self.category_list)

        self.stack = QStackedWidget()
        content_row.addWidget(self.stack, stretch=1)

        outer_layout.addLayout(content_row, stretch=1)

        close_row = QHBoxLayout()
        close_row.addStretch()
        self.close_button = QPushButton("&Kapat")
        self.close_button.clicked.connect(self.accept)
        close_row.addWidget(self.close_button)
        outer_layout.addLayout(close_row)

        self._admin_rows = set()
        self._current_panel = None
        self._current_row = -1

        self._build_categories(
            telegram_settings_manager,
            telegram_recipients_manager,
            on_channels_changed
        )

        self.category_list.currentRowChanged.connect(
            self._on_category_changed
        )

        first_row = self._first_selectable_row()

        if first_row is not None:
            self.category_list.setCurrentRow(first_row)

    # -------------------------------------------------

    def closeEvent(self, event):

        self._cleanup_all_panels()

        save_geometry(self, SETTINGS_KEY)

        super().closeEvent(event)

    def accept(self):

        self._cleanup_all_panels()

        super().accept()

    def _cleanup_all_panels(self):

        for index in range(self.stack.count()):

            panel = self.stack.widget(index)

            if hasattr(panel, "cleanup"):
                panel.cleanup()

    # -------------------------------------------------
    # Kategoriler
    # -------------------------------------------------

    def _add_category(self, name, panel, admin_required=False, band_required=False):

        item = QListWidgetItem(name)
        self.category_list.addItem(item)
        self.stack.addWidget(panel)

        row = self.category_list.count() - 1

        if admin_required:
            self._admin_rows.add(row)
            item.setToolTip("Bu ayarlara sadece yöneticiler erişebilir.")

        if band_required:

            if self.band is None:

                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
                item.setToolTip(
                    "Bu ayar için önce bir band açmalısınız."
                )

            else:

                item.setToolTip("")

    def _build_categories(
        self,
        telegram_settings_manager,
        telegram_recipients_manager,
        on_channels_changed
    ):

        if self.operator_manager is not None:

            self._add_category(
                "Operatörler",
                OperatorManagementPanel(self.operator_manager),
                admin_required=True
            )

            self._add_category(
                "Telegram Bildirimleri",
                TelegramSettingsPanel(telegram_settings_manager),
                admin_required=True
            )

            self._add_category(
                "Bildirim Alıcıları",
                TelegramRecipientsPanel(
                    telegram_settings_manager, telegram_recipients_manager
                ),
                admin_required=True
            )

        self._add_category(
            "Kamera Kanalları",
            CameraChannelsPanel(
                self.band_manager, self.band,
                on_channels_changed=on_channels_changed
            ),
            band_required=True
        )

        self._add_category(
            "Arduino",
            ArduinoSettingsPanel(
                self.band_manager, self.band, self.operator_name
            ),
            band_required=True
        )

        self._add_category(
            "Vardiya",
            ShiftSettingsPanel(
                self.band_manager, self.band,
                operator_manager=self.operator_manager
            ),
            band_required=True
        )

        self._add_category(
            "Referans Hatırlatıcı",
            ReferenceReminderPanel(
                self.band_manager, self.band, self.operator_name
            ),
            band_required=True
        )

        self._add_category(
            "Model Eğitimi",
            TrainingDataSettingsPanel(
                self.band_manager, self.band, self.operator_name
            ),
            band_required=True
        )

        self._add_category(
            "Otomatik Yedekleme",
            AutoBackupSettingsPanel(
                self.band_manager, self.band, self.operator_name
            ),
            band_required=True
        )

        self._add_category(
            "Veri Saklama",
            DataRetentionSettingsPanel(
                self.band_manager, self.band, self.operator_name
            ),
            band_required=True
        )

    # -------------------------------------------------

    def _first_selectable_row(self):
        """
        Yönetici olmayan bir operatör için Operatörler/Telegram
        satırları hiçbir zaman seçilebilir olmayacağından, ilk
        açılışta geçerli (tıklanabilir) ilk satırı bulur -
        aksi halde dialog açılır açılmaz uyarı gösterip hiçbir
        panel göstermeden kalır.
        """

        for row in range(self.category_list.count()):

            if row in self._admin_rows and not self._is_admin():
                continue

            item = self.category_list.item(row)

            if not (item.flags() & Qt.ItemIsEnabled):
                continue

            return row

        return None

    def _on_category_changed(self, row):

        if row < 0:
            return

        if row in self._admin_rows and not self._is_admin():

            QMessageBox.warning(
                self,
                "Uyarı",
                "Bu ayarlara sadece yöneticiler erişebilir."
            )

            fallback_row = self._current_row if self._current_row >= 0 else 0

            self.category_list.blockSignals(True)
            self.category_list.setCurrentRow(fallback_row)
            self.category_list.blockSignals(False)

            return

        previous_panel = self._current_panel

        if previous_panel is not None and hasattr(previous_panel, "cleanup"):
            previous_panel.cleanup()

        self.stack.setCurrentIndex(row)
        self._current_panel = self.stack.widget(row)
        self._current_row = row

    def _is_admin(self) -> bool:

        return (
            self.operator_manager is not None
            and self.operator_manager.is_admin(self.operator_name)
        )
