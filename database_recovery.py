#!/usr/bin/env python3
"""
Database Recovery Script for BlockchainPlus Bot
Run this if database gets corrupted or needs recovery
"""
import json
import os
import sys
from datetime import datetime

def check_and_fix_database(db_file: str):
    """Check database integrity and fix issues"""
    print(f"Checking database: {db_file}")
    
    if not os.path.exists(db_file):
        print("Database file does not exist. Creating new one...")
        create_new_database(db_file)
        return True
    
    try:
        with open(db_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check structure
        required_keys = ['users', 'payouts', 'commissions', 'referrals', 'metadata']
        for key in required_keys:
            if key not in data:
                print(f"Missing key: {key}, adding...")
                if key == 'users':
                    data[key] = {}
                elif key == 'payouts':
                    data[key] = {}
                elif key == 'commissions':
                    data[key] = {}
                elif key == 'referrals':
                    data[key] = {}
                elif key == 'metadata':
                    data[key] = {
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat(),
                        'total_users': len(data.get('users', {})),
                        'total_affiliates': 0,
                        'total_commissions': 0,
                        'total_payouts': 0
                    }
        
        # Fix user structure
        users_fixed = 0
        for user_id, user in data['users'].items():
            # Ensure required fields
            required_fields = ['tg_id', 'name', 'program', 'is_affiliate']
            for field in required_fields:
                if field not in user:
                    if field == 'tg_id':
                        user[field] = int(user_id)
                    elif field == 'name':
                        user[field] = f"User_{user_id}"
                    elif field == 'program':
                        user[field] = 'crypto'
                    elif field == 'is_affiliate':
                        user[field] = False
                    users_fixed += 1
        
        # Save fixed database
        with open(db_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Database checked and fixed. Users fixed: {users_fixed}")
        return True
        
    except json.JSONDecodeError:
        print("Database is corrupted. Creating backup and new database...")
        # Create backup of corrupted file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"{db_file}.corrupted_{timestamp}"
        os.rename(db_file, backup_file)
        print(f"Corrupted file backed up as: {backup_file}")
        
        # Create new database
        create_new_database(db_file)
        return True
    
    except Exception as e:
        print(f"Error checking database: {e}")
        return False

def create_new_database(db_file: str):
    """Create a new empty database"""
    new_db = {
        'users': {},
        'payouts': {},
        'commissions': {},
        'referrals': {},
        'metadata': {
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'total_users': 0,
            'total_affiliates': 0,
            'total_commissions': 0,
            'total_payouts': 0
        }
    }
    
    with open(db_file, 'w', encoding='utf-8') as f:
        json.dump(new_db, f, indent=2, ensure_ascii=False)
    
    print(f"New database created at: {db_file}")

if __name__ == "__main__":
    # Get database path from environment or use default
    database_path = os.environ.get('DATABASE_PATH', '/data')
    db_file = os.path.join(database_path, 'users.json')
    
    print("=" * 50)
    print("Database Recovery Tool")
    print("=" * 50)
    
    if check_and_fix_database(db_file):
        print("✅ Database recovery completed successfully!")
    else:
        print("❌ Database recovery failed!")
        sys.exit(1)