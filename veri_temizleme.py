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


def hata_epostasi_gonder(hata_mesaji):
    # 1. Geliştirme: server değişkenini baştan None yapıyoruz ki finally bloğu hata vermesin.
    server = None

    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    GONDERICI_EPOSTA = "erouw4808@gmail.com"
    UYGULAMA_SIFRESI = os.getenv("GMAIL_UYGULAMA_SIFRESI")
    ALICI_EPOSTA = "erouw4808@gmail.com"

    # 2. Geliştirme: Dinamik e-posta gövdesi. f-string ile hatayı e-postaya gömüyoruz.
    gövde_metni = f"""\
    DIKKAT! Banka ETL Sürecinde Kritik Bir Hata Meydana Geldi.

    Sistem tarafindan yakalanan hata detayi asagidadir:
    HATA: {hata_mesaji}

    Lutfen sunucuya baglanip 'banka_etl_sureci.log' dosyasini acilen inceleyin.
    """

    msg = MIMEText(gövde_metni, "plain", "utf-8")
    msg["Subject"] = "🚨 KRİTİK ALARM: ETL Süreci Çöktü!"
    msg["From"] = GONDERICI_EPOSTA
    msg["To"] = ALICI_EPOSTA

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(GONDERICI_EPOSTA, UYGULAMA_SIFRESI)
        server.sendmail(GONDERICI_EPOSTA, ALICI_EPOSTA, msg.as_string())

        logging.info("Hata e-postası başarıyla gönderildi.")
    except Exception as e:
        logging.error(f"E-posta gönderimi başarısız oldu: {e}")
    finally:
        if server is not None:
            server.quit()



def ana_pipeline_calistir():
    logging.info("gunluk etl pipeline baslatildi")

    try:
        ham_veri = veriyi_oku("gunluk_veri.csv")

        temiz_veri = veriyi_temizle(ham_veri)

        veritabanina_yaz(temiz_veri)

        logging.info("etl sureci basariyla tamamlandı")
        print("surec basriyla tamamlandi, sistem loglarını kontrol edebilirsiniz")

    except Exception as e:
        hata_mesaji = f"Kritik Sistem Hatası: {str(e)}"
        logging.error(f"sistem coktu hata mesajı : {hata_mesaji}")
        print(f"Hata oluştu!!! Yöneticiye e-posta gönderiliyor\nDetay: {hata_mesaji}")


        hata_epostasi_gonder(hata_mesaji)


if __name__ == "__main__":
    ana_pipeline_calistir()