import numpy as np

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QFrame,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QGroupBox
)
from PySide6.QtGui import QImage, QPixmap, QColor
from PySide6.QtCore import Qt

from modules.utils import accessibility_settings as a11y
from modules.utils.display_terms import result_label, state_label, mode_label


class InspectionPage(QWidget):
    """
    Inspection ekranı.

    Bu sınıf SADECE UI'dan sorumludur.
    Kamera, OpenCV, ArUco veya inspection mantığı hakkında hiçbir şey bilmez.

    Controller, aşağıdaki public metodları çağırarak bu sayfayı günceller:

        set_band_list(names: list[str])
        set_model_list(names: list[str])
        set_image(frame)
        clear_image()
        set_results(results: dict)
        clear_results()
        set_mode(text)
        set_confidence(value)
        set_performance(fps, inspection_time_ms)
        set_status(text)
        set_start_button_text(text)
        set_debug_button_text(text)
        enable_selection(enabled: bool)
        show_ng_alert()
        hide_ng_alert()
        show_disk_warning(free_gb: float)
        hide_disk_warning()

    Controller'ın dinlediği sinyaller:

        band_combo.currentIndexChanged
        model_combo.currentIndexChanged
        start_button.clicked
        save_reference_button.clicked
        debug_button.clicked
        history_button.clicked
    """

    COLUMNS = [
        "Göz",
        "Durum",
        "Beklenen",
        "Sonuç",
        "Fark %",
        "Piksel"
    ]

    def __init__(self):

        super().__init__()

        root = QVBoxLayout(self)

        # ---------- Hata Uyarı Bannerı ----------

        self.ng_banner = QLabel("⚠ HATA !")
        self.ng_banner.setAlignment(Qt.AlignCenter)
        self.ng_banner.setStyleSheet(
            "background-color: #cc0000; color: white; "
            "font-size: 22px; font-weight: bold; padding: 10px;"
        )
        self.ng_banner.hide()
        root.addWidget(self.ng_banner)

        # ---------- Disk Alanı Uyarısı ----------

        self.disk_warning_banner = QLabel("")
        self.disk_warning_banner.setAlignment(Qt.AlignCenter)
        self.disk_warning_banner.setStyleSheet(
            "background-color: #e08a00; color: white; "
            "font-size: 14px; font-weight: bold; padding: 6px;"
        )
        self.disk_warning_banner.hide()
        root.addWidget(self.disk_warning_banner)

        # ---------- Kamera Netliği Uyarısı ----------

        self.blur_warning_banner = QLabel("")
        self.blur_warning_banner.setAlignment(Qt.AlignCenter)
        self.blur_warning_banner.setStyleSheet(
            "background-color: #e08a00; color: white; "
            "font-size: 14px; font-weight: bold; padding: 6px;"
        )
        self.blur_warning_banner.hide()
        root.addWidget(self.blur_warning_banner)

        # ---------- Referans Yaşlanma Uyarısı ----------

        self.reference_age_warning_banner = QLabel("")
        self.reference_age_warning_banner.setAlignment(Qt.AlignCenter)
        self.reference_age_warning_banner.setStyleSheet(
            "background-color: #e08a00; color: white; "
            "font-size: 14px; font-weight: bold; padding: 6px;"
        )
        self.reference_age_warning_banner.hide()
        root.addWidget(self.reference_age_warning_banner)

        # ---------- Tanınmayan Kasa Bilgisi ----------

        self.unknown_kasa_banner = QLabel("")
        self.unknown_kasa_banner.setAlignment(Qt.AlignCenter)
        self.unknown_kasa_banner.setStyleSheet(
            "background-color: #3465a4; color: white; "
            "font-size: 14px; font-weight: bold; padding: 6px;"
        )
        self.unknown_kasa_banner.hide()
        root.addWidget(self.unknown_kasa_banner)

        # ---------- Ana Satır: Ne Çalıştırılacak ----------

        selection_row = QHBoxLayout()

        selection_row.addWidget(QLabel("Band:"))

        self.band_combo = QComboBox()
        selection_row.addWidget(self.band_combo)

        selection_row.addWidget(QLabel("Model:"))

        self.model_combo = QComboBox()
        selection_row.addWidget(self.model_combo)

        selection_row.addStretch()

        self.start_button = QPushButton("&Başlat")
        self.start_button.setMinimumHeight(36)
        self.start_button.setStyleSheet("font-weight: bold;")
        selection_row.addWidget(self.start_button)

        root.addLayout(selection_row)

        # ---------- Araçlar: Çalışırken Kullanılanlar ----------

        tools_group = QGroupBox("Araçlar")
        tools_row = QHBoxLayout(tools_group)

        self.save_reference_button = QPushButton("&Referans Kaydet")
        tools_row.addWidget(self.save_reference_button)

        self.history_button = QPushButton("&Geçmiş")
        tools_row.addWidget(self.history_button)

        tools_row.addStretch()

        self.debug_button = QPushButton("&Hata Ayıklama Göster")
        tools_row.addWidget(self.debug_button)

        root.addWidget(tools_group)

        # ---------- Orta Alan (Görüntü + Tablo) ----------

        middle_row = QHBoxLayout()

        self._last_frame = None

        self.image_label = QLabel("Kamera kapalı")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFrameShape(QFrame.Box)
        self.image_label.setMinimumSize(320, 240)
        self.image_label.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        self.image_label.setStyleSheet(
            "background-color: black; color: white;"
        )
        middle_row.addWidget(self.image_label, stretch=2)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(len(self.COLUMNS))
        self.results_table.setHorizontalHeaderLabels(self.COLUMNS)
        self.results_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )
        self.results_table.setMinimumWidth(420)
        middle_row.addWidget(self.results_table, stretch=1)

        root.addLayout(middle_row, stretch=1)

        # ---------- Alt Bilgi Satırı ----------

        info_row = QHBoxLayout()

        self.mode_label = QLabel("Mod: -")
        info_row.addWidget(self.mode_label)

        self.confidence_label = QLabel("Güven: -")
        info_row.addWidget(self.confidence_label)

        self.performance_label = QLabel("Kare/sn: - | Süre: -")
        info_row.addWidget(self.performance_label)

        self.shift_label = QLabel("Vardiya: -")
        info_row.addWidget(self.shift_label)

        info_row.addStretch()

        self.status_label = QLabel("Durum: -")
        info_row.addWidget(self.status_label)

        root.addLayout(info_row)

    # -------------------------------------------------
    # Band / Model Listeleri
    # -------------------------------------------------

    def set_band_list(self, names: list[str]):

        self.band_combo.blockSignals(True)
        self.band_combo.clear()
        self.band_combo.addItems(names)
        self.band_combo.blockSignals(False)

    def set_model_list(self, names: list[str]):

        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItems(names)
        self.model_combo.blockSignals(False)

    def enable_selection(self, enabled: bool):

        self.band_combo.setEnabled(enabled)
        self.model_combo.setEnabled(enabled)

    # -------------------------------------------------
    # Görüntü
    # -------------------------------------------------

    def set_image(self, frame: np.ndarray):

        if frame is None:
            return

        self._last_frame = frame

        self._render_image(frame)

    def _render_image(self, frame: np.ndarray):

        height, width = frame.shape[:2]

        rgb = frame[:, :, ::-1].copy()

        image = QImage(
            rgb.data,
            width,
            height,
            rgb.strides[0],
            QImage.Format_RGB888
        ).copy()

        # .copy() ZORUNLU - bkz. reference_page.py'deki aynı satır:
        # kopyalanmazsa rgb serbest kalınca resizeEvent tekrar çizerken
        # Qt geçersiz belleğe erişip çöküyor.

        pixmap = QPixmap.fromImage(image).scaled(
            self.image_label.width(),
            self.image_label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.image_label.setPixmap(pixmap)

    def clear_image(self):

        self._last_frame = None

        self.image_label.clear()
        self.image_label.setText("Kamera kapalı")

    # -------------------------------------------------
    # Pencere Yeniden Boyutlanınca
    # -------------------------------------------------

    def resizeEvent(self, event):

        super().resizeEvent(event)

        if self._last_frame is not None:
            self._render_image(self._last_frame)

    # -------------------------------------------------
    # Sonuç Tablosu
    # -------------------------------------------------

    def set_results(self, results: dict):

        rows = sorted(results.items())

        self.results_table.setRowCount(len(rows))

        for row_index, (roi_name, data) in enumerate(rows):

            ok = bool(data.get("ok", False))

            color = QColor(
                *(
                    a11y.get_ok_color_light_rgb()
                    if ok
                    else a11y.get_ng_color_light_rgb()
                )
            )

            values = [
                roi_name,
                state_label(str(data.get("state", "-"))),
                state_label(str(data.get("expected", "-"))),
                result_label("OK" if ok else "NG"),
                f"{data.get('change_ratio', 0):.2f}",
                str(data.get("changed_pixels", 0))
            ]

            for column_index, value in enumerate(values):

                item = QTableWidgetItem(value)
                item.setBackground(color)

                self.results_table.setItem(
                    row_index,
                    column_index,
                    item
                )

    def clear_results(self):

        self.results_table.setRowCount(0)

    # -------------------------------------------------
    # Bilgi Etiketleri
    # -------------------------------------------------

    def set_mode(self, text: str):

        self.mode_label.setText(f"Mod: {mode_label(text)}")

    def set_confidence(self, value):

        self.confidence_label.setText(f"Güven: {value}")

    def set_performance(self, fps: float, inspection_time_ms: float):

        self.performance_label.setText(
            f"Kare/sn: {fps:.1f} | Süre: {inspection_time_ms:.1f} ms"
        )

    def set_status(self, text: str):

        self.status_label.setText(f"Durum: {text}")

    def set_shift_progress(self, info: dict | None):
        """
        info: {"produced", "name", "start", "end", "operator"} - şu an
        içinde bulunulan vardiya penceresi, o pencerede üretilen kasa
        sayısı ve (varsa) atanan operatör. Şu an aktif bir pencere
        yoksa (ya da hiç pencere tanımlı değilse) None.
        """

        if info is None:
            self.shift_label.setText("Vardiya: -")
            return

        text = (
            f"Vardiya: {info['produced']} kasa — {info['name']} "
            f"({info['start']}-{info['end']})"
        )

        if info.get("operator"):
            text += f" — {info['operator']}"

        self.shift_label.setText(text)

    # -------------------------------------------------
    # Buton Metinleri
    # -------------------------------------------------

    def set_start_button_text(self, text: str):

        self.start_button.setText(text)

    def set_debug_button_text(self, text: str):

        self.debug_button.setText(text)

    # -------------------------------------------------
    # NG Uyarısı
    # -------------------------------------------------

    def show_ng_alert(self):

        r, g, b = a11y.get_ng_color_rgb()

        self.ng_banner.setStyleSheet(
            f"background-color: rgb({r},{g},{b}); color: white; "
            "font-size: 22px; font-weight: bold; padding: 10px;"
        )

        self.ng_banner.show()

    def hide_ng_alert(self):

        self.ng_banner.hide()

    # -------------------------------------------------
    # Disk Alanı Uyarısı
    # -------------------------------------------------

    def show_disk_warning(self, free_gb: float):

        self.disk_warning_banner.setText(
            f"⚠ Disk alanı azalıyor: {free_gb:.1f} GB kaldı — "
            f"yedekleme/temizlik gerekebilir"
        )

        self.disk_warning_banner.show()

    def hide_disk_warning(self):

        self.disk_warning_banner.hide()

    # -------------------------------------------------
    # Kamera Netliği Uyarısı
    # -------------------------------------------------

    def show_blur_warning(self, sharpness: float):

        self.blur_warning_banner.setText(
            f"⚠ Kamera görüntüsü bulanık görünüyor (netlik: "
            f"{sharpness:.1f}) — lens temiz mi, odak doğru mu kontrol edin"
        )

        self.blur_warning_banner.show()

    def hide_blur_warning(self):

        self.blur_warning_banner.hide()

    # -------------------------------------------------
    # Referans Yaşlanma Uyarısı
    # -------------------------------------------------

    def show_reference_age_warning(self, text: str):

        self.reference_age_warning_banner.setText(f"⚠ {text}")
        self.reference_age_warning_banner.show()

    def hide_reference_age_warning(self):

        self.reference_age_warning_banner.hide()

    # -------------------------------------------------
    # Tanınmayan Kasa Bilgisi
    # -------------------------------------------------

    def show_unknown_kasa_warning(self, text: str):

        self.unknown_kasa_banner.setText(text)
        self.unknown_kasa_banner.show()

    def hide_unknown_kasa_warning(self):

        self.unknown_kasa_banner.hide()
