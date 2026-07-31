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
def gunluk_veri_yolu(csv_yolu):
    baglanti = None

    try:
        baglanti = sqlite3.connect("banka_veritabani.db")
        logging.info(f"{csv_yolu} dosyası okunmaya başlandı.")
        df = pd.read_csv(csv_yolu, sep=";", dtype={"Musteri_TC": str})
        df_temiz = df.dropna(subset=["Musteri_TC"])
        df_temiz["Tutar"] = ((df["Tutar"].str.replace("₺","",regex=False))
                             .str.replace(".","",regex=False)
                             .str.replace(",",".",regex=False))
        df_temiz["Tutar"]= pd.to_numeric(df_temiz["Tutar"],errors="coerce")
        df_temiz["Tarih"] = ((df_temiz["Tarih"].str.replace("/","-",regex=False)).str.replace(".","-",regex=False))
        df_temiz["Tarih"] = pd.to_datetime(df_temiz["Tarih"],format="%d-%m-%Y",errors="coerce"
                                             ).fillna( pd.to_datetime(df_temiz["Tarih"],format="%Y-%m-%d",errors="coerce"))
        logging.info("veri temizlendi")

        toplam_tutar = df_temiz["Tutar"].sum()
        if toplam_tutar == 0:
            raise ValueError("toplam tutar sıfır!!!")

        if df_temiz.empty:
            raise ValueError("KRİTİK: Temizlenmiş veri seti tamamen boş! SQL'e yazma işlemi iptal edildi.")
        else:
            df_temiz.to_sql("kredi_karti_islemleri", baglanti, if_exists="replace", index=False)
            logging.info(f"Toplam {len(df_temiz)} satır veri SQL veritabanına aktarıldı.")

    except Exception as hata:
        #logging.error("test debug mesajı")
        logging.exception("hata mesajı")
        hata_epostasi_gonder(str(hata))

    finally:
        if baglanti is not None:
            baglanti.close()
            logging.info("INFO TEST")


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
        # 3. Geliştirme: print yerine logging kullanıyoruz ki mail atılıp atılmadığı da kara kutuya yazılsın.
        logging.info("Hata e-postası başarıyla gönderildi.")
    except Exception as e:
        logging.error(f"E-posta gönderimi başarısız oldu: {e}")
    finally:
        # 4. Geliştirme: Güvenli kapatma. Server gerçekten oluşturulmuşsa kapat.
        if server is not None:
            server.quit()

if __name__ == "__main__":
    gunluk_veri_yolu("bos_veri.csv")

