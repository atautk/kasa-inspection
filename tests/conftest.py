import threading

import pytest


@pytest.fixture(autouse=True)
def _qt_event_loop_pump():
    """
    Test paketi boyunca aynı QApplication paylaşılıyor, ve Telegram
    bildirimleri/kuyruk/rapor gönderimi gibi özellikler
    threading.Thread(daemon=True) ile "fire and forget" arka plan
    thread'leri başlatıyor. Bir test bitip bir sonraki test yeni
    mock/nesne oluştururken, önceki testin arka plan thread'i hâlâ
    çalışıyorsa (ör. callback tetiklendi ama thread fonksiyonu henüz
    tam dönmedi), ikisi aynı anda çakışıp gerçek bir "access
    violation" çökmesine yol açabiliyordu (unittest.mock'un thread-
    safe olmayan iç durumu üzerinden doğrulandı). Her testten sonra
    ana thread dışındaki tüm thread'lerin bitmesini beklemek ve Qt
    olay döngüsünü pompalamak (deleteLater() ile zamanlanmış
    temizlikler için) bu riski ortadan kaldırır.
    """

    yield

    main_thread = threading.main_thread()

    # Kısa bir zaman aşımı bilinçli: amaç KISA süren thread'lerin
    # (mocked/hızlı ağ çağrıları) tam bitmesini beklemek, gerçek bir
    # ağ isteğine takılmış (ör. yanlış temizlenmiş bir test'ten kalma)
    # bir thread'i beklemek değil. Öyle bir thread her testte 3'er
    # saniye harcanarak tekrar tekrar join edilirse, tüm paketi
    # dakikalarca yavaşlatabiliyordu (gerçek bir olayla doğrulandı) -
    # o durumda bu thread birkaç test boyunca "hâlâ canlı" görünmeye
    # devam eder ama en azından paketin geri kalanını bloklamaz.
    for thread in threading.enumerate():

        if thread is not main_thread and thread.is_alive():
            thread.join(timeout=0.2)

    try:

        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()

        if app is not None:

            for _ in range(3):
                app.processEvents()

    except Exception:

        pass
