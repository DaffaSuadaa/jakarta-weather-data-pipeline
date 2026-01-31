import os
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv() 
DATABASE_URL = os.getenv('DATABASE_URL')

def run_etl():
    """
    Fungsi utama untuk menjalankan pipeline cuaca.
    """
    # --- 1. EXTRACT ---
    print("Mengekstrak data dari API...")
    url = "https://api.open-meteo.com/v1/forecast?latitude=-6.2146&longitude=106.8451&current_weather=true"
    response = requests.get(url)
    response.raise_for_status() # Akan error jika API down (bagus untuk log)
    data = response.json()['current_weather']

    # --- 2. TRANSFORM ---
    print("Mentransformasi data...")
    df = pd.DataFrame([data])
    df['time'] = pd.to_datetime(df.get('time', datetime.now())) # Aman jika 'time' tidak ada
    df['extracted_at'] = datetime.now()

    # --- 3. LOAD ---
    print("Mengirim data ke Neon.tech...")
    # Gunakan environment variable untuk keamanan
    conn_url = DATABASE_URL
    
    if not conn_url:
        raise ValueError("DATABASE_URL tidak ditemukan!")

    if conn_url.startswith("postgres://"):
        conn_url = conn_url.replace("postgres://", "postgresql://", 1)

    engine = create_engine(conn_url)
    df.to_sql('jakarta_weather', engine, if_exists='append', index=False)
    
    return "Proses ETL Berhasil!"

# Titik masuk utama program
if __name__ == "__main__":
    try:
        status = run_etl()
        print(status)
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")