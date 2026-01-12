# database.py - MERGED VERSION WITH AUTO-SAVE FUNCTIONALITY
import json
import logging
import os
import shutil
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any

logger = logging.getLogger(__name__)

class UserDatabase:
    def __init__(self, db_file: str = None):
        # Use DATABASE_PATH environment variable or default to current directory
        db_dir = os.environ.get('DATABASE_PATH', '.')
        
        if not db_file:
            db_file = os.path.join(db_dir, 'users.json')
        
        self.db_file = db_file
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
        
        # Initialize empty database structure
        self.db = self._create_empty_db()

        # Initialize collections
        self.users = {} 
        self.affiliates = {}
        self.payouts = [] 
        self.commissions = {}
        
        # Load existing database
        self._load_database()
        
        # Set references to collections
        self.users = self.db.get('users', {})
        self.payouts = self.db.get('payouts', {})
        self.commissions = self.db.get('commissions', {})
        self.referrals = self.db.get('referrals', {})
        
        # Track changes for auto-save
        self.changes_since_save = 0
        self.last_save_time = time.time()
        
        # Verify database integrity after loading
        self.verify_database_integrity()
        
        logger.info(f"Database initialized at: {self.db_file}")

    def _load_database(self):
        """Load database from file or create new - FIXED VERSION"""
        try:
            if os.path.exists(self.db_file):
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    loaded_db = json.load(f)
                
                # CRITICAL FIX: Merge loaded data into base structure properly
                base_db = self._create_empty_db()
                
                # Merge with loaded_db taking priority (preserves existing data)
                # Start with base structure, then update with loaded data
                self.db = base_db.copy()
                
                # Update each key with loaded data
                for key in loaded_db:
                    if key in self.db:
                        if isinstance(self.db[key], dict) and isinstance(loaded_db[key], dict):
                            # For dictionaries, update recursively
                            self.db[key].update(loaded_db[key])
                        else:
                            # For other types, replace
                            self.db[key] = loaded_db[key]
                    else:
                        # Add new keys
                        self.db[key] = loaded_db[key]
                
                logger.info(f"Loaded database with {len(self.db['users'])} users")
            else:
                self._save_database()
                logger.info("Created new database file")
                
        except Exception as e:
            logger.error(f"Error loading database: {e}")
            # Create backup if corrupted
            if os.path.exists(self.db_file):
                try:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    backup_file = f"{self.db_file}.corrupted_{timestamp}"
                    os.rename(self.db_file, backup_file)
                    logger.warning(f"Created backup of corrupted file: {backup_file}")
                except:
                    pass
            
            # Start with empty database
            self.db = self._create_empty_db()
            self._save_database()

    def _create_empty_db(self) -> Dict:
        """Create an empty database structure"""
        return {
            'users': {},
            'payouts': {},
            'commissions': {},
            'referrals': {},
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'updated_at': None,
                'total_users': 0,
                'total_affiliates': 0,
                'total_commissions': 0,
                'total_payouts': 0
            }
        }

    def verify_database_integrity(self):
        """Verify database structure and fix any inconsistencies - NEW METHOD"""
        try:
            logger.info("Verifying database integrity...")
            
            # Ensure all required keys exist
            required_keys = ['users', 'payouts', 'commissions', 'referrals', 'metadata']
            base_db = self._create_empty_db()
            
            for key in required_keys:
                if key not in self.db:
                    self.db[key] = base_db[key]
                    logger.warning(f"Added missing key to database: {key}")
            
            # Ensure all users have required affiliate fields
            for user_id_str, user in list(self.db['users'].items()):
                # Convert user_id to string if it's not already
                if isinstance(user_id_str, int):
                    new_key = str(user_id_str)
                    self.db['users'][new_key] = user
                    if user_id_str != new_key:
                        del self.db['users'][user_id_str]
                
                # Ensure required fields exist
                required_affiliate_fields = {
                    'is_affiliate': False,
                    'affiliate_status': 'none',
                    'affiliate_code': None,
                    'affiliate_earnings': 0.0,
                    'affiliate_paid': 0.0,
                    'affiliate_pending': 0.0,
                    'affiliate_available': 0.0,
                    'affiliate_applied_date': None,
                    'affiliate_approved_date': None,
                    'referred_by': None,
                    'referrals': [],
                    'referral_count': 0,
                    'pending_pop': None
                }
                
                for field, default_value in required_affiliate_fields.items():
                    if field not in user:
                        user[field] = default_value
                
                # Ensure tg_id exists and is correct
                if 'tg_id' not in user:
                    user['tg_id'] = int(user_id_str)
            
            # Update references
            self.users = self.db.get('users', {})
            self.payouts = self.db.get('payouts', {})
            self.commissions = self.db.get('commissions', {})
            self.referrals = self.db.get('referrals', {})
            
            # Save if any changes were made
            if self.changes_since_save > 0:
                self._save_database()
            
            logger.info(f"Database integrity check completed. Users: {len(self.users)}, Affiliates: {len([u for u in self.users.values() if u.get('is_affiliate')])}")
            return True
        except Exception as e:
            logger.error(f"Error verifying database integrity: {e}")
            return False

    def _save_database(self):
        """Save database to file"""
        try:
            # Update metadata
            self.db['metadata']['updated_at'] = datetime.now().isoformat()
            self.db['metadata']['total_users'] = len(self.users)
            self.db['metadata']['total_affiliates'] = len([
                u for u in self.users.values() 
                if u.get('is_affiliate', False)
            ])
            self.db['metadata']['total_commissions'] = len(self.commissions)
            self.db['metadata']['total_payouts'] = len(self.payouts)
            
            # Create backup of current file
            if os.path.exists(self.db_file):
                try:
                    backup_file = f"{self.db_file}.backup"
                    with open(self.db_file, 'r', encoding='utf-8') as f:
                        backup_data = f.read()
                    with open(backup_file, 'w', encoding='utf-8') as f:
                        f.write(backup_data)
                except Exception as backup_error:
                    logger.warning(f"Could not create backup: {backup_error}")
            
            # Save to file
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(self.db, f, indent=2, ensure_ascii=False)
            
            self.changes_since_save = 0
            self.last_save_time = time.time()
            
            logger.debug(f"Database saved with {len(self.users)} users")
            return True
            
        except Exception as e:
            logger.error(f"Error saving database: {e}")
            return False

    def auto_save_check(self):
        """Check if we should auto-save based on changes or time"""
        try:
            # Save if we have 5 or more changes
            if self.changes_since_save >= 5:
                self._save_database()
                return True
            
            # Save if 30 seconds have passed since last save
            current_time = time.time()
            if current_time - self.last_save_time >= 30:  # 30 seconds
                self._save_database()
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error in auto-save check: {e}")
            return False

    def mark_changed(self):
        """Mark that a change has been made to the database"""
        self.changes_since_save += 1
        self.auto_save_check()

    def save_database(self):
        """Manual save - forces immediate save"""
        return self._save_database()

    # ====================
    # USER MANAGEMENT
    # ====================

    def insert_user(self, user_id: int, name: str, username: str, program: str = 'crypto'):
        """Insert a new user into the database"""
        try:
            user_id_str = str(user_id)
            
            if user_id_str in self.users:
                return self.users[user_id_str]
            
            user_data = {
                'tg_id': user_id,
                'name': name,
                'username': username,
                'program': program,
                'crypto_academy_expiry_date': None,
                'crypto_vip_expiry_date': None,
                'forex_academy_expiry_date': None,
                'forex_vip_expiry_date': None,
                'crypto_trial_used': False,
                'forex_trial_used': False,
                'pending_pop': None,
                'referred_by': None,  # Affiliate who referred this user
                'referrals': [],  # Users referred by this user
                'referral_count': 0,
                'is_affiliate': False,
                'affiliate_status': 'none',  # none, pending, approved, rejected
                'affiliate_code': None,
                'affiliate_earnings': 0.0,
                'affiliate_paid': 0.0,
                'affiliate_pending': 0.0,
                'affiliate_available': 0.0,
                'affiliate_applied_date': None,
                'affiliate_approved_date': None,
                'registration_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'last_active': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            self.users[user_id_str] = user_data
            self.db['users'] = self.users
            self.mark_changed()
            
            logger.info(f"New user inserted: {user_id} ({name})")
            return user_data
        except Exception as e:
            logger.error(f"Error inserting user: {e}")
            return None

    def fetch_user(self, user_id: int) -> Optional[Dict]:
        """Fetch user data by ID"""
        try:
            user_data = self.users.get(str(user_id))
            if user_data:
                # Update last active
                user_data['last_active'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.users[str(user_id)] = user_data
                self.mark_changed()
            return user_data
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            return None

    def update_user(self, user_id: int, updates: Dict):
        """Update user data"""
        try:
            user_id_str = str(user_id)
            if user_id_str in self.users:
                self.users[user_id_str].update(updates)
                self.users[user_id_str]['last_active'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.db['users'] = self.users
                self.mark_changed()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False

    def get_all_users(self) -> Dict:
        """Get all users"""
        return self.users

    def set_program(self, user_id: int, program: str):
        """Set user's program preference"""
        return self.update_user(user_id, {'program': program})

    # ====================
    # SUBSCRIPTION MANAGEMENT
    # ====================

    def set_subscription(self, user_id: int, program: str, plan_type: str, days: int):
        """Set user's subscription expiry date"""
        try:
            if days <= 0:
                expiry_date = None
            else:
                expiry_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
            
            user = self.fetch_user(user_id)
            if not user:
                return False
            
            if program == 'crypto':
                if plan_type == 'academy':
                    user['crypto_academy_expiry_date'] = expiry_date
                    # If this is first academy subscription, reset trial
                    if days > 0 and not user.get('crypto_trial_used', False):
                        user['crypto_trial_used'] = False
                elif plan_type == 'vip':
                    user['crypto_vip_expiry_date'] = expiry_date
                    user['crypto_trial_used'] = True
            else:  # forex
                if plan_type == 'academy':
                    user['forex_academy_expiry_date'] = expiry_date
                    # If this is first academy subscription, reset trial
                    if days > 0 and not user.get('forex_trial_used', False):
                        user['forex_trial_used'] = False
                elif plan_type == 'vip':
                    user['forex_vip_expiry_date'] = expiry_date
                    user['forex_trial_used'] = True
            
            self.users[str(user_id)] = user
            self.db['users'] = self.users
            self.mark_changed()
            return True
        except Exception as e:
            logger.error(f"Error setting subscription for {user_id}: {e}")
            return False

    def mark_trial_used(self, user_id: int, program: str):
        """Mark trial as used for a user"""
        try:
            user = self.fetch_user(user_id)
            if not user:
                return False
            
            if program == 'crypto':
                user['crypto_trial_used'] = True
            else:
                user['forex_trial_used'] = True
            
            self.users[str(user_id)] = user
            self.db['users'] = self.users
            self.mark_changed()
            return True
        except Exception as e:
            logger.error(f"Error marking trial used for {user_id}: {e}")
            return False

    def get_trial_used(self, user_id: int, program: str) -> bool:
        """Check if trial has been used"""
        user = self.fetch_user(user_id)
        if not user:
            return False
        
        if program == 'crypto':
            return user.get('crypto_trial_used', False)
        else:
            return user.get('forex_trial_used', False)

    # ====================
    # PAYMENT/POP MANAGEMENT
    # ====================

    def set_pending_pop(self, user_id: int, file_id: str, program: str, plan_choice: str, vip_duration: Optional[str] = None):
        """Set pending proof of payment for user"""
        try:
            user = self.fetch_user(user_id)
            if not user:
                return False
            
            user['pending_pop'] = {
                'file_id': file_id,
                'program': program,
                'plan_choice': plan_choice,
                'vip_duration': vip_duration,
                'uploaded_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            self.users[str(user_id)] = user
            self.db['users'] = self.users
            self.mark_changed()
            return True
        except Exception as e:
            logger.error(f"Error setting pending POP for {user_id}: {e}")
            return False

    def clear_pending_pop(self, user_id: int):
        """Clear pending proof of payment"""
        try:
            user = self.fetch_user(user_id)
            if user and user.get('pending_pop'):
                user['pending_pop'] = None
                self.users[str(user_id)] = user
                self.db['users'] = self.users
                self.mark_changed()
                return True
            return False
        except Exception as e:
            logger.error(f"Error clearing pending POP for {user_id}: {e}")
            return False

    # ====================
    # AFFILIATE SYSTEM METHODS
    # ====================

    def set_affiliate_status(self, user_id: int, status: str, affiliate_code: str = None):
        """Set affiliate status for a user"""
        try:
            user = self.fetch_user(user_id)
            if not user:
                # Create user if doesn't exist
                name = f"User_{user_id}"
                self.insert_user(user_id, name, None, 'crypto')
                user = self.fetch_user(user_id)
            
            if user:
                user['affiliate_status'] = status
                user['affiliate_applied_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                if affiliate_code:
                    user['affiliate_code'] = affiliate_code
                
                if status == 'approved':
                    user['is_affiliate'] = True
                    user['affiliate_approved_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                else:
                    user['is_affiliate'] = False
                
                self.mark_changed()
                return True
            return False
        except Exception as e:
            logger.error(f"Error setting affiliate status for {user_id}: {e}")
            return False

    def approve_affiliate(self, user_id: int, affiliate_code: str):
        """Approve an affiliate application"""
        try:
            user = self.fetch_user(user_id)
            if not user:
                return False
            
            user['is_affiliate'] = True
            user['affiliate_status'] = 'approved'
            user['affiliate_code'] = affiliate_code
            user['affiliate_approved_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            self.users[str(user_id)] = user
            self.db['users'] = self.users
            self.mark_changed()
            return True
        except Exception as e:
            logger.error(f"Error approving affiliate {user_id}: {e}")
            return False

    def get_user_by_affiliate_code(self, affiliate_code: str) -> Optional[Dict]:
        """Get user by affiliate code"""
        try:
            for user in self.users.values():
                if user.get('affiliate_code') == affiliate_code and user.get('is_affiliate', False):
                    return user
            return None
        except Exception as e:
            logger.error(f"Error getting user by affiliate code: {e}")
            return None

    def set_referred_by(self, user_id: int, referred_by_id: int):
        """Set who referred this user"""
        try:
            user = self.fetch_user(user_id)
            referred_by_user = self.fetch_user(referred_by_id)
            
            if not user or not referred_by_user:
                return False
            
            # Set referred_by for the new user
            user['referred_by'] = referred_by_id
            
            # Add to referrals list of the affiliate
            if 'referrals' not in referred_by_user:
                referred_by_user['referrals'] = []
            
            if user_id not in referred_by_user['referrals']:
                referred_by_user['referrals'].append(user_id)
                referred_by_user['referral_count'] = len(referred_by_user['referrals'])
            
            self.users[str(user_id)] = user
            self.users[str(referred_by_id)] = referred_by_user
            self.db['users'] = self.users
            
            # Also store in referrals collection for easier querying
            referral_id = f"{referred_by_id}_{user_id}"
            self.referrals[referral_id] = {
                'affiliate_id': referred_by_id,
                'user_id': user_id,
                'referral_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'has_subscribed': False,
                'commission_earned': 0.0
            }
            self.db['referrals'] = self.referrals
            
            self.mark_changed()
            return True
        except Exception as e:
            logger.error(f"Error setting referred_by for {user_id}: {e}")
            return False

    def add_referral(self, affiliate_id: int, user_id: int):
        """Add a referral (user clicked affiliate link but hasn't subscribed yet)"""
        try:
            referral_id = f"{affiliate_id}_{user_id}"
            
            self.referrals[referral_id] = {
                'affiliate_id': affiliate_id,
                'user_id': user_id,
                'referral_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'has_subscribed': False,
                'commission_earned': 0.0
            }
            
            self.db['referrals'] = self.referrals
            self.mark_changed()
            return True
        except Exception as e:
            logger.error(f"Error adding referral: {e}")
            return False

    def add_commission(self, affiliate_id: int, user_id: int, amount: float, 
                      program: str, plan_type: str, vip_duration: Optional[str] = None):
        """Add commission for an affiliate"""
        try:
            # Update affiliate's earnings
            affiliate = self.fetch_user(affiliate_id)
            if not affiliate:
                return False
            
            current_earnings = affiliate.get('affiliate_earnings', 0.0)
            current_pending = affiliate.get('affiliate_pending', 0.0)
            current_available = affiliate.get('affiliate_available', 0.0)
            
            affiliate['affiliate_earnings'] = current_earnings + amount
            affiliate['affiliate_pending'] = current_pending + amount
            affiliate['affiliate_available'] = current_available + amount
            
            # Add to affiliate's referral record
            if 'referrals' not in affiliate:
                affiliate['referrals'] = []
            
            # Update or create referral record in affiliate's data
            referral_found = False
            for ref in affiliate['referrals']:
                if ref.get('user_id') == user_id:
                    ref['has_subscribed'] = True
                    ref['commission_earned'] = ref.get('commission_earned', 0.0) + amount
                    ref['last_commission_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    referral_found = True
                    break
            
            if not referral_found:
                affiliate['referrals'].append({
                    'user_id': user_id,
                    'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'has_subscribed': True,
                    'commission_earned': amount
                })
            
            # Add to affiliate's commission history
            if 'commission_history' not in affiliate:
                affiliate['commission_history'] = []
            
            affiliate['commission_history'].append({
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'referral_id': user_id,
                'amount': amount,
                'program': program,
                'plan_type': plan_type,
                'vip_duration': vip_duration
            })
            
            self.users[str(affiliate_id)] = affiliate
            self.db['users'] = self.users
            
            # Update referral record
            referral_id = f"{affiliate_id}_{user_id}"
            if referral_id in self.referrals:
                self.referrals[referral_id]['has_subscribed'] = True
                self.referrals[referral_id]['commission_earned'] = amount
                self.referrals[referral_id]['subscription_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Add commission record
            commission_id = f"COMM_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{affiliate_id}"
            self.commissions[commission_id] = {
                'id': commission_id,
                'affiliate_id': affiliate_id,
                'user_id': user_id,
                'amount': amount,
                'program': program,
                'plan_type': plan_type,
                'vip_duration': vip_duration,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            self.db['commissions'] = self.commissions
            self.db['referrals'] = self.referrals
            self.mark_changed()
            
            logger.info(f"Commission added: {amount} for affiliate {affiliate_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding commission: {e}")
            return False

    def get_affiliate_stats(self, user_id: int) -> Dict:
        """Get affiliate statistics"""
        try:
            user = self.fetch_user(user_id)
            if not user or not user.get('is_affiliate'):
                return {
                    'total_referrals': 0,
                    'active_referrals': 0,
                    'total_earnings': 0.0,
                    'pending_payout': user.get('affiliate_pending', 0.0) if user else 0.0,
                    'total_paid': user.get('affiliate_paid', 0.0) if user else 0.0,
                    'available_balance': user.get('affiliate_available', 0.0) if user else 0.0
                }
            
            # Count referrals
            total_referrals = user.get('referral_count', 0)
            
            # Count active referrals (those who have subscribed)
            active_referrals = 0
            for referral_id, referral in self.referrals.items():
                if str(referral['affiliate_id']) == str(user_id) and referral['has_subscribed']:
                    active_referrals += 1
            
            return {
                'total_referrals': total_referrals,
                'active_referrals': active_referrals,
                'total_earnings': user.get('affiliate_earnings', 0.0),
                'pending_payout': user.get('affiliate_pending', 0.0),
                'total_paid': user.get('affiliate_paid', 0.0),
                'available_balance': user.get('affiliate_available', 0.0)
            }
        except Exception as e:
            logger.error(f"Error getting affiliate stats for {user_id}: {e}")
            return {}

    def get_recent_commissions(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get recent commissions for an affiliate"""
        try:
            # Check user's commission history first
            user = self.fetch_user(user_id)
            if user and 'commission_history' in user:
                commissions = user['commission_history']
                commissions.sort(key=lambda x: x.get('date', ''), reverse=True)
                return commissions[:limit]
            
            # Fallback to commission collection
            commissions = []
            for commission in self.commissions.values():
                if str(commission['affiliate_id']) == str(user_id):
                    commissions.append({
                        'amount': commission['amount'],
                        'plan_type': commission['plan_type'],
                        'date': commission['date'],
                        'user_id': commission['user_id']
                    })
            
            # Sort by date descending
            commissions.sort(key=lambda x: x['date'], reverse=True)
            return commissions[:limit]
        except Exception as e:
            logger.error(f"Error getting recent commissions for {user_id}: {e}")
            return []

    def get_all_referrals(self, user_id: int) -> List[Dict]:
        """Get all referrals for an affiliate"""
        try:
            referrals = []
            for referral_id, referral in self.referrals.items():
                if str(referral['affiliate_id']) == str(user_id):
                    referrals.append(referral)
            
            # Sort by date descending
            referrals.sort(key=lambda x: x['referral_date'], reverse=True)
            return referrals
        except Exception as e:
            logger.error(f"Error getting referrals for {user_id}: {e}")
            return []

    def get_commission_history(self, user_id: int) -> List[Dict]:
        """Get commission history for an affiliate"""
        try:
            # Check user's commission history first
            user = self.fetch_user(user_id)
            if user and 'commission_history' in user:
                history = user['commission_history']
                history.sort(key=lambda x: x.get('date', ''), reverse=True)
                return history
            
            # Fallback to commission collection
            history = []
            for commission in self.commissions.values():
                if str(commission['affiliate_id']) == str(user_id):
                    history.append({
                        'amount': commission['amount'],
                        'plan_type': commission['plan_type'],
                        'vip_duration': commission.get('vip_duration'),
                        'date': commission['date'],
                        'user_id': commission['user_id']
                    })
            
            # Sort by date descending
            history.sort(key=lambda x: x['date'], reverse=True)
            return history
        except Exception as e:
            logger.error(f"Error getting commission history for {user_id}: {e}")
            return []

    # ====================
    # PAYOUT SYSTEM METHODS
    # ====================

    def create_payout_request(self, user_id: int, amount: float, method: str, details: str) -> Optional[str]:
        """Create a new payout request"""
        try:
            user = self.fetch_user(user_id)
            if not user:
                return None
            
            # Generate payout ID
            import random
            import string
            payout_id = f"PAYOUT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id}_{''.join(random.choices(string.ascii_uppercase + string.digits, k=4))}"
            
            # Create payout record
            self.payouts[payout_id] = {
                'id': payout_id,
                'user_id': user_id,
                'affiliate_name': user.get('name', 'Unknown'),
                'amount': amount,
                'method': method,
                'details': details,
                'status': 'pending',
                'request_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'processed_date': None,
                'proof_file_id': None
            }
            
            # Update user's pending balance (move from available to pending payout)
            current_pending = user.get('affiliate_pending', 0.0)
            current_available = user.get('affiliate_available', 0.0)
            
            user['affiliate_pending'] = current_pending - amount
            user['affiliate_available'] = current_available - amount
            
            self.users[str(user_id)] = user
            self.db['users'] = self.users
            self.db['payouts'] = self.payouts
            
            self.mark_changed()
            
            logger.info(f"Payout request created: {payout_id} for user {user_id}, amount: {amount}")
            return payout_id
        except Exception as e:
            logger.error(f"Error creating payout request: {e}")
            return None

    def mark_payout_paid(self, payout_id: str) -> bool:
        """Mark a payout as paid"""
        try:
            if payout_id not in self.payouts:
                return False
            
            payout = self.payouts[payout_id]
            user_id = payout['user_id']
            
            # Update payout status
            self.payouts[payout_id]['status'] = 'paid'
            self.payouts[payout_id]['processed_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Update user's paid amount
            user = self.fetch_user(user_id)
            if user:
                current_paid = user.get('affiliate_paid', 0.0)
                user['affiliate_paid'] = current_paid + payout['amount']
                
                self.users[str(user_id)] = user
                self.db['users'] = self.users
            
            self.db['payouts'] = self.payouts
            self.mark_changed()
            return True
        except Exception as e:
            logger.error(f"Error marking payout paid: {e}")
            return False

    def mark_payout_paid_with_proof(self, payout_id: str, proof_file_id: str) -> bool:
        """Mark a payout as paid with proof and reset affiliate balance"""
        try:
            if payout_id not in self.payouts:
                return False
            
            payout = self.payouts[payout_id]
            user_id = payout['user_id']
            
            # Update payout status
            self.payouts[payout_id]['status'] = 'paid'
            self.payouts[payout_id]['processed_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.payouts[payout_id]['proof_file_id'] = proof_file_id
            
            # Update user's paid amount and reset pending balance
            user = self.fetch_user(user_id)
            if user:
                current_paid = user.get('affiliate_paid', 0.0)
                user['affiliate_paid'] = current_paid + payout['amount']
                
                # Reset pending and available balances to zero
                user['affiliate_pending'] = 0.0
                user['affiliate_available'] = max(0.0, user.get('affiliate_earnings', 0.0) - user['affiliate_paid'])
                
                self.users[str(user_id)] = user
                self.db['users'] = self.users
            
            self.db['payouts'] = self.payouts
            self.mark_changed()
            
            logger.info(f"Payout {payout_id} marked as paid with proof, user {user_id} balance reset")
            return True
        except Exception as e:
            logger.error(f"Error marking payout paid with proof: {e}")
            return False

    def reject_payout_request(self, payout_id: str) -> bool:
        """Reject a payout request"""
        try:
            if payout_id not in self.payouts:
                return False
            
            payout = self.payouts[payout_id]
            user_id = payout['user_id']
            
            # Update payout status
            self.payouts[payout_id]['status'] = 'rejected'
            self.payouts[payout_id]['processed_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Return amount to user's available balance
            user = self.fetch_user(user_id)
            if user:
                current_available = user.get('affiliate_available', 0.0)
                current_pending = user.get('affiliate_pending', 0.0)
                
                user['affiliate_available'] = current_available + payout['amount']
                user['affiliate_pending'] = current_pending + payout['amount']
                
                self.users[str(user_id)] = user
                self.db['users'] = self.users
            
            self.db['payouts'] = self.payouts
            self.mark_changed()
            return True
        except Exception as e:
            logger.error(f"Error rejecting payout request: {e}")
            return False

    def get_payout_by_id(self, payout_id: str) -> Optional[Dict]:
        """Get payout by ID"""
        return self.payouts.get(payout_id)

    def get_all_payout_requests(self) -> List[Dict]:
        """Get all payout requests"""
        return list(self.payouts.values())

    def get_processed_payouts(self) -> List[Dict]:
        """Get processed payouts (paid or rejected)"""
        return [
            payout for payout in self.payouts.values()
            if payout['status'] in ['paid', 'rejected']
        ]

    def get_user_payout_history(self, user_id: int) -> List[Dict]:
        """Get payout history for a user"""
        payouts = []
        for payout in self.payouts.values():
            if payout['user_id'] == user_id:
                payouts.append(payout)
        return sorted(payouts, key=lambda x: x['request_date'], reverse=True)

    # ====================
    # ADMIN MANAGEMENT METHODS
    # ====================

    def get_all_affiliates(self) -> List[Dict]:
        """Get all approved affiliates"""
        affiliates = []
        for user in self.users.values():
            if user.get('is_affiliate', False):
                affiliates.append(user)
        return affiliates

    def get_pending_affiliate_applications(self) -> List[Dict]:
        """Get pending affiliate applications"""
        applications = []
        for user in self.users.values():
            if user.get('affiliate_status') == 'pending':
                applications.append(user)
        return applications

    def get_commission_report(self) -> Dict:
        """Get commission report for admin"""
        try:
            total_commissions = sum(commission['amount'] for commission in self.commissions.values())
            total_affiliates = len([u for u in self.users.values() if u.get('is_affiliate', False)])
            
            # Count by plan type
            by_plan_type = {}
            for commission in self.commissions.values():
                plan_type = commission['plan_type']
                if plan_type not in by_plan_type:
                    by_plan_type[plan_type] = 0.0
                by_plan_type[plan_type] += commission['amount']
            
            # Get recent commissions
            recent_commissions = sorted(
                self.commissions.values(),
                key=lambda x: x['date'],
                reverse=True
            )[:10]
            
            # Format recent commissions
            formatted_recent = []
            for commission in recent_commissions:
                affiliate = self.fetch_user(commission['affiliate_id'])
                formatted_recent.append({
                    'amount': commission['amount'],
                    'affiliate_name': affiliate.get('name', 'Unknown') if affiliate else 'Unknown',
                    'date': commission['date']
                })
            
            return {
                'total_commissions': total_commissions,
                'total_affiliates': total_affiliates,
                'total_referrals': len(self.referrals),
                'by_plan_type': by_plan_type,
                'recent_commissions': formatted_recent
            }
        except Exception as e:
            logger.error(f"Error generating commission report: {e}")
            return {}

    def get_affiliate_performance_stats(self) -> Dict:
        """Get affiliate performance statistics"""
        try:
            active_affiliates = []
            for user in self.users.values():
                if user.get('is_affiliate', False):
                    active_affiliates.append(user)
            
            if not active_affiliates:
                return {
                    'active_affiliates': 0,
                    'total_referrals': 0,
                    'conversion_rate': 0.0,
                    'avg_commission': 0.0,
                    'top_performers': [],
                    'academy_commissions': 0.0,
                    'vip_commissions': 0.0
                }
            
            # Calculate metrics
            total_referrals = sum(user.get('referral_count', 0) for user in active_affiliates)
            total_commissions = sum(user.get('affiliate_earnings', 0.0) for user in active_affiliates)
            
            # Calculate conversion rate
            active_referrals = 0
            for referral in self.referrals.values():
                if referral['has_subscribed']:
                    active_referrals += 1
            
            conversion_rate = (active_referrals / len(self.referrals) * 100) if self.referrals else 0.0
            
            # Get top performers (this month)
            current_month = datetime.now().strftime('%Y-%m')
            monthly_commissions = {}
            
            for commission in self.commissions.values():
                commission_month = commission['date'][:7]  # Get YYYY-MM
                if commission_month == current_month:
                    affiliate_id = commission['affiliate_id']
                    if affiliate_id not in monthly_commissions:
                        monthly_commissions[affiliate_id] = 0.0
                    monthly_commissions[affiliate_id] += commission['amount']
            
            # Get top 5 performers
            top_performers = []
            for affiliate_id, earnings in sorted(monthly_commissions.items(), key=lambda x: x[1], reverse=True)[:5]:
                affiliate = self.fetch_user(affiliate_id)
                if affiliate:
                    top_performers.append({
                        'name': affiliate.get('name', 'Unknown'),
                        'earnings': earnings,
                        'referrals': affiliate.get('referral_count', 0)
                    })
            
            # Calculate commission distribution
            academy_commissions = 0.0
            vip_commissions = 0.0
            
            for commission in self.commissions.values():
                if commission['plan_type'] == 'academy':
                    academy_commissions += commission['amount']
                else:
                    vip_commissions += commission['amount']
            
            return {
                'active_affiliates': len(active_affiliates),
                'total_referrals': total_referrals,
                'conversion_rate': conversion_rate,
                'avg_commission': total_commissions / len(active_affiliates) if active_affiliates else 0.0,
                'top_performers': top_performers,
                'academy_commissions': academy_commissions,
                'vip_commissions': vip_commissions
            }
        except Exception as e:
            logger.error(f"Error getting affiliate performance stats: {e}")
            return {}

    def get_payout_requests_by_status(self, status: str = 'pending') -> List[Dict]:
        """Get payout requests by status"""
        return [
            payout for payout in self.payouts.values()
            if payout['status'] == status
        ]

    def get_commission_summary(self, user_id: int) -> Dict:
        """Get commission summary for a user"""
        try:
            user = self.fetch_user(user_id)
            if not user or not user.get('is_affiliate'):
                return {}
            
            # Calculate monthly earnings
            monthly_earnings = {}
            for commission in self.commissions.values():
                if str(commission['affiliate_id']) == str(user_id):
                    month = commission['date'][:7]  # YYYY-MM
                    if month not in monthly_earnings:
                        monthly_earnings[month] = 0.0
                    monthly_earnings[month] += commission['amount']
            
            # Get top earning plans
            plan_earnings = {}
            for commission in self.commissions.values():
                if str(commission['affiliate_id']) == str(user_id):
                    plan_key = f"{commission['plan_type']}_{commission.get('vip_duration', '')}"
                    if plan_key not in plan_earnings:
                        plan_earnings[plan_key] = 0.0
                    plan_earnings[plan_key] += commission['amount']
            
            return {
                'total_earnings': user.get('affiliate_earnings', 0.0),
                'total_paid': user.get('affiliate_paid', 0.0),
                'pending_payout': user.get('affiliate_pending', 0.0),
                'available_balance': user.get('affiliate_available', 0.0),
                'monthly_earnings': monthly_earnings,
                'plan_earnings': plan_earnings,
                'referral_count': user.get('referral_count', 0)
            }
        except Exception as e:
            logger.error(f"Error getting commission summary for {user_id}: {e}")
            return {}

    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        try:
            total_users = len(self.users)
            total_affiliates = len([u for u in self.users.values() if u.get('is_affiliate', False)])
            total_commissions = sum(commission['amount'] for commission in self.commissions.values())
            total_payouts = sum(payout['amount'] for payout in self.payouts.values() if payout['status'] == 'paid')
            
            # Calculate active subscriptions
            active_subscriptions = 0
            for user in self.users.values():
                for program in ['crypto', 'forex']:
                    for plan_type in ['academy', 'vip']:
                        expiry_key = f"{program}_{plan_type}_expiry_date"
                        if user.get(expiry_key):
                            try:
                                expiry_date = datetime.strptime(user[expiry_key], '%Y-%m-%d')
                                if expiry_date > datetime.now():
                                    active_subscriptions += 1
                            except:
                                pass
            
            return {
                'total_users': total_users,
                'total_affiliates': total_affiliates,
                'total_commissions': total_commissions,
                'total_payouts': total_payouts,
                'active_subscriptions': active_subscriptions,
                'pending_payout_requests': len([p for p in self.payouts.values() if p['status'] == 'pending']),
                'total_referrals': len(self.referrals)
            }
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}

    # ====================
    # BACKUP AND MAINTENANCE
    # ====================

    def backup_database(self, backup_file: str = None):
        """Create a backup of the database"""
        try:
            if not backup_file:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_file = f"backup_users_{timestamp}.json"
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(self.db, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Database backed up to {backup_file}")
            return backup_file
        except Exception as e:
            logger.error(f"Error backing up database: {e}")
            return None

    def cleanup_old_data(self, days_old: int = 30):
        """Clean up old data (e.g., expired subscriptions)"""
        try:
            cleaned_count = 0
            current_date = datetime.now()
            
            for user_id, user in self.users.items():
                # Check for expired subscriptions
                for program in ['crypto', 'forex']:
                    for plan_type in ['academy', 'vip']:
                        expiry_key = f"{program}_{plan_type}_expiry_date"
                        if user.get(expiry_key):
                            try:
                                expiry_date = datetime.strptime(user[expiry_key], '%Y-%m-%d')
                                if expiry_date < current_date - timedelta(days=days_old):
                                    user[expiry_key] = None
                                    cleaned_count += 1
                            except:
                                pass
                
                # Clean old pending POP (older than 7 days)
                if user.get('pending_pop'):
                    try:
                        uploaded_at = datetime.strptime(user['pending_pop']['uploaded_at'], '%Y-%m-%d %H:%M:%S')
                        if uploaded_at < current_date - timedelta(days=7):
                            user['pending_pop'] = None
                            cleaned_count += 1
                    except:
                        pass
                
                self.users[user_id] = user
            
            self.db['users'] = self.users
            self.mark_changed()
            
            logger.info(f"Cleaned up {cleaned_count} old records")
            return cleaned_count
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
            return 0

    def cleanup_database(self):
        """Clean up database - alias for compatibility"""
        return self.cleanup_old_data()

    def periodic_backup(self, interval_hours: int = 24):
        """Create periodic backups of the database"""
        try:
            # Create backup directory
            backup_dir = os.path.join(os.path.dirname(self.db_file), 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(backup_dir, f'users_backup_{timestamp}.json')
            
            # Copy current database to backup
            shutil.copy2(self.db_file, backup_file)
            
            logger.info(f"Created database backup: {backup_file}")
            
            # Clean up old backups (keep last 7 days)
            self.cleanup_old_backups(backup_dir, days_to_keep=7)
            
            return backup_file
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return None

    def cleanup_old_backups(self, backup_dir: str, days_to_keep: int = 7):
        """Remove old backup files"""
        try:
            current_time = time.time()
            cutoff_time = current_time - (days_to_keep * 24 * 3600)
            
            for filename in os.listdir(backup_dir):
                if filename.startswith('users_backup_'):
                    file_path = os.path.join(backup_dir, filename)
                    # Get file modification time
                    file_mtime = os.path.getmtime(file_path)
                    
                    if file_mtime < cutoff_time:
                        os.remove(file_path)
                        logger.info(f"Removed old backup: {filename}")
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")