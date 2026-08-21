from modules.core.telegram_notifier import TelegramNotifier
from modules.utils.logger import get_logger

app_logger = get_logger()


class MarkerDetectionMixin:
    """
    ArUco marker ile otomatik model tespiti: sol-üst tanı marker'ına
    bakarak hangi kasa modelinin kamerada olduğunu tespit eder ve
    modeli otomatik değiştirir. Bilinmeyen bir marker görülürse
    "tanınmayan kasa" akışını tetikler (fotoğraf kaydı + Telegram
    bildirimi). Chat id / retry-callback için TelegramMixin'e, model
    değişimi için InspectionUIController._select_model'e bağımlıdır.
    """

    MARKER_SWITCH_CONFIRM_FRAMES = 5
    UNKNOWN_KASA_NOTIFY_COOLDOWN_SECONDS = 300.0

    def _rebuild_marker_id_map(self):
        """
        Bandın modellerinden marker_id -> Model haritasını kurar.
        Hiçbir modelde marker_id ayarlanmamışsa (eski/tek modelli
        bandlar) tespit tamamen devre dışı kalır - sıfır davranış
        değişikliği.
        """

        self._marker_id_to_model = {
            model.marker_id: model for model in self.models
            if model.marker_id is not None
        }

        self._marker_detection_enabled = bool(self._marker_id_to_model)
        self._pending_marker_candidate = None
        self._pending_marker_streak = 0
        self._last_unknown_marker_id_captured = None

        self.page.hide_unknown_kasa_warning()

    def _handle_marker_model_detection(self, result) -> bool:
        """
        Bu karede görülen sol-üst tanı marker ID'sini işler:
        - Aynı ID MARKER_SWITCH_CONFIRM_FRAMES kadar ardışık
          görülmeden hiçbir şey yapmaz (titreme filtresi).
        - Zaten seçili modelin marker'ıysa dokunmaz.
        - Bilinen bir modelin marker'ıysa o modele otomatik geçer.
        - Hiçbir modelle eşleşmiyorsa "tanınmayan kasa" akışını
          tetikler ve True döner (bu karede OK/NG kararı
          loglanmamalı/Telegram'a bildirilmemeli).
        """

        candidate_id = result.get("identity_marker_id")

        if candidate_id == self._pending_marker_candidate:
            self._pending_marker_streak += 1
        else:
            self._pending_marker_candidate = candidate_id
            self._pending_marker_streak = 1

        if self._pending_marker_streak < self.MARKER_SWITCH_CONFIRM_FRAMES:
            return False

        if candidate_id is None:
            return False

        current_marker_id = (
            self.current_model.marker_id
            if self.current_model is not None
            else None
        )

        if candidate_id == current_marker_id:
            self.page.hide_unknown_kasa_warning()
            return False

        model = self._marker_id_to_model.get(candidate_id)

        if model is not None:
            self._switch_to_model_by_marker(model)
            return False

        self._handle_unknown_kasa(candidate_id, result)
        return True

    def _switch_to_model_by_marker(self, model):

        index = next(
            i for i, m in enumerate(self.models) if m is model
        )

        app_logger.info(
            "[%s] kasa modeli marker ile otomatik değişti: %s -> %s "
            "(marker %s)",
            self.operator_name,
            self.current_model.name if self.current_model else "-",
            model.name,
            model.marker_id
        )

        self.page.model_combo.blockSignals(True)
        self.page.model_combo.setCurrentIndex(index)
        self.page.model_combo.blockSignals(False)

        # recipe_manager + inspection_controller'ı yeniden kurar.
        self._select_model(index)

        self.page.hide_unknown_kasa_warning()

    def _handle_unknown_kasa(self, candidate_id, result):

        self.page.show_unknown_kasa_warning(
            f"Tanınmayan kasa (işaret {candidate_id}) — mühendis "
            "incelemesi için kaydedildi."
        )

        if candidate_id == self._last_unknown_marker_id_captured:
            # Aynı bilinmeyen kasa hâlâ kamerada - her karede tekrar
            # fotoğraf/kayıt oluşturma.
            return

        self._last_unknown_marker_id_captured = candidate_id

        roi_states = {
            name: data.get("state")
            for name, data in (result.get("results") or {}).items()
        }

        image = result.get("reference_display")

        if image is None:
            image = result.get("reference")

        self.unknown_kasa_capture_manager.save(
            self.current_band, image, candidate_id, roi_states
        )

        self._notify_unknown_kasa(candidate_id)

    def _notify_unknown_kasa(self, candidate_id):

        if not self._cooldown_ready(
            "_last_unknown_kasa_notified_at",
            self.UNKNOWN_KASA_NOTIFY_COOLDOWN_SECONDS
        ):
            return

        settings = self.telegram_settings_manager.load()

        if not settings.is_configured():
            return

        band_name = (
            self.current_band.name
            if self.current_band is not None
            else "?"
        )

        text = (
            f"❓ Tanınmayan kasa - {band_name}\n"
            f"İşaret Kimliği: {candidate_id}. Fotoğraf ve göz durumları "
            "kaydedildi, model tanımı gerekiyor."
        )

        for chat_id in self._telegram_chat_ids(settings.chat_id):

            callback = self._telegram_retry_on_failure_callback(
                kind="message",
                bot_token=settings.bot_token,
                chat_id=chat_id,
                text=text
            )

            TelegramNotifier(settings.bot_token, chat_id).send_message_async(
                text, on_sent=callback
            )
