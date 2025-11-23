import json
import time
from datetime import datetime, timedelta, date
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
import customtkinter as ctk
from ttkthemes import ThemedTk
import platform
import logging
import winsound
from tkcalendar import Calendar, DateEntry

# Logging ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# JSON dosya adları
GUBRELEME_DATA_FILE = "gubreleme_data.json"
ILACLAMA_DATA_FILE = "ilaclama_data.json"
GENEL_AYARLAR_FILE = "genel_ayarlar.json"

# Sabitler
HAVA_DURUMU_PARAMETRELERI = ["Sıcaklık", "Hava Durumu", "Yağmur", "Nem", "Rüzgar Hızı", "Rakım", "Gün Doğumu", "Gün Batımı"]

# Renk paleti
COLOR_PRIMARY = "#388E3C"
COLOR_SECONDARY = "#66BB6A"
COLOR_ACCENT = "#FFC107"
COLOR_BACKGROUND = "#F0F4C3"
COLOR_TEXT = "#212121"
COLOR_TEXT_SECONDARY = "#757575"
COLOR_ERROR = "#B00020"

FONT_SIZE_NORMAL = 14
FONT_SIZE_LARGE = 18
FONT_SIZE_TITLE = 24

# FONT_FAMILY'yi TarimTakipApp içinde tanımlıyoruz.


def load_data(filename, default_value):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        logging.info(f"{filename} bulunamadı, varsayılan değerler kullanılıyor ve dosya oluşturuluyor.")
        save_data(filename, default_value)
        return default_value
    except json.JSONDecodeError:
        logging.error(f"{filename} dosyasında geçersiz JSON formatı.  Dosya sıfırlanıyor.")
        save_data(filename, default_value)
        return default_value


def save_data(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"{filename} dosyasına yazarken hata: {e}")
        messagebox.showerror("Hata", f"{filename} dosyasına yazarken hata oluştu: {e}")

def load_gubreleme_data():
    return load_data(GUBRELEME_DATA_FILE, {"son_gubreleme": None, "gubre_araligi": 30})

def save_gubreleme_data(data):
    save_data(GUBRELEME_DATA_FILE, data)

def load_ilaclama_data():
    return load_data(ILACLAMA_DATA_FILE, {"son_ilaclama": None, "ilac_araligi": 15})

def save_ilaclama_data(data):
    save_data(ILACLAMA_DATA_FILE, data)


def load_genel_ayarlar():
    default_ayarlar = {
        "hava_durumu": {},
        "secilen_hava_durumu": [],
        "il": "İstanbul",
        "ilce": "Kadıköy",
        "hatirlaticilar": {parametre: [] for parametre in HAVA_DURUMU_PARAMETRELERI}
    }
    ayarlar = load_data(GENEL_AYARLAR_FILE, default_ayarlar)

    for parametre in HAVA_DURUMU_PARAMETRELERI:
        ayarlar["hatirlaticilar"].setdefault(parametre, [])
    return ayarlar


def save_genel_ayarlar(data):
    save_data(GENEL_AYARLAR_FILE, data)

def play_notification_sound():
    if platform.system() == "Windows":
        try:
            winsound.PlaySound("SystemExclamation", winsound.SND_ASYNC)
        except Exception as e:
            logging.error(f"Ses çalma hatası: {e}")


class TarimTakipApp(ThemedTk):
    def __init__(self):
        super().__init__(theme="arc")
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("green")

        self.title("Gübreleme ve İlaçlama Takip Sistemi")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.geometry("400x700")
        self.resizable(False, False)

        global FONT_FAMILY
        FONT_FAMILY = ctk.CTkFont().cget("family")


        self.gubreleme_data = load_gubreleme_data()
        self.ilaclama_data = load_ilaclama_data()
        self.genel_ayarlar = load_genel_ayarlar()

        self.stop_thread = threading.Event()
        self.driver = None
        self.last_fetch_time = 0
        self.fetching_weather = False

        self.create_widgets()
        self.guncelle_ve_goster_hava_durumu()
        self.after(60000, self.periyodik_guncelleme)

    def start_webdriver(self):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")
        options.add_argument('--disable-dev-shm-usage')

        try:
            driver = webdriver.Chrome(options=options)
            return driver
        except WebDriverException as e:
            logging.error(f"Web sürücüsü başlatma hatası: {e}")
            messagebox.showerror("Hata", f"Web sürücüsü başlatılamadı: {e}. Chrome ve ChromeDriver'ın uyumlu olduğundan emin olun.")
            return None
        except Exception as e:
            logging.error(f"Web sürücüsü başlatma hatası (bilinmeyen): {e}")
            messagebox.showerror("Hata", f"Web sürücüsü başlatılırken bilinmeyen bir hata oluştu: {e}")
            return None

    def create_widgets(self):
        self.main_frame = ctk.CTkFrame(self, fg_color=COLOR_BACKGROUND)
        self.main_frame.pack(fill="both", expand=True)

        self.create_top_frame()
        self.create_tabs()
        self.create_weather_tab_content()
        self.create_reminders_tab_content()
        self.create_actions_tab_content()
        self.create_calendar_tab_content()
        self.create_settings_tab_content()

    def create_top_frame(self):
        self.top_frame = ctk.CTkFrame(self.main_frame, fg_color=COLOR_PRIMARY)
        self.top_frame.pack(fill="x")

        self.title_label = ctk.CTkLabel(self.top_frame, text="Tarım Takip", font=(FONT_FAMILY, FONT_SIZE_TITLE), text_color="white")
        self.title_label.pack(pady=10)

        self.location_frame = ctk.CTkFrame(self.top_frame, fg_color=COLOR_PRIMARY)
        self.location_frame.pack(pady=(0, 10), padx=10)

        self.il_label = ctk.CTkLabel(self.location_frame, text="İl:", font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color="white", anchor="w")
        self.il_label.grid(row=0, column=0, padx=(0, 5), sticky="w")

        self.il_entry = ctk.CTkEntry(self.location_frame, font=(FONT_FAMILY, FONT_SIZE_NORMAL), corner_radius=8, border_width=0, width=100)
        self.il_entry.grid(row=0, column=1, padx=5)
        self.il_entry.insert(0, self.genel_ayarlar.get("il", "İstanbul"))

        self.ilce_label = ctk.CTkLabel(self.location_frame, text="İlçe:", font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color="white", anchor="w")
        self.ilce_label.grid(row=0, column=2, padx=(5, 0), sticky="w")
        self.ilce_entry = ctk.CTkEntry(self.location_frame, font=(FONT_FAMILY, FONT_SIZE_NORMAL), corner_radius=8, border_width=0, width=100)
        self.ilce_entry.grid(row=0, column=3, padx=(5, 0))
        self.ilce_entry.insert(0, self.genel_ayarlar.get("ilce", "Kadıköy"))

        self.kaydet_konum_button = ctk.CTkButton(self.location_frame, text="Kaydet", command=self.kaydet_konum,
                                                  font=(FONT_FAMILY, FONT_SIZE_NORMAL), corner_radius=8,
                                                  fg_color=COLOR_SECONDARY, hover_color=COLOR_ACCENT,
                                                  text_color="white", width=80)
        self.kaydet_konum_button.grid(row=0, column=4, padx=10)

    def create_tabs(self):
        self.tabview = ctk.CTkTabview(self.main_frame,
                                      segmented_button_fg_color=COLOR_PRIMARY,
                                      segmented_button_selected_color=COLOR_SECONDARY,
                                      segmented_button_selected_hover_color=COLOR_ACCENT,
                                      segmented_button_unselected_hover_color=COLOR_PRIMARY)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tabview.add("Hava Durumu")
        self.tabview.add("Hatırlatıcılar")
        self.tabview.add("İşlemler")
        self.tabview.add("Takvim")
        self.tabview.add("Ayarlar")
        self.tabview.set("Hava Durumu")


    def create_weather_tab_content(self):
        self.hava_durumu_frame = ctk.CTkScrollableFrame(self.tabview.tab("Hava Durumu"), fg_color=COLOR_BACKGROUND)
        self.hava_durumu_frame.pack(fill="both", expand=True)

        self.hava_durumu_labels = {}
        for secenek in HAVA_DURUMU_PARAMETRELERI:
            frame = ctk.CTkFrame(self.hava_durumu_frame, fg_color="transparent")
            frame.pack(fill="x", padx=10, pady=5)

            label_text = ctk.CTkLabel(frame, text=f"{secenek}:", font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=COLOR_TEXT, anchor="w")
            label_text.pack(side="left")
            label_value = ctk.CTkLabel(frame, text="", font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=COLOR_TEXT, anchor="w")
            label_value.pack(side="left")
            self.hava_durumu_labels[secenek] = label_value

        self.hava_durumu_secenek_combo = ctk.CTkComboBox(self.tabview.tab("Hava Durumu"), values=HAVA_DURUMU_PARAMETRELERI, command=self.on_combobox_select, font=(FONT_FAMILY, FONT_SIZE_NORMAL), corner_radius=8)
        self.hava_durumu_secenek_combo.pack(fill="x", padx=10, pady=(5, 0))

        self.guncelle_button = ctk.CTkButton(self.tabview.tab("Hava Durumu"), text="Güncelle", command=self.guncelle_ve_goster_hava_durumu, font=(FONT_FAMILY, FONT_SIZE_NORMAL), corner_radius=8, fg_color=COLOR_SECONDARY, hover_color=COLOR_ACCENT, text_color="white")
        self.guncelle_button.pack(pady=10)

    def create_reminders_tab_content(self):
        self.hatirlatici_frame = ctk.CTkFrame(self.tabview.tab("Hatırlatıcılar"), fg_color=COLOR_BACKGROUND)
        self.hatirlatici_frame.pack(fill="both", expand=True)

        ctk.CTkLabel(self.hatirlatici_frame, text="Hava Olayı:", font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=COLOR_TEXT, anchor="w").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 2))
        self.hatirlatici_parametre_combo = ctk.CTkComboBox(self.hatirlatici_frame, values=HAVA_DURUMU_PARAMETRELERI, command=self.hatirlatici_parametre_secildi, font=(FONT_FAMILY, FONT_SIZE_NORMAL), corner_radius=8)
        self.hatirlatici_parametre_combo.grid(row=0, column=1, sticky="ew", padx=10, pady=(10, 2))

        ctk.CTkLabel(self.hatirlatici_frame, text="Tip:", font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=COLOR_TEXT, anchor="w").grid(row=1, column=0, sticky="w", padx=10, pady=2)
        self.hatirlatici_tip_combo = ctk.CTkComboBox(self.hatirlatici_frame, values=["altinda", "ustunde", "esit"], font=(FONT_FAMILY, FONT_SIZE_NORMAL), corner_radius=8)
        self.hatirlatici_tip_combo.grid(row=1, column=1, sticky="ew", padx=10, pady=2)

        ctk.CTkLabel(self.hatirlatici_frame, text="Değer:", font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=COLOR_TEXT, anchor="w").grid(row=2, column=0, sticky="w", padx=10, pady=2)
        self.hatirlatici_deger_entry = ctk.CTkEntry(self.hatirlatici_frame, font=(FONT_FAMILY, FONT_SIZE_NORMAL), corner_radius=8)
        self.hatirlatici_deger_entry.grid(row=2, column=1, sticky="ew", padx=10, pady=2)

        ctk.CTkLabel(self.hatirlatici_frame, text="Tekrarlama:", font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=COLOR_TEXT, anchor="w").grid(row=3, column=0, sticky="w", padx=10, pady=2)
        self.hatirlatici_tekrar_combo = ctk.CTkComboBox(self.hatirlatici_frame, values=["Bir Kez", "Günlük", "Haftalık", "Aylık"], font=(FONT_FAMILY, FONT_SIZE_NORMAL), corner_radius=8)
        self.hatirlatici_tekrar_combo.grid(row=3, column=1, sticky="ew", padx=10, pady=2)
        self.hatirlatici_tekrar_combo.set("Bir Kez")

        # Tarih ve saat ile ilgili kısımlar kaldırıldı

        self.hatirlatici_aktif_var = tk.BooleanVar()
        self.hatirlatici_aktif_switch = ctk.CTkSwitch(self.hatirlatici_frame, text="Aktif", variable=self.hatirlatici_aktif_var, onvalue=True, offvalue=False, font=(FONT_FAMILY, FONT_SIZE_NORMAL), corner_radius=8)
        self.hatirlatici_aktif_switch.grid(row=4, column=0, columnspan=2, padx=10, pady=10)

        self.hatirlatici_ekle_button = ctk.CTkButton(self.hatirlatici_frame, text="Ekle/Güncelle", command=self.hatirlatici_ekle_guncelle, font=(FONT_FAMILY, FONT_SIZE_NORMAL), corner_radius=8, fg_color=COLOR_SECONDARY, hover_color=COLOR_ACCENT, text_color="white")
        self.hatirlatici_ekle_button.grid(row=5, column=0, columnspan=2, sticky="ew", padx=10, pady=5)

        self.hatirlatici_listbox = tk.Listbox(self.hatirlatici_frame, height=5, width=30, bg=COLOR_BACKGROUND, fg=COLOR_TEXT, selectbackground=COLOR_SECONDARY, font=(FONT_FAMILY, FONT_SIZE_NORMAL))
        self.hatirlatici_listbox.grid(row=6, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        self.hatirlatici_listbox.bind("<<ListboxSelect>>", self.hatirlatici_secim_degisti)

        self.hatirlatici_sil_button = ctk.CTkButton(self.hatirlatici_frame, text="Sil", command=self.hatirlatici_sil, state=tk.DISABLED, font=(FONT_FAMILY, FONT_SIZE_NORMAL), corner_radius=8, fg_color=COLOR_SECONDARY, hover_color=COLOR_ACCENT, text_color="white")
        self.hatirlatici_sil_button.grid(row=7, column=0, columnspan=2, sticky="ew", padx=10, pady=5)


    def create_actions_tab_content(self):
        self.islemler_frame = ctk.CTkFrame(self.tabview.tab("İşlemler"), fg_color=COLOR_BACKGROUND)
        self.islemler_frame.pack(fill="both", expand=True)

        self.gubreleme_frame = ctk.CTkFrame(self.islemler_frame, fg_color="transparent")
        self.gubreleme_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(self.gubreleme_frame, text="Gübreleme:", font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=COLOR_TEXT, anchor="w").pack(side="left", padx=5)
        self.gubreleme_var = tk.BooleanVar()
        self.gubreleme_switch = ctk.CTkSwitch(self.gubreleme_frame, text="", variable=self.gubreleme_var, onvalue=True, offvalue=False, font=(FONT_FAMILY, FONT_SIZE_NORMAL), corner_radius=8)
        self.gubreleme_switch.pack(side="right", padx=5)

        self.ilaclama_frame = ctk.CTkFrame(self.islemler_frame, fg_color="transparent")
        self.ilaclama_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(self.ilaclama_frame, text="İlaçlama:", font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=COLOR_TEXT, anchor="w").pack(side="left", padx=5)
        self.ilaclama_var = tk.BooleanVar()
        self.ilaclama_switch = ctk.CTkSwitch(self.ilaclama_frame, text="", variable=self.ilaclama_var, onvalue=True, offvalue=False, font=(FONT_FAMILY, FONT_SIZE_NORMAL), corner_radius=8)
        self.ilaclama_switch.pack(side="right", padx=5)

        self.kaydet_button = ctk.CTkButton(self.islemler_frame, text="Kaydet", command=self.kaydet, font=(FONT_FAMILY, FONT_SIZE_NORMAL), corner_radius=8, fg_color=COLOR_SECONDARY, hover_color=COLOR_ACCENT, text_color="white")
        self.kaydet_button.pack(fill="x", padx=10, pady=10)

        self.kalan_sure_label = ctk.CTkLabel(self.islemler_frame, text=self.kalan_gun_hesapla(), font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=COLOR_TEXT, anchor="w", justify="left")
        self.kalan_sure_label.pack(fill="x", padx=10, pady=5)

    def create_calendar_tab_content(self):
        self.takvim_frame = ctk.CTkFrame(self.tabview.tab("Takvim"), fg_color=COLOR_BACKGROUND)
        self.takvim_frame.pack(fill="both", expand=True)

        self.takvim = Calendar(self.takvim_frame, selectmode="day", locale="tr_TR",
                                date_pattern='y-m-d',
                                background=COLOR_PRIMARY, foreground="white",
                                bordercolor=COLOR_BACKGROUND, headersbackground=COLOR_BACKGROUND,
                                headersforeground=COLOR_TEXT, normalbackground=COLOR_BACKGROUND,
                                normalforeground=COLOR_TEXT, selectbackground=COLOR_SECONDARY,
                                selectforeground="white",
                                font=(FONT_FAMILY, FONT_SIZE_NORMAL))

        self.takvim.pack(fill="both", expand=True, padx=10, pady=10)
        self.takvim.bind("<<CalendarSelected>>", self.takvim_tarih_secildi)

        self.takvim_bilgi_label = ctk.CTkLabel(self.takvim_frame, text="", font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=COLOR_TEXT)
        self.takvim_bilgi_label.pack(pady=5)

        self.update_calendar_markings()

    def create_settings_tab_content(self):
        self.ayarlar_frame = ctk.CTkFrame(self.tabview.tab("Ayarlar"), fg_color=COLOR_BACKGROUND)
        self.ayarlar_frame.pack(fill="both", expand=True)

        self.yedekle_button = ctk.CTkButton(self.ayarlar_frame, text="Verileri Yedekle", command=self.yedekle, font=(FONT_FAMILY, FONT_SIZE_NORMAL), corner_radius=8, fg_color=COLOR_SECONDARY, hover_color=COLOR_ACCENT, text_color="white")
        self.yedekle_button.pack(pady=10)

        self.geri_yukle_button = ctk.CTkButton(self.ayarlar_frame, text="Verileri Geri Yükle", command=self.geri_yukle, font=(FONT_FAMILY, FONT_SIZE_NORMAL), corner_radius=8, fg_color=COLOR_SECONDARY, hover_color=COLOR_ACCENT, text_color="white")
        self.geri_yukle_button.pack(pady=10)



    def fetch_weather_data(self):
        il = self.il_entry.get().strip()
        ilce = self.ilce_entry.get().strip()

        if not il or not ilce:
            messagebox.showerror("Hata", "Lütfen şehir ve ilçe bilgilerini girin.")
            return {}

        url = f"https://www.mgm.gov.tr/tahmin/il-ve-ilceler.aspx?il={il}&ilce={ilce}"
        logging.info(f"Hava durumu verisi çekiliyor: {url}")

        try:
            if self.driver is None:
                self.driver = self.start_webdriver()
                if self.driver is None:
                    return {}

            if self.driver.current_url != url:
                self.driver.get(url)

            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "anlik-sicaklik-deger")))

            def get_text(class_name):
                try:
                    return self.driver.find_element(By.CLASS_NAME, class_name).text.strip()
                except NoSuchElementException:
                    logging.warning(f"Element bulunamadı: {class_name}")
                    return "Veri Yok"

            sicaklik = get_text("anlik-sicaklik-deger")
            hava_durumu = get_text("anlik-sicaklik-havadurumu-ikonismi")
            yagmur = get_text("anlik-yagis-deger-kac")
            nem = get_text("anlik-nem-deger-kac")
            ruzgar_hizi = get_text("anlik-ruzgar-deger-kac")

            try:
                rakim_element = self.driver.find_element(By.CLASS_NAME, "rakim-bilgisi")
                rakim = rakim_element.find_element(By.XPATH, ".//span[@class='ng-binding']").text.strip()
            except NoSuchElementException:
                rakim = "Veri Yok"
                logging.warning("Rakım elementi bulunamadı.")

            try:
                gun_dogumu_element = self.driver.find_elements(By.CLASS_NAME, "rakim-sonrasi-bilgisi")[2]
                gun_dogumu = gun_dogumu_element.find_element(By.XPATH, ".//span[@class='ng-binding']").text.strip()

                gun_batimi_element = self.driver.find_elements(By.CLASS_NAME, "rakim-sonrasi-bilgisi")[3]
                gun_batimi = gun_batimi_element.find_element(By.XPATH, ".//span[@class='ng-binding']").text.strip()
            except (NoSuchElementException, IndexError):
                gun_dogumu = "Veri Yok"
                gun_batimi = "Veri Yok"
                logging.warning("Gün doğumu/batımı elementleri bulunamadı.")


            weather_data = {
                "Sıcaklık": f"{sicaklik}°C",
                "Hava Durumu": hava_durumu,
                "Yağmur": f"{yagmur} mm",
                "Nem": f"{nem} %",
                "Rüzgar Hızı": f"{ruzgar_hizi} km/sa",
                "Rakım": f"{rakim} m",
                "Gün Doğumu": gun_dogumu,
                "Gün Batımı": gun_batimi,
            }
            logging.info(f"Hava durumu verisi alındı: {weather_data}")
            return weather_data

        except (NoSuchElementException, TimeoutException) as e:
            logging.error(f"Hava durumu verileri alınırken element bulunamadı veya zaman aşımı: {e}")
            messagebox.showerror("Hata", f"Hava durumu verileri alınamadı: {e}\nİnternet bağlantınızı kontrol edin veya daha sonra tekrar deneyin.")
            return {}
        except WebDriverException as e:
            logging.error(f"WebDriver hatası: {e}")
            messagebox.showerror("Hata", f"Web sürücüsü ile ilgili bir hata oluştu: {e}")
            self.driver = None
            return {}
        except Exception as e:
            logging.error(f"Bilinmeyen hata: {e}")
            messagebox.showerror("Hata", f"Bilinmeyen bir hata oluştu: {e}")
            return {}


    def guncelle_ve_goster_hava_durumu(self):
        if self.fetching_weather:
            return

        self.fetching_weather = True
        self.guncelle_button.configure(text="Güncelleniyor...", state="disabled")

        def update_ui():
            hava_durumu = self.genel_ayarlar["hava_durumu"]

            for parametre in HAVA_DURUMU_PARAMETRELERI:
                if parametre in self.genel_ayarlar["secilen_hava_durumu"]:
                    self.hava_durumu_labels[parametre].configure(text=hava_durumu.get(parametre, "Veri Yok"))
                else:
                    self.hava_durumu_labels[parametre].configure(text="")

            self.hava_durumu_kontrol()
            self.fetching_weather = False
            self.guncelle_button.configure(text="Güncelle", state="normal")

        def fetch_data_thread():
            current_time = time.time()
            if current_time - self.last_fetch_time >= 60:
                hava_durumu = self.fetch_weather_data()
                if hava_durumu:
                    self.genel_ayarlar["hava_durumu"] = hava_durumu
                    save_genel_ayarlar(self.genel_ayarlar)
                    self.last_fetch_time = current_time
            self.after(0, update_ui)

        threading.Thread(target=fetch_data_thread, daemon=True).start()


    def on_combobox_select(self, event=None):
        selected_option = self.hava_durumu_secenek_combo.get()
        if selected_option:
            if selected_option not in self.genel_ayarlar["secilen_hava_durumu"]:
                self.genel_ayarlar["secilen_hava_durumu"].append(selected_option)
            else:
                self.genel_ayarlar["secilen_hava_durumu"].remove(selected_option)

            save_genel_ayarlar(self.genel_ayarlar)
            self.guncelle_ve_goster_hava_durumu()


    def periyodik_guncelleme(self):
        def thread_target():
             if not self.stop_thread.is_set():
                self.guncelle_ve_goster_hava_durumu()
                self.after(60000, self.periyodik_guncelleme)

        if self.driver or True:
            threading.Thread(target=thread_target, daemon=True).start()


    def on_closing(self):
        self.stop_thread.set()
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logging.error(f"WebDriver kapatılırken hata: {e}")
        self.destroy()

    def kaydet_konum(self):
        self.genel_ayarlar["il"] = self.il_entry.get().strip()
        self.genel_ayarlar["ilce"] = self.ilce_entry.get().strip()

        if not self.genel_ayarlar["il"] or not self.genel_ayarlar["ilce"]:
            messagebox.showerror("Hata", "Lütfen hem il hem de ilçe bilgisini girin.")
            return

        save_genel_ayarlar(self.genel_ayarlar)
        messagebox.showinfo("Başarılı", "Konum bilgisi kaydedildi!")
        self.guncelle_ve_goster_hava_durumu()


    def kaydet(self):
        if self.gubreleme_var.get():
            self.gubreleme_data["son_gubreleme"] = datetime.now().strftime("%Y-%m-%d")
            save_gubreleme_data(self.gubreleme_data)

        if self.ilaclama_var.get():
            self.ilaclama_data["son_ilaclama"] = datetime.now().strftime("%Y-%m-%d")
            save_ilaclama_data(self.ilaclama_data)

        messagebox.showinfo("Başarılı", "Veriler kaydedildi!")
        self.kalan_sure_label.configure(text=self.kalan_gun_hesapla())
        self.update_calendar_markings() # Takvimi güncelle


    def kalan_gun_hesapla(self):
        son_gubreleme = self.gubreleme_data.get("son_gubreleme")
        son_ilaclama = self.ilaclama_data.get("son_ilaclama")

        gubre_text = "Gübreleme bilgisi bulunmuyor."
        ilac_text = "İlaçlama bilgisi bulunmuyor."

        if son_gubreleme:
            son_tarih = datetime.strptime(son_gubreleme, "%Y-%m-%d")
            kalan_gun = (son_tarih + timedelta(days=self.gubreleme_data["gubre_araligi"])) - datetime.now()
            gubre_text = f"Bir sonraki gübreleme: {max(0, kalan_gun.days)} gün sonra."

        if son_ilaclama:
            son_tarih = datetime.strptime(son_ilaclama, "%Y-%m-%d")
            kalan_gun = (son_tarih + timedelta(days=self.ilaclama_data["ilac_araligi"])) - datetime.now()
            ilac_text = f"Bir sonraki ilaçlama: {max(0, kalan_gun.days)} gün sonra."

        return f"{gubre_text}\n{ilac_text}"

    def hatirlatici_parametre_secildi(self, event=None):
        parametre = self.hatirlatici_parametre_combo.get()
        if parametre:
            self.hatirlatici_listbox_guncelle(parametre)
            self.hatirlatici_yukle(parametre)

    def hatirlatici_listbox_guncelle(self, parametre):
        self.hatirlatici_listbox.delete(0, tk.END)
        for hatirlatici in self.genel_ayarlar["hatirlaticilar"].get(parametre, []):
            aktif_str = "Aktif" if hatirlatici["aktif"] else "Pasif"
            tekrar_str = hatirlatici.get("tekrar", "Bir Kez")
            self.hatirlatici_listbox.insert(tk.END, f"{parametre}: {hatirlatici['tip']} {hatirlatici['deger']} ({aktif_str}) ({tekrar_str})")

    def hatirlatici_yukle(self, parametre):
        self.hatirlatici_tip_combo.set("")
        self.hatirlatici_deger_entry.delete(0, tk.END)
        self.hatirlatici_aktif_var.set(False)
        self.hatirlatici_sil_button.configure(state=tk.DISABLED)
        self.hatirlatici_tekrar_combo.set("Bir Kez")


    def hatirlatici_ekle_guncelle(self):
        parametre = self.hatirlatici_parametre_combo.get()
        tip = self.hatirlatici_tip_combo.get()
        deger_str = self.hatirlatici_deger_entry.get()
        aktif = self.hatirlatici_aktif_var.get()
        tekrar = self.hatirlatici_tekrar_combo.get()

        if not parametre or not tip or not deger_str or not tekrar:
            return

        try:
            deger = float(deger_str)
        except ValueError:
            return

        yeni_hatirlatici = {"tip": tip, "deger": deger, "aktif": aktif, "tekrar": tekrar}
        index = self.hatirlatici_listbox.curselection()

        if len(index) > 0:
            index = index[0]
            self.genel_ayarlar["hatirlaticilar"][parametre][index] = yeni_hatirlatici
            self.hatirlatici_ekle_button.configure(text="Ekle/Güncelle")
        else:
            self.genel_ayarlar["hatirlaticilar"][parametre].append(yeni_hatirlatici)

        save_genel_ayarlar(self.genel_ayarlar)
        self.hatirlatici_listbox_guncelle(parametre)
        messagebox.showinfo("Başarılı", "Hatırlatıcı kaydedildi!")
        self.hatirlatici_yukle(parametre)

    def hatirlatici_secim_degisti(self, event=None):
        index = self.hatirlatici_listbox.curselection()
        parametre = self.hatirlatici_parametre_combo.get()
        if len(index) > 0 and parametre:
            index = index[0]
            hatirlatici = self.genel_ayarlar["hatirlaticilar"][parametre][index]
            self.hatirlatici_tip_combo.set(hatirlatici["tip"])
            self.hatirlatici_deger_entry.delete(0, tk.END)
            self.hatirlatici_deger_entry.insert(0, str(hatirlatici["deger"]))
            self.hatirlatici_aktif_var.set(hatirlatici["aktif"])
            self.hatirlatici_tekrar_combo.set(hatirlatici.get("tekrar", "Bir Kez"))

            self.hatirlatici_sil_button.configure(state=tk.NORMAL)
            self.hatirlatici_ekle_button.configure(text="Güncelle")
        else:
            self.hatirlatici_sil_button.configure(state=tk.DISABLED)
            self.hatirlatici_ekle_button.configure(text="Ekle/Güncelle")

    def hatirlatici_sil_index(self, parametre, index):
        try:
            del self.genel_ayarlar["hatirlaticilar"][parametre][index]
            save_genel_ayarlar(self.genel_ayarlar)

            if self.hatirlatici_parametre_combo.get() == parametre:
                self.hatirlatici_listbox_guncelle(parametre)
                self.hatirlatici_yukle(parametre)

        except (KeyError, IndexError) as e:
            logging.error(f"Hata: Hatırlatıcı silinirken hata oluştu: {e}")
            messagebox.showerror("Hata", "Hatırlatıcı silinirken bir hata oluştu.")

    def hatirlatici_sil(self):
        index = self.hatirlatici_listbox.curselection()
        parametre = self.hatirlatici_parametre_combo.get()
        if len(index) > 0 and parametre:
            index = index[0]
            self.hatirlatici_sil_index(parametre, index)
            messagebox.showinfo("Başarılı", "Hatırlatıcı silindi!")


    def check_single_reminders(self, parametre, parametre_deger, hatirlatici):
        if hatirlatici["tip"] == "altinda" and parametre_deger < hatirlatici["deger"]:
            return f"{parametre} değeri {hatirlatici['deger']} değerinin altında! (Şu anki {parametre}: {self.genel_ayarlar['hava_durumu'][parametre]})"
        elif hatirlatici["tip"] == "ustunde" and parametre_deger > hatirlatici["deger"]:
            return f"{parametre} değeri {hatirlatici['deger']} değerinin üstünde! (Şu anki {parametre}: {self.genel_ayarlar['hava_durumu'][parametre]})"
        elif hatirlatici["tip"] == "esit" and parametre_deger == hatirlatici["deger"]:
            return f"{parametre} değeri {hatirlatici['deger']} değerine eşit! (Şu anki {parametre}: {self.genel_ayarlar['hava_durumu'][parametre]})"
        return None

    def check_recurring_reminders(self, parametre, parametre_deger, hatirlatici):
        bugun = datetime.now()

        if hatirlatici["tekrar"] == "Günlük":
            return self.check_single_reminders(parametre, parametre_deger, hatirlatici)
        elif hatirlatici["tekrar"] == "Haftalık":
            if bugun.weekday() == 0:  # Pazartesi ise (0: Pazartesi, 6: Pazar)
                return self.check_single_reminders(parametre, parametre_deger, hatirlatici)
        elif hatirlatici["tekrar"] == "Aylık":
            if bugun.day == 1:  # Ayın 1'i ise
                return self.check_single_reminders(parametre, parametre_deger, hatirlatici)
        return None


    def get_parametre_deger(self, parametre):
        hava_durumu = self.genel_ayarlar.get("hava_durumu", {})
        if parametre in ("Hava Durumu", "Gün Doğumu", "Gün Batımı"):
            return hava_durumu[parametre]
        elif parametre == "Rüzgar Hızı":
            return hava_durumu[parametre]
        else:
            #parametre_deger_str = hava_durumu[parametre].split(" ")[0].replace("°C", "").replace("%", "").replace(",", ".")
            return hava_durumu[parametre]


    def hava_durumu_kontrol(self):
        hava_durumu = self.genel_ayarlar.get("hava_durumu", {})
        if not hava_durumu:
            return

        for parametre, hatirlaticilar in self.genel_ayarlar.get("hatirlaticilar", {}).items():
            if parametre not in hava_durumu:
                continue

            try:
                parametre_deger = self.get_parametre_deger(parametre)

                for hatirlatici in hatirlaticilar:
                    if not hatirlatici["aktif"]:
                        continue

                    uyari_mesaji = None

                    if hatirlatici.get("tekrar") == "Bir Kez":
                        uyari_mesaji = self.check_single_reminders(parametre, parametre_deger, hatirlatici)
                    else:
                        uyari_mesaji = self.check_recurring_reminders(parametre, parametre_deger, hatirlatici)

                    if uyari_mesaji:
                        play_notification_sound()
                        cevap = messagebox.askyesnocancel("Hatırlatıcı", f"{uyari_mesaji}\n\nBu hatırlatıcıyı silmek istiyor musunuz?")
                        if cevap is True:
                            try:
                                index = self.genel_ayarlar["hatirlaticilar"][parametre].index(hatirlatici)
                                self.hatirlatici_sil_index(parametre, index)
                            except ValueError:
                                logging.error(f"Silinecek hatırlatıcı listede bulunamadı: {hatirlatici}")
                        elif cevap is False or cevap is None:
                            if hatirlatici.get("tekrar") == "Bir Kez":
                                try:
                                    index = self.genel_ayarlar["hatirlaticilar"][parametre].index(hatirlatici)
                                    self.hatirlatici_sil_index(parametre, index)

                                except ValueError:
                                    logging.error(f"Silinecek/Pasif yapılacak hatırlatıcı listede bulunamadı: {hatirlatici}")

            except (ValueError, TypeError) as e:
                logging.error(f"Hata: {parametre} için hatırlatıcı kontrolünde hata: {e}")
                continue
            except KeyError as e:
                logging.error(f"Hava durumu verisinde eksik anahtar: {e}")
                continue

    def calculate_next_date(self, last_date_str, interval):
        if last_date_str:
            try:
                last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
                next_date = last_date + timedelta(days=interval)
                return next_date
            except ValueError:
                logging.error(f"Geçersiz tarih formatı: {last_date_str}")
                return None
        return None

    def update_calendar_markings(self):
        self.takvim.calevent_remove("all")  # Önceki tüm işaretlemeleri temizle

        # Gübreleme (Geçmiş)
        son_gubreleme_str = self.gubreleme_data.get("son_gubreleme")
        if son_gubreleme_str:
            try:
                son_gubreleme = datetime.strptime(son_gubreleme_str, "%Y-%m-%d").date()
                self.takvim.calevent_create(son_gubreleme, "Gübreleme (Geçmiş)", "gubreleme_gecmis")
            except ValueError:
                logging.error(f"Geçersiz gübreleme tarihi formatı: {son_gubreleme_str}")

        # Gübreleme (Gelecek)
        gubreleme_araligi = self.gubreleme_data.get("gubre_araligi", 30)  # Varsayılan 30
        gelecek_gubreleme = self.calculate_next_date(son_gubreleme_str, gubreleme_araligi)
        if gelecek_gubreleme:
            self.takvim.calevent_create(gelecek_gubreleme, "Gübreleme (Gelecek)", "gubreleme_gelecek")


        # İlaçlama (Geçmiş)
        son_ilaclama_str = self.ilaclama_data.get("son_ilaclama")
        if son_ilaclama_str:
            try:
                son_ilaclama = datetime.strptime(son_ilaclama_str, "%Y-%m-%d").date()
                self.takvim.calevent_create(son_ilaclama, "İlaçlama (Geçmiş)", "ilaclama_gecmis")
            except ValueError:
                 logging.error(f"Geçersiz ilaçlama tarihi formatı: {son_ilaclama_str}")


        # İlaçlama (Gelecek)
        ilaclama_araligi = self.ilaclama_data.get("ilac_araligi", 15) # Varsayılan 15
        gelecek_ilaclama = self.calculate_next_date(son_ilaclama_str, ilaclama_araligi)
        if gelecek_ilaclama:
            self.takvim.calevent_create(gelecek_ilaclama, "İlaçlama (Gelecek)", "ilaclama_gelecek")


        # Stil ayarları (tag_config)
        self.takvim.tag_config("gubreleme_gecmis", background="green", foreground="white")
        self.takvim.tag_config("gubreleme_gelecek", background="lightgreen", foreground="black")
        self.takvim.tag_config("ilaclama_gecmis", background="blue", foreground="white")
        self.takvim.tag_config("ilaclama_gelecek", background="lightblue", foreground="black")


    def takvim_tarih_secildi(self, event=None):
        secilen_tarih_str = self.takvim.get_date()
        secilen_tarih = datetime.strptime(secilen_tarih_str, "%Y-%m-%d").date()

        gubreleme_bilgisi = ""
        ilaclama_bilgisi = ""

        # Gübreleme
        son_gubreleme_str = self.gubreleme_data.get("son_gubreleme")
        if son_gubreleme_str:
            son_gubreleme = datetime.strptime(son_gubreleme_str, "%Y-%m-%d").date()
            if son_gubreleme == secilen_tarih:
                gubreleme_bilgisi = "Gübreleme yapıldı."
            elif self.calculate_next_date(son_gubreleme_str, self.gubreleme_data.get("gubre_araligi", 30)) == secilen_tarih:
                gubreleme_bilgisi = "Sonraki gübreleme tarihi."

        # İlaçlama
        son_ilaclama_str = self.ilaclama_data.get("son_ilaclama")
        if son_ilaclama_str:
            son_ilaclama = datetime.strptime(son_ilaclama_str, "%Y-%m-%d").date()
            if son_ilaclama == secilen_tarih:
                ilaclama_bilgisi = "İlaçlama yapıldı."
            elif self.calculate_next_date(son_ilaclama_str, self.ilaclama_data.get("ilac_araligi", 15)) == secilen_tarih:
                ilaclama_bilgisi = "Sonraki ilaçlama tarihi."

        if not gubreleme_bilgisi and not ilaclama_bilgisi:
            self.takvim_bilgi_label.configure(text="Bu tarihte kayıtlı işlem yok.")
        else:
             self.takvim_bilgi_label.configure(text=f"{gubreleme_bilgisi}\n{ilaclama_bilgisi}")

    def yedekle(self):
        try:
            dosya_yolu = filedialog.askdirectory(title="Yedekleme Klasörünü Seçin")
            if dosya_yolu:
                import shutil
                shutil.copy2(GUBRELEME_DATA_FILE, dosya_yolu)
                shutil.copy2(ILACLAMA_DATA_FILE, dosya_yolu)
                shutil.copy2(GENEL_AYARLAR_FILE, dosya_yolu)
                messagebox.showinfo("Başarılı", "Veriler başarıyla yedeklendi!")

        except Exception as e:
            logging.error(f"Yedekleme hatası: {e}")
            messagebox.showerror("Hata", f"Yedekleme sırasında bir hata oluştu: {e}")

    def geri_yukle(self):
        try:
            dosya_yolu = filedialog.askdirectory(title="Yedekleme Klasörünü Seçin")
            if dosya_yolu:
                import shutil
                shutil.copy2(f"{dosya_yolu}/{GUBRELEME_DATA_FILE}", ".")
                shutil.copy2(f"{dosya_yolu}/{ILACLAMA_DATA_FILE}", ".")
                shutil.copy2(f"{dosya_yolu}/{GENEL_AYARLAR_FILE}", ".")

                self.gubreleme_data = load_gubreleme_data()
                self.ilaclama_data = load_ilaclama_data()
                self.genel_ayarlar = load_genel_ayarlar()

                messagebox.showinfo("Başarılı", "Veriler başarıyla geri yüklendi!")

                self.il_entry.delete(0, tk.END)
                self.il_entry.insert(0, self.genel_ayarlar.get("il", "İstanbul"))
                self.ilce_entry.delete(0, tk.END)
                self.ilce_entry.insert(0, self.genel_ayarlar.get("ilce", "Kadıköy"))
                self.guncelle_ve_goster_hava_durumu()
                self.kalan_sure_label.configure(text=self.kalan_gun_hesapla())
                self.update_calendar_markings()
                if self.hatirlatici_parametre_combo.get():
                    self.hatirlatici_listbox_guncelle(self.hatirlatici_parametre_combo.get())

        except Exception as e:
            logging.error(f"Geri yükleme hatası: {e}")
            messagebox.showerror("Hata", f"Geri yükleme sırasında bir hata oluştu: {e}")


if __name__ == "__main__":
    app = TarimTakipApp()
    app.mainloop()