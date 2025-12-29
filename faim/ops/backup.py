import os
import subprocess
import datetime
import boto3

# Ops Configuration
DB_URL = os.getenv("FAIM_DB_URL") 
# e.g. postgresql://user:pass@localhost:5432/faim
# pg_dump requires PGPASSWORD env var or .pgpass

MINIO_BUCKET = os.getenv("MINIO_BUCKET", "faim-backups")
# Standard MinIO/S3 env vars handled by boto3 or explicit init

def perform_backup():
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backup_faim_{ts}.sql"
    
    # 1. Dump Database
    print(f"Dumping database to {backup_file}...")
    # Parsing DB_URL to set PGPASSWORD is safer, but for script MVP assume env is set
    # or rely on pg_dump parsing URL if supported (newer versions do)
    
    cmd = f"pg_dump {DB_URL} -f {backup_file}"
    try:
        subprocess.check_call(cmd, shell=True)
    except subprocess.CalledProcessError:
        print("Backup failed (pg_dump error)")
        return

    # 2. Upload to S3/MinIO
    print("Uploading to Object Storage...")
    s3 = boto3.client("s3") # Uses env vars
    try:
        s3.upload_file(backup_file, MINIO_BUCKET, f"db/{backup_file}")
        print("Backup uploaded successfully.")
    except Exception as e:
        print(f"Upload failed: {e}")
    finally:
        # Cleanup
        if os.path.exists(backup_file):
            os.remove(backup_file)

if __name__ == "__main__":
    perform_backup()
