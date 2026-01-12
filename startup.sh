#!/bin/bash

# Set database path
export DATABASE_PATH=/data

# Ensure data directory exists
mkdir -p $DATABASE_PATH

# Check if database exists, if not create a basic structure
if [ ! -f "$DATABASE_PATH/users.json" ]; then
    echo "No database found. Creating initial database structure..."
    echo '{"users": {}, "payouts": {}, "commissions": {}, "referrals": {}, "metadata": {"created_at": "'$(date -Iseconds)'", "updated_at": "'$(date -Iseconds)'", "total_users": 0, "total_affiliates": 0, "total_commissions": 0, "total_payouts": 0}}' > $DATABASE_PATH/users.json
fi

# Run database recovery check (optional)
if [ -f "database_recovery.py" ]; then
    python database_recovery.py
fi

# Start the bot
python main.py