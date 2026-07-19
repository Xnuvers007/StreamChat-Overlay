# 💬 Stream Chat Overlay

![Build Status](https://github.com/Raychel21/StreamChat-Overlay/actions/workflows/build.yml/badge.svg)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![PySide6](https://img.shields.io/badge/GUI-PySide6-green)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)

**Stream Chat Overlay** adalah aplikasi ringan berbasis Python yang dirancang khusus untuk para *Streamer* (terutama yang menggunakan satu monitor) untuk menampilkan Live Chat YouTube di atas layar tanpa mengganggu jalannya permainan atau aplikasi utama. 

Aplikasi ini menggunakan **PySide6** (Qt for Python) dengan WebEngine untuk me-render chat YouTube secara langsung dengan tampilan transparan dan *borderless*.

---

## ✨ Fitur Utama

- 👻 **Transparent & Frameless:** Tampilan *overlay* tanpa *border* dengan latar belakang transparan yang menyatu dengan layar Anda.
- 📌 **Always on Top:** Chat akan selalu berada di atas aplikasi lain (termasuk game yang berjalan dalam mode *Windowed/Borderless*).
- 🖱️ **Smart Click-Through:** Secara otomatis mengunci *overlay* (membuat kursor tembus) saat Anda sedang bermain game, dan membuka kunci saat Anda beralih ke jendela utama.
- 📐 **Resizable & Draggable:** Mudah dipindahkan dan diatur ukurannya dengan menarik bagian tepi jendela.
- 🌙 **Force Dark Theme:** Memaksa tampilan YouTube Live Chat menggunakan mode gelap agar lebih nyaman di mata.
- 🛡️ **Bypass Restrictions:** Menggunakan kustomisasi *User-Agent* (Chrome/Edge) agar YouTube tidak memblokir browser WebEngine bawaan.

---

## 🚀 Cara Menggunakan (Untuk Pengguna)

Jika Anda hanya ingin menggunakan aplikasinya tanpa repot melakukan *coding*:

1. Buka tab **[Releases](../../releases)** di repositori GitHub ini.
2. Download file **`StreamChatOverlay-windows.zip`** terbaru.
3. Ekstrak file ZIP tersebut di komputer Anda.
4. Jalankan aplikasi **`StreamChatOverlay.exe`**.
5. Buka Live Stream YouTube Anda di browser, klik **⋮ (titik tiga)** di pojok kanan atas chat, lalu pilih **Pop-out chat**.
6. Copy URL dari *address bar* browser Anda dan paste ke dalam aplikasi Stream Chat Overlay.
7. Klik **Start**! 🎉

---

## 🛠️ Build dari Source (Untuk Developer)

Jika Anda ingin memodifikasi atau melakukan proses *build* sendiri:

### 1. Persiapan Environment
Pastikan Anda sudah menginstal **Python 3.10** atau versi lebih baru. 

Clone repositori ini:
```bash
git clone https://github.com/Raychel21/StreamChat-Overlay.git
cd StreamChat-Overlay
```

### 2. Install Dependencies
Sangat disarankan menggunakan virtual environment atau package manager seperti `uv`:

**Menggunakan pip biasa:**
```bash
python -m pip install --upgrade pip
pip install PySide6 pyinstaller pyinstaller-hooks-contrib
```

**Menggunakan uv (Jauh lebih cepat):**
```bash
pip install uv
uv pip install PySide6 pyinstaller pyinstaller-hooks-contrib
```

### 3. Menjalankan Aplikasi
Anda dapat menjalankan script secara langsung untuk melakukan testing:
```bash
python stream-chat.py
```

### 4. Build menjadi .exe
Untuk melakukan *compile* dari `.py` menjadi file `.exe` yang siap digunakan (standalone):
```bash
pyinstaller --clean --noconfirm --noconsole --onedir --upx-exclude="Qt*.dll" --name "StreamChatOverlay" stream-chat.py
```
> **Catatan:** Hasil *build* akan berada di dalam folder `dist/StreamChatOverlay/`.

---

## 🤖 CI/CD (GitHub Actions)
Project ini sudah dilengkapi dengan *workflow* **GitHub Actions** (`build.yml`). 
Setiap kali Anda membuat **Release** baru di GitHub, sistem akan secara otomatis melakukan kompilasi (*build*) kode sumber menjadi `.exe` (menggunakan Windows runner) dan melampirkan hasil ZIP-nya ke halaman Release.

---

## 📄 Lisensi
Project ini dilisensikan di bawah **MIT License**. Anda bebas memodifikasi, mendistribusikan, dan mengembangkan ulang aplikasi ini untuk keperluan pribadi maupun komersial, dengan syarat tetap menyertakan atribusi lisensi aslinya. 

Selengkapnya dapat dilihat pada file [LICENSE](LICENSE).

---
*Dibuat dengan ❤️ untuk para streamer.*
