import os
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Signal

ROOT = Path(__file__).resolve().parents[2]


class TestRunner(QObject):
    """
    pytest test suite'ini ayrı bir process olarak (arayüzü kilitlemeden)
    çalıştırıp JUnit XML çıktısını ayrıştırır.

    `run()` çağrıldığında test suite arka planda başlar; bittiğinde
    `finished` sinyali {"results": [...], "summary": str, "success": bool}
    içeren bir sözlükle tetiklenir.
    """

    finished = Signal(dict)

    def __init__(self, parent=None):

        super().__init__(parent)

        self.process = None
        self._report_path = None

    # -------------------------------------------------

    def is_running(self) -> bool:

        return self.process is not None

    def run(self):

        if self.process is not None:
            return

        fd, report_path = tempfile.mkstemp(suffix=".xml")

        # mkstemp dosyayı açık bir tanıtıcıyla döndürür; Windows'ta
        # açık bir dosya silinemediği için hemen kapatıyoruz - aksi
        # halde iş bitince temizlik PermissionError ile patlar ve
        # `finished` sinyali hiç tetiklenmeden arayüz "Çalışıyor..."
        # durumunda sonsuza dek takılı kalır.
        os.close(fd)

        self._report_path = Path(report_path)

        self.process = QProcess(self)
        self.process.setWorkingDirectory(str(ROOT))
        self.process.finished.connect(self._on_finished)
        self.process.errorOccurred.connect(self._on_error)

        self.process.start(
            sys.executable,
            [
                "-m", "pytest", "tests/", "-q",
                f"--junitxml={self._report_path}"
            ]
        )

    # -------------------------------------------------

    def _on_error(self, error):

        self.process = None

        self.finished.emit({
            "results": [],
            "summary": f"Test süreci başlatılamadı (hata kodu: {error}).",
            "success": False
        })

    def _on_finished(self, exit_code, exit_status):

        stdout = bytes(
            self.process.readAllStandardOutput()
        ).decode("utf-8", errors="replace")

        stderr = bytes(
            self.process.readAllStandardError()
        ).decode("utf-8", errors="replace")

        self.process = None

        try:

            results, summary, success = self._parse_report(
                self._report_path
            )

        except Exception as e:

            # Ayrıştırma başarısız oldu (ör. rapor boş/bozuk) -
            # nedenini görebilmek için ham pytest çıktısını, tek bir
            # "hata" satırı olarak sonuç tablosuna koyuyoruz. Böylece
            # kullanıcı satıra tıklayınca gerçek nedeni görebiliyor.
            output = (stdout + "\n" + stderr).strip()

            results = [{
                "name": "pytest çalıştırma hatası",
                "status": "error",
                "duration": 0.0,
                "message": (
                    f"Rapor ayrıştırılamadı: {e}\n"
                    f"Çıkış kodu: {exit_code}\n\n"
                    f"--- stdout ---\n{stdout}\n\n"
                    f"--- stderr ---\n{stderr}"
                )
            }]

            summary = (
                f"Test çalıştırma başarısız: {e}"
                if not output
                else "Test çalıştırma başarısız - ayrıntı için "
                     "aşağıdaki satıra tıklayın."
            )

            success = False

        finally:

            # Temizlik başarısız olsa bile sonucu arayüze iletmek
            # her zaman öncelikli; bu yüzden hatayı yutuyoruz.
            try:

                if self._report_path is not None:
                    self._report_path.unlink(missing_ok=True)

            except OSError:
                pass

        self.finished.emit({
            "results": results,
            "summary": summary,
            "success": success
        })

    # -------------------------------------------------
    # JUnit XML Ayrıştırma
    # -------------------------------------------------

    def _parse_report(self, path: Path):

        tree = ET.parse(path)
        root = tree.getroot()

        suite = root.find("testsuite") if root.tag == "testsuites" else root

        if suite is None:
            return [], "Test raporu boş.", False

        total = int(suite.get("tests", 0))
        failures = int(suite.get("failures", 0))
        errors = int(suite.get("errors", 0))
        skipped = int(suite.get("skipped", 0))
        time_taken = float(suite.get("time", 0))

        results = []

        for case in suite.findall("testcase"):

            name = self._display_name(
                case.get("classname", ""),
                case.get("name", "")
            )
            duration = float(case.get("time", 0))

            failure = case.find("failure")
            error = case.find("error")
            skip = case.find("skipped")

            if failure is not None:

                status = "failed"
                message = (
                    (failure.get("message") or "")
                    + "\n\n" + (failure.text or "")
                )

            elif error is not None:

                status = "error"
                message = (
                    (error.get("message") or "")
                    + "\n\n" + (error.text or "")
                )

            elif skip is not None:

                status = "skipped"
                message = skip.get("message") or ""

            else:

                status = "passed"
                message = ""

            results.append({
                "name": name,
                "status": status,
                "duration": duration,
                "message": message.strip()
            })

        passed = total - failures - errors - skipped
        success = failures == 0 and errors == 0

        summary = f"{passed}/{total} başarılı"

        if failures:
            summary += f", {failures} başarısız"

        if errors:
            summary += f", {errors} hata"

        if skipped:
            summary += f", {skipped} atlandı"

        summary += f" ({time_taken:.2f} sn)"

        return results, summary, success

    # -------------------------------------------------
    # Okunabilir Test Adı
    # -------------------------------------------------

    ACRONYMS = {
        "ng", "roi", "db", "pin", "id", "ok", "sql",
        "json", "png", "wal", "csv", "xml", "ui", "fps"
    }

    def _display_name(self, classname: str, test_name: str) -> str:

        module = classname.rsplit(".", 1)[-1] if classname else ""

        module_label = self._humanize_module(module)
        test_label = self._humanize_test_name(test_name)

        if module_label and test_label:
            return f"{module_label} — {test_label}"

        return test_label or module_label or test_name

    def _humanize_module(self, module: str) -> str:

        if module.startswith("test_"):
            module = module[len("test_"):]

        words = [w for w in module.split("_") if w]

        return " ".join(
            self._format_word(w, capitalize=True) for w in words
        )

    def _humanize_test_name(self, test_name: str) -> str:

        if test_name.startswith("test_"):
            test_name = test_name[len("test_"):]

        words = [w for w in test_name.split("_") if w]

        return " ".join(
            self._format_word(w, capitalize=(i == 0))
            for i, w in enumerate(words)
        )

    def _format_word(self, word: str, capitalize: bool) -> str:

        if word.lower() in self.ACRONYMS:
            return word.upper()

        if capitalize:
            return word[:1].upper() + word[1:]

        return word
