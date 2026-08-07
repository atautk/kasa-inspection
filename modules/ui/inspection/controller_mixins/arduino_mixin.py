from modules.core.arduino_controller import ArduinoController
from modules.utils.logger import get_logger

app_logger = get_logger()


class ArduinoMixin:
    """
    Arduino bağlantısını kurma ve (kablo çekilmesi, USB kopması vb.)
    koptuğunda kendiliğinden yeniden bağlanmayı deneme.
    """

    ARDUINO_RECONNECT_INTERVAL_SECONDS = 5.0

    def _connect_arduino(self):

        if self.arduino_controller is not None:
            self.arduino_controller.close()
            self.arduino_controller = None

        port = self.current_band.arduino_port

        if not port:
            return

        self.arduino_controller = ArduinoController(port)

        if self.arduino_controller.is_connected():

            app_logger.info(
                "Arduino'ya bağlandı: %s (band=%s)",
                port,
                self.current_band.name
            )

        else:

            app_logger.warning(
                "Arduino'ya bağlanılamadı: %s (band=%s)",
                port,
                self.current_band.name
            )

    def _attempt_arduino_reconnect(self):
        """
        Kamera gibi Arduino da (kablo çekilmesi, USB kopması vb.)
        bağlantı koptuğunda kendiliğinden tekrar bağlanmayı dener.
        Her tick'te değil, ARDUINO_RECONNECT_INTERVAL_SECONDS'ta bir
        denenir (bağlantı denemesi ~2 saniye bloklayabildiği için).
        """

        if not self._throttled(
            "last_arduino_reconnect_attempt",
            self.ARDUINO_RECONNECT_INTERVAL_SECONDS
        ):
            return

        port = self.arduino_controller.port

        self.arduino_controller.close()
        self.arduino_controller = ArduinoController(port)

        if self.arduino_controller.is_connected():

            app_logger.info(
                "Arduino ile bağlantı yeniden kuruldu: %s",
                port
            )
