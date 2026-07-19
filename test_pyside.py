import sys
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Configure Profile
    profile = QWebEngineProfile.defaultProfile()
    # Edge User Agent
    profile.setHttpUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0")

    window = QMainWindow()
    window.resize(600, 800)
    
    browser = QWebEngineView()
    # YouTube Live Chat URL
    browser.setUrl(QUrl("https://www.youtube.com/live_chat?is_popout=1&v=EVWoYqnDb9w&dark_theme=1"))
    
    window.setCentralWidget(browser)
    window.show()
    sys.exit(app.exec())
