from dataclasses import dataclass
from email.mime.text import MIMEText
import logging
import os
import smtplib
import sqlite3
from typing import Optional
from dotenv import load_dotenv
import pandas as pd


load_dotenv()


@dataclass
class PipelineConfig:

    csv_path: str = "kredi_karti_islemleri.csv"
    db_path: str = "banka_veritabani.db"
    table_name: str = "kredi_karti_islemleri"
    log_file: str = "banka_etl_sureci.log"

    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    sender_email: str = os.getenv("GONDERICI_EPOSTA", "erouw4808@gmail.com")
    app_password: Optional[str] = os.getenv("GMAIL_UYGULAMA_SIFRESI")
    receiver_email: str = os.getenv("ALICI_EPOSTA", "erouw4808@gmail.com")


class NotificationService:


    def __init__(self, config: PipelineConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger

    def send_error_email(self, error_message: str) -> None:
        if not self.config.app_password:
            self.logger.warning(
                "GMAIL_UYGULAMA_SIFRESI bulunamadı, e-posta uyarısı gönderilemiyor."
            )
            return

        body = f"""\
dikkat! banka ETL sürecinde kritik bir hata meydana geldi.

Sistem tarafından yakalanan hata detayı aşağıdadır:
HATA: {error_message}

Lütfen sunucuya bağlanıp '{self.config.log_file}' dosyasını acilen inceleyin.
"""
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = "🚨 KRİTİK ALARM: ETL Süreci Çöktü!"
        msg["From"] = self.config.sender_email
        msg["To"] = self.config.receiver_email

        server = None
        try:
            server = smtplib.SMTP(
                self.config.smtp_server, self.config.smtp_port
            )
            server.starttls()
            server.login(self.config.sender_email, self.config.app_password)
            server.sendmail(
                self.config.sender_email,
                self.config.receiver_email,
                msg.as_string(),
            )
            self.logger.info("Hata e-postası başarıyla gönderildi.")
        except Exception as e:
            self.logger.error(
                f"E-posta gönderimi başarısız oldu: {e}", exc_info=True
            )
        finally:
            if server:
                server.quit()


class BankaETLPipeline:

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.logger = self._setup_logger()
        self.notifier = NotificationService(self.config, self.logger)

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger("BankaETL")
        logger.setLevel(logging.DEBUG)

        if not logger.handlers:
            handler = logging.FileHandler(
                self.config.log_file, mode="a", encoding="utf-8"
            )
            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def extract(self) -> pd.DataFrame:
        self.logger.info(
            f"'{self.config.csv_path}' dosyası okunmaya başlandı."
        )

        if not os.path.exists(self.config.csv_path):
            raise FileNotFoundError(
                f"Kaynak dosya bulunamadı: {self.config.csv_path}"
            )

        df = pd.read_csv(self.config.csv_path, encoding="utf-8-sig", sep=";")
        self.logger.info(
            f"Dosya başarıyla okundu. Toplam satır sayısı: {len(df)}"
        )
        return df

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        self.logger.info("Veri temizleme adımı başlatıldı.")

        if df.empty:
            raise ValueError("Gelen veri seti tamamen boş!")

        if "Musteri_TC" not in df.columns:
            raise KeyError("Veri setinde 'Musteri_TC' sütunu bulunamadı!")

        df_cleaned = df.dropna(subset=["Musteri_TC"]).copy()
        self.logger.info(
            f"Veri temizlendi. Kalan satır sayısı: {len(df_cleaned)}"
        )
        return df_cleaned

    def load(self, df: pd.DataFrame) -> None:
        self.logger.info("Veriler hedef veritabanına yazılıyor...")

        with sqlite3.connect(self.config.db_path) as conn:
            df.to_sql(
                self.config.table_name,
                conn,
                if_exists="append",
                index=False,
            )

        self.logger.info(
            f"Toplam {len(df)} satır '{self.config.table_name}' tablosuna aktarıldı."
        )

    def run(self) -> None:
        self.logger.info("Günlük Banka ETL Pipeline Başlatıldı")

        try:
            raw_data = self.extract()
            cleaned_data = self.transform(raw_data)
            self.load(cleaned_data)

            self.logger.info("ETL Süreci Başarıyla Tamamlandı")
            print(
                "Süreç başarıyla tamamlandı. Log dosyasını kontrol edebilirsiniz."
            )

        except Exception as e:
            error_msg = f"Kritik Sistem Hatası: {str(e)}"
            # exc_info=True sayesinde hatanın tam yerini (stack trace) loga yazarız
            self.logger.critical(
                f"Sistem çöktü! {error_msg}", exc_info=True
            )
            print(
                f"Hata oluştu! Yöneticiye e-posta gönderiliyor.\nDetay: {error_msg}"
            )

            self.notifier.send_error_email(error_msg)

if __name__ == "__main__":
    config = PipelineConfig()
    pipeline = BankaETLPipeline(config)
    pipeline.run()