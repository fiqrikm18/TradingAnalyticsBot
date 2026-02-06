import logging
from database import engine, Base

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    if engine:
        print("Creating database tables...")
        try:
            # 1. Enable TimescaleDB Extension (Needs Superuser usually, or pre-installed)
            with engine.connect() as connection:
                connection.execute(
                    "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
                connection.commit()
                print("✅ TimescaleDB extension enabled.")
        except Exception as e:
            print(
                f"⚠️ Could not enable TimescaleDB (might be already installed or permission denied): {e}")

        try:
            Base.metadata.create_all(bind=engine)
            print("✅ Tables created successfully.")

            # 2. Convert to Hypertable
            with engine.connect() as connection:
                # We interpret 'if not exists' via exception handling or ignore
                try:
                    connection.execute(
                        "SELECT create_hypertable('daily_prices', 'time', if_not_exists => TRUE);")
                    connection.commit()
                    print("✅ 'daily_prices' converted to Hypertable.")
                except Exception as e:
                    print(
                        f"ℹ️ Hypertable creation skipped (likely exists): {e}")

        except Exception as e:
            print(f"❌ Failed to create tables: {e}")
    else:
        print("⚠️ No database configured (DATABASE_URL missing). Skipping init.")
