import sys
import os
import json
import ctypes
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from PySide6.QtCore import Qt, QUrl, QPoint, QRect
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
    QWidget, QPushButton, QLabel, QLineEdit, QFrame,
    QScrollArea, QSizePolicy
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings


# ==============================================================================
# Constants
# ==============================================================================
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(sys.argv[0])), "config.json"
)
WEBDATA_DIR = os.path.join(
    os.path.dirname(os.path.abspath(sys.argv[0])), "webdata"
)

RESIZE_MARGIN = 8
OVERLAY_MIN_W = 300
OVERLAY_MIN_H = 350

# User-agent Chrome/Edge asli — KUNCI agar YouTube tidak menolak WebEngine
CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0"
)


# ==============================================================================
# Config Helpers
# ==============================================================================
def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_config(data: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        print(f"[Config] Gagal menyimpan config: {e}")


# ==============================================================================
# URL Normalization
# ==============================================================================
def normalize_chat_url(url: str) -> str:
    """
    Pastikan URL menggunakan dark theme untuk YouTube Live Chat.
    Kita HAPUS embed_domain karena ini dijalankan sebagai top-level frame, 
    bukan di dalam iframe, sehingga embed_domain justru membuat YouTube nge-blank.
    """
    if "youtube.com/live_chat" not in url:
        return url
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        # Paksa dark theme
        params["dark_theme"] = ["1"]
        # Hapus embed_domain jika ada
        if "embed_domain" in params:
            del params["embed_domain"]
            
        flat = {k: (v[0] if isinstance(v, list) and v else "") for k, v in params.items()}
        return urlunparse(parsed._replace(query=urlencode(flat)))
    except Exception:
        return url


# ==============================================================================
# WebEngine Profile Configuration
# Harus dipanggil SEBELUM window apapun dibuat
# ==============================================================================
def configure_web_profile():
    """
    Konfigurasi global QWebEngineProfile:
    1. User-agent Chrome — YouTube menolak UA bawaan Qt
    2. Persistent cookies — session YouTube tersimpan antar sesi
    3. Storage path — data tidak hilang setelah restart .exe
    """
    profile = QWebEngineProfile.defaultProfile()

    # [FIX UTAMA] Set Chrome user-agent
    profile.setHttpUserAgent(CHROME_UA)

    # Simpan cookie & session secara permanen di folder aplikasi
    profile.setPersistentCookiesPolicy(QWebEngineProfile.AllowPersistentCookies)
    os.makedirs(WEBDATA_DIR, exist_ok=True)
    profile.setPersistentStoragePath(WEBDATA_DIR)
    profile.setCachePath(os.path.join(WEBDATA_DIR, "cache"))


# ==============================================================================
# ChatOverlay — Frameless, Always on Top, Fully Resizable
# ==============================================================================
class ChatOverlay(QMainWindow):

    _CURSOR_MAP = {
        "nw": Qt.SizeFDiagCursor, "se": Qt.SizeFDiagCursor,
        "ne": Qt.SizeBDiagCursor, "sw": Qt.SizeBDiagCursor,
        "n":  Qt.SizeVerCursor,   "s":  Qt.SizeVerCursor,
        "w":  Qt.SizeHorCursor,   "e":  Qt.SizeHorCursor,
    }

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self._url = url
        self._locked = False
        self._dragging: bool = False
        self._drag_pos: Optional[QPoint] = None
        self._resizing: bool = False
        self._resize_dir: Optional[str] = None
        self._start_geo: Optional[QRect] = None
        self._start_mouse: Optional[QPoint] = None
        self._init_ui(url)

    def _init_ui(self, url: str):
        self.setGeometry(60, 60, 420, 680)
        self.setMinimumSize(OVERLAY_MIN_W, OVERLAY_MIN_H)
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        # ── Root widget ──────────────────────────────────────────────────────
        root = QWidget(self)
        root.setObjectName("overlayRoot")
        root.setStyleSheet("""
            QWidget#overlayRoot {
                background-color: rgba(8, 8, 14, 115);
                border: 1px solid rgba(255, 255, 255, 15);
                border-radius: 10px;
            }
        """)
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Title bar ────────────────────────────────────────────────────────
        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(32)
        self.title_bar.setMouseTracking(True)
        self.title_bar.setStyleSheet(
            "background-color: rgba(18, 18, 26, 220); border-radius: 10px 10px 0 0;"
        )
        self.title_bar.setCursor(Qt.SizeAllCursor)

        tb_layout = QHBoxLayout(self.title_bar)
        tb_layout.setContentsMargins(10, 0, 8, 0)
        tb_layout.setSpacing(6)

        dot = QLabel("●")
        dot.setStyleSheet("color: #3ecf6b; font-size: 9px; padding-top: 1px;")
        tb_layout.addWidget(dot)

        title_lbl = QLabel("Live Chat")
        title_lbl.setStyleSheet(
            "color: rgba(255,255,255,140); font-size: 11px; font-family: 'Segoe UI', Arial;"
        )
        tb_layout.addWidget(title_lbl)
        tb_layout.addStretch()

        hint_lbl = QLabel("↔ tarik tepi untuk resize")
        hint_lbl.setStyleSheet("color: rgba(255,255,255,35); font-size: 9px;")
        tb_layout.addWidget(hint_lbl)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(22, 22)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(200, 50, 50, 160);
                color: white; border: none; border-radius: 11px; font-size: 10px;
            }
            QPushButton:hover { background: rgba(230, 80, 80, 230); }
            QPushButton:pressed { background: rgba(170, 30, 30, 240); }
        """)
        close_btn.clicked.connect(self.close)
        tb_layout.addWidget(close_btn)

        layout.addWidget(self.title_bar)

        # ── WebEngine View ───────────────────────────────────────────────────
        self.browser = QWebEngineView()
        self.browser.setMouseTracking(True)

        # Aktifkan semua setting web yang dibutuhkan YouTube
        ws = self.browser.settings()
        ws.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        ws.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        ws.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        ws.setAttribute(QWebEngineSettings.ScrollAnimatorEnabled, True)
        ws.setAttribute(QWebEngineSettings.AllowWindowActivationFromJavaScript, True)
        ws.setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, False)
        ws.setAttribute(QWebEngineSettings.PluginsEnabled, True)
        ws.setAttribute(QWebEngineSettings.FullScreenSupportEnabled, False)

        self.browser.page().setBackgroundColor(QColor(0, 0, 0, 0))
        self.browser.loadFinished.connect(self._on_load_finished)

        # Normalize URL (tambah embed_domain) lalu load
        normalized = normalize_chat_url(url)
        print(f"[ChatOverlay] Loading URL: {normalized}")
        self.browser.setUrl(QUrl(normalized))

        layout.addWidget(self.browser)

    def _on_load_finished(self, success: bool):
        if not success:
            print("[ChatOverlay] Load gagal.")
            self.browser.setHtml("""
            <html><body style="background:transparent;color:#ff9f43;
                font-family:'Segoe UI',Arial,sans-serif;display:flex;
                align-items:center;justify-content:center;height:100vh;
                margin:0;text-align:center;">
                <div>
                    <div style='font-size:30px;margin-bottom:10px;'>🌐</div>
                    <div style='font-size:13px;line-height:1.8;'>
                        Gagal memuat chat.<br>
                        Periksa URL &amp; koneksi internet.
                    </div>
                </div>
            </body></html>
            """)
            return
            
        # CSS SUPER AGRESIF untuk memastikan Header, Footer, dan Box Login HILANG
        css = """
        /* Sembunyikan Header */
        yt-live-chat-header-renderer, #chat-header, #header { 
            display: none !important; 
        }
        
        /* Sembunyikan Footer & Box Login */
        yt-live-chat-message-input-renderer, 
        yt-live-chat-restricted-participation-renderer,
        yt-live-chat-viewer-engagement-message-renderer,
        #action-panel, #input-panel, #message-input { 
            display: none !important; 
        }
        
        /* Background full transparan */
        body, yt-live-chat-renderer, yt-live-chat-app, #contents, #item-scroller { 
            background: transparent !important; 
            background-color: transparent !important; 
        }
        """
            
        js = f"""
        var style = document.createElement('style');
        style.type = 'text/css';
        style.textContent = `{css}`;
        document.head.appendChild(style);
        """
        self.browser.page().runJavaScript(js)

    def set_locked(self, locked: bool):
        if self._locked == locked:
            return
        self._locked = locked
        self.title_bar.setVisible(not locked)

        # Gunakan API Windows untuk membuat window menjadi click-through (tembus kursor)
        try:
            hwnd = int(self.winId())
            GWL_EXSTYLE = -20
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_LAYERED = 0x00080000
            
            user32 = ctypes.windll.user32
            exstyle = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            
            if locked:
                # Tambahkan flag click-through
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle | WS_EX_TRANSPARENT | WS_EX_LAYERED)
            else:
                # Hapus flag click-through
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle & ~WS_EX_TRANSPARENT)
        except Exception as e:
            print("[ChatOverlay] Gagal mengubah status click-through:", e)

    # ── Resize direction detection ────────────────────────────────────────────
    def _get_resize_dir(self, pos: QPoint) -> Optional[str]:
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        m = RESIZE_MARGIN
        left   = x <= m
        right  = x >= w - m
        top    = y <= m
        bottom = y >= h - m
        if left  and top:    return "nw"
        if right and top:    return "ne"
        if left  and bottom: return "sw"
        if right and bottom: return "se"
        if left:             return "w"
        if right:            return "e"
        if top:              return "n"
        if bottom:           return "s"
        return None

    # ── Mouse Events ─────────────────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        d = self._get_resize_dir(event.pos())
        if d:
            self._resizing = True
            self._resize_dir = d
            self._start_geo = self.geometry()
            self._start_mouse = event.globalPos()
        else:
            self._dragging = True
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
        event.accept()

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            d = self._get_resize_dir(event.pos())
            self.setCursor(self._CURSOR_MAP.get(d, Qt.ArrowCursor))
            return

        if self._resizing and self._resize_dir and self._start_geo and self._start_mouse:
            delta = event.globalPos() - self._start_mouse
            g = self._start_geo
            x, y, w, h = g.x(), g.y(), g.width(), g.height()
            d = self._resize_dir

            if "e" in d:
                w = max(OVERLAY_MIN_W, g.width() + delta.x())
            if "s" in d:
                h = max(OVERLAY_MIN_H, g.height() + delta.y())
            if "w" in d:
                w = max(OVERLAY_MIN_W, g.width() - delta.x())
                x = g.right() - w + 1
            if "n" in d:
                h = max(OVERLAY_MIN_H, g.height() - delta.y())
                y = g.bottom() - h + 1

            self.setGeometry(x, y, w, h)

        elif self._dragging and self._drag_pos is not None:
            self.move(event.globalPos() - self._drag_pos)

        event.accept()

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self._resizing = False
        self._resize_dir = None
        self._start_geo = None
        self._start_mouse = None
        self.setCursor(Qt.ArrowCursor)


# ==============================================================================
# MainWindow — Launcher UI (minimize / maximize / close standar)
# ==============================================================================
class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self._overlay: Optional[ChatOverlay] = None
        self._init_ui()
        self._prefill_saved_url()

    def _init_ui(self):
        self.setWindowTitle("Stream Chat Overlay")
        self.setMinimumSize(500, 540)
        self.resize(540, 600)
        self.setWindowFlags(Qt.Window)
        
        # Pantau status aplikasi (aktif/tidak aktif)
        app = QApplication.instance()
        app.applicationStateChanged.connect(self._on_app_state_changed)

        # ── Global stylesheet ────────────────────────────────────────────────
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0a0a12;
            }
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
                background-color: transparent;
            }
            QScrollArea {
                border: none;
                background-color: #0a0a12;
            }
            QScrollBar:vertical {
                background: #0d0d18;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #2a2a48;
                border-radius: 3px;
                min-height: 24px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QLineEdit {
                background-color: #13131e;
                color: #ddddf5;
                border: 1.5px solid #22223a;
                border-radius: 9px;
                padding: 14px 18px;
                font-size: 16px;
            }
            QLineEdit:focus {
                border: 1.5px solid #4a6fc8;
                background-color: #16162a;
            }
            QLineEdit[invalid="true"] {
                border: 1.5px solid #c84040;
            }
        """)

        # ── Root ─────────────────────────────────────────────────────────────
        root = QWidget()
        root.setStyleSheet("background-color: #0a0a12;")
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Top accent bar
        accent = QWidget()
        accent.setFixedHeight(4)
        accent.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            " stop:0 #3a6fc8, stop:0.5 #3ecf6b, stop:1 #3a6fc8);"
        )
        outer.addWidget(accent)

        # ── Scroll Area (agar bisa di-scroll jika window diperkecil) ─────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("background-color: #0a0a12; border: none;")
        outer.addWidget(scroll)

        # Konten dalam scroll
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: #0a0a12;")
        scroll.setWidget(scroll_content)

        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(52, 48, 52, 48)
        layout.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────────────
        icon_lbl = QLabel("💬")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            "font-size: 64px; margin-bottom: 12px; background: transparent;"
        )
        layout.addWidget(icon_lbl)

        title_lbl = QLabel("Stream Chat Overlay")
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet(
            "color: #e8e8f8; font-size: 32px; font-weight: 700;"
            " letter-spacing: 0.5px; margin-bottom: 8px; background: transparent;"
        )
        layout.addWidget(title_lbl)

        sub_lbl = QLabel("Tampilkan live chat YouTube di atas layar kamu")
        sub_lbl.setAlignment(Qt.AlignCenter)
        sub_lbl.setStyleSheet(
            "color: #8a8a98; font-size: 16px; margin-bottom: 38px; background: transparent;"
        )
        layout.addWidget(sub_lbl)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("color: #16162a; margin-bottom: 26px;")
        layout.addWidget(div)

        # ── Label URL ───────────────────────────────────────────────────────
        url_lbl = QLabel("YOUTUBE LIVE CHAT URL")
        url_lbl.setStyleSheet(
            "color: #757598; font-size: 14px; font-weight: 600;"
            " letter-spacing: 1px; margin-bottom: 10px; background: transparent;"
        )
        layout.addWidget(url_lbl)

        # ── Kotak panduan ────────────────────────────────────────────────────
        guide_box = QFrame()
        guide_box.setFrameShape(QFrame.NoFrame)
        guide_box.setStyleSheet("""
            QFrame {
                background-color: #0e0e1c;
                border: 1px solid #1c1c2e;
                border-radius: 8px;
            }
            QLabel { background: transparent; }
        """)
        guide_layout = QVBoxLayout(guide_box)
        guide_layout.setContentsMargins(20, 16, 20, 16)
        guide_layout.setSpacing(8)

        guide_title = QLabel("📋  Cara mendapatkan link:")
        guide_title.setStyleSheet(
            "color: #7a7a98; font-size: 15px; font-weight: 600;"
        )
        guide_layout.addWidget(guide_title)

        for step in [
            "1. Buka Live Stream YouTube kamu",
            "2. Klik ⋮ (titik tiga) di pojok atas chat",
            "3. Pilih  'Pop-out chat'",
            "4. Copy URL dari address bar browser",
        ]:
            lbl = QLabel(step)
            lbl.setStyleSheet("color: #a6a6b8; font-size: 14px;")
            guide_layout.addWidget(lbl)

        layout.addWidget(guide_box)
        layout.addSpacing(16)

        # ── Input URL ────────────────────────────────────────────────────────
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/live_chat?v=...")
        self.url_input.setFixedHeight(56)
        self.url_input.returnPressed.connect(self._on_start)
        self.url_input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.url_input)

        # ── Error label ──────────────────────────────────────────────────────
        self.error_lbl = QLabel("⚠  Link tidak valid. Pastikan URL dari YouTube Pop-out Chat.")
        self.error_lbl.setStyleSheet(
            "color: #d05050; font-size: 14px; margin-top: 8px; background: transparent;"
        )
        self.error_lbl.setWordWrap(True)
        self.error_lbl.hide()
        layout.addWidget(self.error_lbl)

        layout.addSpacing(24)
        layout.addStretch()

        # ── Start button (DI LUAR SCROLL AREA AGAR SELALU MUNCUL) ────────────
        self.start_btn = QPushButton("▶   Start")
        self.start_btn.setFixedHeight(56)
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #276e44, stop:1 #1b5233);
                color: #e0ffe8;
                border: none;
                border-radius: 13px;
                font-size: 18px;
                font-weight: 700;
                letter-spacing: 1.5px;
                margin: 0px 52px 30px 52px; 
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #33a05f, stop:1 #24703d);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1e5535, stop:1 #143d25);
            }
        """)
        self.start_btn.clicked.connect(self._on_start)
        outer.addWidget(self.start_btn)

    def _on_app_state_changed(self, state):
        if self._overlay:
            # Jika aplikasi aktif (user menyorot jendela main app atau chat) -> Unlock
            if state == Qt.ApplicationState.ApplicationActive:
                self._overlay.set_locked(False)
            # Jika user klik game atau minimize app -> Lock (click-through)
            else:
                self._overlay.set_locked(True)

    def _prefill_saved_url(self):
        saved = load_config().get("chat_url", "")
        if saved:
            self.url_input.setText(saved)

    def _on_text_changed(self):
        if self.error_lbl.isVisible():
            self.error_lbl.hide()
        self.url_input.setProperty("invalid", "false")
        self.url_input.style().unpolish(self.url_input)
        self.url_input.style().polish(self.url_input)

    def _on_start(self):
        url = self.url_input.text().strip()

        if not url or not url.startswith("http"):
            self._show_error()
            return

        cfg = load_config()
        cfg["chat_url"] = url
        save_config(cfg)

        self.error_lbl.hide()
        self._on_text_changed()

        if self._overlay is not None and self._overlay.isVisible():
            self._overlay.close()

        self._overlay = ChatOverlay(url, parent=None)
        self._overlay.show()

        self.showMinimized()

    def _show_error(self):
        self.error_lbl.show()
        self.url_input.setProperty("invalid", "true")
        self.url_input.style().unpolish(self.url_input)
        self.url_input.style().polish(self.url_input)
        self.url_input.setFocus()

    def closeEvent(self, event):
        if self._overlay is not None and self._overlay.isVisible():
            self._overlay.close()
        event.accept()


# ==============================================================================
# Entry Point
# ==============================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Stream Chat Overlay")

    # PENTING: configure_web_profile() harus dipanggil sebelum window apapun dibuat
    configure_web_profile()

    window = MainWindow()
    window.show()

    sys.exit(app.exec())