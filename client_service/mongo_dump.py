
import os
import subprocess
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ----- CONFIG -----
MONGO_URI = os.getenv("MONGO_URI")               # Source DB
MONGO_DB = os.getenv("MONGO_DB")

SERVER_URI = os.getenv("SERVER_URI")             # Destination DB
SERVER_DB_NAME = os.getenv("SERVER_DB_NAME")

# Validate environment variables
REQUIRED_ENV = {
    "MONGO_URI": MONGO_URI,
    "MONGO_DB": MONGO_DB,
    "SERVER_URI": SERVER_URI,
    "SERVER_DB_NAME": SERVER_DB_NAME,
}

missing = [k for k, val in REQUIRED_ENV.items() if not val]
if missing:
    raise ValueError(f"❌ Missing required environment variables: {missing}")

# Timestamp folder for backup
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
DUMP_DIR = Path(f"mongo_dump_{TIMESTAMP}")

# ------------------------------------------------------------------
# MongoDB Dump Function
# ------------------------------------------------------------------
def dump_mongo_db():
    """Dump MongoDB database locally with timestamp-based folder."""
    try:
        DUMP_DIR.mkdir(parents=True, exist_ok=True)

        dump_cmd = [
            "mongodump",
            f"--uri={MONGO_URI}",
            f"--db={MONGO_DB}",
            f"--out={DUMP_DIR}",
        ]

        print("\n🚀 Running MongoDB Dump Command:")
        print(" ".join(dump_cmd))

        subprocess.run(dump_cmd, check=True)

        print(f"✔ Dump completed! Saved at: {DUMP_DIR}")

    except FileNotFoundError:
        print("❌ ERROR: 'mongodump' not found. Install MongoDB Database Tools.")
        raise
    except subprocess.CalledProcessError as e:
        print("❌ Dump failed:", e)
        raise


# ------------------------------------------------------------------
# MongoDB Restore Function
# ------------------------------------------------------------------
def restore_to_server():
    """Restore local dump folder to target MongoDB server."""
    try:
        restore_path = DUMP_DIR / MONGO_DB

        restore_cmd = [
            "mongorestore",
            f"--uri={SERVER_URI}",
            f"--db={SERVER_DB_NAME}",
            str(restore_path),
        ]

        print("\n🚀 Running MongoDB Restore Command:")
        print(" ".join(restore_cmd))

        subprocess.run(restore_cmd, check=True)

        print(f"✔ Restore completed successfully to {SERVER_DB_NAME} on server")

    except FileNotFoundError:
        print("❌ ERROR: 'mongorestore' not found. Install MongoDB Database Tools.")
        raise
    except subprocess.CalledProcessError as e:
        print("❌ Restore failed:", e)
        raise


# ------------------------------------------------------------------
# MAIN PROCESS
# ------------------------------------------------------------------
if __name__ == "__main__":
    print("\n====================================================")
    print("            🔄 MongoDB Backup & Restore Tool         ")
    print("====================================================\n")

    try:
        dump_mongo_db()
        restore_to_server()

        print("\n🎉 DATABASE MIGRATION COMPLETED SUCCESSFULLY!")

    except Exception as e:
        print(f"\n❌ Process failed: {e}")

    print("\n====================================================\n")
