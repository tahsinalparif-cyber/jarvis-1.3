import os
import sys
import base64

# .exe olduğunda klasör yolunu sabitleme kodu
if getattr(sys, 'frozen', False):
    DOKUMAN_YOLU = os.path.dirname(sys.executable)
else:
    DOKUMAN_YOLU = os.path.dirname(os.path.abspath(__file__))

HAFIZA_FILE = os.path.join(DOKUMAN_YOLU, "hafiza.txt")
KEY_FILE_PATH = os.path.join(DOKUMAN_YOLU, "jarvis_api_key.txt")
SES_FILE_PATH = os.path.join(DOKUMAN_YOLU, "jarvis_ses.txt")

import time
import asyncio
import threading
import tempfile
import glob
import platform
import psutil
import requests
from bs4 import BeautifulSoup
import datetime
import pyautogui

# Arayüz kütüphaneleri
import tkinter as tk
from tkinter import ttk, messagebox

# Gerekli arka plan kütüphaneleri
import speech_recognition as sr
import keyboard
import pyaudio
import edge_tts
import pygame

# Groq kütüphanesi
from groq import Groq

# ─────────────────────────────────────────────
# 🎙️ TÜRKÇE SES SEÇENEKLERİ
# ─────────────────────────────────────────────
SESLER = {
    "Emel (Kadın)"      : "tr-TR-EmelNeural",
    "Ahmet (Erkek)"     : "tr-TR-AhmetNeural",
    "Filiz (Kadın-2)"   : "tr-TR-FilizNeural",
    "Erkek (EN-onur)"   : "en-US-OnurNeural",      # Türkçe telaffuz kabul eder, derin erkek ses
    "Kadın (EN-pınar)"  : "en-US-PinarNeural",     # Türkçe isim, Türkçe telaffuz yapar
}
secili_ses = "tr-TR-EmelNeural"   # varsayılan

def sesi_kaydet(ses_kodu):
    with open(SES_FILE_PATH, "w", encoding="utf-8") as f:
        f.write(ses_kodu)

def sesi_oku():
    if os.path.exists(SES_FILE_PATH):
        with open(SES_FILE_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "tr-TR-EmelNeural"

# Global değişkenler
secilen_mikrofon_id = None
mikrofon_aktif = True
son_basim = 0
client = None
sohbet_gecmisi = []
secili_ses = sesi_oku()

# ─────────────────────────────────────────────
# HAFIZA
# ─────────────────────────────────────────────
def hafizayi_oku():
    dosya_yolu = os.path.join(DOKUMAN_YOLU, "hafiza.txt")
    if os.path.exists(dosya_yolu):
        with open(dosya_yolu, "r", encoding="utf-8") as f:
            return f.read()
    return "Henüz bir bilgi kaydedilmemiş."

# Pygame ses mikserini başlatıyoruz
pygame.mixer.init()

# ─────────────────────────────────────────────
# 🔊 KİLİTLENMEYEN SES MOTORU
# ─────────────────────────────────────────────
def ses_calici_thread(yazi, log_callback):
    global secili_ses
    zaman_damgasi = int(time.time() * 1000)
    ses_dosyasi = os.path.join(tempfile.gettempdir(), f"jarvis_voice_{zaman_damgasi}.mp3")

    try:
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
    except:
        pass

    async def speak_async():
        communicate = edge_tts.Communicate(yazi, secili_ses)
        await communicate.save(ses_dosyasi)

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(speak_async())
        loop.close()

        if os.path.exists(ses_dosyasi):
            if log_callback:
                log_callback(f"🤖 J.A.R.V.İ.S: {yazi}")
            pygame.mixer.music.load(ses_dosyasi)
            pygame.mixer.music.play()
            threading.Thread(target=eski_sesleri_temizle, args=(ses_dosyasi,), daemon=True).start()
    except Exception as e:
        if log_callback:
            log_callback(f"⚠️ Ses Hatası: {e}")

def eski_sesleri_temizle(su_anki_dosya):
    time.sleep(2)
    klasor = tempfile.gettempdir()
    for dosya in glob.glob(os.path.join(klasor, "jarvis_voice_*.mp3")):
        if dosya != su_anki_dosya:
            try:
                os.remove(dosya)
            except:
                pass

def sesli_konus(yazi, log_callback=None):
    threading.Thread(target=ses_calici_thread, args=(yazi, log_callback), daemon=True).start()

# ─────────────────────────────────────────────
# 📅 ZAMAN & SİSTEM
# ─────────────────────────────────────────────
GUNLER_TR = {
    "Monday": "Pazartesi", "Tuesday": "Salı", "Wednesday": "Çarşamba",
    "Thursday": "Perşembe", "Friday": "Cuma", "Saturday": "Cumartesi", "Sunday": "Pazar"
}
AYLAR_TR = {
    1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
    7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
}

def saati_ogren():
    return datetime.datetime.now().strftime("%H:%M")

def tarihi_ogren():
    now = datetime.datetime.now()
    gun_tr = GUNLER_TR.get(now.strftime("%A"), now.strftime("%A"))
    ay_tr  = AYLAR_TR.get(now.month, str(now.month))
    return f"{gun_tr}, {now.day} {ay_tr} {now.year}"

def gunu_ogren():
    return GUNLER_TR.get(datetime.datetime.now().strftime("%A"), "")

def yili_ogren():
    return str(datetime.datetime.now().year)

def sistem_durumu_ogren():
    cpu      = psutil.cpu_percent(interval=1)
    ram      = psutil.virtual_memory().percent
    ram_gb   = round(psutil.virtual_memory().total / (1024**3), 1)
    disk     = psutil.disk_usage('/').percent
    os_bilgi = platform.system()
    return (
        f"Sistem {os_bilgi} üzerinde çalışıyor efendim. "
        f"İşlemci yüzde {cpu}, bellek yüzde {ram} (toplam {ram_gb} gigabayt), "
        f"disk yüzde {disk} dolu."
    )

# ─────────────────────────────────────────────
# 🌤️ HAVA DURUMU
# ─────────────────────────────────────────────
def hava_durumu_ogren(sehir):
    try:
        url = f"https://wttr.in/{sehir}?format=j1&lang=tr"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        cur  = data["current_condition"][0]
        sicaklik = cur["temp_C"]
        his      = cur["FeelsLikeC"]
        nem      = cur["humidity"]
        durum    = cur["lang_tr"][0]["value"] if "lang_tr" in cur else cur["weatherDesc"][0]["value"]
        return (
            f"{sehir.title()} için hava durumu: {durum}, "
            f"sıcaklık {sicaklik} derece, hissedilen {his} derece, nem yüzde {nem}."
        )
    except Exception as e:
        return f"Hava durumu alınamadı efendim: {e}"

# ─────────────────────────────────────────────
# 🌐 WEB ARAMA (BeautifulSoup + DuckDuckGo)
# ─────────────────────────────────────────────
def web_ara(sorgu):
    try:
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(sorgu)}&kl=tr-tr"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(resp.text, "html.parser")
        sonuclar = soup.find_all("a", class_="result__snippet", limit=3)
        if not sonuclar:
            # alternatif: result__body
            sonuclar = soup.find_all("div", class_="result__body", limit=3)
        if not sonuclar:
            return "Bu konuda bir şey bulamadım efendim."
        metin = " ".join(s.get_text(strip=True) for s in sonuclar)
        return metin[:350]
    except Exception as e:
        return f"Arama yapılamadı efendim: {e}"

# ─────────────────────────────────────────────
# 🖥️ EKRAN GÖRÜNTÜSÜ + GROQ VISION
# ─────────────────────────────────────────────
def ekrani_yorumla(log_callback=None):
    try:
        if log_callback:
            log_callback("📸 Ekran görüntüsü alınıyor...")
        ekran = pyautogui.screenshot()
        ekran = ekran.resize((1280, 720))
        tmp = os.path.join(tempfile.gettempdir(), "jarvis_screen.jpg")
        ekran.save(tmp, "JPEG", quality=75)

        with open(tmp, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        if client is None:
            return "API bağlantısı yok efendim."

        resp = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    {"type": "text", "text": (
                        "Bu ekran görüntüsünü Türkçe olarak kısaca açıkla. "
                        "Ne yapılıyor, hangi uygulama açık, önemli bir şey var mı? "
                        "Maksimum 3 kısa cümle."
                    )}
                ]
            }],
            max_tokens=200
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"Ekran yorumlanamadı efendim: {e}"

# ─────────────────────────────────────────────
# 🧠 SYSTEM INSTRUCTION
# ─────────────────────────────────────────────
SYSTEM_INSTRUCTION = """Sen kullanıcının bilgisayarında çalışan, J.A.R.V.İ.S adında sesli bir AI asistansın.
Kurallar:
1. Samimi bir arkadaş gibi, sıcak ve doğal konuş (efendim hitabını kullan; başka hitap isterse öyle hitap et).
2. Cevapları asla uzun tutma, sesli okunduğu için maksimum 1-2-3 kısa cümle.
3. Sana sorulan her soruya cevap ver.
4. Bilmediğin bir soruda bilmediğini dile getir.
5. Seni yapan kişi icomnes53, asıl adı Tahsin Çavuşoğlu.
6. Hatalı durumda hata vermeden önce konuyu değiştir."""

# ─────────────────────────────────────────────
# 🖥️ HUD ARAYÜZÜ
# ─────────────────────────────────────────────
class JarvisMinimalHUD:
    def __init__(self, root):
        self.root = root
        self.root.title("JARVIS")
        self.root.geometry("280x320")
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#0b0f19")
        self.root.resizable(False, False)
        self.check_api_key()

    def check_api_key(self):
        if os.path.exists(KEY_FILE_PATH):
            with open(KEY_FILE_PATH, "r", encoding="utf-8") as f:
                saved_key = f.read().strip()
            if saved_key:
                self.start_jarvis_engine(saved_key)
                return
        self.create_login_widgets()

    def create_login_widgets(self):
        self.clear_window()
        tk.Label(self.root, text="⚡ JARVIS GROQ LOGIN ⚡", font=("Segoe UI", 10, "bold"),
                 bg="#0b0f19", fg="#00f0ff").pack(pady=20)
        tk.Label(self.root, text="Groq API Key Yapıştır Kanka (gsk_...):",
                 font=("Segoe UI", 9), bg="#0b0f19", fg="#8a95a5").pack(pady=5)
        self.entry_key = tk.Entry(self.root, width=26, bg="#141a29", fg="#e1e7ed",
                                  insertbackground="#00f0ff", font=("Segoe UI", 10),
                                  bd=0, highlightthickness=1, highlightbackground="#1f2d3d")
        self.entry_key.pack(pady=10, ipady=4)
        tk.Button(self.root, text="BAŞLAT 🚀", bg="#00ff66", fg="#0f141c",
                  font=("Segoe UI", 10, "bold"), width=12, bd=0, cursor="hand2",
                  command=self.save_and_activate_key).pack(pady=15)

    def save_and_activate_key(self):
        input_key = self.entry_key.get().strip()
        if not input_key:
            messagebox.showwarning("Uyarı", "Anahtar boş olamaz kanka.")
            return
        try:
            with open(KEY_FILE_PATH, "w", encoding="utf-8") as f:
                f.write(input_key)
            self.start_jarvis_engine(input_key)
        except Exception as e:
            messagebox.showerror("Hata", f"Yazma hatası: {e}")

    def start_jarvis_engine(self, api_key):
        global client
        try:
            client = Groq(api_key=api_key)
        except Exception as e:
            messagebox.showerror("Hata", f"Groq API Hatası: {e}")
            if os.path.exists(KEY_FILE_PATH):
                os.remove(KEY_FILE_PATH)
            self.create_login_widgets()
            return

        self.clear_window()
        self.create_hud_widgets()
        self.running = True
        self.loop_thread = threading.Thread(target=self.jarvis_ana_dongu, daemon=True)
        self.p = pyaudio.PyAudio()
        self.taraci_mikrofonlar()
        keyboard.add_hotkey('m', self.tetikle_mute_klavye)

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def create_hud_widgets(self):
        # Mikrofon seçici
        self.mic_box = ttk.Combobox(self.root, width=28, state="readonly", font=("Segoe UI", 9))
        self.mic_box.pack(pady=6)
        self.mic_box.bind("<<ComboboxSelected>>", self.mikrofon_degistir)

        # Log alanı
        self.txt_logs = tk.Text(self.root, height=5, width=32, bg="#111625", fg="#d1d9e6",
                                insertbackground="white", font=("Consolas", 9), bd=0,
                                highlightthickness=1, highlightbackground="#1c2336")
        self.txt_logs.pack(pady=4)
        self.txt_logs.config(state="disabled")

        # Mute butonu
        self.btn_mute = tk.Button(self.root, text="🎙️ MİKROFON: AKTİF", bg="#00ff66", fg="#0b0f19",
                                  font=("Segoe UI", 9, "bold"), width=24, bd=0, cursor="hand2",
                                  command=self.tetikle_mute_click)
        self.btn_mute.pack(pady=4)

        # ── SES SEÇİCİ ──
        ses_frame = tk.Frame(self.root, bg="#0b0f19")
        ses_frame.pack(pady=2)
        tk.Label(ses_frame, text="🔊 Ses:", font=("Segoe UI", 8), bg="#0b0f19", fg="#8a95a5").pack(side=tk.LEFT, padx=(0, 4))
        self.ses_box = ttk.Combobox(ses_frame, width=18, state="readonly", font=("Segoe UI", 8))
        self.ses_box["values"] = list(SESLER.keys())
        # Kayıtlı sesi bul ve seç
        mevcut_kod = sesi_oku()
        mevcut_isim = next((k for k, v in SESLER.items() if v == mevcut_kod), list(SESLER.keys())[0])
        self.ses_box.set(mevcut_isim)
        self.ses_box.pack(side=tk.LEFT)
        self.ses_box.bind("<<ComboboxSelected>>", self.ses_degistir)

        # Yazı girişi
        self.entry_text = tk.Entry(self.root, width=26, bg="#111625", fg="#e1e7ed",
                                   insertbackground="#00f0ff", font=("Segoe UI", 10), bd=0,
                                   highlightthickness=1, highlightbackground="#1c2336")
        self.entry_text.pack(pady=4, ipady=4)
        self.entry_text.bind("<Return>", self.elle_yazi_gonder)

        self.lbl_info = tk.Label(self.root, text="Kısayol: 'M' | Yaz ve Enter'a bas",
                                 font=("Segoe UI", 8), bg="#0b0f19", fg="#525f78")
        self.lbl_info.pack(pady=2)

    def ses_degistir(self, event):
        global secili_ses
        secilen_isim = self.ses_box.get()
        secili_ses = SESLER[secilen_isim]
        sesi_kaydet(secili_ses)
        self.log_yaz(f"🔊 Ses değiştirildi: {secilen_isim}")
        threading.Thread(target=sesli_konus, args=(f"Ses değiştirildi efendim.", self.log_yaz), daemon=True).start()

    def log_yaz(self, mesaj):
        self.txt_logs.config(state="normal")
        self.txt_logs.insert(tk.END, mesaj + "\n")
        self.txt_logs.see(tk.END)
        self.txt_logs.config(state="disabled")

    def taraci_mikrofonlar(self):
        device_count = self.p.get_device_count()
        self.gecerli_mics = {}
        liste = []
        sayac = 0
        for i in range(device_count):
            info = self.p.get_device_info_by_index(i)
            if info.get('maxInputChannels') > 0:
                name = info.get('name')
                try:
                    name = name.encode('utf-8', errors='ignore').decode('utf-8')
                except:
                    pass
                self.gecerli_mics[sayac] = i
                liste.append(f"[{sayac}] {name[:18]}")
                sayac += 1
        self.mic_box['values'] = liste
        if liste:
            self.mic_box.current(0)
            self.mikrofon_degistir(None)

    def mikrofon_degistir(self, event):
        global secilen_mikrofon_id
        index = self.mic_box.current()
        if index != -1:
            secilen_mikrofon_id = self.gecerli_mics[index]
            self.log_yaz(f"⚙️ Mic ID {secilen_mikrofon_id} seçildi.")
            if not self.loop_thread.is_alive():
                self.loop_thread.start()

    def tetikle_mute_click(self):
        global mikrofon_aktif, son_basim
        son_basim = time.time()
        mikrofon_aktif = not mikrofon_aktif
        self.arayuz_mute_guncelle()

    def tetikle_mute_klavye(self):
        global mikrofon_aktif, son_basim
        su_an = time.time()
        if su_an - son_basim < 0.5:
            return
        son_basim = su_an
        mikrofon_aktif = not mikrofon_aktif
        self.arayuz_mute_guncelle()

    def arayuz_mute_guncelle(self):
        if mikrofon_aktif:
            self.btn_mute.config(text="🎙️ MİKROFON: AKTİF", bg="#00ff66", fg="#0b0f19")
            self.log_yaz("🔊 Dinleme aktif.")
        else:
            self.btn_mute.config(text="🔇 MİKROFON: KAPALI", bg="#ff3366", fg="#ffffff")
            self.log_yaz("🔇 Dinleme durduruldu.")

    def elle_yazi_gonder(self, event):
        yazi = self.entry_text.get().strip()
        if not yazi:
            return
        self.entry_text.delete(0, tk.END)
        self.log_yaz(f"🗣️ Sen: {yazi}")
        threading.Thread(target=self.jarvis_cevap_uret, args=(yazi,), daemon=True).start()

    def modern_onay_kutusu(self, baslik, mesaj):
        onay_penceresi = tk.Toplevel(self.root)
        onay_penceresi.title(baslik)
        onay_penceresi.geometry("200x100")
        onay_penceresi.configure(bg="#111625")
        onay_penceresi.attributes("-topmost", True)
        onay_penceresi.resizable(False, False)
        x = self.root.winfo_x() + 40
        y = self.root.winfo_y() + 80
        onay_penceresi.geometry(f"+{x}+{y}")
        lbl = tk.Label(onay_penceresi, text=mesaj, bg="#111625", fg="#d1d9e6",
                       font=("Segoe UI", 9), wraplength=160)
        lbl.pack(pady=10)
        self.onay_sonuc = False

        def secim_yap(deger):
            self.onay_sonuc = deger
            onay_penceresi.destroy()

        btn_frame = tk.Frame(onay_penceresi, bg="#111625")
        btn_frame.pack()
        tk.Button(btn_frame, text="Evet", bg="#00ff66", fg="#0b0f19",
                  font=("Segoe UI", 9, "bold"), width=6, bd=0,
                  command=lambda: secim_yap(True)).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Hayır", bg="#ff3366", fg="#ffffff",
                  font=("Segoe UI", 9, "bold"), width=6, bd=0,
                  command=lambda: secim_yap(False)).pack(side=tk.RIGHT, padx=5)
        self.root.wait_window(onay_penceresi)
        return self.onay_sonuc

    # ─────────────────────────────────────────
    # 🧠 ANA CEVAP ÜRETİCİ
    # ─────────────────────────────────────────
    def jarvis_cevap_uret(self, istek):
        global client, sohbet_gecmisi
        il = istek.lower()

        # ── KAYDET ──
        if "kaydet" in il:
            dosya_yolu = os.path.join(DOKUMAN_YOLU, "hafiza.txt")
            temiz = il.replace("kaydet", "").strip()
            with open(dosya_yolu, "a", encoding="utf-8") as f:
                f.write(temiz + "\n")
                f.flush()
            sesli_konus("Not aldım efendim.", self.log_yaz)
            return

        # ── KAPAT ──
        if any(x in il for x in ["iptal", "exit", "kapat"]):
            if self.modern_onay_kutusu("Onay", "Kapatılsın mı?"):
                sesli_konus("Görüşürüz efendim.", self.log_yaz)
                time.sleep(1.5)
                os._exit(0)
            else:
                self.log_yaz("⚙️ İptal edildi.")
                return

        # ── SAAT ──
        if any(x in il for x in ["saat kaç", "saat nedir", "şu an saat"]):
            sesli_konus(f"Şu an saat {saati_ogren()}, efendim.", self.log_yaz)
            return

        # ── TARİH ──
        if any(x in il for x in ["bugün tarih", "tarih nedir", "hangi tarih", "bugün kaçı"]):
            sesli_konus(f"Bugün {tarihi_ogren()}, efendim.", self.log_yaz)
            return

        # ── GÜN ──
        if any(x in il for x in ["günlerden ne", "bugün ne günü", "hangi gün"]):
            sesli_konus(f"Bugün günlerden {gunu_ogren()}, efendim.", self.log_yaz)
            return

        # ── YIL ──
        if any(x in il for x in ["yıl kaç", "kaçıncı yıl", "hangi yıl"]):
            sesli_konus(f"Şu an {yili_ogren()} yılındayız efendim.", self.log_yaz)
            return

        # ── SİSTEM ──
        if any(x in il for x in ["durumun nasıl", "sistem durumu", "cpu", "işlemci", "ram durumu", "bellek"]):
            sesli_konus(sistem_durumu_ogren(), self.log_yaz)
            return

        # ── HAVA ──
        if any(x in il for x in ["hava durumu", "hava nasıl", "kaç derece", "sıcaklık"]):
            temiz = il
            for k in ["hava durumu", "hava nasıl", "kaç derece", "sıcaklık", "için", " da ", " de "]:
                temiz = temiz.replace(k, " ")
            parcalar = [p for p in temiz.split() if len(p) > 1]
            if not parcalar:
                sesli_konus("Hangi şehrin hava durumunu öğrenmek istersiniz efendim?", self.log_yaz)
                return
            sehir = parcalar[-1].strip()
            self.log_yaz(f"🌤️ {sehir} için hava sorgulanıyor...")
            sesli_konus(hava_durumu_ogren(sehir), self.log_yaz)
            return

        # ── EKRAN ──
        if any(x in il for x in ["ekrana bak", "ekranı yorumla", "ekranda ne var", "ne görüyorsun", "bilgisayara bak"]):
            self.log_yaz("📸 Ekran analiz ediliyor...")
            sesli_konus(ekrani_yorumla(self.log_yaz), self.log_yaz)
            return

        # ── WEB ARA ──
        if any(x in il for x in ["ara", "araştır", "bul", "haber", "son dakika", "nedir", "kimdir"]):
            self.log_yaz(f"🌐 Aranıyor: {istek}")
            sesli_konus("Arıyorum efendim.", self.log_yaz)
            sonuc = web_ara(istek)
            sesli_konus(sonuc[:350], self.log_yaz)
            return

        # ── GROQ AI ──
        sohbet_gecmisi.append({"role": "user", "content": istek})
        if len(sohbet_gecmisi) > 80:
            sohbet_gecmisi.pop(0)

        bilgi = hafizayi_oku()
        sistem_talimati = f"{SYSTEM_INSTRUCTION}\nKullanıcı hakkında bilgiler: {bilgi}"
        messages = [{"role": "system", "content": sistem_talimati}] + sohbet_gecmisi[-40:]

        try:
            chat_completion = client.chat.completions.create(
                messages=messages,
                model="llama-3.3-70b-versatile",
                temperature=0.3,
                max_tokens=150
            )
            cevap = chat_completion.choices[0].message.content
            sohbet_gecmisi.append({"role": "assistant", "content": cevap})
            sesli_konus(cevap, self.log_yaz)
        except Exception as e:
            self.log_yaz(f"❌ Hata: {e}")

    def jarvis_ana_dongu(self):
        global mikrofon_aktif, secilen_mikrofon_id
        r = sr.Recognizer()
        r.dynamic_energy_threshold = True
        r.energy_threshold = 1750
        r.pause_threshold = 1.2
        r.non_speaking_duration = 0.5

        self.root.after(800, lambda: sesli_konus("Jarvis hazır efendim.", self.log_yaz))

        while self.running:
            if not mikrofon_aktif or secilen_mikrofon_id is None:
                time.sleep(0.3)
                continue

            with sr.Microphone(device_index=secilen_mikrofon_id) as source:
                r.adjust_for_ambient_noise(source, duration=0.4)
                try:
                    audio = r.listen(source, timeout=4, phrase_time_limit=10)
                except sr.WaitTimeoutError:
                    continue

            if not mikrofon_aktif:
                continue

            try:
                istek = r.recognize_google(audio, language="tr-TR")
                if istek.strip() and len(istek.strip()) >= 4:
                    self.log_yaz(f"🗣️ Sen: {istek}")
                    self.jarvis_cevap_uret(istek)
            except sr.UnknownValueError:
                pass
            except Exception as e:
                self.log_yaz(f"⚠️ Hata: {e}")


if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = JarvisMinimalHUD(root)
        root.mainloop()
    except Exception as e:
        print(f"Hata çıktı kanka: {e}")
        input()
