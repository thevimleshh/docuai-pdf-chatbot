from database import engine

try:
    with engine.connect() as connection:
        print("✅ TiDB Cloud Connected Successfully!")
except Exception as e:
    print("❌ Connection Failed!")
    print(e)