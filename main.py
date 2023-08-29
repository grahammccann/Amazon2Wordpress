import sys
from PyQt5.QtWidgets import QApplication
from browser_app import BrowserApp

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = BrowserApp()
    window.show()
    sys.exit(app.exec_())