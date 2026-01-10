# FAIM Database Setup Guide

This guide will help you set up PostgreSQL for full FAIM functionality.

## Quick Install (Ubuntu/Debian)

```bash
# 1. Install PostgreSQL
sudo apt update
sudo apt install -y postgresql postgresql-contrib

# 2. Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 3. Create the FAIM database and user
sudo -u postgres psql -c "CREATE DATABASE faim_lab;"
sudo -u postgres psql -c "CREATE USER faim WITH PASSWORD 'faim_dev_pass';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE faim_lab TO faim;"
sudo -u postgres psql -c "ALTER USER faim CREATEDB;"

# 4. Set environment variable (add to ~/.bashrc for persistence)
export FAIM_DB_URL="postgresql://faim:faim_dev_pass@localhost/faim_lab"
```

## Initialize Database Tables

After PostgreSQL is running, initialize the tables:

```bash
cd /home/ravi_saini/FAIM12
python3 -c "
from faim.db import engine
from faim.models_sql import Base
Base.metadata.create_all(bind=engine)
print('✓ Database tables created successfully!')
"
```

## Verify Setup

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -h localhost -U faim -d faim_lab -c "SELECT 1;"
```

## Environment Variables

Add these to your shell profile (`~/.bashrc` or `~/.zshrc`):

```bash
export FAIM_MODE="dev"
export FAIM_DB_URL="postgresql://faim:faim_dev_pass@localhost/faim_lab"
```

Then restart your backend server:

```bash
cd /home/ravi_saini/FAIM12
uvicorn faim.api.app:app --reload
```

## Alternative: Docker (if preferred)

If you install Docker later:

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in

# Run PostgreSQL container
docker run -d \
  --name faim-postgres \
  -e POSTGRES_USER=faim \
  -e POSTGRES_PASSWORD=faim_dev_pass \
  -e POSTGRES_DB=faim_lab \
  -p 5432:5432 \
  postgres:15

# Check it's running
docker ps
```

## Troubleshooting

**Connection refused:**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# If not, start it
sudo systemctl start postgresql
```

**Permission denied:**
```bash
# Check pg_hba.conf allows local connections
sudo nano /etc/postgresql/*/main/pg_hba.conf
# Ensure this line exists:
# local   all   all   md5
# Then restart:
sudo systemctl restart postgresql
```
