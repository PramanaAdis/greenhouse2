import time
import threading
import schedule  # <-- 1. IMPORT LIBRARY SCHEDULE
from bot_telegram import TelegramBot
from firebase_connector import FirebaseConnector
import requests
from fuzzy_mamdani import FuzzyMamdani

# Konfigurasi
BOT_TOKEN = "8158211888:AAFC35N85-7QsspxvorzZb75eWD4AwKe8nE"
CHAT_ID = 1099636525
FIREBASE_CRED_PATH = 'greenhouse.json'
FIREBASE_DATABASE_URL = 'https://kondisigreenhouse-default-rtdb.asia-southeast1.firebasedatabase.app/'

# Inisialisasi konektor Firebase dan bot Telegram
firebase_connector = FirebaseConnector(FIREBASE_CRED_PATH, FIREBASE_DATABASE_URL)
telegram_bot = TelegramBot(BOT_TOKEN, CHAT_ID)

# Inisialisasi Fuzzy Mamdani
fuzzy_mamdani = FuzzyMamdani(FIREBASE_CRED_PATH, FIREBASE_DATABASE_URL, BOT_TOKEN, CHAT_ID)

running = False  # Status untuk mengontrol pengiriman data

# 2. DIUBAH: Fungsi ini sekarang hanya untuk mengirim satu laporan, bukan loop
def send_report():
    """
    Mengambil data dari Firebase, menghitung fuzzy, dan mengirim satu laporan ke Telegram.
    """
    print(f"[{time.strftime('%H:%M:%S')}] Menjalankan tugas terjadwal: send_report...")
    data = firebase_connector.get_data('sensor')
    if data:
        suhu_air = data.get('suhu_air', 'Data tidak tersedia')
        ph_air = data.get('ph_air', 'Data tidak tersedia')
        cahaya = data.get('cahaya', 'Data tidak tersedia')
        co2 = data.get('co2', 'Data tidak tersedia')
        suhu_air_val = data.get('suhu_air', 0)
        ph_air_val = data.get('ph_air', 0)
        cahaya_val = data.get('cahaya', 0)
        co2_val = data.get('co2', 0)

        suhu_air_label = fuzzy_mamdani.get_linguistic_label(fuzzy_mamdani.suhu_air, suhu_air_val)
        ph_air_label = fuzzy_mamdani.get_linguistic_label(fuzzy_mamdani.ph_air, ph_air_val)
        cahaya_label = fuzzy_mamdani.get_linguistic_label(fuzzy_mamdani.cahaya, cahaya_val)
        co2_label = fuzzy_mamdani.get_linguistic_label(fuzzy_mamdani.co2, co2_val)

        kondisi = fuzzy_mamdani.calculate_fuzzy()

        if kondisi is not None:
            kondisi_linguistik = fuzzy_mamdani.get_linguistic_condition(kondisi)

            message = (f"KONDISI GREENHOUSE🌳\n"
                       f"=====================\n"
                       f"📅Tanggal : {time.strftime('%d-%m-%Y')}\n" 
                       f"⏱️Jam      : {time.strftime('%H:%M')}\n"
                       f"🌡️Suhu Air  : {suhu_air} °C ({suhu_air_label})\n"
                       f"💧pH Air    : {ph_air} ({ph_air_label})\n"
                       f"💡Cahaya    : {cahaya} % ({cahaya_label})\n"
                       f"🍃CO2       : {co2} ppm ({co2_label})\n"
                       f"=====================\n"
                       f"🧠Nilai Fuzzy: {kondisi:.2f}\n"
                       f"📊Kondisi : {kondisi_linguistik}")

            telegram_bot.send_message(message)
        else:
            telegram_bot.send_message("⚠️ Data fuzzy tidak dapat dihitung.")
    else:
        telegram_bot.send_message("⚠️ Data sensor tidak ditemukan di Firebase.")

# 3. DIUBAH: Fungsi ini sekarang menjadi mesin penjadwal
def scheduler_loop():
    """
    Loop untuk menjalankan tugas yang sudah dijadwalkan.
    """
    global running
    while running:
        schedule.run_pending()
        time.sleep(1) # Cek setiap 1 detik apakah ada tugas yang harus dijalankan

def listen_messages():
    global running
    last_update_id = None
    while True:
        try:
            resp = requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates', params={'offset': last_update_id, 'timeout': 5})
            data = resp.json()
            for result in data['result']:
                last_update_id = result['update_id'] + 1
                if 'message' in result:
                    text = result['message'].get('text', '').strip()
                    if text == "▶️ Start":
                        if not running:
                            running = True
                            
                            # 4. DIUBAH: Atur jadwal pengiriman di sini
                            # Contoh: kirim setiap 2 jam
                            # schedule.every(2).hours.do(send_report)

                            # Contoh: kirim pada jam-jam spesifik setiap hari
                            jadwal_jam = ["07:00", "09:00", "11:00", "13:00", "15:00", "17:00"]
                            for jam in jadwal_jam:
                                schedule.every().day.at(jam).do(send_report)

                            telegram_bot.send_message(f"✅ Bot mulai berjalan. Laporan akan dikirim pada jam: {', '.join(jadwal_jam)}.")
                            # telegram_bot.send_message(f"✅ Bot mulai berjalan. Laporan akan dikirim setiap 2 jam")
                            
                            # Mulai thread baru untuk scheduler_loop
                            threading.Thread(target=scheduler_loop, daemon=True).start()
                        else:
                            telegram_bot.send_message("⚠️ Bot sudah berjalan.")
                    elif text == "🪴Status":
                                send_report()
                    elif text == "⏹ Stop":
                        if running:
                            running = False
                            schedule.clear() # 5. DIUBAH: Hapus semua jadwal saat berhenti
                            telegram_bot.send_message("🛑 Pengiriman dihentikan dan semua jadwal dihapus.")
                        else:
                            telegram_bot.send_message("⚠️ Pengiriman pesan otomatis sudah dalam keadaan berhenti.")
        except Exception as e:
            print(f"Error di listen_messages: {e}")
        time.sleep(2)

# Program Utama
print("Bot Telegram sedang mendengarkan perintah...")
telegram_bot.send_keyboard()
listen_messages()