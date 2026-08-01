import logging
import pandas as pd
import sqlite3
import smtplib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

load_dotenv()


logging.basicConfig(
    filename='banka_etl_sureci.log',
    filemode='a',
    encoding="utf-8",
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')

def veriyi_oku(csv_yolu):
    logging.info(f"{csv_yolu} dosyası okunmaya baslandi")
    df = pd.read_csv(csv_yolu)
    logging.info(f"dosya basariyla okundu {len(df)} satır var")
    return df

def veriyi_temizle(df):
    if df.empty:
        raise ValueError("gelen veri seti bos!!!")

    df_temiz = df.dropna(subset=["Musteri_TC"])
    return df_temiz


def veritabanina_yaz(df):
    logging.info("Veriler veritabanına yazılıyor...")
    with sqlite3.connect("banka_veritabani.db") as baglanti:
        df.to_sql("kredi_karti_islemleri", baglanti, if_exists="append", index=False)

    logging.info(f"Toplam {len(df)} satır veri SQL veritabanına aktarıldı.")


def ana_pipeline_calistir():
    logging.info("=== GÜNLÜK ETL BORU HATTI BAŞLATILDI ===")

    try:

        ham_veri = veriyi_oku("gunluk_veri.csv")

        temiz_veri = veriyi_temizle(ham_veri)

        veritabanina_yaz(temiz_veri)

        logging.info("=== ETL SÜRECİ BAŞARIYLA TAMAMLANDI ===")
        print("Süreç başarıyla tamamlandı, sistem loglarını kontrol edebilirsiniz.")

    except Exception as e:
        hata_mesaji = f"Kritik Sistem Hatası: {str(e)}"
        logging.error(f"SİSTEM ÇÖKTÜ: {hata_mesaji}")
        print(f"Hata oluştu! Yöneticiye e-posta gönderiliyor...\nDetay: {hata_mesaji}")

if __name__ == "__main__":
    ana_pipeline_calistir()