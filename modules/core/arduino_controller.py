import time

try:
    import serial
except ImportError:
    serial = None


class ArduinoController:
    """
    Inspection sonuçlarını Arduino'ya seri port üzerinden gönderir.

    Protokol (satır bazlı, '\n' ile biter):

        Tüm gözler beklenen gibi -> "OK\n"
        NG olan gözler var       -> "NG:G02,G04\n"

    Arduino tarafında buzzer + alarm LED + LCD ekranı bu satırlara
    göre güncellenir
    (bkz. arduino/kasa_inspection_alarm/kasa_inspection_alarm.ino).

    Bağlantı yoksa, port yanlışsa veya kablo çekilirse Inspection
    uygulaması ÇÖKMEZ; gönderim sessizce atlanır ve konsola tek
    seferlik bir uyarı basılır.
    """

    def __init__(self, port: str, baudrate: int = 9600):

        self.port = port
        self.baudrate = baudrate

        self.connection = None
        self.last_message = None

        self.connect()

    # -------------------------------------------------

    def connect(self):

        if serial is None:

            print(
                "[ArduinoController] 'pyserial' kurulu değil. "
                "Kurmak için: pip install pyserial"
            )
            return

        try:

            self.connection = serial.Serial(
                self.port,
                self.baudrate,
                timeout=1
            )

            # Arduino, seri port açılınca resetlenir.
            # Hazır olması için kısa bir bekleme gerekir.

            time.sleep(2)

            print(f"[ArduinoController] Bağlandı: {self.port}")

        except Exception as e:

            print(
                f"[ArduinoController] Bağlanamadı ({self.port}): {e}"
            )

            self.connection = None

    # -------------------------------------------------

    def is_connected(self) -> bool:

        return (
            self.connection is not None
            and self.connection.is_open
        )

    # -------------------------------------------------

    def send_results(self, results: dict):
        """
        results: InspectionProcessor.process()['results'] formatı.
        Her ROI için {"ok": bool, ...} içerir.
        """

        ng_names = [
            name
            for name, data in results.items()
            if not data.get("ok", True)
        ]

        if ng_names:

            message = f"NG:{','.join(ng_names)}"

        else:

            message = "OK"

        self._send_line(message)

    # -------------------------------------------------

    def send_waiting(self):
        """
        Kamera henüz hizalanmadığında ya da kasa/parça hiç
        görünmediğinde (results boş) çağrılır. Arduino'nun son
        bilinen OK/NG durumunda takılı kalmaması için ayrı bir
        "WAIT" mesajı gönderir.
        """

        self._send_line("WAIT")

    # -------------------------------------------------

    def _send_line(self, message: str):

        # Aynı durumu her karede tekrar tekrar göndermeye gerek yok.
        if message == self.last_message:
            return

        self.last_message = message

        if not self.is_connected():
            return

        try:

            self.connection.write(
                (message + "\n").encode("utf-8")
            )

        except Exception as e:

            print(f"[ArduinoController] Gönderim hatası: {e}")

            self.connection = None

    # -------------------------------------------------

    def close(self):

        if self.connection is not None:

            self.connection.close()
            self.connection = None
