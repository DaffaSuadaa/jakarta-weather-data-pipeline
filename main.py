import os
import requests
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values
from datetime import datetime, timedelta
import logging

load_dotenv()
# 1. Konfigurasi Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

def run_etl():
    # Ambil koneksi dari environment variable (GitHub Secrets)
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # 2. Tentukan Rentang Waktu (Ambil 7 hari terakhir untuk jaga-jaga jika kemarin gagal)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)
    
    url = f"https://archive-api.open-meteo.com/v1/archive?latitude=-6.1823&longitude=106.8293&start_date={start_date}&end_date={end_date}&hourly=temperature_2m,relative_humidity_2m,precipitation,surface_pressure,wind_speed_10m,weather_code&timezone=Asia%2FBangkok"

    try:
        # 3. Extract
        logger.info(f"Mengambil data dari {start_date} hingga {end_date}...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()['hourly']
        
        # Susun data untuk batch insert
        records = []
        for i in range(len(data['time'])):
            records.append((
                data['time'][i],
                data['temperature_2m'][i],
                data['relative_humidity_2m'][i],
                data['precipitation'][i],
                data['surface_pressure'][i],
                data['wind_speed_10m'][i],
                data['weather_code'][i],
                datetime.now()
            ))

        # 4. Load (dengan Anti-Duplikat)
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Query UPSERT: Jika timeinterval sudah ada, jangan lakukan apa-apa (atau update)
        upsert_query = """
        INSERT INTO weather_history (
            time_interval, 
            temperature, 
            humidity, 
            precipitation, 
            pressure, 
            wind_speed, 
            weather_code, 
            extracted_at
        ) VALUES %s
        ON CONFLICT (time_interval) DO UPDATE SET
            temperature = EXCLUDED.temperature,
            humidity = EXCLUDED.humidity,
            precipitation = EXCLUDED.precipitation,
            pressure = EXCLUDED.pressure,
            wind_speed = EXCLUDED.wind_speed,      -- Perbaikan: sebelumnya windspeed
            weather_code = EXCLUDED.weather_code,  -- Perbaikan: sebelumnya weathercode
            extracted_at = EXCLUDED.extracted_at;
        """
        
        execute_values(cur, upsert_query, records)
        conn.commit()
        
        logger.info(f"Berhasil memproses {len(records)} baris data ke Neon Tech.")

    except requests.exceptions.RequestException as e:
        logger.error(f"🌐 Gagal mengambil data dari API: {e}")
        raise
    except psycopg2.Error as e:
        logger.error(f"🗄️ Gagal operasi database: {e}")
        raise 
    except Exception as e:
        logger.error(f"⚠️ Terjadi kesalahan tidak terduga: {e}")
        raise
    finally:
        if 'conn' in locals():
            cur.close()
            conn.close()

if __name__ == "__main__":
    run_etl()