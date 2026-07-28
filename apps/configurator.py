import sys

from PySide6.QtWidgets import QApplication

from modules.ui.configurator.main_window import MainWindow


def main():

    app = QApplication(sys.argv)

    window = MainWindow()

    from modules.ui.configurator.configurator_controller import ConfiguratorController
    controller = ConfiguratorController(window)

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()