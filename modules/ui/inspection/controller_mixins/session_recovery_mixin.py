from modules.ui.window_utils import get_app_settings


class SessionRecoveryMixin:
    """
    Son kullanılan band/model/çalışma durumunu makine ayarlarında
    (window_settings.ini) saklar - bkz. otomatik toparlanma
    (crash/elektrik kesintisi sonrası) InspectionUIController._load_bands.
    """

    SESSION_SETTINGS_KEY = "inspection_session"

    def _save_session_band(self):

        settings = get_app_settings()

        settings.setValue(
            f"{self.SESSION_SETTINGS_KEY}/last_band_id",
            self.current_band.id if self.current_band is not None else None
        )

    def _save_session_model(self):

        settings = get_app_settings()

        settings.setValue(
            f"{self.SESSION_SETTINGS_KEY}/last_model_id",
            self.current_model.id
            if self.current_model is not None else None
        )

    def _save_session_running(self, running: bool):

        settings = get_app_settings()

        settings.setValue(
            f"{self.SESSION_SETTINGS_KEY}/was_running", running
        )

    def _load_session_state(self) -> dict:

        settings = get_app_settings()

        return {
            "last_band_id": settings.value(
                f"{self.SESSION_SETTINGS_KEY}/last_band_id", None
            ),
            "last_model_id": settings.value(
                f"{self.SESSION_SETTINGS_KEY}/last_model_id", None
            ),
            "was_running": settings.value(
                f"{self.SESSION_SETTINGS_KEY}/was_running",
                False,
                type=bool
            )
        }

    def _index_of_band_id(self, band_id):

        if band_id is None:
            return None

        for index, band in enumerate(self.bands):

            if band.id == band_id:
                return index

        return None

    def _index_of_model_id(self, model_id):

        if model_id is None:
            return None

        for index, model in enumerate(self.models):

            if model.id == model_id:
                return index

        return None
