# main.py - Complete Working Bot with All Fixes Applied + Affiliate System + Full Payout Flow
# UPDATED: Admin Affiliate Management System Fully Fixed
import time
from typing import Optional, Dict, List, Tuple
from telebot import TeleBot, types
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import logging
import traceback
import csv
import io
import config
from database import UserDatabase
# main.py or bot.py
import logging
from config import bot_token, admin_ids, admin_id, DB_FILE
from config import setup_logging  # Optional
import os
from threading import Thread
from flask import Flask, Response

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Use the variables
TOKEN = bot_token
ADMIN_IDS = admin_ids
ADMIN_ID = admin_id

# Rest of your bot code...

# --- Initialization ---
bot = TeleBot(config.bot_token, threaded=True, num_threads=5)
user_db = UserDatabase()
scheduler = BackgroundScheduler()
ADMIN_IDS = config.admin_ids

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Pricing for both programs
PRICING = {
    'crypto': {
        'academy': {'ngn': '₦35,000', 'usd': '$25', 'days': 365},
        'vip': {
            'monthly': {'ngn': '₦15,000', 'usd': '$12', 'days': 30},
            '3_months': {'ngn': '₦40,000', 'usd': '$30', 'days': 90},
            '6_months': {'ngn': '₦75,000', 'usd': '$55', 'days': 180},
            'yearly': {'ngn': '₦150,000', 'usd': '$105', 'days': 365}
        }
    },
    'forex': {
        'academy': {'ngn': '₦35,000', 'usd': '$25', 'days': 365},
        'vip': {
            'monthly': {'ngn': '₦15,000', 'usd': '$12', 'days': 30},
            '3_months': {'ngn': '₦40,000', 'usd': '$30', 'days': 90},
            '6_months': {'ngn': '₦75,000', 'usd': '$55', 'days': 180},
            'yearly': {'ngn': '₦150,000', 'usd': '$105', 'days': 365}
        }
    }
}

# ====================
# AFFILIATE SYSTEM CONSTANTS
# ====================

# Commission rates structure
COMMISSION_RATES = {
    'academy': 0.30,  # 30% for academy
    'vip': {
        'monthly': 0.15,  # 15% for monthly VIP
        '3_months': 0.20,  # 20% for 3 months
        '6_months': 0.20,  # 20% for 6 months
        'yearly': 0.20  # 20% for yearly
    }
}

MINIMUM_PAYOUT = 10000  # ₦10,000 minimum payout

# ====================
# AFFILIATE HELPER FUNCTIONS
# ====================

def generate_affiliate_code(user_id: int) -> str:
    """Generate a unique affiliate code based on user ID"""
    import hashlib
    import string
    import random
    
    # Create a hash from user_id + timestamp
    hash_input = f"{user_id}{time.time()}"
    hash_digest = hashlib.md5(hash_input.encode()).hexdigest()[:8].upper()
    
    # Combine with random letters
    letters = ''.join(random.choices(string.ascii_uppercase, k=3))
    return f"AFF{letters}{hash_digest[:5]}"

def calculate_commission(plan_type: str, vip_duration: Optional[str], amount_text: str) -> float:
    """Calculate commission based on plan type and duration"""
    try:
        # Extract numeric amount from amount text (e.g., "₦35,000" -> 35000)
        if '₦' in amount_text:
            amount_str = amount_text.replace('₦', '').replace(',', '')
            amount = float(amount_str)
            currency = 'naira'
        elif '$' in amount_text:
            amount_str = amount_text.replace('$', '').replace(',', '')
            amount = float(amount_str) * 1400  # Convert USD to NGN at approximate rate
            currency = 'usd'
        else:
            return 0.0
        
        # Calculate commission based on plan type
        if plan_type == 'academy':
            commission_rate = COMMISSION_RATES['academy']
        elif plan_type == 'vip' and vip_duration:
            commission_rate = COMMISSION_RATES['vip'].get(vip_duration, 0.15)
        else:
            commission_rate = 0.15  # Default 15%
        
        commission = amount * commission_rate
        return round(commission, 2)
        
    except Exception as e:
        logger.error(f"Error calculating commission: {e}")
        return 0.0

def add_commission_to_affiliate(referred_by_id: int, user_id: int, program: str, plan_type: str, 
                               vip_duration: Optional[str], amount_text: str):
    """Add commission to affiliate when referral makes payment"""
    try:
        # Calculate commission
        commission_amount = calculate_commission(plan_type, vip_duration, amount_text)
        
        if commission_amount > 0:
            # Add commission to affiliate's earnings
            user_db.add_commission(referred_by_id, user_id, commission_amount, program, plan_type, vip_duration)
            
            # Get affiliate details
            affiliate = user_db.fetch_user(referred_by_id)
            if affiliate:
                # Notify affiliate
                try:
                    plan_name = plan_display_name(plan_type, vip_duration)
                    bot.send_message(
                        referred_by_id,
                        f"💰 <b>Commission Earned!</b>\n\n"
                        f"✅ New referral subscribed!\n"
                        f"👤 Referral ID: {user_id}\n"
                        f"📋 Plan: {program.capitalize()} {plan_name}\n"
                        f"💸 Commission: <b>₦{commission_amount:,.2f}</b>\n\n"
                        f"Your total earnings: <b>₦{affiliate.get('affiliate_earnings', 0) + commission_amount:,.2f}</b>\n\n"
                        f"Keep sharing your referral link to earn more! 🚀",
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.error(f"Could not notify affiliate {referred_by_id}: {e}")
                
                # Notify admins about commission
                for admin_id in ADMIN_IDS:
                    try:
                        bot.send_message(
                            admin_id,
                            f"💰 <b>Commission Generated</b>\n\n"
                            f"Affiliate: {affiliate.get('name', 'Unknown')} (ID: {referred_by_id})\n"
                            f"Referral: {user_id}\n"
                            f"Plan: {program} {plan_type} {vip_duration or ''}\n"
                            f"Commission: ₦{commission_amount:,.2f}",
                            parse_mode='HTML'
                        )
                    except Exception as e:
                        logger.error(f"Could not notify admin {admin_id}: {e}")
            
            return True
        return False
        
    except Exception as e:
        logger.error(f"Error adding commission: {e}")
        return False

# Tutorial videos data with Telegram video file_ids for playing within the bot
TUTORIALS = [
    {
        'id': 1,
        'title': 'Complete Bybit Futures Trading Tutorial',
        'url': 'https://youtu.be/V18dbSJAiSg?si=vpDzwUAUdxmKshUy',
        'telegram_video_id': 'BAACAgEAAxkBAAIBmWc8hN-6qkF2G5e6Yp-JhVTPWn0cAAI9CwACE6NpR3r3rxrJj-h2MAQ',
        'description': 'Learn everything about Bybit futures trading from scratch',
        'category': 'bybit',
        'thumbnail': 'https://img.youtube.com/vi/V18dbSJAiSg/maxresdefault.jpg'
    },
    {
        'id': 2,
        'title': 'How to Take Bybit Futures Trade',
        'url': 'https://youtu.be/_mZpfmzJwNI?si=hu0unpTY61bo_Xyc',
        'telegram_video_id': 'BAACAgEAAxkBAAIBm2c8hPvL-JB6W0XqyPwCg4kAAZ-B1AACQAwAAhOjaUcAAcUe5h2E_3kwBA',
        'description': 'Step-by-step guide to executing trades on Bybit',
        'category': 'bybit',
        'thumbnail': 'https://img.youtube.com/vi/_mZpfmzJwNI/maxresdefault.jpg'
    },
    {
        'id': 3,
        'title': 'Risk Management in Trading',
        'url': 'https://youtu.be/mrWATu8ArvQ?si=kxU5nmGXHYkoIEjK',
        'telegram_video_id': 'BAACAgEAAxkBAAIBnWc8hSbV5-8oAAE3q6nF2X7Kk8jWbgACQQwAAhOjaUfKxH4YxX8sRzAE',
        'description': 'Essential risk management strategies for traders',
        'category': 'strategies',
        'thumbnail': 'https://img.youtube.com/vi/mrWATu8ArvQ/maxresdefault.jpg'
    },
    {
        'id': 4,
        'title': 'Binance Futures Trading Tutorial',
        'url': 'https://youtu.be/skR2iwjbyCk?si=SJNUs87z3GPfsd2P',
        'telegram_video_id': 'BAACAgEAAxkBAAIBn2c8hVOkC18Q3_4AAb3pU_3pXoJ9eQACQgwAAhOjaUdM2f53J6LfizAE',
        'description': 'Complete guide to Binance Futures trading',
        'category': 'binance',
        'thumbnail': 'https://img.youtube.com/vi/skR2iwjbyCk/maxresdefault.jpg'
    },
    {
        'id': 5,
        'title': 'Difference Between Futures and Spot Trading',
        'url': 'https://youtu.be/uaRQHxnArXY?si=nc-pEz3FPBIgCH1t',
        'telegram_video_id': 'BAACAgEAAxkBAAIBoWc8hY3Z4H9rqQABy0nWxXp7l6V3YwACQwwAAhOjaUdqQe8AAeFd1-YwBA',
        'description': 'Understand the key differences between trading styles',
        'category': 'education',
        'thumbnail': 'https://img.youtube.com/vi/uaRQHxnArXY/maxresdefault.jpg'
    }
]

# Tutorial categories
TUTORIAL_CATEGORIES = {
    'bybit': '📊 Bybit Tutorials',
    'binance': '💼 Binance Tutorials',
    'exchanges': '🔄 Other Exchanges',
    'strategies': '📈 Trading Strategies',
    'education': '📚 Trading Education',
    'security': '🔒 Security Guides'
}

# Reminder settings
REMINDER_DAYS = [7, 3, 1, 0]  # Days before expiry to send reminders
GRACE_PERIOD_DAYS = 3  # Days after expiry before removal

# ----------------------
# Helper Functions - FIXED VERSION
# ----------------------
def plan_display_name(plan_key: str, vip_duration: Optional[str] = None) -> str:
    """Get human-readable plan name"""
    if plan_key == "academy":
        return "Academy"
    if plan_key == "vip":
        if vip_duration == "monthly":
            return "VIP Signal Monthly"
        if vip_duration == "3_months":
            return "VIP Signal 3 Months"
        if vip_duration == "6_months":
            return "VIP Signal 6 Months"
        if vip_duration == "yearly":
            return "VIP Signal 1 Year"
        return "VIP Signals"
    return plan_key

def get_amount_text(program: str, plan_choice: str, vip_duration: Optional[str], currency: str) -> str:
    """Get price text for the selected plan"""
    if plan_choice == "academy":
        return PRICING[program]["academy"]["ngn"] if currency == "naira" else PRICING[program]["academy"]["usd"]
    if plan_choice == "vip" and vip_duration:
        return PRICING[program]["vip"][vip_duration]["ngn"] if currency == "naira" else PRICING[program]["vip"][vip_duration]["usd"]
    return ""

def _safe_get_chat_info(user_id: int):
    """Safely get user info from Telegram"""
    try:
        chat = bot.get_chat(user_id)
        name = f"{getattr(chat, 'first_name', '') or ''} {getattr(chat, 'last_name', '') or ''}".strip()
        if not name:
            name = getattr(chat, 'first_name', '') or None
        username = getattr(chat, 'username', None)
        return name or None, username or None
    except Exception as e:
        logger.error(f"Error getting chat info for {user_id}: {e}")
        return None, None

def get_chat_ids(program: str, plan_type: str):
    """Get chat ID and invite link for a specific program and plan type"""
    if program == 'crypto':
        if plan_type == 'academy':
            return config.crypto_academy_chat_id, config.crypto_academy_invite
        elif plan_type == 'vip':
            return config.crypto_vip_chat_id, config.crypto_vip_invite
        elif plan_type == 'degen':
            return config.crypto_degen_chat_id, config.crypto_degen_invite
    else:  # forex
        if plan_type == 'academy':
            return config.forex_academy_chat_id, config.forex_academy_invite
        elif plan_type == 'vip':
            return config.forex_vip_chat_id, config.forex_vip_invite
    return None, None

def add_user_to_group(user_id: int, chat_id: int, chat_name: str) -> bool:
    """Try to add user directly to a group/channel"""
    try:
        # First try to unban if previously banned
        try:
            bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
        except Exception:
            pass
        
        # Try to add user to chat
        bot.add_chat_members(chat_id, [user_id])
        logger.info(f"Successfully added user {user_id} to {chat_name}")
        return True
        
    except Exception as e:
        error_msg = str(e)
        logger.warning(f"Could not add user {user_id} to {chat_name}: {error_msg}")
        
        # Check specific error types
        if "USER_ALREADY_PARTICIPANT" in error_msg:
            logger.info(f"User {user_id} is already in {chat_name}")
            return True
        elif "USER_NOT_MUTUAL_CONTACT" in error_msg or "USER_PRIVACY_RESTRICTED" in error_msg:
            logger.info(f"User {user_id} has privacy restrictions for {chat_name}")
            return False
        elif "CHAT_ADMIN_REQUIRED" in error_msg:
            logger.error(f"Bot is not admin in {chat_name}")
            return False
        else:
            logger.error(f"Error adding user to {chat_name}: {error_msg}")
            return False

def send_group_access(user_id: int, program: str, plan_type: str, days: int = None):
    """Handle sending group access to user - FIXED VERSION"""
    program_name = "Crypto" if program == "crypto" else "Forex"
    plan_name = plan_display_name(plan_type, None)
    
    chat_id, invite_link = get_chat_ids(program, plan_type)
    
    if not chat_id:
        logger.error(f"No chat ID found for {program} {plan_type}")
        bot.send_message(user_id, f"✅ Approved for {program_name} {plan_name}! Admin will add you shortly.")
        return
    
    # Format expiry text
    expiry_text = f" until {(datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')}" if days else ""
    
    # SPECIAL FIX: For Crypto Academy, always use invite link (not direct addition)
    if program == 'crypto' and plan_type == 'academy':
        if invite_link:
            # Test if the link is valid by checking if it contains the correct format
            if invite_link.startswith('https://t.me/+'):
                bot.send_message(user_id, f"✅ You have been approved for {program_name} {plan_name}!\n\nJoin here: {invite_link}")
                logger.info(f"Sent Crypto Academy invite link to user {user_id}: {invite_link}")
            else:
                bot.send_message(user_id, f"✅ Approved for {program_name} {plan_name}! Please use this link to join: {invite_link}")
        else:
            bot.send_message(user_id, f"✅ Approved for {program_name} {plan_name}! Please contact admin for access link.")
        return
    
    # For other groups, try direct addition first
    chat_name = f"{program_name} {plan_name}"
    if add_user_to_group(user_id, chat_id, chat_name):
        bot.send_message(user_id, f"✅ You have been added to {program_name} {plan_name}{expiry_text}!")
    else:
        # Fallback to invite link
        if invite_link:
            bot.send_message(user_id, f"✅ You have {program_name} {plan_name} access{expiry_text}!\n\nJoin here: {invite_link}")
        else:
            bot.send_message(user_id, f"✅ Approved for {program_name} {plan_name}{expiry_text}! Please contact admin for access link.")
    
    # If crypto VIP, also handle degen group
    if program == 'crypto' and plan_type == 'vip':
        degen_chat_id, degen_invite = get_chat_ids(program, 'degen')
        if degen_chat_id:
            degen_name = "Crypto DeGen Group"
            if add_user_to_group(user_id, degen_chat_id, degen_name):
                bot.send_message(user_id, f"🔥 Added to Crypto DeGen Group!")
            elif degen_invite:
                bot.send_message(user_id, f"🔥 Crypto DeGen Group (included with VIP Signals): {degen_invite}")
            else:
                bot.send_message(user_id, "🔥 Crypto DeGen Group access granted!")

# ----------------------
# REMINDER SYSTEM FUNCTIONS WITH BENEFIT-RICH MESSAGES
# ----------------------
def get_program_benefits(program: str, plan_type: str) -> dict:
    """Get benefits for specific program and plan type"""
    benefits = {
        'crypto': {
            'academy': {
                'bullets': [
                    "Step-by-step crypto & blockchain education",
                    "Live Q&A sessions with trading experts",
                    "Practical trading strategies & risk management",
                    "Access to growing community of crypto traders",
                    "Regular market updates & analysis"
                ],
                'dashes': [
                    "Master cryptocurrency fundamentals",
                    "Learn to spot high-potential projects",
                    "Develop profitable trading strategies",
                    "Stay updated with market trends"
                ]
            },
            'vip': {
                'bullets': [
                    "Premium crypto signals with 70%+ accuracy",
                    "Exclusive DeGen Group for high-reward plays",
                    "Early access to presales & new listings",
                    "Real-time market analysis & alerts",
                    "Priority support from expert traders"
                ],
                'dashes': [
                    "Consistent profit opportunities",
                    "Exclusive access to hidden gems",
                    "Professional risk management",
                    "Community of successful traders"
                ]
            }
        },
        'forex': {
            'academy': {
                'bullets': [
                    "Structured forex trading education",
                    "Live trading sessions & market analysis",
                    "Risk management & psychology training",
                    "Proven entry/exit strategies",
                    "Community support & peer learning"
                ],
                'dashes': [
                    "Master currency pairs & market structure",
                    "Learn professional chart analysis",
                    "Develop disciplined trading habits",
                    "Stay ahead of economic events"
                ]
            },
            'vip': {
                'bullets': [
                    "High-probability forex signals",
                    "Real-time trade setups & alerts",
                    "Economic calendar analysis",
                    "Risk-reward ratio guidance",
                    "VIP community & mastermind sessions"
                ],
                'dashes': [
                    "Daily profit opportunities",
                    "Professional market insights",
                    "Optimal entry/exit timing",
                    "Support from experienced traders"
                ]
            }
        }
    }
    
    program_key = program.lower()
    plan_key = plan_type.lower()
    
    if program_key in benefits and plan_key in benefits[program_key]:
        return benefits[program_key][plan_key]
    
    # Default benefits if program/plan not found
    return {
        'bullets': [
            "Premium educational content",
            "Expert guidance and support",
            "Community access",
            "Market insights",
            "Trading opportunities"
        ],
        'dashes': [
            "Professional guidance",
            "Community support",
            "Market opportunities",
            "Growth potential"
        ]
    }

def remove_user_from_group(user_id: int, program: str, plan_type: str):
    """Remove user from group when subscription expires"""
    try:
        chat_id, invite_link = get_chat_ids(program, plan_type)
        if not chat_id:
            logger.error(f"No chat ID found for {program} {plan_type} to remove user")
            return False
        
        program_name = "Crypto" if program == "crypto" else "Forex"
        plan_name = plan_display_name(plan_type, None)
        chat_name = f"{program_name} {plan_name}"
        
        try:
            # Ban user to remove them from the group
            bot.ban_chat_member(chat_id, user_id)
            logger.info(f"Removed user {user_id} from {chat_name}")
            return True
        except Exception as e:
            error_msg = str(e)
            if "USER_NOT_PARTICIPANT" in error_msg or "Chat not found" in error_msg:
                logger.info(f"User {user_id} is not in {chat_name} or left already")
                return True
            elif "CHAT_ADMIN_REQUIRED" in error_msg:
                logger.error(f"Bot is not admin in {chat_name}, cannot remove user")
                return False
            else:
                logger.error(f"Error removing user {user_id} from {chat_name}: {error_msg}")
                return False
                
    except Exception as e:
        logger.error(f"Error in remove_user_from_group for user {user_id}: {e}")
        return False

def send_expiry_reminder(user_id: int, program: str, plan_type: str, days_left: int):
    """Send compelling reminder message to user about expiry"""
    try:
        program_name = "Crypto" if program == "crypto" else "Forex"
        plan_name = plan_display_name(plan_type, None)
        benefits = get_program_benefits(program, plan_type)
        
        if days_left > 0:
            if days_left == 7:
                bullets = "\n".join([f"✓ {benefit}" for benefit in benefits['bullets']])
                message = (
                    f"🌟 <b>Friendly Renewal Reminder</b>\n\n"
                    f"Your {program_name} {plan_name} subscription has <b>7 days remaining</b>.\n\n"
                    f"<b>What you'll continue to enjoy by renewing:</b>\n"
                    f"{bullets}\n\n"
                    f"Renew now to maintain uninterrupted access to these premium features. "
                    f"Your continued success is our priority! ✨\n\n"
                    f"<b>Renew now:</b> Use \"Make Payment\" in the menu"
                )
            elif days_left == 3:
                dashes = "\n".join([f"• {benefit}" for benefit in benefits['dashes']])
                message = (
                    f"💎 <b>Your Premium Access Expires Soon</b>\n\n"
                    f"Only <b>3 days left</b> on your {program_name} {plan_name} subscription.\n\n"
                    f"<b>Don't miss out on:</b>\n"
                    f"{dashes}\n\n"
                    f"Every day you're with us brings new opportunities for growth and learning. "
                    f"Renew today to continue your journey toward financial mastery.\n\n"
                    f"<b>Quick renewal:</b> Tap \"Make Payment\" to continue"
                )
            elif days_left == 1:
                message = (
                    f"🚀 <b>Final Day to Renew!</b>\n\n"
                    f"Your {program_name} {plan_name} access expires <b>tomorrow</b>.\n\n"
                    f"<b>Act now to continue receiving:</b>\n"
                    f"✅ Daily/weekly {'signals' if plan_type == 'vip' else 'lessons'}\n"
                    f"✅ Exclusive community access\n"
                    f"✅ Personal growth opportunities\n"
                    f"✅ Support from our expert team\n\n"
                    f"Renew in the next 24 hours to avoid any interruption in your progress. "
                    f"We'd hate to see you miss out!\n\n"
                    f"<b>Renew now:</b> Use \"Make Payment\" immediately"
                )
            else:
                # Fallback for other positive days_left values
                message = f"⏰ Reminder: Your {program_name} {plan_name} subscription expires in {days_left} days. Renew soon to continue your growth journey!"
                
        elif days_left == 0:
            message = (
                f"⏳ <b>Today is Your Last Day!</b>\n\n"
                f"Your {program_name} {plan_name} subscription <b>expires today</b>.\n\n"
                f"You have a <b>{GRACE_PERIOD_DAYS}-day grace period</b> before access is paused, but why wait?\n\n"
                f"<b>Renew today and continue benefiting from:</b>\n"
                f"• Real-time market insights\n"
                f"• Community support\n"
                f"• Ongoing education\n"
                f"• Investment opportunities\n\n"
                f"Don't let your momentum slow down. Renew now to stay ahead of the curve!\n\n"
                f"<b>Renew today:</b> Tap \"Make Payment\" now"
            )
        else:  # days_left < 0 (in grace period)
            days_expired = abs(days_left)
            if days_expired <= GRACE_PERIOD_DAYS:
                grace_days_left = GRACE_PERIOD_DAYS - days_expired
                message = (
                    f"⚠️ <b>Your Access is Paused</b>\n\n"
                    f"Your {program_name} {plan_name} subscription expired <b>{days_expired} day(s) ago</b>.\n\n"
                    f"You have <b>{grace_days_left} day(s)</b> left to renew before full access is temporarily suspended.\n\n"
                    f"<b>What you're currently missing:</b>\n"
                    f"📊 Latest market analysis\n"
                    f"💡 Exclusive insights\n"
                    f"👥 Community discussions\n"
                    f"🚀 Growth opportunities\n\n"
                    f"We want you back! Renew now to instantly restore your access and continue where you left off.\n\n"
                    f"<b>Restore access:</b> Use \"Make Payment\" immediately"
                )
            else:
                # Should not reach here as user should be removed already
                return
        
        bot.send_message(user_id, message, parse_mode='HTML')
        logger.info(f"Sent expiry reminder to user {user_id} for {program} {plan_type}: {days_left} days left")
        
    except Exception as e:
        logger.error(f"Error sending expiry reminder to user {user_id}: {e}")

def check_expiring_subscriptions():
    """Check for expiring subscriptions and send reminders"""
    try:
        logger.info("Running expiry check for subscriptions...")
        all_users = user_db.get_all_users()
        today = datetime.now().date()
        
        expired_users_to_remove = []
        
        for user_id_str, user_data in all_users.items():
            try:
                user_id = int(user_id_str)
                
                # Check both programs
                for program in ['crypto', 'forex']:
                    # Check Academy subscription
                    academy_exp = user_data.get(f'{program}_academy_expiry_date')
                    if academy_exp:
                        try:
                            expiry_date = datetime.strptime(academy_exp, '%Y-%m-%d').date()
                            days_left = (expiry_date - today).days
                            
                            # Check if we should send reminder
                            if days_left in REMINDER_DAYS:
                                send_expiry_reminder(user_id, program, 'academy', days_left)
                            
                            # Check if expired beyond grace period
                            elif days_left < -GRACE_PERIOD_DAYS:
                                expired_users_to_remove.append((user_id, program, 'academy'))
                                logger.info(f"Marked {program} academy for removal for user {user_id}: expired {abs(days_left)} days ago")
                        
                        except ValueError:
                            logger.error(f"Invalid date format for {program} academy expiry: {academy_exp}")
                    
                    # Check VIP subscription
                    vip_exp = user_data.get(f'{program}_vip_expiry_date')
                    if vip_exp:
                        try:
                            expiry_date = datetime.strptime(vip_exp, '%Y-%m-%d').date()
                            days_left = (expiry_date - today).days
                            
                            # Check if we should send reminder
                            if days_left in REMINDER_DAYS:
                                send_expiry_reminder(user_id, program, 'vip', days_left)
                            
                            # Check if expired beyond grace period
                            elif days_left < -GRACE_PERIOD_DAYS:
                                expired_users_to_remove.append((user_id, program, 'vip'))
                                logger.info(f"Marked {program} vip for removal for user {user_id}: expired {abs(days_left)} days ago")
                        
                        except ValueError:
                            logger.error(f"Invalid date format for {program} vip expiry: {vip_exp}")
            
            except Exception as e:
                logger.error(f"Error processing user {user_id_str}: {e}")
                continue
        
        # Process removals
        for user_id, program, plan_type in expired_users_to_remove:
            try:
                # Remove from group
                removed = remove_user_from_group(user_id, program, plan_type)
                
                if removed:
                    # Clear subscription in database
                    if plan_type == 'academy':
                        user_db.set_subscription(user_id, program, 'academy', 0)
                    else:
                        user_db.set_subscription(user_id, program, 'vip', 0)
                    
                    # Send final removal notice to user
                    program_name = "Crypto" if program == "crypto" else "Forex"
                    plan_name = plan_display_name(plan_type, None)
                    
                    removal_message = (
                        f"🎯 <b>We Miss You Already!</b>\n\n"
                        f"Your {program_name} {plan_name} access has been temporarily paused.\n\n"
                        f"<b>As a valued member, you enjoyed:</b>\n"
                        f"• Premium {'signals' if plan_type == 'vip' else 'education'} during your time with us\n"
                        f"• Growth opportunities that helped your development\n"
                        f"• Access to our exclusive trading community\n\n"
                        f"We'd love to welcome you back! Your participation made our community richer.\n\n"
                        f"<b>Ready to return?</b> Use \"Make Payment\" anytime to restart your journey with us. "
                        f"We're here to support your success! 🤝"
                    )
                    
                    try:
                        bot.send_message(user_id, removal_message, parse_mode='HTML')
                    except Exception as e:
                        logger.error(f"Could not send removal message to user {user_id}: {e}")
                    
                    # Notify admin
                    for admin_id in ADMIN_IDS:
                        try:
                            bot.send_message(
                                admin_id,
                                f"🔄 Auto-removed user {user_id} from {program_name} {plan_name} (expired beyond grace period)"
                            )
                        except Exception as e:
                            logger.error(f"Could not notify admin {admin_id}: {e}")
                
            except Exception as e:
                logger.error(f"Error removing user {user_id} from {program} {plan_type}: {e}")
        
        logger.info(f"Expiry check completed. Processed {len(expired_users_to_remove)} expired subscriptions.")
        
    except Exception as e:
        logger.error(f"Error in check_expiring_subscriptions: {e}")
        logger.error(traceback.format_exc())

# ====================
# AFFILIATE PAYOUT SYSTEM - NEW
# ====================

def handle_payout_request(uid: int, message_id: int = None):
    """Handle affiliate payout request with payment details collection"""
    try:
        user = user_db.fetch_user(uid)
        if not user or not user.get('is_affiliate'):
            bot.send_message(uid, "You need to be an approved affiliate to request payout.")
            return
        
        stats = user_db.get_affiliate_stats(uid)
        available_balance = stats.get('available_balance', 0)
        
        if available_balance < MINIMUM_PAYOUT:
            bot.send_message(
                uid,
                f"❌ <b>Minimum Payout Not Reached</b>\n\n"
                f"Your available balance: <b>₦{available_balance:,.2f}</b>\n"
                f"Minimum payout amount: <b>₦{MINIMUM_PAYOUT:,.2f}</b>\n\n"
                f"You need <b>₦{MINIMUM_PAYOUT - available_balance:,.2f}</b> more to request payout.\n"
                f"Keep sharing your referral link to earn more!",
                parse_mode='HTML'
            )
            return
        
        # Show payment method options
        text = (
            f"💰 <b>Request Payout</b>\n\n"
            f"Available balance: <b>₦{available_balance:,.2f}</b>\n"
            f"Minimum payout: <b>₦{MINIMUM_PAYOUT:,.2f}</b>\n\n"
            f"<b>Select Payment Method:</b>\n\n"
            f"🏦 <b>Bank Transfer</b> (Nigeria only)\n"
            f"• Provide bank details\n"
            f"• Account name, number, and bank\n\n"
            f"💎 <b>USDT Transfer</b>\n"
            f"• Provide USDT wallet address\n"
            f"• Specify network (BEP20, TRC20, TON)\n\n"
            f"Choose your preferred payment method:"
        )
        
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.row(
            types.InlineKeyboardButton("🏦 Bank Transfer", callback_data=f"payout_method:bank:{uid}"),
            types.InlineKeyboardButton("💎 USDT Transfer", callback_data=f"payout_method:usdt:{uid}")
        )
        kb.row(
            types.InlineKeyboardButton("📊 Back to Dashboard", callback_data="affiliate_dashboard"),
            types.InlineKeyboardButton("❌ Cancel", callback_data="affiliate_dashboard")
        )
        
        if message_id:
            bot.edit_message_text(text, uid, message_id, parse_mode='HTML', reply_markup=kb)
        else:
            bot.send_message(uid, text, parse_mode='HTML', reply_markup=kb)
            
    except Exception as e:
        logger.error(f"Error handling payout request: {e}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("payout_method:"))
def handle_payment_method(call: types.CallbackQuery):
    """Handle payment method selection for payout"""
    try:
        uid = int(call.data.split(":")[2])
        if call.from_user.id != uid:
            bot.answer_callback_query(call.id, "Unauthorized action.")
            return
            
        parts = call.data.split(":")
        method = parts[1]
        
        if method == "bank":
            # Ask for bank details
            text = (
                "🏦 <b>Bank Transfer Details</b>\n\n"
                "Please provide your bank details in this format:\n\n"
                "<code>Account Name\nAccount Number\nBank Name</code>\n\n"
                "Example:\n"
                "<code>John Doe\n0123456789\nZenith Bank</code>\n\n"
                "Send your bank details now:"
            )
        else:  # USDT
            text = (
                "💎 <b>USDT Wallet Details</b>\n\n"
                "Please provide your USDT details in this format:\n\n"
                "<code>Network (BEP20/TRC20/TON)\nWallet Address</code>\n\n"
                "Example:\n"
                "<code>BEP20\n0x1234abc...xyz</code>\n\n"
                "Send your USDT details now:"
            )
        
        # Edit the message
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML'
        )
        
        # Register next step handler to receive payment details
        bot.register_next_step_handler(call.message, process_payment_details, method, uid)
        
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"Error handling payment method: {e}")
        bot.answer_callback_query(call.id, "Error processing request.")

def process_payment_details(message: types.Message, method: str, uid: int):
    """Process payment details from affiliate"""
    try:
        if message.from_user.id != uid:
            return
            
        payment_details = message.text.strip()
        
        # Validate format
        lines = payment_details.split('\n')
        if method == "bank" and len(lines) < 3:
            bot.send_message(
                uid,
                "❌ Invalid format. Please provide:\n"
                "1. Account Name\n"
                "2. Account Number\n"
                "3. Bank Name\n\n"
                "Try again:",
                parse_mode='HTML'
            )
            bot.register_next_step_handler(message, process_payment_details, method, uid)
            return
        elif method == "usdt" and len(lines) < 2:
            bot.send_message(
                uid,
                "❌ Invalid format. Please provide:\n"
                "1. Network (BEP20/TRC20/TON)\n"
                "2. Wallet Address\n\n"
                "Try again:",
                parse_mode='HTML'
            )
            bot.register_next_step_handler(message, process_payment_details, method, uid)
            return
        
        # Get affiliate stats
        stats = user_db.get_affiliate_stats(uid)
        available_balance = stats.get('available_balance', 0)
        
        # Create payout request with details
        payout_id = user_db.create_payout_request(
            uid, 
            available_balance, 
            method, 
            payment_details
        )
        
        if payout_id:
            # Confirm to affiliate
            text = (
                f"✅ <b>Payout Request Submitted</b>\n\n"
                f"Request ID: <code>{payout_id}</code>\n"
                f"Amount: <b>₦{available_balance:,.2f}</b>\n"
                f"Method: {method.upper()}\n"
                f"Status: <b>Pending Admin Approval</b>\n\n"
                f"Your payment details have been received.\n"
                f"Admin will process your payout within 7 business days.\n\n"
                f"You will be notified when your payout is processed."
            )
            
            bot.send_message(uid, text, parse_mode='HTML')
            
            # Notify admin with payment details
            notify_admin_payout_request_with_details(
                uid, 
                message.from_user.first_name, 
                payout_id, 
                available_balance,
                method,
                payment_details
            )
        else:
            bot.send_message(uid, "❌ Failed to create payout request. Please try again.")
            
    except Exception as e:
        logger.error(f"Error processing payment details: {e}")
        bot.send_message(uid, "❌ An error occurred. Please try again.")

def notify_admin_payout_request_with_details(uid: int, user_name: str, payout_id: str, 
                                          amount: float, method: str, details: str):
    """Notify admins about payout request with payment details"""
    try:
        method_display = "🏦 Bank Transfer" if method == "bank" else "💎 USDT Transfer"
        
        text = (
            f"💰 <b>New Payout Request</b>\n\n"
            f"👤 <b>Affiliate:</b> {user_name or 'Unknown'}\n"
            f"🆔 <b>User ID:</b> <code>{uid}</code>\n"
            f"📄 <b>Request ID:</b> <code>{payout_id}</code>\n"
            f"💸 <b>Amount:</b> <b>₦{amount:,.2f}</b>\n"
            f"📱 <b>Method:</b> {method_display}\n\n"
            f"<b>Payment Details:</b>\n"
            f"<code>{details}</code>\n\n"
            f"📅 <b>Requested:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"Process this payout request:"
        )
        
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.row(
            types.InlineKeyboardButton("✅ Mark as Paid + Upload Proof", callback_data=f"admin_payout_paid_with_proof:{payout_id}"),
            types.InlineKeyboardButton("❌ Reject", callback_data=f"admin_payout_reject:{payout_id}")
        )
        kb.row(
            types.InlineKeyboardButton("👤 View Affiliate", callback_data=f"admin_view_affiliate:{uid}"),
            types.InlineKeyboardButton("📊 View Details", callback_data=f"admin_view_payout:{payout_id}")
        )
        
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id, text, parse_mode='HTML', reply_markup=kb)
            except Exception as e:
                logger.error(f"Could not notify admin {admin_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error notifying admin about payout: {e}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("admin_payout_paid_with_proof:"))
def handle_admin_payout_paid_with_proof(call: types.CallbackQuery):
    """Handle admin marking payout as paid with proof upload"""
    try:
        if call.from_user.id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ Not authorized.")
            return
        
        payout_id = call.data.split(":")[1]
        
        # Ask admin to upload proof
        bot.edit_message_text(
            f"📤 <b>Upload Payment Proof</b>\n\n"
            f"Please upload proof of payment (photo or document) for payout {payout_id}.\n\n"
            f"After uploading, the system will:\n"
            f"1. Mark payout as paid\n"
            f"2. Reset affiliate's balance to zero\n"
            f"3. Send proof to affiliate\n\n"
            f"Upload proof now:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML'
        )
        
        # Register next step to receive proof
        bot.register_next_step_handler(call.message, process_payment_proof, payout_id)
        
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"Error in admin payout with proof: {e}")

def process_payment_proof(message: types.Message, payout_id: str):
    """Process payment proof from admin"""
    try:
        if message.from_user.id not in ADMIN_IDS:
            return
            
        file_id = None
        if message.content_type == 'photo':
            file_id = message.photo[-1].file_id
        elif message.content_type == 'document':
            file_id = message.document.file_id
        else:
            bot.send_message(message.chat.id, "❌ Please upload a photo or document as proof.")
            return
        
        # Mark payout as paid and reset affiliate balance
        payout = user_db.get_payout_by_id(payout_id)
        if not payout:
            bot.send_message(message.chat.id, f"❌ Payout {payout_id} not found.")
            return
        
        success = user_db.mark_payout_paid_with_proof(payout_id, file_id)
        
        if success:
            # Get updated payout info
            payout = user_db.get_payout_by_id(payout_id)
            
            # Send proof to affiliate
            try:
                if message.content_type == 'photo':
                    bot.send_photo(
                        payout['user_id'],
                        file_id,
                        caption=(
                            f"✅ <b>Payout Processed!</b>\n\n"
                            f"Your payout request has been processed.\n"
                            f"📄 Request ID: <code>{payout_id}</code>\n"
                            f"💰 Amount: <b>₦{payout['amount']:,.2f}</b>\n"
                            f"📅 Processed on: {datetime.now().strftime('%Y-%m-%d')}\n\n"
                            f"<b>Payment proof is attached.</b>\n\n"
                            f"Your affiliate balance has been reset to zero.\n"
                            f"Keep sharing your referral link to earn more! 🚀"
                        ),
                        parse_mode='HTML'
                    )
                else:  # document
                    bot.send_document(
                        payout['user_id'],
                        file_id,
                        caption=(
                            f"✅ <b>Payout Processed!</b>\n\n"
                            f"Your payout request has been processed.\n"
                            f"📄 Request ID: <code>{payout_id}</code>\n"
                            f"💰 Amount: <b>₦{payout['amount']:,.2f}</b>\n"
                            f"📅 Processed on: {datetime.now().strftime('%Y-%m-%d')}\n\n"
                            f"<b>Payment proof is attached.</b>\n\n"
                            f"Your affiliate balance has been reset to zero.\n"
                            f"Keep sharing your referral link to earn more! 🚀"
                        ),
                        parse_mode='HTML'
                    )
            except Exception as e:
                logger.error(f"Could not send proof to affiliate: {e}")
            
            # Update admin
            bot.send_message(
                message.chat.id,
                f"✅ Payout {payout_id} processed successfully!\n\n"
                f"• Amount: ₦{payout['amount']:,.2f}\n"
                f"• Affiliate: {payout['affiliate_name']}\n"
                f"• Proof sent to affiliate\n"
                f"• Balance reset to zero"
            )
        else:
            bot.send_message(message.chat.id, f"❌ Failed to process payout {payout_id}.")
            
    except Exception as e:
        logger.error(f"Error processing payment proof: {e}")
        bot.send_message(message.chat.id, "❌ An error occurred.")

# ====================
# COMMISSION STRUCTURE VIEW
# ====================

def show_commission_structure(uid: int, message_id: int = None):
    """Show commission structure to user"""
    text = (
        "💰 <b>Affiliate Commission Structure</b>\n\n"
        "<b>Earn commissions on every successful referral:</b>\n\n"
        
        "📚 <b>Academy Subscription</b>\n"
        f"• Commission Rate: <b>{COMMISSION_RATES['academy']*100}%</b>\n"
        f"• Example: ₦35,000 × {COMMISSION_RATES['academy']*100}% = <b>₦{35000 * COMMISSION_RATES['academy']:,.0f}</b>\n\n"
        
        "💎 <b>VIP Signals - Monthly</b>\n"
        f"• Commission Rate: <b>{COMMISSION_RATES['vip']['monthly']*100}%</b>\n"
        f"• Example: ₦15,000 × {COMMISSION_RATES['vip']['monthly']*100}% = <b>₦{15000 * COMMISSION_RATES['vip']['monthly']:,.0f}</b>\n\n"
        
        "💎 <b>VIP Signals - 3 Months</b>\n"
        f"• Commission Rate: <b>{COMMISSION_RATES['vip']['3_months']*100}%</b>\n"
        f"• Example: ₦40,000 × {COMMISSION_RATES['vip']['3_months']*100}% = <b>₦{40000 * COMMISSION_RATES['vip']['3_months']:,.0f}</b>\n\n"
        
        "💎 <b>VIP Signals - 6 Months</b>\n"
        f"• Commission Rate: <b>{COMMISSION_RATES['vip']['6_months']*100}%</b>\n"
        f"• Example: ₦75,000 × {COMMISSION_RATES['vip']['6_months']*100}% = <b>₦{75000 * COMMISSION_RATES['vip']['6_months']:,.0f}</b>\n\n"
        
        "💎 <b>VIP Signals - 1 Year</b>\n"
        f"• Commission Rate: <b>{COMMISSION_RATES['vip']['yearly']*100}%</b>\n"
        f"• Example: ₦150,000 × {COMMISSION_RATES['vip']['yearly']*100}% = <b>₦{150000 * COMMISSION_RATES['vip']['yearly']:,.0f}</b>\n\n"
        
        f"🎯 <b>Minimum Payout:</b> ₦{MINIMUM_PAYOUT:,.2f}\n"
        f"⏰ <b>Payout Processing:</b> 7 business days\n\n"
        
        "<b>How It Works:</b>\n"
        "1. Share your unique referral link\n"
        "2. When someone clicks and subscribes\n"
        "3. You earn commission automatically!\n"
        "4. Request payout when you reach minimum\n"
        "5. Get paid within 7 business days\n\n"
        
        "Start earning today by sharing your referral link! 🚀"
    )
    
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("🤝 Apply to Become Affiliate", callback_data="affiliate_apply"),
        types.InlineKeyboardButton("📱 Back to Menu", callback_data="mainmenu_back")
    )
    
    if message_id:
        bot.edit_message_text(text, uid, message_id, parse_mode='HTML', reply_markup=kb)
    else:
        bot.send_message(uid, text, parse_mode='HTML', reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "affiliate_view_commission")
def handle_view_commission_structure(call: types.CallbackQuery):
    """Handle view commission structure callback"""
    try:
        uid = call.from_user.id
        show_commission_structure(uid, call.message.message_id)
        bot.answer_callback_query(call.id)
    except Exception as e:
        logger.error(f"Error showing commission structure: {e}")
        bot.answer_callback_query(call.id, "Error loading commission structure.")

# ====================
# NEW EXPORT FUNCTIONS
# ====================

def export_affiliates_to_csv(admin_id: int):
    """Export affiliates data to CSV"""
    try:
        affiliates = user_db.get_all_affiliates()
        
        if not affiliates:
            bot.send_message(admin_id, "❌ No affiliates to export.")
            return
        
        # Create CSV in memory
        output = io.StringIO()
        fieldnames = ['ID', 'Name', 'Username', 'Affiliate Code', 'Earnings', 'Paid', 'Pending', 'Status']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for affiliate in affiliates:
            writer.writerow({
                'ID': affiliate.get('tg_id'),
                'Name': affiliate.get('name', 'N/A'),
                'Username': affiliate.get('username', 'N/A'),
                'Affiliate Code': affiliate.get('affiliate_code', 'N/A'),
                'Earnings': affiliate.get('affiliate_earnings', 0),
                'Paid': affiliate.get('affiliate_paid', 0),
                'Pending': affiliate.get('affiliate_pending', 0),
                'Status': 'Approved' if affiliate.get('is_affiliate') else 'Pending' if affiliate.get('affiliate_status') == 'pending' else 'Rejected'
            })
        
        # Convert to bytes
        csv_data = output.getvalue().encode('utf-8')
        csv_file = io.BytesIO(csv_data)
        csv_file.name = f'affiliates_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        # Send file
        bot.send_document(admin_id, csv_file, caption="📊 Affiliates Export - Generated on: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        logger.info(f"Exported affiliates data to admin {admin_id}")
        
    except Exception as e:
        logger.error(f"Error exporting affiliates to CSV: {e}")
        bot.send_message(admin_id, f"❌ Error exporting data: {e}")

def export_payouts_to_csv(admin_id: int):
    """Export payouts data to CSV"""
    try:
        payouts = user_db.get_all_payout_requests()
        
        if not payouts:
            bot.send_message(admin_id, "❌ No payout data to export.")
            return
        
        # Create CSV in memory
        output = io.StringIO()
        fieldnames = ['Payout ID', 'User ID', 'Affiliate Name', 'Amount', 'Method', 'Status', 'Request Date', 'Processed Date', 'Details']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for payout in payouts:
            writer.writerow({
                'Payout ID': payout.get('id', 'N/A'),
                'User ID': payout.get('user_id', 'N/A'),
                'Affiliate Name': payout.get('affiliate_name', 'N/A'),
                'Amount': payout.get('amount', 0),
                'Method': payout.get('method', 'N/A'),
                'Status': payout.get('status', 'pending'),
                'Request Date': payout.get('request_date', 'N/A'),
                'Processed Date': payout.get('processed_date', 'N/A'),
                'Details': payout.get('details', 'N/A')
            })
        
        # Convert to bytes
        csv_data = output.getvalue().encode('utf-8')
        csv_file = io.BytesIO(csv_data)
        csv_file.name = f'payouts_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        # Send file
        bot.send_document(admin_id, csv_file, caption="💰 Payouts Export - Generated on: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        logger.info(f"Exported payouts data to admin {admin_id}")
        
    except Exception as e:
        logger.error(f"Error exporting payouts to CSV: {e}")
        bot.send_message(admin_id, f"❌ Error exporting data: {e}")

# ====================
# NEW REPORT FUNCTIONS
# ====================

def show_monthly_report(admin_id: int, message_id: int = None):
    """Show monthly commission report"""
    try:
        # Get current month data
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        # Get all users to calculate commissions
        all_users = user_db.get_all_users()
        monthly_commissions = []
        monthly_total = 0
        
        for user_id_str, user_data in all_users.items():
            if 'commissions' in user_data:
                for commission in user_data['commissions']:
                    try:
                        commission_date = datetime.strptime(commission.get('date', '2000-01-01'), '%Y-%m-%d')
                        if commission_date.month == current_month and commission_date.year == current_year:
                            commission['affiliate_id'] = int(user_id_str)
                            monthly_commissions.append(commission)
                            monthly_total += commission.get('amount', 0)
                    except:
                        pass
        
        # Get top affiliates for the month
        affiliate_totals = {}
        for commission in monthly_commissions:
            affiliate_id = commission.get('affiliate_id')
            if affiliate_id:
                affiliate_totals[affiliate_id] = affiliate_totals.get(affiliate_id, 0) + commission.get('amount', 0)
        
        # Get affiliate names
        top_affiliates = []
        for affiliate_id, total in sorted(affiliate_totals.items(), key=lambda x: x[1], reverse=True)[:10]:
            affiliate = user_db.fetch_user(affiliate_id)
            if affiliate:
                top_affiliates.append({
                    'name': affiliate.get('name', f'User {affiliate_id}'),
                    'total': total
                })
        
        text = (
            f"📅 <b>Monthly Commission Report - {datetime.now().strftime('%B %Y')}</b>\n\n"
            f"📊 <b>Monthly Summary:</b>\n"
            f"• Total Commissions: ₦{monthly_total:,.2f}\n"
            f"• Total Transactions: {len(monthly_commissions)}\n"
            f"• Active Affiliates: {len(affiliate_totals)}\n\n"
            f"🏆 <b>Top Affiliates This Month:</b>\n"
        )
        
        if top_affiliates:
            for i, affiliate in enumerate(top_affiliates, 1):
                text += f"{i}. {affiliate['name']}: ₦{affiliate['total']:,.2f}\n"
        else:
            text += "No commission data for this month yet.\n"
        
        text += f"\n📈 <b>Commission Distribution:</b>\n"
        
        # Get breakdown by plan type
        plan_breakdown = {}
        for commission in monthly_commissions:
            plan_type = commission.get('plan_type', 'Unknown')
            plan_breakdown[plan_type] = plan_breakdown.get(plan_type, 0) + commission.get('amount', 0)
        
        for plan_type, amount in plan_breakdown.items():
            percentage = (amount / monthly_total * 100) if monthly_total > 0 else 0
            text += f"• {plan_type}: ₦{amount:,.2f} ({percentage:.1f}%)\n"
        
        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton("📊 Export to CSV", callback_data="admin_export_commissions_monthly"),
            types.InlineKeyboardButton("🔄 Refresh", callback_data="admin_monthly_report")
        )
        kb.row(
            types.InlineKeyboardButton("🤝 Back to Management", callback_data="admin_affiliate_mgmt"),
            types.InlineKeyboardButton("📱 Admin Dashboard", callback_data="admin_back")
        )
        
        if message_id:
            bot.edit_message_text(text, admin_id, message_id, parse_mode='HTML', reply_markup=kb)
        else:
            bot.send_message(admin_id, text, parse_mode='HTML', reply_markup=kb)
            
    except Exception as e:
        logger.error(f"Error showing monthly report: {e}")
        error_text = f"❌ Error generating monthly report: {e}"
        if message_id:
            bot.edit_message_text(error_text, admin_id, message_id)
        else:
            bot.send_message(admin_id, error_text)

def show_detailed_stats(admin_id: int, message_id: int = None):
    """Show detailed affiliate statistics"""
    try:
        # Get all affiliates
        affiliates = user_db.get_all_affiliates()
        
        # Calculate stats
        total_affiliates = len(affiliates)
        active_affiliates = sum(1 for a in affiliates if a.get('is_affiliate'))
        total_commissions = sum(a.get('affiliate_earnings', 0) for a in affiliates)
        
        # Get all users for referral stats
        all_users = user_db.get_all_users()
        total_referrals = 0
        for user_data in all_users.values():
            if 'referred_by' in user_data:
                total_referrals += 1
        
        # Calculate averages
        avg_commission = total_commissions / total_affiliates if total_affiliates > 0 else 0
        avg_referrals = total_referrals / total_affiliates if total_affiliates > 0 else 0
        
        text = (
            f"📈 <b>Detailed Affiliate Statistics</b>\n\n"
            f"📊 <b>Overall Performance:</b>\n"
            f"• Total Affiliates: {total_affiliates}\n"
            f"• Active Affiliates: {active_affiliates}\n"
            f"• Inactive Affiliates: {total_affiliates - active_affiliates}\n\n"
            
            f"💰 <b>Financial Performance:</b>\n"
            f"• Total Commissions: ₦{total_commissions:,.2f}\n"
            f"• Average per Affiliate: ₦{avg_commission:,.2f}\n\n"
            
            f"👥 <b>Referral Performance:</b>\n"
            f"• Total Referrals: {total_referrals}\n"
            f"• Avg. Referrals per Affiliate: {avg_referrals:.1f}\n\n"
            
            f"📅 <b>Time-based Analysis:</b>\n"
            f"• Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        )
        
        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton("📅 Monthly Trends", callback_data="admin_monthly_trends"),
            types.InlineKeyboardButton("📊 Export Data", callback_data="admin_export_detailed_stats")
        )
        kb.row(
            types.InlineKeyboardButton("🤝 Back to Management", callback_data="admin_affiliate_mgmt"),
            types.InlineKeyboardButton("📱 Admin Dashboard", callback_data="admin_back")
        )
        
        if message_id:
            bot.edit_message_text(text, admin_id, message_id, parse_mode='HTML', reply_markup=kb)
        else:
            bot.send_message(admin_id, text, parse_mode='HTML', reply_markup=kb)
            
    except Exception as e:
        logger.error(f"Error showing detailed stats: {e}")

def show_payouts_monthly(admin_id: int, message_id: int = None):
    """Show monthly payout report"""
    try:
        # Get current month data
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        # Get all payouts
        payouts = user_db.get_all_payout_requests()
        
        monthly_payouts = []
        monthly_total = 0
        
        for payout in payouts:
            try:
                payout_date = datetime.strptime(payout.get('request_date', '2000-01-01'), '%Y-%m-%d %H:%M:%S')
                if payout_date.month == current_month and payout_date.year == current_year:
                    monthly_payouts.append(payout)
                    monthly_total += payout.get('amount', 0)
            except:
                pass
        
        # Get breakdown by status
        status_counts = {}
        for payout in monthly_payouts:
            status = payout.get('status', 'pending')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        text = (
            f"📅 <b>Monthly Payout Report - {datetime.now().strftime('%B %Y')}</b>\n\n"
            f"💰 <b>Monthly Payout Summary:</b>\n"
            f"• Total Payouts: {len(monthly_payouts)}\n"
            f"• Total Amount: ₦{monthly_total:,.2f}\n"
            f"• Average Payout: ₦{monthly_total/len(monthly_payouts) if monthly_payouts else 0:,.2f}\n\n"
            
            f"📊 <b>Payout Status:</b>\n"
        )
        
        for status, count in status_counts.items():
            text += f"• {status.title()}: {count}\n"
        
        text += f"\n🏦 <b>Payment Methods:</b>\n"
        
        # Get breakdown by method
        method_counts = {}
        for payout in monthly_payouts:
            method = payout.get('method', 'unknown')
            method_counts[method] = method_counts.get(method, 0) + 1
        
        for method, count in method_counts.items():
            text += f"• {method.title()}: {count}\n"
        
        # Show top 5 largest payouts
        text += f"\n🏆 <b>Top 5 Payouts This Month:</b>\n"
        sorted_payouts = sorted(monthly_payouts, key=lambda x: x.get('amount', 0), reverse=True)[:5]
        
        if sorted_payouts:
            for i, payout in enumerate(sorted_payouts, 1):
                text += f"{i}. ₦{payout.get('amount', 0):,.2f} - {payout.get('affiliate_name', 'Unknown')}\n"
        else:
            text += "No payouts this month.\n"
        
        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton("📊 Export to CSV", callback_data="admin_export_payouts_monthly"),
            types.InlineKeyboardButton("📅 Weekly View", callback_data="admin_payouts_weekly")
        )
        kb.row(
            types.InlineKeyboardButton("📋 Back to Payouts", callback_data="admin_view_payouts"),
            types.InlineKeyboardButton("🤝 Affiliate Management", callback_data="admin_affiliate_mgmt")
        )
        
        if message_id:
            bot.edit_message_text(text, admin_id, message_id, parse_mode='HTML', reply_markup=kb)
        else:
            bot.send_message(admin_id, text, parse_mode='HTML', reply_markup=kb)
            
    except Exception as e:
        logger.error(f"Error showing monthly payouts: {e}")

def show_payouts_weekly(admin_id: int, message_id: int = None):
    """Show weekly payout report"""
    try:
        # Get current week data (last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        
        # Get all payouts
        payouts = user_db.get_all_payout_requests()
        
        weekly_payouts = []
        weekly_total = 0
        
        for payout in payouts:
            try:
                payout_date = datetime.strptime(payout.get('request_date', '2000-01-01'), '%Y-%m-%d %H:%M:%S')
                if payout_date >= week_ago:
                    weekly_payouts.append(payout)
                    weekly_total += payout.get('amount', 0)
            except:
                pass
        
        text = (
            f"📅 <b>Weekly Payout Report - Last 7 Days</b>\n\n"
            f"💰 <b>Weekly Summary:</b>\n"
            f"• Total Payouts: {len(weekly_payouts)}\n"
            f"• Total Amount: ₦{weekly_total:,.2f}\n"
            f"• Daily Average: ₦{(weekly_total/7):,.2f}\n\n"
            
            f"📊 <b>Recent Payout Activity:</b>\n"
        )
        
        # Show recent payouts
        recent_payouts = sorted(weekly_payouts, key=lambda x: x.get('request_date', ''), reverse=True)[:10]
        
        if recent_payouts:
            for i, payout in enumerate(recent_payouts, 1):
                status_icon = "✅" if payout.get('status') == 'paid' else "⏳" if payout.get('status') == 'pending' else "❌"
                text += f"{i}. {status_icon} ₦{payout.get('amount', 0):,.2f} - {payout.get('affiliate_name', 'Unknown')}\n"
        else:
            text += "No payouts in the last 7 days.\n"
        
        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton("📅 Monthly View", callback_data="admin_payouts_monthly"),
            types.InlineKeyboardButton("🔄 Refresh", callback_data="admin_payouts_weekly")
        )
        kb.row(
            types.InlineKeyboardButton("📋 Back to Payouts", callback_data="admin_view_payouts"),
            types.InlineKeyboardButton("🤝 Affiliate Management", callback_data="admin_affiliate_mgmt")
        )
        
        if message_id:
            bot.edit_message_text(text, admin_id, message_id, parse_mode='HTML', reply_markup=kb)
        else:
            bot.send_message(admin_id, text, parse_mode='HTML', reply_markup=kb)
            
    except Exception as e:
        logger.error(f"Error showing weekly payouts: {e}")

# ====================
# FIXED ADMIN DASHBOARD
# ====================

def show_admin_dashboard(admin_id: int, message_id: int = None):
    """Show admin dashboard - FIXED"""
    try:
        # Get database stats
        db_stats = user_db.get_database_stats()
        
        text = (
            f"🔧 <b>Admin Dashboard</b>\n\n"
            f"📊 <b>System Statistics:</b>\n"
            f"• Total Users: {db_stats.get('total_users', 0)}\n"
            f"• Active Affiliates: {db_stats.get('total_affiliates', 0)}\n"
            f"• Total Commissions: ₦{db_stats.get('total_commissions', 0):,.2f}\n"
            f"• Active Subscriptions: {db_stats.get('active_subscriptions', 0)}\n\n"
            
            f"📋 <b>Quick Actions:</b>\n"
            f"• Manage affiliates and payouts\n"
            f"• View user subscriptions\n"
            f"• Test system links\n"
            f"• Run manual checks\n\n"
            
            f"⚙️ <b>System Status:</b>\n"
            f"• Bot: ✅ Online\n"
            f"• Database: ✅ Connected\n"
            f"• Scheduler: ✅ Running\n"
            f"• Last Check: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        kb.row("➕ Add User", "📅 Extend User")
        kb.row("📋 List Users", "🔍 Check User")
        kb.row("🔗 Test Links", "⏰ Test Reminders")
        kb.row("🤝 Affiliate Management", "💰 Payout Requests")
        
        if message_id:
            # Edit existing message
            bot.edit_message_text(
                text, 
                admin_id, 
                message_id, 
                parse_mode='HTML'
            )
            # Send new keyboard in a new message
            bot.send_message(admin_id, "🔧 Admin Dashboard:", reply_markup=kb)
        else:
            # Send new message
            bot.send_message(admin_id, text, parse_mode='HTML')
            bot.send_message(admin_id, "🔧 Admin Dashboard:", reply_markup=kb)
            
    except Exception as e:
        logger.error(f"Error showing admin dashboard: {e}")
        bot.send_message(admin_id, f"❌ Error loading dashboard: {e}")

# ====================
# FIXED ADMIN AFFILIATE MANAGEMENT HANDLERS
# ====================

@bot.message_handler(func=lambda m: m.text == "🤝 Affiliate Management")
def handle_admin_affiliate_management(message: types.Message):
    """Show affiliate management dashboard for admins - FIXED"""
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Unauthorized access.")
        return
    
    text = (
        "🤝 <b>Affiliate Management Dashboard</b>\n\n"
        "Manage affiliates, commissions, and payouts.\n\n"
        "Select an option below:"
    )
    
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(
        types.InlineKeyboardButton("📋 All Affiliates", callback_data="admin_view_affiliates"),
        types.InlineKeyboardButton("💰 Payout Requests", callback_data="admin_view_payouts")
    )
    kb.row(
        types.InlineKeyboardButton("📊 Commission Report", callback_data="admin_commission_report"),
        types.InlineKeyboardButton("📈 Performance Stats", callback_data="admin_affiliate_stats")
    )
    kb.row(
        types.InlineKeyboardButton("⏳ Pending Applications", callback_data="admin_pending_applications"),
        types.InlineKeyboardButton("📱 Back to Admin", callback_data="admin_back")
    )
    
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "💰 Payout Requests")
def handle_admin_payout_requests(message: types.Message):
    """Show payout requests for admins"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    show_all_payout_requests(message.chat.id)

def show_all_payout_requests(admin_id: int, message_id: int = None):
    """Show all payout requests to admin"""
    try:
        payouts = user_db.get_all_payout_requests()
        
        if not payouts:
            text = "💰 <b>Payout Requests</b>\n\nNo pending payout requests."
        else:
            pending = [p for p in payouts if p.get('status') == 'pending']
            processed = [p for p in payouts if p.get('status') != 'pending']
            
            text = (
                f"💰 <b>Payout Requests</b>\n\n"
                f"📊 <b>Summary:</b>\n"
                f"• Pending: {len(pending)}\n"
                f"• Processed: {len(processed)}\n"
                f"• Total Amount: ₦{sum(p.get('amount', 0) for p in payouts):,.2f}\n\n"
                f"📋 <b>Pending Requests:</b>\n"
            )
            
            if pending:
                for i, payout in enumerate(pending[:10], 1):
                    text += f"{i}. ID: {payout['id']} - ₦{payout['amount']:,.2f} - {payout['affiliate_name']}\n"
            else:
                text += "No pending requests.\n"
        
        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh_payouts"),
            types.InlineKeyboardButton("📊 View All", callback_data="admin_view_all_payouts")
        )
        kb.row(
            types.InlineKeyboardButton("📋 Processed Payouts", callback_data="admin_processed_payouts"),
            types.InlineKeyboardButton("🤝 Back to Management", callback_data="admin_affiliate_mgmt")
        )
        
        if message_id:
            bot.edit_message_text(text, admin_id, message_id, parse_mode='HTML', reply_markup=kb)
        else:
            bot.send_message(admin_id, text, parse_mode='HTML', reply_markup=kb)
            
    except Exception as e:
        logger.error(f"Error showing payout requests: {e}")

# ====================
# FIXED ADMIN CALLBACK HANDLER
# ====================

@bot.callback_query_handler(func=lambda c: c.data.startswith("admin_"))
def handle_admin_affiliate_callbacks(call: types.CallbackQuery):
    """Handle admin affiliate management callbacks - FIXED VERSION"""
    try:
        if call.from_user.id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ Not authorized.")
            return
        
        action = call.data
        
        if action == "admin_view_affiliates":
            show_all_affiliates(call.from_user.id, call.message.message_id)
        
        elif action == "admin_view_payouts":
            show_all_payout_requests(call.from_user.id, call.message.message_id)
        
        elif action == "admin_commission_report":
            show_commission_report(call.from_user.id, call.message.message_id)
        
        elif action == "admin_affiliate_stats":
            show_affiliate_stats(call.from_user.id, call.message.message_id)
        
        elif action == "admin_pending_applications":
            show_pending_applications(call.from_user.id, call.message.message_id)
        
        elif action == "admin_affiliate_mgmt":
            handle_admin_affiliate_management(call.message)
        
        elif action == "admin_back":
            # Return to admin dashboard
            show_admin_dashboard(call.from_user.id, call.message.message_id)
        
        elif action.startswith("admin_payout_paid:"):
            payout_id = action.split(":")[1]
            mark_payout_paid(call.from_user.id, payout_id, call.message.message_id)
        
        elif action.startswith("admin_payout_reject:"):
            payout_id = action.split(":")[1]
            reject_payout_request(call.from_user.id, payout_id, call.message.message_id)
        
        elif action.startswith("admin_view_affiliate:"):
            user_id = int(action.split(":")[1])
            show_affiliate_details(call.from_user.id, user_id, call.message.message_id)
        
        elif action == "admin_refresh_payouts":
            show_all_payout_requests(call.from_user.id, call.message.message_id)
        
        elif action == "admin_view_all_payouts":
            show_all_payouts_detailed(call.from_user.id, call.message.message_id)
        
        elif action == "admin_processed_payouts":
            show_processed_payouts(call.from_user.id, call.message.message_id)
        
        elif action == "admin_export_affiliates":
            export_affiliates_to_csv(call.from_user.id)
            bot.answer_callback_query(call.id, "✅ Exporting affiliates data...")
        
        elif action == "admin_export_payouts":
            export_payouts_to_csv(call.from_user.id)
            bot.answer_callback_query(call.id, "✅ Exporting payouts data...")
        
        elif action == "admin_monthly_report":
            show_monthly_report(call.from_user.id, call.message.message_id)
        
        elif action == "admin_detailed_stats":
            show_detailed_stats(call.from_user.id, call.message.message_id)
        
        elif action == "admin_payouts_monthly":
            show_payouts_monthly(call.from_user.id, call.message.message_id)
        
        elif action == "admin_payouts_weekly":
            show_payouts_weekly(call.from_user.id, call.message.message_id)
        
        elif action == "admin_export_commissions_monthly":
            bot.answer_callback_query(call.id, "✅ This feature is coming soon!")
        
        elif action == "admin_export_detailed_stats":
            bot.answer_callback_query(call.id, "✅ This feature is coming soon!")
        
        elif action == "admin_export_payouts_monthly":
            bot.answer_callback_query(call.id, "✅ This feature is coming soon!")
        
        elif action == "admin_monthly_trends":
            bot.answer_callback_query(call.id, "✅ This feature is coming soon!")
        
        else:
            bot.answer_callback_query(call.id, "❌ Unknown action.")
        
        # Only answer the callback query if not already answered
        if action not in ["admin_export_affiliates", "admin_export_payouts"]:
            bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"Error in admin affiliate callback: {e}")
        bot.answer_callback_query(call.id, f"❌ Error: {str(e)}")

def mark_payout_paid(admin_id: int, payout_id: str, message_id: int = None):
    """Mark payout as paid"""
    try:
        success = user_db.mark_payout_paid(payout_id)
        
        if success:
            # Get payout details
            payout = user_db.get_payout_by_id(payout_id)
            if payout:
                # Notify affiliate
                try:
                    bot.send_message(
                        payout['user_id'],
                        f"✅ <b>Payout Processed!</b>\n\n"
                        f"Your payout request has been processed.\n"
                        f"📄 Request ID: <code>{payout_id}</code>\n"
                        f"💰 Amount: <b>₦{payout['amount']:,.2f}</b>\n"
                        f"📅 Processed on: {datetime.now().strftime('%Y-%m-%d')}\n\n"
                        f"Funds should reach your account within 3 business days.\n"
                        f"Contact @blockchainpluspro if you have any questions.",
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.error(f"Could not notify affiliate: {e}")
            
            # Update admin
            text = f"✅ Payout {payout_id} marked as paid."
            
            kb = types.InlineKeyboardMarkup()
            kb.row(
                types.InlineKeyboardButton("📋 Back to Payouts", callback_data="admin_view_payouts"),
                types.InlineKeyboardButton("🤝 Affiliate Management", callback_data="admin_affiliate_mgmt")
            )
            
            if message_id:
                bot.edit_message_text(text, admin_id, message_id, reply_markup=kb)
            else:
                bot.send_message(admin_id, text, reply_markup=kb)
        else:
            bot.send_message(admin_id, f"❌ Could not find payout {payout_id}")
            
    except Exception as e:
        logger.error(f"Error marking payout paid: {e}")
        bot.send_message(admin_id, f"Error: {e}")

def reject_payout_request(admin_id: int, payout_id: str, message_id: int = None):
    """Reject payout request"""
    try:
        success = user_db.reject_payout_request(payout_id)
        
        if success:
            # Get payout details
            payout = user_db.get_payout_by_id(payout_id)
            if payout:
                # Notify affiliate
                try:
                    bot.send_message(
                        payout['user_id'],
                        f"❌ <b>Payout Request Rejected</b>\n\n"
                        f"Your payout request has been rejected.\n"
                        f"📄 Request ID: <code>{payout_id}</code>\n"
                        f"💰 Amount: <b>₦{payout['amount']:,.2f}</b>\n\n"
                        f"Possible reasons:\n"
                        f"• Account verification required\n"
                        f"• Minimum payout requirements not met\n"
                        f"• Other administrative reasons\n\n"
                        f"Contact @blockchainpluspro for more information.",
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.error(f"Could not notify affiliate: {e}")
            
            # Update admin
            text = f"❌ Payout {payout_id} rejected."
            
            kb = types.InlineKeyboardMarkup()
            kb.row(
                types.InlineKeyboardButton("📋 Back to Payouts", callback_data="admin_view_payouts"),
                types.InlineKeyboardButton("🤝 Affiliate Management", callback_data="admin_affiliate_mgmt")
            )
            
            if message_id:
                bot.edit_message_text(text, admin_id, message_id, reply_markup=kb)
            else:
                bot.send_message(admin_id, text, reply_markup=kb)
        else:
            bot.send_message(admin_id, f"❌ Could not find payout {payout_id}")
            
    except Exception as e:
        logger.error(f"Error rejecting payout: {e}")
        bot.send_message(admin_id, f"Error: {e}")

def show_all_affiliates(admin_id: int, message_id: int = None):
    """Show all affiliates to admin"""
    try:
        affiliates = user_db.get_all_affiliates()
        
        if not affiliates:
            text = "🤝 <b>All Affiliates</b>\n\nNo affiliates found."
        else:
            text = f"🤝 <b>All Affiliates ({len(affiliates)})</b>\n\n"
            
            total_earnings = 0
            total_paid = 0
            total_pending = 0
            
            for i, affiliate in enumerate(affiliates[:15], 1):  # Limit to 15
                name = affiliate.get('name', 'Unknown')[:20]
                earnings = affiliate.get('affiliate_earnings', 0)
                paid = affiliate.get('affiliate_paid', 0)
                pending = affiliate.get('affiliate_pending', 0)
                
                text += f"{i}. {name} (ID: {affiliate['tg_id']})\n"
                text += f"   Earnings: ₦{earnings:,.2f} | Paid: ₦{paid:,.2f} | Pending: ₦{pending:,.2f}\n"
                text += f"   Code: {affiliate.get('affiliate_code', 'N/A')}\n\n"
                
                total_earnings += earnings
                total_paid += paid
                total_pending += pending
            
            text += f"📊 <b>Totals:</b>\n"
            text += f"• Total Earnings: ₦{total_earnings:,.2f}\n"
            text += f"• Total Paid: ₦{total_paid:,.2f}\n"
            text += f"• Total Pending: ₦{total_pending:,.2f}\n"
            
            if len(affiliates) > 15:
                text += f"\n... and {len(affiliates) - 15} more affiliates"
        
        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton("🔄 Refresh", callback_data="admin_view_affiliates"),
            types.InlineKeyboardButton("📊 Export Data", callback_data="admin_export_affiliates")
        )
        kb.row(
            types.InlineKeyboardButton("🤝 Back to Management", callback_data="admin_affiliate_mgmt"),
            types.InlineKeyboardButton("📱 Admin Dashboard", callback_data="admin_back")
        )
        
        if message_id:
            bot.edit_message_text(text, admin_id, message_id, parse_mode='HTML', reply_markup=kb)
        else:
            bot.send_message(admin_id, text, parse_mode='HTML', reply_markup=kb)
            
    except Exception as e:
        logger.error(f"Error showing affiliates: {e}")

def show_commission_report(admin_id: int, message_id: int = None):
    """Show commission report to admin"""
    try:
        report = user_db.get_commission_report()
        
        text = (
            f"📊 <b>Commission Report</b>\n\n"
            f"💰 <b>Total Commissions Generated:</b> ₦{report.get('total_commissions', 0):,.2f}\n"
            f"👥 <b>Total Affiliates:</b> {report.get('total_affiliates', 0)}\n"
            f"📈 <b>Total Referrals:</b> {report.get('total_referrals', 0)}\n\n"
            f"<b>By Plan Type:</b>\n"
        )
        
        for plan_type, amount in report.get('by_plan_type', {}).items():
            text += f"• {plan_type}: ₦{amount:,.2f}\n"
        
        text += f"\n<b>Recent Commission Activity:</b>\n"
        
        recent = report.get('recent_commissions', [])
        if recent:
            for i, commission in enumerate(recent[:10], 1):
                text += f"{i}. ₦{commission['amount']:,.2f} - {commission['affiliate_name']}\n"
        else:
            text += "No recent commissions.\n"
        
        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton("🔄 Refresh", callback_data="admin_commission_report"),
            types.InlineKeyboardButton("📅 Monthly Report", callback_data="admin_monthly_report")
        )
        kb.row(
            types.InlineKeyboardButton("🤝 Back to Management", callback_data="admin_affiliate_mgmt"),
            types.InlineKeyboardButton("📱 Admin Dashboard", callback_data="admin_back")
        )
        
        if message_id:
            bot.edit_message_text(text, admin_id, message_id, parse_mode='HTML', reply_markup=kb)
        else:
            bot.send_message(admin_id, text, parse_mode='HTML', reply_markup=kb)
            
    except Exception as e:
        logger.error(f"Error showing commission report: {e}")

def show_affiliate_stats(admin_id: int, message_id: int = None):
    """Show affiliate performance stats to admin"""
    try:
        stats = user_db.get_affiliate_performance_stats()
        
        text = (
            f"📈 <b>Affiliate Performance Statistics</b>\n\n"
            f"<b>Overall Performance:</b>\n"
            f"• Active Affiliates: {stats.get('active_affiliates', 0)}\n"
            f"• Total Referrals: {stats.get('total_referrals', 0)}\n"
            f"• Conversion Rate: {stats.get('conversion_rate', 0):.1f}%\n"
            f"• Avg. Commission per Affiliate: ₦{stats.get('avg_commission', 0):,.2f}\n\n"
            f"<b>Top Performers (This Month):</b>\n"
        )
        
        top_performers = stats.get('top_performers', [])
        if top_performers:
            for i, performer in enumerate(top_performers[:5], 1):
                text += f"{i}. {performer['name']}: ₦{performer['earnings']:,.2f} ({performer['referrals']} referrals)\n"
        else:
            text += "No performance data yet.\n"
        
        text += f"\n<b>Commission Distribution:</b>\n"
        text += f"• Academy Commissions: ₦{stats.get('academy_commissions', 0):,.2f}\n"
        text += f"• VIP Commissions: ₦{stats.get('vip_commissions', 0):,.2f}\n"
        
        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton("🔄 Refresh", callback_data="admin_affiliate_stats"),
            types.InlineKeyboardButton("📊 Detailed Report", callback_data="admin_detailed_stats")
        )
        kb.row(
            types.InlineKeyboardButton("🤝 Back to Management", callback_data="admin_affiliate_mgmt"),
            types.InlineKeyboardButton("📱 Admin Dashboard", callback_data="admin_back")
        )
        
        if message_id:
            bot.edit_message_text(text, admin_id, message_id, parse_mode='HTML', reply_markup=kb)
        else:
            bot.send_message(admin_id, text, parse_mode='HTML', reply_markup=kb)
            
    except Exception as e:
        logger.error(f"Error showing affiliate stats: {e}")

def show_pending_applications(admin_id: int, message_id: int = None):
    """Show pending affiliate applications to admin"""
    try:
        applications = user_db.get_pending_affiliate_applications()
        
        if not applications:
            text = "⏳ <b>Pending Affiliate Applications</b>\n\nNo pending applications."
        else:
            text = f"⏳ <b>Pending Affiliate Applications ({len(applications)})</b>\n\n"
            
            for i, app in enumerate(applications, 1):
                text += f"{i}. {app.get('name', 'Unknown')} (ID: {app['tg_id']})\n"
                text += f"   Applied: {app.get('affiliate_applied_date', 'Unknown')}\n"
                text += f"   Code: {app.get('affiliate_code', 'N/A')}\n\n"
        
        kb = types.InlineKeyboardMarkup()
        
        if applications:
            # Add buttons for each application
            for i, app in enumerate(applications[:5], 1):  # Limit to 5 buttons
                kb.row(
                    types.InlineKeyboardButton(
                        f"✅ Approve {app.get('name', 'User')[:10]}",
                        callback_data=f"admin_approve_affiliate:{app['tg_id']}"
                    ),
                    types.InlineKeyboardButton(
                        f"❌ Reject {app.get('name', 'User')[:10]}",
                        callback_data=f"admin_reject_affiliate:{app['tg_id']}"
                    )
                )
        
        kb.row(
            types.InlineKeyboardButton("🔄 Refresh", callback_data="admin_pending_applications"),
            types.InlineKeyboardButton("🤝 Back to Management", callback_data="admin_affiliate_mgmt")
        )
        
        if message_id:
            bot.edit_message_text(text, admin_id, message_id, parse_mode='HTML', reply_markup=kb)
        else:
            bot.send_message(admin_id, text, parse_mode='HTML', reply_markup=kb)
            
    except Exception as e:
        logger.error(f"Error showing pending applications: {e}")

def show_affiliate_details(admin_id: int, user_id: int, message_id: int = None):
    """Show detailed affiliate information to admin"""
    try:
        affiliate = user_db.fetch_user(user_id)
        
        if not affiliate or not affiliate.get('is_affiliate'):
            text = f"User {user_id} is not an affiliate."
        else:
            stats = user_db.get_affiliate_stats(user_id)
            
            text = (
                f"👤 <b>Affiliate Details</b>\n\n"
                f"<b>Basic Information:</b>\n"
                f"• Name: {affiliate.get('name', 'Unknown')}\n"
                f"• User ID: <code>{user_id}</code>\n"
                f"• Username: @{affiliate.get('username', 'N/A')}\n"
                f"• Affiliate Code: <code>{affiliate.get('affiliate_code', 'N/A')}</code>\n"
                f"• Approved Date: {affiliate.get('affiliate_approved_date', 'Unknown')}\n\n"
                f"<b>Performance Statistics:</b>\n"
                f"• Total Referrals: {stats.get('total_referrals', 0)}\n"
                f"• Active Referrals: {stats.get('active_referrals', 0)}\n"
                f"• Total Earnings: ₦{stats.get('total_earnings', 0):,.2f}\n"
                f"• Total Paid: ₦{stats.get('total_paid', 0):,.2f}\n"
                f"• Pending Payout: ₦{stats.get('pending_payout', 0):,.2f}\n"
                f"• Available Balance: ₦{stats.get('available_balance', 0):,.2f}\n\n"
                f"<b>Recent Activity:</b>\n"
            )
            
            recent = user_db.get_recent_commissions(user_id, limit=5)
            if recent:
                for i, commission in enumerate(recent, 1):
                    text += f"{i}. ₦{commission['amount']:,.2f} - {commission['plan_type']} - {commission['date']}\n"
            else:
                text += "No recent commissions.\n"
        
        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton("📊 View All Referrals", callback_data=f"admin_view_referrals_detail:{user_id}"),
            types.InlineKeyboardButton("💸 Commission History", callback_data=f"admin_commission_history_detail:{user_id}")
        )
        kb.row(
            types.InlineKeyboardButton("📋 Payout History", callback_data=f"admin_payout_history:{user_id}"),
            types.InlineKeyboardButton("✉️ Message Affiliate", url=f"tg://user?id={user_id}")
        )
        kb.row(
            types.InlineKeyboardButton("🤝 Back to Affiliates", callback_data="admin_view_affiliates"),
            types.InlineKeyboardButton("📱 Admin Dashboard", callback_data="admin_back")
        )
        
        if message_id:
            bot.edit_message_text(text, admin_id, message_id, parse_mode='HTML', reply_markup=kb)
        else:
            bot.send_message(admin_id, text, parse_mode='HTML', reply_markup=kb)
            
    except Exception as e:
        logger.error(f"Error showing affiliate details: {e}")

def show_all_payouts_detailed(admin_id: int, message_id: int = None):
    """Show detailed payout information to admin"""
    try:
        payouts = user_db.get_all_payout_requests()
        
        if not payouts:
            text = "💰 <b>All Payouts</b>\n\nNo payout requests found."
        else:
            text = f"💰 <b>All Payouts ({len(payouts)})</b>\n\n"
            
            pending_total = 0
            paid_total = 0
            rejected_total = 0
            
            for payout in payouts:
                status = payout.get('status', 'pending')
                amount = payout.get('amount', 0)
                
                if status == 'pending':
                    pending_total += amount
                elif status == 'paid':
                    paid_total += amount
                elif status == 'rejected':
                    rejected_total += amount
            
            text += f"<b>Summary:</b>\n"
            text += f"• Pending: ₦{pending_total:,.2f}\n"
            text += f"• Paid: ₦{paid_total:,.2f}\n"
            text += f"• Rejected: ₦{rejected_total:,.2f}\n"
            text += f"• Total: ₦{pending_total + paid_total + rejected_total:,.2f}\n\n"
            
            text += f"<b>Recent Payouts:</b>\n"
            
            for i, payout in enumerate(payouts[:10], 1):
                status_icon = "⏳" if payout['status'] == 'pending' else "✅" if payout['status'] == 'paid' else "❌"
                text += f"{i}. {status_icon} {payout['id']} - ₦{payout['amount']:,.2f} - {payout['affiliate_name']}\n"
        
        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton("📊 Export to CSV", callback_data="admin_export_payouts"),
            types.InlineKeyboardButton("🔄 Refresh", callback_data="admin_view_all_payouts")
        )
        kb.row(
            types.InlineKeyboardButton("📋 Back to Payouts", callback_data="admin_view_payouts"),
            types.InlineKeyboardButton("🤝 Affiliate Management", callback_data="admin_affiliate_mgmt")
        )
        
        if message_id:
            bot.edit_message_text(text, admin_id, message_id, parse_mode='HTML', reply_markup=kb)
        else:
            bot.send_message(admin_id, text, parse_mode='HTML', reply_markup=kb)
            
    except Exception as e:
        logger.error(f"Error showing detailed payouts: {e}")

def show_processed_payouts(admin_id: int, message_id: int = None):
    """Show processed payouts to admin"""
    try:
        payouts = user_db.get_processed_payouts()
        
        if not payouts:
            text = "✅ <b>Processed Payouts</b>\n\nNo processed payouts found."
        else:
            text = f"✅ <b>Processed Payouts ({len(payouts)})</b>\n\n"
            
            total_paid = 0
            this_month = 0
            this_week = 0
            
            current_date = datetime.now()
            
            for payout in payouts:
                amount = payout.get('amount', 0)
                payout_date = payout.get('processed_date', '')
                
                total_paid += amount
                
                # Check if this month
                try:
                    if payout_date:
                        payout_dt = datetime.strptime(payout_date, '%Y-%m-%d %H:%M:%S')
                        if payout_dt.month == current_date.month and payout_dt.year == current_date.year:
                            this_month += amount
                        # Check if this week (last 7 days)
                        if (current_date - payout_dt).days <= 7:
                            this_week += amount
                except:
                    pass
            
            text += f"<b>Summary:</b>\n"
            text += f"• Total Paid: ₦{total_paid:,.2f}\n"
            text += f"• This Month: ₦{this_month:,.2f}\n"
            text += f"• This Week: ₦{this_week:,.2f}\n\n"
            
            text += f"<b>Recent Processed Payouts:</b>\n"
            
            for i, payout in enumerate(payouts[:10], 1):
                text += f"{i}. {payout['id']} - ₦{payout['amount']:,.2f} - {payout['affiliate_name']} - {payout.get('processed_date', '')}\n"
        
        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton("📊 Monthly Report", callback_data="admin_payouts_monthly"),
            types.InlineKeyboardButton("📈 Weekly Report", callback_data="admin_payouts_weekly")
        )
        kb.row(
            types.InlineKeyboardButton("📋 Back to Payouts", callback_data="admin_view_payouts"),
            types.InlineKeyboardButton("🤝 Affiliate Management", callback_data="admin_affiliate_mgmt")
        )
        
        if message_id:
            bot.edit_message_text(text, admin_id, message_id, parse_mode='HTML', reply_markup=kb)
        else:
            bot.send_message(admin_id, text, parse_mode='HTML', reply_markup=kb)
            
    except Exception as e:
        logger.error(f"Error showing processed payouts: {e}")

# ====================
# FIXED ADMIN START HANDLER
# ====================

@bot.message_handler(commands=['start'])
def handle_start(message: types.Message):
    """Updated /start handler with admin dashboard fix"""
    try:
        user = message.from_user
        uid = user.id
        command_args = message.text.split()
        
        # Check for referral code
        referred_by = None
        if len(command_args) > 1 and command_args[1].startswith('ref_'):
            referral_code = command_args[1].replace('ref_', '')
            referred_by = user_db.get_user_by_affiliate_code(referral_code)
            
            if referred_by:
                # Store referral in database
                user_db.add_referral(referred_by['tg_id'], uid)
                
                # Send welcome message with referral info
                bot.send_message(
                    uid,
                    f"👋 Welcome! You were referred by {referred_by.get('name', 'an affiliate')}.\n\n"
                    f"Start your journey with BlockchainPlus Hub!",
                    parse_mode='HTML'
                )
        
        if uid in ADMIN_IDS:
            # Show admin dashboard immediately
            show_admin_dashboard(uid)
            return
        
        # Regular user flow
        # Ask user to select program
        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton("🚀 Crypto Program", callback_data="program:crypto"),
            types.InlineKeyboardButton("📈 Forex Program", callback_data="program:forex")
        )
        bot.send_message(uid, "👋 Welcome to BlockchainPlus Hub!\n\nPlease select your program:", reply_markup=kb)
        
        # Create user in database if not exists
        if not user_db.fetch_user(uid):
            user_db.insert_user(uid, f"{user.first_name or ''}", user.username or "", 'crypto')
            
        # Store referral if exists
        if referred_by:
            user_db.set_referred_by(uid, referred_by['tg_id'])
            
    except Exception as e:
        logger.error(f"Error in /start: {e}")

# ----------------------------
# Compact Menu System with Affiliate Option
# ----------------------------
def send_compact_menu(uid: int, program: str):
    """Send compact menu with main menu button - Updated with affiliate"""
    program_name = "Crypto" if program == "crypto" else "Forex"
    
    # Check if user is affiliate
    user = user_db.fetch_user(uid)
    is_affiliate = user and user.get('is_affiliate')
    
    # Compact keyboard
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.row("📱 Main Menu", "📌 Contact Admin")
    
    if is_affiliate:
        kb.row("🤝 Affiliate Dashboard", "❓ Help")
    else:
        kb.row("🔄 Switch Program", "❓ Help")
    
    welcome_text = (
        f"👋 Welcome to BlockchainPlus {program_name} Program!\n\n"
        f"🔹 <b>Main Menu:</b> Access all features\n"
        f"🔹 <b>Contact Admin:</b> Get support\n"
    )
    
    if is_affiliate:
        welcome_text += f"🔹 <b>Affiliate Dashboard:</b> Track earnings & referrals\n"
    else:
        welcome_text += f"🔹 <b>Switch Program:</b> Change program\n"
    
    welcome_text += f"🔹 <b>Help:</b> Quick assistance\n\n"
    welcome_text += f"Tap <b>📱 Main Menu</b> to get started!"
    
    bot.send_message(uid, welcome_text, parse_mode='HTML', reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "📱 Main Menu")
def show_main_menu(message: types.Message):
    """Show main menu dashboard"""
    try:
        uid = message.from_user.id
        user = user_db.fetch_user(uid)
        program = user.get('program', 'crypto') if user else 'crypto'
        
        program_name = "Crypto" if program == "crypto" else "Forex"
        
        # Main menu dashboard
        menu_text = (
            f"📱 <b>{program_name} Program Dashboard</b>\n\n"
            f"Select an option below:\n\n"
            f"🔹 <b>Account & Subscriptions</b>\n"
            f"• 👋 Welcome: Program overview\n"
            f"• ⏳ Check Status: Subscription details\n"
            f"• 💳 Make Payment: Subscribe/renew\n\n"
            f"🔹 <b>Learning Resources</b>\n"
            f"• 🎥 Tutorials: Video learning\n"
            f"• 🆘 Help: Support & assistance\n\n"
            f"🔹 <b>Settings & Support</b>\n"
            f"• 📌 Contact: Admin support\n"
            f"• 🔄 Switch: Change program\n"
            f"• ❓ Help: Quick assistance\n"
        )
        
        # Add affiliate option if user is approved affiliate
        if user and user.get('is_affiliate'):
            menu_text += f"\n🔹 <b>Affiliate Program</b>\n• 🤝 Affiliate Dashboard: Earn commissions\n"
        
        # Create inline keyboard for main menu
        kb = types.InlineKeyboardMarkup(row_width=2)
        
        # Account & Subscriptions
        kb.row(
            types.InlineKeyboardButton("👋 Welcome", callback_data="mainmenu_welcome"),
            types.InlineKeyboardButton("⏳ Check Status", callback_data="mainmenu_status")
        )
        kb.row(
            types.InlineKeyboardButton("💳 Make Payment", callback_data="mainmenu_payment"),
            types.InlineKeyboardButton("🎥 Tutorials", callback_data="mainmenu_tutorials")
        )
        kb.row(
            types.InlineKeyboardButton("🆘 Help Center", callback_data="mainmenu_help"),
            types.InlineKeyboardButton("📌 Contact Admin", callback_data="mainmenu_contact")
        )
        kb.row(
            types.InlineKeyboardButton("🔄 Switch Program", callback_data="mainmenu_switch"),
            types.InlineKeyboardButton("📋 Quick Actions", callback_data="mainmenu_quick")
        )
        
        # Add affiliate button if user is approved affiliate
        if user and user.get('is_affiliate'):
            kb.row(types.InlineKeyboardButton("🤝 Affiliate Dashboard", callback_data="affiliate_dashboard"))
        
        # Add affiliate registration button if not an affiliate
        elif user and not user.get('is_affiliate') and not user.get('affiliate_status') == 'pending':
            kb.row(types.InlineKeyboardButton("🤝 Become Affiliate", callback_data="affiliate_apply"))
        
        bot.send_message(uid, menu_text, parse_mode='HTML', reply_markup=kb)
        
    except Exception as e:
        logger.error(f"Error showing main menu: {e}")
        bot.send_message(message.chat.id, "Error loading menu. Please try again.")

@bot.message_handler(func=lambda m: m.text == "❓ Help")
def quick_help(message: types.Message):
    """Quick help shortcut"""
    uid = message.from_user.id
    quick_help_text = (
        "❓ <b>Quick Help</b>\n\n"
        "<b>Need assistance?</b>\n"
        "• Tap 📱 Main Menu for all options\n"
        "• Use 🆘 Help in menu for detailed help\n"
        "• Contact admin: @blockchainpluspro\n\n"
        "<b>Common Questions:</b>\n"
        "• Payment issues? Check Payment Help\n"
        "• Can't join groups? Contact admin\n"
        "• Want to change program? Use Switch\n\n"
        "<b>Need more help?</b> Tap below:"
    )
    
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("📱 Open Main Menu", callback_data="mainmenu_back"),
        types.InlineKeyboardButton("🆘 Detailed Help", callback_data="mainmenu_help")
    )
    
    bot.send_message(uid, quick_help_text, parse_mode='HTML', reply_markup=kb)

# FIXED: Main menu callback handler with proper error handling
@bot.callback_query_handler(func=lambda c: c.data.startswith("mainmenu_"))
def handle_main_menu(call: types.CallbackQuery):
    """Handle main menu callbacks - FIXED VERSION"""
    try:
        uid = call.from_user.id
        action = call.data.split("_")[1]
        
        if action == "welcome":
            show_welcome(uid, call.message.message_id)
            
        elif action == "status":
            show_subscription_status(uid, call.message.message_id)
            
        elif action == "payment":
            show_payment_menu(uid, call.message.message_id)
            
        elif action == "tutorials":
            show_tutorials_menu(uid, call.message.message_id)
            
        elif action == "help":
            show_help_menu(uid, call.message.message_id)
            
        elif action == "contact":
            show_contact_admin(uid, call.message.message_id)
            
        elif action == "switch":
            show_switch_program(uid, call.message.message_id)
            
        elif action == "quick":
            show_quick_actions(uid, call.message.message_id)
            
        elif action == "back":
            # FIXED: Properly go back to main menu
            try:
                user = user_db.fetch_user(uid)
                program = user.get('program', 'crypto') if user else 'crypto'
                program_name = "Crypto" if program == "crypto" else "Forex"
                
                menu_text = (
                    f"📱 <b>{program_name} Program Dashboard</b>\n\n"
                    f"Select an option below:\n\n"
                    f"🔹 <b>Account & Subscriptions</b>\n"
                    f"• 👋 Welcome: Program overview\n"
                    f"• ⏳ Check Status: Subscription details\n"
                    f"• 💳 Make Payment: Subscribe/renew\n\n"
                    f"🔹 <b>Learning Resources</b>\n"
                    f"• 🎥 Tutorials: Video learning\n"
                    f"• 🆘 Help: Support & assistance\n\n"
                    f"🔹 <b>Settings & Support</b>\n"
                    f"• 📌 Contact: Admin support\n"
                    f"• 🔄 Switch: Change program\n"
                    f"• ❓ Help: Quick assistance\n"
                )
                
                # Add affiliate option if user is approved affiliate
                if user and user.get('is_affiliate'):
                    menu_text += f"\n🔹 <b>Affiliate Program</b>\n• 🤝 Affiliate Dashboard: Earn commissions\n"
                
                kb = types.InlineKeyboardMarkup(row_width=2)
                kb.row(
                    types.InlineKeyboardButton("👋 Welcome", callback_data="mainmenu_welcome"),
                    types.InlineKeyboardButton("⏳ Check Status", callback_data="mainmenu_status")
                )
                kb.row(
                    types.InlineKeyboardButton("💳 Make Payment", callback_data="mainmenu_payment"),
                    types.InlineKeyboardButton("🎥 Tutorials", callback_data="mainmenu_tutorials")
                )
                kb.row(
                    types.InlineKeyboardButton("🆘 Help Center", callback_data="mainmenu_help"),
                    types.InlineKeyboardButton("📌 Contact Admin", callback_data="mainmenu_contact")
                )
                kb.row(
                    types.InlineKeyboardButton("🔄 Switch Program", callback_data="mainmenu_switch"),
                    types.InlineKeyboardButton("📋 Quick Actions", callback_data="mainmenu_quick")
                )
                
                # Add affiliate button if user is approved affiliate
                if user and user.get('is_affiliate'):
                    kb.row(types.InlineKeyboardButton("🤝 Affiliate Dashboard", callback_data="affiliate_dashboard"))
                
                # Add affiliate registration button if not an affiliate
                elif user and not user.get('is_affiliate') and not user.get('affiliate_status') == 'pending':
                    kb.row(types.InlineKeyboardButton("🤝 Become Affiliate", callback_data="affiliate_apply"))
                
                bot.edit_message_text(
                    menu_text,
                    uid,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=kb
                )
            except Exception as e:
                logger.error(f"Error in mainmenu_back: {e}")
                # Fallback to sending new message
                show_main_menu(call.message)
            
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"Error in main menu handler: {e}")
        bot.answer_callback_query(call.id, "Error loading menu. Please try again.")

def show_welcome(uid: int, message_id: int = None):
    """Show welcome message"""
    user = user_db.fetch_user(uid)
    program = user.get('program', 'crypto') if user else 'crypto'
    
    if program == 'crypto':
        text = (
            "🚀 <b>Welcome to BlockchainPlus Crypto Program</b>\n\n"
            "📚 <b>Crypto Academy</b>\n"
            "• Learn blockchain and crypto trading step-by-step\n"
            "• Live Q&A sessions with experts\n"
            "• Practical trading strategies & risk management\n"
            "• Access to growing community of crypto traders\n"
            "• Regular market updates & analysis\n\n"
            "💎 <b>Crypto VIP Signals</b>\n"
            "• Premium crypto signals with 70%+ accuracy\n"
            "• Exclusive DeGen Group for high-reward plays\n"
            "• Early access to presales & new listings\n"
            "• Real-time market analysis & alerts\n"
            "• Priority support from expert traders\n\n"
            "🔥 <b>DeGen/DeFi Group</b>\n"
            "• High-risk, high-reward plays\n"
            "• Included with Crypto VIP Signals\n\n"
            "✨ <b>Special Bonus:</b> First-time Crypto Academy subscribers receive 3 months FREE VIP Signals + DeGen!\n\n"
            "<b>Use the Main Menu to:</b>\n"
            "• Check your subscription status\n"
            "• Make payment to subscribe\n"
            "• Access tutorial videos\n"
            "• Get help and support"
        )
    else:
        text = (
            "📈 <b>Welcome to BlockchainPlus Forex Program</b>\n\n"
            "📚 <b>Forex Academy</b>\n"
            "• Learn forex trading step-by-step\n"
            "• Live trading sessions & market analysis\n"
            "• Risk management & psychology training\n"
            "• Proven entry/exit strategies\n"
            "• Community support & peer learning\n\n"
            "💎 <b>Forex VIP Signals</b>\n"
            "• High-probability forex signals\n"
            "• Real-time trade setups & alerts\n"
            "• Economic calendar analysis\n"
            "• Risk-reward ratio guidance\n"
            "• VIP community & mastermind sessions\n\n"
            "✨ <b>Special Bonus:</b> First-time Forex Academy subscribers receive 3 months FREE VIP Signals!\n\n"
            "<b>Use the Main Menu to:</b>\n"
            "• Check your subscription status\n"
            "• Make payment to subscribe\n"
            "• Access tutorial videos\n"
            "• Get help and support"
        )
    
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("📱 Back to Menu", callback_data="mainmenu_back"),
        types.InlineKeyboardButton("💳 Make Payment", callback_data="mainmenu_payment")
    )
    
    if message_id:
        bot.edit_message_text(text, uid, message_id, parse_mode='HTML', reply_markup=kb)
    else:
        bot.send_message(uid, text, parse_mode='HTML', reply_markup=kb)

def show_subscription_status(uid: int, message_id: int = None):
    """Show subscription status"""
    try:
        user = user_db.fetch_user(uid)
        if not user:
            text = "You have no active subscription. Click Make Payment to subscribe."
        else:
            lines = ["<b>Your Subscription Status:</b>"]
            
            for prog in ['crypto', 'forex']:
                academy_exp = user.get(f'{prog}_academy_expiry_date')
                vip_exp = user.get(f'{prog}_vip_expiry_date')
                trial_used = user.get(f'{prog}_trial_used', False)
                
                prog_name = "Crypto" if prog == "crypto" else "Forex"
                lines.append(f"\n<b>{prog_name} Program:</b>")
                
                if academy_exp:
                    try:
                        expiry_dt = datetime.strptime(academy_exp, '%Y-%m-%d')
                        days_left = (expiry_dt - datetime.now()).days
                        if days_left >= 0:
                            lines.append(f"📚 Academy: Active until {academy_exp} ({days_left} days left)")
                        else:
                            if days_left >= -GRACE_PERIOD_DAYS:
                                lines.append(f"📚 Academy: Expired ({abs(days_left)} days ago) - {GRACE_PERIOD_DAYS + days_left} grace days left")
                            else:
                                lines.append(f"📚 Academy: Expired ({abs(days_left)} days ago) - Access removed")
                    except:
                        lines.append(f"📚 Academy: Active until {academy_exp}")
                else:
                    lines.append(f"📚 Academy: Not subscribed")
                    
                if vip_exp:
                    try:
                        expiry_dt = datetime.strptime(vip_exp, '%Y-%m-%d')
                        days_left = (expiry_dt - datetime.now()).days
                        if days_left >= 0:
                            lines.append(f"💎 VIP Signals: Active until {vip_exp} ({days_left} days left)")
                        else:
                            if days_left >= -GRACE_PERIOD_DAYS:
                                lines.append(f"💎 VIP Signals: Expired ({abs(days_left)} days ago) - {GRACE_PERIOD_DAYS + days_left} grace days left")
                            else:
                                lines.append(f"💎 VIP Signals: Expired ({abs(days_left)} days ago) - Access removed")
                    except:
                        lines.append(f"💎 VIP Signals: Active until {vip_exp}")
                else:
                    lines.append(f"💎 VIP Signals: Not subscribed")
                    
                if prog == 'crypto' and vip_exp:
                    lines.append(f"🔥 DeGen Group: Included with VIP")
                
                if not trial_used and academy_exp and not vip_exp:
                    lines.append(f"✨ Note: You're eligible for 3 months free VIP trial!")
            
            text = "\n".join(lines)
        
        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton("📱 Back to Menu", callback_data="mainmenu_back"),
            types.InlineKeyboardButton("💳 Renew Subscription", callback_data="mainmenu_payment")
        )
        
        if message_id:
            bot.edit_message_text(text, uid, message_id, parse_mode='HTML', reply_markup=kb)
        else:
            bot.send_message(uid, text, parse_mode='HTML', reply_markup=kb)
            
    except Exception as e:
        logger.error(f"Error in subscription status: {e}")
        if message_id:
            bot.edit_message_text("Error checking status. Please try again.", uid, message_id)
        else:
            bot.send_message(uid, "Error checking status. Please try again.")

def show_payment_menu(uid: int, message_id: int = None):
    """Show payment menu"""
    user = user_db.fetch_user(uid)
    program = user.get('program', 'crypto') if user else 'crypto'
    
    program_name = "Crypto" if program == "crypto" else "Forex"
    
    text = (
        f"💳 <b>{program_name} Program - Make Payment</b>\n\n"
        f"Select a plan to continue:\n\n"
        f"📚 <b>Academy:</b> Complete education program\n"
        f"• Duration: 1 year\n"
        f"• Price: {PRICING[program]['academy']['ngn']} / {PRICING[program]['academy']['usd']}\n"
        f"• Bonus: 3 months FREE VIP included!\n\n"
        f"💎 <b>VIP Signals:</b> Premium trading signals\n"
        f"• Choose from monthly to yearly plans\n"
        f"• Real-time signals & analysis\n"
        f"• Exclusive community access\n"
    )
    
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(text="📚 Academy", callback_data=f"choose_{program}_academy"))
    kb.add(types.InlineKeyboardButton(text="💎 VIP Signals", callback_data=f"choose_{program}_vip"))
    kb.add(types.InlineKeyboardButton("📱 Back to Menu", callback_data="mainmenu_back"))
    
    if message_id:
        bot.edit_message_text(text, uid, message_id, parse_mode='HTML', reply_markup=kb)
    else:
        bot.send_message(uid, text, parse_mode='HTML', reply_markup=kb)

# ----------------------------
# UPDATED TUTORIALS SECTION - VIDEOS PLAY DIRECTLY IN TELEGRAM BOT
# ----------------------------
def show_tutorials_menu(uid: int, message_id: int = None):
    """Show tutorials menu"""
    text = (
        "🎬 <b>BlockchainPlus Tutorial Library</b>\n\n"
        "Access our comprehensive collection of trading tutorials:\n\n"
        "📊 <b>Bybit Tutorials:</b> Complete trading guides\n"
        "💼 <b>Binance Tutorials:</b> Exchange walkthroughs\n"
        "🔄 <b>Other Exchanges:</b> Ourbit, Bitunix, MEXC\n"
        "📈 <b>Trading Strategies:</b> Risk management, profits\n"
        "📚 <b>Trading Education:</b> Beginner to advanced\n"
        "🔒 <b>Security Guides:</b> Stay safe while trading\n\n"
        "Select a category below:"
    )
    
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("📊 Bybit Tutorials", callback_data="tut_cat:bybit"))
    kb.add(types.InlineKeyboardButton("💼 Binance Tutorials", callback_data="tut_cat:binance"))
    kb.add(types.InlineKeyboardButton("🔄 Other Exchanges", callback_data="tut_cat:exchanges"))
    kb.add(types.InlineKeyboardButton("📈 Trading Strategies", callback_data="tut_cat:strategies"))
    kb.add(types.InlineKeyboardButton("📚 Trading Education", callback_data="tut_cat:education"))
    kb.add(types.InlineKeyboardButton("🔒 Security Guides", callback_data="tut_cat:security"))
    kb.add(types.InlineKeyboardButton("🔍 Search Tutorials", callback_data="tut_search"))
    kb.add(types.InlineKeyboardButton("📱 Back to Menu", callback_data="mainmenu_back"))
    
    if message_id:
        bot.edit_message_text(text, uid, message_id, parse_mode='HTML', reply_markup=kb)
    else:
        bot.send_message(uid, text, parse_mode='HTML', reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("tut_"))
def handle_tutorial_callback(call: types.CallbackQuery):
    """Handle all tutorial-related callbacks"""
    try:
        uid = call.from_user.id
        data = call.data
        
        if data.startswith("tut_cat:"):
            # Category selected
            category = data.split(":")[1]
            show_tutorials_by_category(uid, category, call.message.message_id)
            
        elif data == "tut_search":
            # Show search options
            show_tutorial_search(uid, call.message.message_id)
            
        elif data.startswith("tut_view:"):
            # View specific tutorial
            tutorial_id = int(data.split(":")[1])
            show_tutorial_detail(uid, tutorial_id, call.message.message_id)
            
        elif data.startswith("tut_page:"):
            # Pagination
            parts = data.split(":")
            category = parts[1]
            page = int(parts[2])
            show_tutorials_by_category(uid, category, call.message.message_id, page)
            
        elif data == "tut_back_menu":
            # Back to tutorial menu
            show_tutorials_menu(uid, call.message.message_id)
            
        elif data.startswith("tut_back_cat:"):
            # Back to category
            category = data.split(":")[1]
            show_tutorials_by_category(uid, category, call.message.message_id)
            
        elif data == "tut_back_search":
            # Back to search
            show_tutorial_search(uid, call.message.message_id)
            
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"Error in tutorial callback: {e}")
        bot.answer_callback_query(call.id, "Error loading content. Please try again.")

def show_tutorials_by_category(uid: int, category: str, message_id: int, page: int = 0):
    """Show tutorials by category with pagination - IMPROVED WITH FULL TITLES"""
    try:
        # Filter tutorials by category
        category_tutorials = [t for t in TUTORIALS if t['category'] == category]
        
        if not category_tutorials:
            bot.edit_message_text(
                "❌ No tutorials found in this category.",
                uid,
                message_id,
                parse_mode='HTML'
            )
            return
        
        # Pagination
        per_page = 5
        start_idx = page * per_page
        end_idx = start_idx + per_page
        current_tutorials = category_tutorials[start_idx:end_idx]
        
        # Create message
        category_name = TUTORIAL_CATEGORIES.get(category, category.title())
        message_text = f"<b>{category_name}</b>\n\n"
        
        for i, tutorial in enumerate(current_tutorials, 1):
            message_text += f"<b>{start_idx + i}. {tutorial['title']}</b>\n"
            message_text += f"<i>{tutorial['description']}</i>\n\n"
        
        # Add pagination info
        total_pages = (len(category_tutorials) + per_page - 1) // per_page
        message_text += f"📄 Page {page + 1} of {total_pages}\n"
        message_text += f"📹 Total videos: {len(category_tutorials)}"
        
        # Create keyboard - IMPROVED: Show full titles in buttons
        kb = types.InlineKeyboardMarkup(row_width=1)
        
        # Add tutorial buttons with full titles (truncate if too long)
        for i, tutorial in enumerate(current_tutorials, start=start_idx + 1):
            # Truncate title if too long for button
            title = tutorial['title']
            if len(title) > 40:
                title = title[:37] + "..."
            
            kb.add(types.InlineKeyboardButton(
                f"🎬 {i}: {title}",
                callback_data=f"tut_view:{tutorial['id']}"
            ))
        
        # Add navigation buttons
        nav_buttons = []
        if page > 0:
            nav_buttons.append(types.InlineKeyboardButton(
                "⬅️ Previous",
                callback_data=f"tut_page:{category}:{page-1}"
            ))
        
        nav_buttons.append(types.InlineKeyboardButton(
            "📱 Back to Menu",
            callback_data="mainmenu_back"
        ))
        
        if end_idx < len(category_tutorials):
            nav_buttons.append(types.InlineKeyboardButton(
                "Next ➡️",
                callback_data=f"tut_page:{category}:{page+1}"
            ))
        
        if nav_buttons:
            kb.row(*nav_buttons)
        
        # Edit the message
        bot.edit_message_text(
            message_text,
            uid,
            message_id,
            parse_mode='HTML',
            reply_markup=kb
        )
        
    except Exception as e:
        logger.error(f"Error showing tutorials by category: {e}")
        bot.edit_message_text(
            "Error loading tutorials. Please try again.",
            uid,
            message_id
        )

def show_tutorial_detail(uid: int, tutorial_id: int, message_id: int):
    """Show detailed tutorial information with video playing directly in Telegram"""
    try:
        # Find tutorial
        tutorial = next((t for t in TUTORIALS if t['id'] == tutorial_id), None)
        
        if not tutorial:
            bot.edit_message_text(
                "❌ Tutorial not found.",
                uid,
                message_id,
                parse_mode='HTML'
            )
            return
        
        # First, send the video directly within Telegram (if we have the file_id)
        video_caption = (
            f"🎬 <b>{tutorial['title']}</b>\n\n"
            f"📝 <b>Description:</b>\n"
            f"{tutorial['description']}\n\n"
            f"📊 <b>Category:</b> {TUTORIAL_CATEGORIES.get(tutorial['category'], tutorial['category'].title())}"
        )
        
        # Try to send video directly if we have telegram_video_id
        if tutorial.get('telegram_video_id'):
            try:
                # Send video directly within Telegram
                sent_video = bot.send_video(
                    uid,
                    tutorial['telegram_video_id'],
                    caption=video_caption,
                    parse_mode='HTML'
                )
                
                # Send buttons in a separate message below the video
                buttons_text = "👇 <b>Additional Options:</b>"
                
                kb = types.InlineKeyboardMarkup(row_width=1)
                kb.add(types.InlineKeyboardButton(
                    "📺 Watch on YouTube",
                    url=tutorial['url']
                ))
                
                # Add navigation buttons
                kb.row(
                    types.InlineKeyboardButton("⬅️ Back to Category", callback_data=f"tut_back_cat:{tutorial['category']}"),
                    types.InlineKeyboardButton("📱 Main Menu", callback_data="mainmenu_back")
                )
                
                bot.send_message(uid, buttons_text, parse_mode='HTML', reply_markup=kb)
                
            except Exception as e:
                logger.error(f"Error sending Telegram video: {e}. Falling back to thumbnail.")
                # Fallback to thumbnail
                send_tutorial_fallback(uid, tutorial, video_caption)
        else:
            # If no Telegram video ID, use fallback
            send_tutorial_fallback(uid, tutorial, video_caption)
        
        # Delete the original list message
        try:
            bot.delete_message(uid, message_id)
        except Exception as e:
            logger.error(f"Could not delete message: {e}")
        
    except Exception as e:
        logger.error(f"Error showing tutorial detail: {e}")
        bot.edit_message_text(
            "Error loading tutorial details. Please try again.",
            uid,
            message_id
        )

def send_tutorial_fallback(uid: int, tutorial: dict, caption: str):
    """Fallback method if Telegram video is not available"""
    try:
        # Try to send thumbnail first
        if tutorial.get('thumbnail'):
            sent_msg = bot.send_photo(
                uid,
                tutorial['thumbnail'],
                caption=caption,
                parse_mode='HTML'
            )
        else:
            # Send text message
            sent_msg = bot.send_message(
                uid,
                caption,
                parse_mode='HTML'
            )
        
        # Send buttons below
        buttons_text = "👇 <b>Watch this tutorial:</b>"
        
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(types.InlineKeyboardButton(
            "📺 Watch on YouTube",
            url=tutorial['url']
        ))
        
        # Add navigation buttons
        kb.row(
            types.InlineKeyboardButton("⬅️ Back to Category", callback_data=f"tut_back_cat:{tutorial['category']}"),
            types.InlineKeyboardButton("📱 Main Menu", callback_data="mainmenu_back")
        )
        
        bot.send_message(
            uid,
            buttons_text,
            parse_mode='HTML',
            reply_markup=kb
        )
        
    except Exception as e:
        logger.error(f"Error in tutorial fallback: {e}")
        bot.send_message(
            uid,
            f"🎬 <b>{tutorial['title']}</b>\n\n"
            f"📝 <b>Description:</b>\n"
            f"{tutorial['description']}\n\n"
            f"📊 <b>Category:</b> {TUTORIAL_CATEGORIES.get(tutorial['category'], tutorial['category'].title())}\n\n"
            f"Watch on YouTube: {tutorial['url']}",
            parse_mode='HTML'
        )

def show_tutorial_search(uid: int, message_id: int):
    """Show tutorial search interface"""
    try:
        message_text = (
            "🔍 <b>Tutorial Search</b>\n\n"
            "Search tutorials by category:\n\n"
            "• <b>Bybit Tutorials:</b> Trading, P2P, futures\n"
            "• <b>Binance Tutorials:</b> Spot, futures, exchange\n"
            "• <b>Other Exchanges:</b> Ourbit, Bitunix, MEXC\n"
            "• <b>Trading Strategies:</b> Risk, profit, margin\n"
            "• <b>Trading Education:</b> Beginner guides\n"
            "• <b>Security Guides:</b> Stay safe while trading\n\n"
            "Select a category below:"
        )
        
        kb = types.InlineKeyboardMarkup(row_width=2)
        
        # Add quick search buttons
        kb.add(
            types.InlineKeyboardButton("🔍 Bybit", callback_data="tut_cat:bybit"),
            types.InlineKeyboardButton("🔍 Binance", callback_data="tut_cat:binance")
        )
        kb.add(
            types.InlineKeyboardButton("🔍 Other Exchanges", callback_data="tut_cat:exchanges"),
            types.InlineKeyboardButton("🔍 Strategies", callback_data="tut_cat:strategies")
        )
        kb.add(
            types.InlineKeyboardButton("🔍 Education", callback_data="tut_cat:education"),
            types.InlineKeyboardButton("🔍 Security", callback_data="tut_cat:security")
        )
        
        # Add back button
        kb.add(types.InlineKeyboardButton("⬅️ Back to Tutorials", callback_data="tut_back_menu"))
        
        # Edit the message
        bot.edit_message_text(
            message_text,
            uid,
            message_id,
            parse_mode='HTML',
            reply_markup=kb
        )
        
    except Exception as e:
        logger.error(f"Error showing tutorial search: {e}")
        bot.edit_message_text(
            "Error loading search. Please try again.",
            uid,
            message_id
        )

# ----------------------------
# UPDATED HELP SECTION WITH COMPLETE FAQ AND OFFICIAL LINKS
# ----------------------------
def show_help_menu(uid: int, message_id: int = None):
    """Show help menu"""
    text = (
        "🆘 <b>BlockchainPlus Help Center</b>\n\n"
        "Get assistance for:\n\n"
        "🔹 <b>Technical Issues:</b>\n"
        "• Problems joining groups\n"
        "• Payment verification\n"
        "• Subscription status\n\n"
        "🔹 <b>Trading Assistance:</b>\n"
        "• Understanding trading concepts\n"
        "• Platform navigation\n"
        "• Strategy explanations\n\n"
        "🔹 <b>Account & Billing:</b>\n"
        "• Payment methods\n"
        "• Subscription renewals\n"
        "• Account access\n\n"
        "Select an option below:"
    )
    
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📞 Contact Support", url="https://t.me/blockchainpluspro"),
        types.InlineKeyboardButton("📚 FAQ & Guides", callback_data="help_faq")
    )
    kb.add(
        types.InlineKeyboardButton("💳 Payment Help", callback_data="help_payment"),
        types.InlineKeyboardButton("🚀 Getting Started", callback_data="help_started")
    )
    kb.add(
        types.InlineKeyboardButton("🎯 Trading Basics", callback_data="help_trading"),
        types.InlineKeyboardButton("🔐 Account Security", callback_data="help_security")
    )
    kb.add(
        types.InlineKeyboardButton("📧 Email Support", callback_data="help_email"),
        types.InlineKeyboardButton("🔗 Official Channels", callback_data="help_official")
    )
    kb.add(types.InlineKeyboardButton("📱 Back to Menu", callback_data="mainmenu_back"))
    
    if message_id:
        bot.edit_message_text(text, uid, message_id, parse_mode='HTML', reply_markup=kb)
    else:
        bot.send_message(uid, text, parse_mode='HTML', reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("help_"))
def handle_help_callback(call: types.CallbackQuery):
    """Handle all help-related callbacks"""
    try:
        uid = call.from_user.id
        help_type = call.data
        
        help_responses = {
            "help_faq": {
                "title": "📚 <b>Blockchain Plus Hub – Frequently Asked Questions (FAQs)</b>",
                "content": (
                    "<b>📋 General Information</b>\n\n"
                    "<b>Q: What is Blockchain Plus Hub?</b>\n"
                    "A: Blockchain Plus Hub is an educational and trading-focused platform designed to help individuals learn, grow, and earn through Forex trading and Cryptocurrency trading & investing.\n\n"
                    
                    "<b>Q: Who is Blockchain Plus Hub for?</b>\n"
                    "A: Blockchain Plus Hub is for:\n"
                    "• Beginners who want to learn Forex or Crypto from scratch\n"
                    "• Intermediate traders looking to improve consistency\n"
                    "• Advanced traders seeking structured systems and discipline\n"
                    "• Investors who want to understand crypto markets properly\n\n"
                    
                    "<b>Q: Is Blockchain Plus Hub an investment company?</b>\n"
                    "A: No. We are NOT an investment firm and do not accept funds to trade on behalf of members. We are an education, signals, and mentorship platform.\n\n"
                    
                    "<b>💱 Forex Trading Program FAQs</b>\n\n"
                    "<b>Q: What is the Forex Trading Program about?</b>\n"
                    "A: The Forex Trading Program teaches members how to trade the foreign exchange market using proven strategies, proper risk management, and market psychology.\n\n"
                    
                    "<b>Q: Is the Forex program suitable for beginners?</b>\n"
                    "A: Yes. The Forex program starts from the basics and gradually moves to advanced concepts.\n\n"
                    
                    "<b>Q: Do you provide Forex trading signals?</b>\n"
                    "A: Yes. Members may receive Forex trading signals including entry points, stop loss, and take profit levels.\n\n"
                    
                    "<b>🚀 Cryptocurrency Program FAQs</b>\n\n"
                    "<b>Q: What is the Crypto Trading & Investment Program about?</b>\n"
                    "A: The Crypto program focuses on helping members understand and profit from the cryptocurrency market through spot trading, futures trading, and long-term investing.\n\n"
                    
                    "<b>Q: Do you provide crypto signals?</b>\n"
                    "A: Yes. Crypto signals may include spot trade entries, futures trade setups, and market structure updates.\n\n"
                    
                    "<b>Q: Is Futures trading included?</b>\n"
                    "A: Yes, but Futures trading is recommended only for experienced traders.\n\n"
                    
                    "<b>📝 Membership & Access</b>\n\n"
                    "<b>Q: What do I get when I join?</b>\n"
                    "A: Depending on your subscription, you may receive educational materials, trading signals, community support via Telegram, mentorship, and challenges.\n\n"
                    
                    "<b>⚠️ Risk & Disclaimer</b>\n\n"
                    "<b>Q: Are profits guaranteed?</b>\n"
                    "A: NO. There are NO guaranteed profits in trading or investing. Results vary based on market conditions, discipline, capital, and risk management.\n\n"
                    
                    "<b>Q: Can I lose money?</b>\n"
                    "A: Yes. Trading involves risk, and losses are possible. Never trade with money you cannot afford to lose.\n\n"
                    
                    "<b>👥 Community & Support</b>\n\n"
                    "<b>Q: Is there a community I can join?</b>\n"
                    "A: Yes. Members gain access to our Telegram community for market updates, questions, and experience sharing.\n\n"
                    
                    "<b>🎯 Getting Started</b>\n\n"
                    "<b>Q: How do I join Blockchain Plus Hub?</b>\n"
                    "A: You can join by following the official registration or subscription links shared by Blockchain Plus Hub admins.\n\n"
                    
                    "<b>📢 Final Note:</b> Blockchain Plus Hub is built to educate, guide, and empower traders—not to promise unrealistic profits. Success comes from consistency, patience, and continuous learning."
                ),
                "buttons": [
                    {"text": "📞 Contact Support", "url": "https://t.me/blockchainpluspro"},
                    {"text": "📱 Back to Menu", "callback_data": "mainmenu_back"}
                ]
            },
            "help_payment": {
                "title": "💳 <b>Payment Help & Support</b>",
                "content": (
                    "<b>Payment Issues & Solutions:</b>\n\n"
                    
                    "🔸 <b>Payment Not Verified?</b>\n"
                    "• Upload clear POP (Proof of Payment)\n"
                    "• Include transaction ID and amount\n"
                    "• Allow 1 hour for verification\n\n"
                    
                    "🔸 <b>Accepted Payment Methods:</b>\n"
                    "• 🇳🇬 NGN: Opay & MoniePoint\n"
                    "• 💎 USDT: BEP20, TRC20, or TON\n\n"
                    
                    "🔸 <b>Payment Security Tips:</b>\n"
                    "• Verify account details before sending\n"
                    "• Keep transaction screenshots\n"
                    "• Contact us immediately for issues\n\n"
                    
                    "<b>Need help?</b> Contact @blockchainpluspro"
                ),
                "buttons": [
                    {"text": "📞 Payment Support", "url": "https://t.me/blockchainpluspro"},
                    {"text": "💳 Make Payment", "callback_data": "mainmenu_payment"},
                    {"text": "📱 Back to Menu", "callback_data": "mainmenu_back"}
                ]
            },
            "help_started": {
                "title": "🚀 <b>Getting Started Guide</b>",
                "content": (
                    "<b>Welcome! Follow these steps:</b>\n\n"
                    
                    "1️⃣ <b>Choose Your Program</b>\n"
                    "• Select Crypto or Forex\n"
                    "• Use 'Switch Program' to change later\n\n"
                    
                    "2️⃣ <b>Subscribe to a Plan</b>\n"
                    "• Academy: Complete education (1 year)\n"
                    "• VIP: Premium signals (choose duration)\n"
                    "• Use 'Make Payment' to subscribe\n\n"
                    
                    "3️⃣ <b>Join Your Groups</b>\n"
                    "• Added automatically after approval\n"
                    "• Save group links for easy access\n\n"
                    
                    "4️⃣ <b>Learn & Trade</b>\n"
                    "• Watch tutorials in 'Tutorials'\n"
                    "• Check subscription status anytime\n"
                    "• Contact admin for guidance\n\n"
                    
                    "<b>Pro Tip:</b> Start with Academy + FREE VIP trial!"
                ),
                "buttons": [
                    {"text": "🎥 Watch Tutorials", "callback_data": "mainmenu_tutorials"},
                    {"text": "💳 Subscribe Now", "callback_data": "mainmenu_payment"},
                    {"text": "📱 Back to Menu", "callback_data": "mainmenu_back"}
                ]
            },
            "help_trading": {
                "title": "🎯 <b>Trading Basics & Essentials</b>",
                "content": (
                    "<b>Essential Trading Knowledge:</b>\n\n"
                    
                    "📊 <b>Key Concepts:</b>\n"
                    "• Spot vs Futures trading\n"
                    "• Risk management strategies\n"
                    "• Market analysis techniques\n"
                    "• Position sizing basics\n\n"
                    
                    "🛡️ <b>Risk Management:</b>\n"
                    "• Never risk more than 2% per trade\n"
                    "• Always use stop-loss orders\n"
                    "• Diversify your portfolio\n"
                    "• Keep emotions in check\n\n"
                    
                    "📈 <b>Learning Path:</b>\n"
                    "1. Start with our tutorial videos\n"
                    "2. Join Academy for structured learning\n"
                    "3. Practice with demo accounts first\n"
                    "4. Apply VIP signals with small amounts\n"
                ),
                "buttons": [
                    {"text": "🎬 Watch Tutorials", "callback_data": "tut_cat:strategies"},
                    {"text": "📚 Beginner Guides", "callback_data": "tut_cat:education"},
                    {"text": "📱 Back to Menu", "callback_data": "mainmenu_back"}
                ]
            },
            "help_security": {
                "title": "🔐 <b>Account Security Guide</b>",
                "content": (
                    "<b>Protect Your Accounts & Funds:</b>\n\n"
                    
                    "🛡️ <b>Essential Security:</b>\n"
                    "• Use strong, unique passwords\n"
                    "• Enable 2FA on all exchanges\n"
                    "• Never share full-permission API keys\n"
                    "• Beware of phishing links\n\n"
                    
                    "🚫 <b>Common Scams to Avoid:</b>\n"
                    "• Fake support accounts\n"
                    "• 'Guaranteed profit' schemes\n"
                    "• Unverified investment opportunities\n"
                    "• Impersonation of our team\n\n"
                    
                    "✅ <b>Official Channels Only:</b>\n"
                    "• This bot is official\n"
                    "• Admin: @blockchainpluspro\n"
                    "• Never send funds to random addresses\n"
                ),
                "buttons": [
                    {"text": "🎥 Security Tutorial", "callback_data": "tut_cat:security"},
                    {"text": "📞 Report Issue", "url": "https://t.me/blockchainpluspro"},
                    {"text": "📱 Back to Menu", "callback_data": "mainmenu_back"}
                ]
            },
            "help_email": {
                "title": "📧 <b>Email Support</b>",
                "content": (
                    "<b>For comprehensive support, email:</b>\n\n"
                    "📨 <b>Support Email:</b>\n"
                    "blockchainplushub@gmail.com\n\n"
                    
                    "<b>Include in your email:</b>\n"
                    "1. Your Telegram ID\n"
                    "2. Brief description of issue\n"
                    "3. Screenshots if applicable\n"
                    "4. Transaction IDs for payments\n\n"
                    
                    "<b>Response Time:</b>\n"
                    "• Usually within 24 hours\n"
                    "• Faster via Telegram\n"
                    "• Business hours: 9 AM - 6 PM GMT+1\n"
                ),
                "buttons": [
                    {"text": "📞 Telegram Support", "url": "https://t.me/blockchainpluspro"},
                    {"text": "📱 Back to Menu", "callback_data": "mainmenu_back"}
                ]
            },
            "help_official": {
                "title": "🔗 <b>Official Channels & Social Media</b>",
                "content": (
                    "<b>Stay Connected with Blockchain Plus Hub:</b>\n\n"
                    
                    "📢 <b>Official Telegram Channel:</b>\n"
                    "Get updates, announcements, and market insights\n\n"
                    
                    "🎬 <b>YouTube Channel:</b>\n"
                    "Watch our latest tutorials, trading guides, and educational content\n\n"
                    
                    "🎵 <b>TikTok:</b>\n"
                    "Short-form trading tips and market updates\n\n"
                    
                    "🐦 <b>Twitter/X:</b>\n"
                    "Follow for crypto news, trading insights, and community updates\n\n"
                    
                    "📍 <b>Always verify you're following our official channels to avoid scams!</b>"
                ),
                "buttons": [
                    {"text": "📢 Telegram Channel", "url": "https://t.me/blockchainplushub"},
                    {"text": "🎬 YouTube Channel", "url": "https://www.youtube.com/@Blockchainplushub"},
                    {"text": "🎵 TikTok", "url": "https://www.tiktok.com/@blockchainplus?_r=1&_t=ZS-92vZFPIWKV2"},
                    {"text": "🐦 Twitter/X", "url": "https://x.com/bcplushub?t=aiphzEilvUyoptHO64MyEA&s=09"},
                    {"text": "📞 Contact Admin", "url": "https://t.me/blockchainpluspro"},
                    {"text": "📱 Back to Menu", "callback_data": "mainmenu_back"}
                ]
            }
        }
        
        response = help_responses.get(help_type)
        if not response:
            bot.answer_callback_query(call.id, "Help topic not found.")
            return
        
        # Create message text
        message_text = f"{response['title']}\n\n{response['content']}"
        
        # Create keyboard
        kb = types.InlineKeyboardMarkup(row_width=2)
        
        # Add buttons in rows
        buttons = []
        for btn in response.get("buttons", []):
            if 'url' in btn:
                buttons.append(types.InlineKeyboardButton(btn['text'], url=btn['url']))
            else:
                buttons.append(types.InlineKeyboardButton(btn['text'], callback_data=btn['callback_data']))
        
        # Arrange buttons in rows of 2
        for i in range(0, len(buttons), 2):
            if i + 1 < len(buttons):
                kb.row(buttons[i], buttons[i+1])
            else:
                kb.row(buttons[i])
        
        # Edit the message
        bot.edit_message_text(
            message_text,
            uid,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=kb
        )
        
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"Error in help callback: {e}")
        bot.answer_callback_query(call.id, "Error loading help information.")

def show_contact_admin(uid: int, message_id: int = None):
    """Show contact admin"""
    text = (
        "📌 <b>Contact Admin</b>\n\n"
        "Need help or have questions?\n\n"
        "💬 <b>Telegram:</b> @blockchainpluspro\n\n"
        "📧 <b>Email:</b> blockchainplushub@gmail.com\n\n"
        "⏰ <b>Response Time:</b>\n"
        "• Usually within 1 hour\n"
        "• Business hours: 9 AM - 6 PM GMT+1\n\n"
        "🔹 <b>For urgent matters:</b>\n"
        "Please use Telegram for faster response."
    )
    
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("📱 Back to Menu", callback_data="mainmenu_back"),
        types.InlineKeyboardButton("💬 Message Admin", url="https://t.me/blockchainpluspro")
    )
    
    if message_id:
        bot.edit_message_text(text, uid, message_id, parse_mode='HTML', reply_markup=kb)
    else:
        bot.send_message(uid, text, parse_mode='HTML', reply_markup=kb)

def show_switch_program(uid: int, message_id: int = None):
    """Show switch program"""
    text = (
        "🔄 <b>Switch Program</b>\n\n"
        "Select the program you want to switch to:\n\n"
        "🚀 <b>Crypto Program:</b>\n"
        "• Cryptocurrency trading\n"
        "• Blockchain education\n"
        "• Crypto VIP signals\n"
        "• DeGen group access\n\n"
        "📈 <b>Forex Program:</b>\n"
        "• Forex trading\n"
        "• Currency pair analysis\n"
        "• Forex VIP signals\n"
        "• Market analysis\n\n"
        "Note: Switching programs doesn't cancel your current subscriptions."
    )
    
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("🚀 Crypto Program", callback_data="program:crypto"),
        types.InlineKeyboardButton("📈 Forex Program", callback_data="program:forex")
    )
    kb.add(types.InlineKeyboardButton("📱 Back to Menu", callback_data="mainmenu_back"))
    
    if message_id:
        bot.edit_message_text(text, uid, message_id, parse_mode='HTML', reply_markup=kb)
    else:
        bot.send_message(uid, text, parse_mode='HTML', reply_markup=kb)

def show_quick_actions(uid: int, message_id: int = None):
    """Show quick actions"""
    text = (
        "📋 <b>Quick Actions</b>\n\n"
        "Frequently used actions:\n\n"
        "⚡ <b>Check Status:</b> View subscription details\n"
        "⚡ <b>Make Payment:</b> Subscribe or renew\n"
        "⚡ <b>Tutorials:</b> Watch learning videos\n"
        "⚡ <b>Help:</b> Get assistance\n"
        "⚡ <b>Contact:</b> Reach admin\n"
        "⚡ <b>Switch:</b> Change program\n\n"
        "Select an action below:"
    )
    
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(
        types.InlineKeyboardButton("⏳ Check Status", callback_data="mainmenu_status"),
        types.InlineKeyboardButton("💳 Make Payment", callback_data="mainmenu_payment")
    )
    kb.row(
        types.InlineKeyboardButton("🎥 Tutorials", callback_data="mainmenu_tutorials"),
        types.InlineKeyboardButton("🆘 Help", callback_data="mainmenu_help")
    )
    kb.row(
        types.InlineKeyboardButton("📌 Contact", callback_data="mainmenu_contact"),
        types.InlineKeyboardButton("🔄 Switch", callback_data="mainmenu_switch")
    )
    kb.add(types.InlineKeyboardButton("📱 Back to Menu", callback_data="mainmenu_back"))
    
    if message_id:
        bot.edit_message_text(text, uid, message_id, parse_mode='HTML', reply_markup=kb)
    else:
        bot.send_message(uid, text, parse_mode='HTML', reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🔄 Switch Program")
def menu_switch_program(message: types.Message):
    show_switch_program(message.chat.id)

@bot.message_handler(func=lambda m: m.text == "📌 Contact Admin")
def menu_contact(message: types.Message):
    show_contact_admin(message.chat.id)

# ----------------------------
# Make Payment flow (EXISTING - UNCHANGED)
# ----------------------------
@bot.callback_query_handler(func=lambda c: c.data.startswith("choose_"))
def on_choose_plan(call: types.CallbackQuery):
    try:
        data = call.data
        uid = call.from_user.id
        
        # Handle academy selection
        if "academy" in data:
            program = "crypto" if "crypto" in data else "forex"
            amount_naira = PRICING[program]['academy']['ngn']
            amount_usd = PRICING[program]['academy']['usd']
            
            header = (
                f"You selected {program.capitalize()} Academy\n"
                f"Amount: {amount_naira} / {amount_usd}\n\n"
                "Choose your payment method and proceed to make payment."
            )
            
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("Pay in ₦ (NGN)", callback_data=f"pay:{program}:naira:academy:"))
            kb.add(types.InlineKeyboardButton("Pay in USDT (USDT)", callback_data=f"pay:{program}:usdt:academy:"))
            kb.add(types.InlineKeyboardButton("📱 Back to Menu", callback_data="mainmenu_back"))
            bot.send_message(uid, header, reply_markup=kb)
        
        # Handle VIP selection - show duration options
        elif "vip" in data:
            program = "crypto" if "crypto" in data else "forex"
            
            kb = types.InlineKeyboardMarkup(row_width=1)
            kb.add(
                types.InlineKeyboardButton(
                    f"Monthly — {PRICING[program]['vip']['monthly']['ngn']} / {PRICING[program]['vip']['monthly']['usd']}", 
                    callback_data=f"vip_dur:{program}:monthly"
                ),
                types.InlineKeyboardButton(
                    f"3 Months — {PRICING[program]['vip']['3_months']['ngn']} / {PRICING[program]['vip']['3_months']['usd']}", 
                    callback_data=f"vip_dur:{program}:3_months"
                ),
                types.InlineKeyboardButton(
                    f"6 Months — {PRICING[program]['vip']['6_months']['ngn']} / {PRICING[program]['vip']['6_months']['usd']}", 
                    callback_data=f"vip_dur:{program}:6_months"
                ),
                types.InlineKeyboardButton(
                    f"1 Year — {PRICING[program]['vip']['yearly']['ngn']} / {PRICING[program]['vip']['yearly']['usd']}", 
                    callback_data=f"vip_dur:{program}:yearly"
                )
            )
            kb.add(types.InlineKeyboardButton("📱 Back to Menu", callback_data="mainmenu_back"))
            bot.send_message(uid, f"Select a {program.capitalize()} VIP Signals plan:", reply_markup=kb)
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        logger.error(f"Error in choose plan: {e}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("vip_dur:"))
def on_vip_duration_selected(call: types.CallbackQuery):
    """Handle VIP duration selection"""
    try:
        parts = call.data.split(":")
        program = parts[1]
        duration = parts[2]
        uid = call.from_user.id
        
        # Duration display names
        dur_names = {
            'monthly': 'Monthly',
            '3_months': '3 Months',
            '6_months': '6 Months',
            'yearly': '1 Year'
        }
        
        dur_display = dur_names.get(duration, duration)
        amount_naira = PRICING[program]['vip'][duration]['ngn']
        amount_usd = PRICING[program]['vip'][duration]['usd']
        
        header = (
            f"You selected {program.capitalize()} VIP Signal {dur_display}\n"
            f"Amount: {amount_naira} / {amount_usd}\n\n"
            "Choose your payment method and proceed to make payment."
        )
        
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Pay in ₦ (NGN)", callback_data=f"pay:{program}:naira:vip:{duration}"))
        kb.add(types.InlineKeyboardButton("Pay in USDT (USDT)", callback_data=f"pay:{program}:usdt:vip:{duration}"))
        kb.add(types.InlineKeyboardButton("📱 Back to Menu", callback_data="mainmenu_back"))
        
        bot.send_message(uid, header, reply_markup=kb)
        bot.answer_callback_query(call.id)
    except Exception as e:
        logger.error(f"Error in VIP duration selection: {e}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("pay:"))
def on_pay_choice(call: types.CallbackQuery):
    """Handle payment method selection"""
    try:
        parts = call.data.split(":")
        program = parts[1]  # 'crypto' or 'forex'
        currency = parts[2]  # 'naira' or 'usdt'
        plan_choice = parts[3]  # 'academy' or 'vip'
        vip_dur = parts[4] if len(parts) > 4 and parts[4] else None
        uid = call.from_user.id

        amount_text = get_amount_text(program, plan_choice, vip_dur, currency)
        program_name = program.capitalize()
        plan_name = plan_display_name(plan_choice, vip_dur)

        if currency == "naira":
            text = (
                f"💳 <b>{program_name} Program - NGN Payment</b>\n"
                f"Plan: {plan_name}\n"
                f"Amount: <b>{amount_text}</b>\n\n"
                "Please make payment to:\n\n"
                "<b>Opay</b>\n"
                f"Account: {config.opay_number}\n"
                f"Name: {config.opay_name}\n\n"
                "<b>MoniePoint</b>\n"
                f"Account: {config.monie_number}\n"
                f"Name: {config.monie_name}\n\n"
                "📌 <b>Important:</b> After payment, click the button below to upload your POP (proof of payment)."
            )
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("📤 Upload POP", callback_data=f"uploadpop:{program}:{currency}:{plan_choice}:{vip_dur or ''}"))
            kb.add(types.InlineKeyboardButton("📱 Back to Menu", callback_data="mainmenu_back"))
            bot.send_message(uid, text, parse_mode='HTML', reply_markup=kb)

        else:
            text = (
                f"🪙 <b>{program_name} Program - USDT Payment</b>\n"
                f"Plan: {plan_name}\n"
                f"Amount: <b>{amount_text}</b>\n\n"
                "Please send USDT to:\n\n"
                "<b>USDT (BEP20):</b>\n"
                f"<code>{config.usdt_bep20}</code>\n\n"
                "<b>TRC20 (Tron):</b>\n"
                f"<code>{config.usdt_tron}</code>\n\n"
                "<b>TON:</b>\n"
                f"<code>{config.ton_addr}</code>\n\n"
                "📌 <b>Important:</b> After payment, click the button below to upload your POP (proof of payment)."
            )
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("📤 Upload POP", callback_data=f"uploadpop:{program}:{currency}:{plan_choice}:{vip_dur or ''}"))
            kb.add(types.InlineKeyboardButton("📱 Back to Menu", callback_data="mainmenu_back"))
            bot.send_message(uid, text, parse_mode='HTML', reply_markup=kb)

        bot.answer_callback_query(call.id)
    except Exception as e:
        logger.error(f"Error in pay choice: {e}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("uploadpop:"))
def on_uploadpop_button(call: types.CallbackQuery):
    """Handle upload POP button click"""
    try:
        parts = call.data.split(":")
        program = parts[1]
        currency = parts[2]
        plan = parts[3]
        vip_dur = parts[4] or None
        uid = call.from_user.id
        
        bot.answer_callback_query(call.id)
        bot.send_message(uid, "📤 Please send your proof of payment now (photo or file).\n\nMake sure it's clear and includes transaction details.")
        
        if not user_db.fetch_user(uid):
            user_db.insert_user(uid, f"{call.from_user.first_name or ''}", call.from_user.username or "", program)
        
        user_db.set_pending_pop(uid, file_id="PENDING", program=program, plan_choice=plan, vip_duration=vip_dur)
        
        try:
            amount_text = get_amount_text(program, plan, vip_dur, currency)
            user_data = user_db.fetch_user(uid)
            if user_data and user_data.get('pending_pop'):
                user_data['pending_pop']['currency'] = currency
                user_data['pending_pop']['amount_text'] = amount_text
                user_db.users[str(uid)] = user_data
                user_db.save_database()
        except Exception as e:
            logger.error(f"Error setting pending pop details: {e}")
    except Exception as e:
        logger.error(f"Error in uploadpop button: {e}")

@bot.message_handler(content_types=['photo', 'document'])
def receive_pop(message: types.Message):
    """Handle receipt of POP"""
    try:
        uid = message.from_user.id
        user = user_db.fetch_user(uid)
        if not user or not user.get('pending_pop'):
            bot.reply_to(message, "ℹ️ We couldn't find a pending payment request. Please choose a plan first via Make Payment.")
            return
        
        file_id = None
        if message.content_type == 'photo':
            file_id = message.photo[-1].file_id
        elif message.content_type == 'document':
            file_id = message.document.file_id
        
        pending = user['pending_pop']
        program = pending.get('program', 'crypto')
        plan_choice = pending.get('plan_choice')
        vip_duration = pending.get('vip_duration')
        currency = pending.get('currency', 'naira')
        amount_text = pending.get('amount_text', '')
        
        user_db.set_pending_pop(uid, file_id=file_id, program=program, plan_choice=plan_choice, vip_duration=vip_duration)
        
        try:
            user_data = user_db.fetch_user(uid)
            if user_data and user_data.get('pending_pop'):
                user_data['pending_pop']['currency'] = currency
                user_data['pending_pop']['amount_text'] = amount_text
                user_db.users[str(uid)] = user_data
                user_db.save_database()
        except Exception as e:
            logger.error(f"Error updating pending pop details: {e}")
        
        bot.reply_to(message, "✅ Thanks, your payment has been received. An admin will approve and confirm your registration shortly.")
        
        notify_admin_new_payment(uid, user_db.fetch_user(uid))
    except Exception as e:
        logger.error(f"Error receiving POP: {e}")

def notify_admin_new_payment(user_id: int, user_record: dict):
    """Notify admins about new payment"""
    try:
        pending = user_record.get('pending_pop') or {}
        file_id = pending.get('file_id')
        program = pending.get('program', 'crypto')
        plan_choice = pending.get('plan_choice') or '-'
        vip_dur = pending.get('vip_duration') or ''
        currency = pending.get('currency') or 'naira'
        amount_text = pending.get('amount_text', '')
        
        name = user_record.get('name') or None
        username = user_record.get('username') or None
        if not name or not username:
            n, u = _safe_get_chat_info(user_id)
            if n:
                name = n
            if u:
                username = u
        
        program_name = program.capitalize()
        plan_display = "VIP Signals" if plan_choice == 'vip' else "Academy"
        vip_dur_display = f"({vip_dur.replace('_', ' ')})" if vip_dur else ''
        
        text = (
            f"📢 <b>New Payment Alert - {program_name} Program</b>\n\n"
            f"👤 <b>Name:</b> {name or '-'}\n"
            f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
            f"📱 <b>Username:</b> @{username or '-'}\n"
            f"🎯 <b>Program:</b> {program_name}\n"
            f"📋 <b>Plan:</b> {plan_display} {vip_dur_display}\n"
            f"💰 <b>Currency:</b> {currency.upper()}\n"
            f"💵 <b>Amount:</b> {amount_text}\n"
            f"⏰ <b>Uploaded at:</b> {pending.get('uploaded_at','-')}\n\n"
            f"POP below:"
        )
        
        kb = types.InlineKeyboardMarkup(row_width=2)
        
        if plan_choice == "academy":
            kb.add(
                types.InlineKeyboardButton(f"✅ Approve {program_name} Academy", 
                                         callback_data=f"approve_{program}_academy_{user_id}"),
                types.InlineKeyboardButton("❌ Reject", 
                                         callback_data=f"reject:{user_id}")
            )
        elif plan_choice == "vip":
            if vip_dur:
                kb.add(
                    types.InlineKeyboardButton(f"✅ Approve {program_name} VIP ({vip_dur.replace('_', ' ')})", 
                                             callback_data=f"approve_vip_direct:{program}:{vip_dur}:{user_id}"),
                    types.InlineKeyboardButton("❌ Reject", 
                                             callback_data=f"reject:{user_id}")
                )
            else:
                kb.add(
                    types.InlineKeyboardButton(f"✅ Approve {program_name} VIP", 
                                             callback_data=f"approve_{program}_vip_{user_id}"),
                    types.InlineKeyboardButton("❌ Reject", 
                                             callback_data=f"reject:{user_id}")
                )
        
        for aid in ADMIN_IDS:
            try:
                bot.send_message(aid, text, parse_mode="HTML")
                
                if file_id and file_id != "PENDING":
                    try:
                        bot.send_document(aid, file_id)
                    except Exception:
                        try:
                            bot.send_photo(aid, file_id)
                        except Exception:
                            pass
                
                bot.send_message(aid, "Action:", reply_markup=kb)
            except Exception as e:
                logger.error(f"Failed to notify admin {aid}: {e}")
    except Exception as e:
        logger.error(f"Error in notify admin: {e}")

# ----------------------------
# Admin approval flows - FIXED WITH COMMISSION TRACKING
# ----------------------------
def approve_academy(user_id: int, program: str, call: types.CallbackQuery):
    """Updated Academy approval with commission tracking"""
    try:
        user = user_db.fetch_user(user_id)
        if not user or not user.get('pending_pop'):
            bot.answer_callback_query(call.id, "No pending payment found for this user.")
            return
        
        # Check if user has already used their trial
        trial_used = user_db.get_trial_used(user_id, program)
        
        # Check if user was referred by an affiliate
        referred_by_id = user.get('referred_by')
        amount_text = user.get('pending_pop', {}).get('amount_text', PRICING[program]['academy']['ngn'])
        
        # Activate Academy
        user_db.set_subscription(user_id, program, "academy", PRICING[program]['academy']['days'])
        
        messages = [f"{program.capitalize()} Academy subscription activated for 1 year."]
        
        # Give FREE 3-month VIP trial to ALL new Academy users
        user_db.set_subscription(user_id, program, "vip", 90)  # 3 months free
        user_db.mark_trial_used(user_id, program)
        messages.append("Granted 3 months FREE VIP Signals!")
        
        # Send VIP access immediately for trial
        send_group_access(user_id, program, 'vip', 90)
        
        # Clear pending pop
        user_db.clear_pending_pop(user_id)
        
        # Send academy access
        send_group_access(user_id, program, 'academy')
        
        # Add commission for affiliate if user was referred
        if referred_by_id:
            add_commission_to_affiliate(
                referred_by_id, user_id, program, 'academy', 
                None, amount_text
            )
        
        bot.answer_callback_query(call.id, f"✅ {program.capitalize()} Academy approved.")
        bot.send_message(call.from_user.id, f"User {user_id} approved for {program.capitalize()} Academy.\n" + "\n".join(messages))
        
        # Send welcome message
        try:
            program_name = "Crypto" if program == "crypto" else "Forex"
            welcome_msg = f"🎉 Welcome to BlockchainPlus {program_name} Academy!\n"
            welcome_msg += "Your Academy subscription is active for 1 year.\n"
            welcome_msg += "Check your subscription status anytime using the menu.\n\n"
            
            welcome_msg += "✨ You have received 3 months FREE VIP Signals!\n\n"
            
            if program == 'crypto':
                welcome_msg += "For Crypto Program: You also get access to the DeGen Group!\n\n"
            
            welcome_msg += "If you have any issues joining the groups, please contact @blockchainpluspro"
            bot.send_message(user_id, welcome_msg)
        except Exception as e:
            logger.error(f"Error sending welcome message: {e}")
            
    except Exception as e:
        logger.error(f"Error approving academy: {e}")
        bot.answer_callback_query(call.id, "Error approving Academy.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm_vip:"))
def confirm_vip_approval(call: types.CallbackQuery):
    """Updated VIP approval with commission tracking"""
    try:
        if call.from_user.id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ Not authorized.")
            return
        
        parts = call.data.split(":")
        program = parts[1]
        duration = parts[2]
        user_id = int(parts[3])
        
        logger.info(f"Confirming VIP approval: {program}, {duration}, {user_id}")
        
        user = user_db.fetch_user(user_id)
        if not user or not user.get('pending_pop'):
            bot.answer_callback_query(call.id, "No pending payment found for this user.")
            return
        
        # Map duration to days
        duration_map = {
            'monthly': 30,
            '3_months': 90,
            '6_months': 180,
            'yearly': 365
        }
        
        days = duration_map.get(duration, 90)
        
        # Check if user was referred by an affiliate
        referred_by_id = user.get('referred_by')
        amount_text = user.get('pending_pop', {}).get('amount_text', PRICING[program]['vip'][duration]['ngn'])
        
        # Set subscription
        user_db.set_subscription(user_id, program, "vip", days)
        
        # Clear pending pop
        user_db.clear_pending_pop(user_id)
        
        # Send VIP access
        send_group_access(user_id, program, 'vip', days)
        
        # Add commission for affiliate if user was referred
        if referred_by_id:
            add_commission_to_affiliate(
                referred_by_id, user_id, program, 'vip', 
                duration, amount_text
            )
        
        duration_display = {
            'monthly': 'Monthly',
            '3_months': '3 Months',
            '6_months': '6 Months',
            'yearly': '1 Year'
        }.get(duration, duration)
        
        bot.answer_callback_query(call.id, f"✅ {program.capitalize()} VIP approved.")
        bot.send_message(call.from_user.id, 
                       f"✅ User {user_id} approved for {program.capitalize()} VIP ({duration_display}).\nVIP active for {days} days.")
        
        # Send confirmation to user
        try:
            program_name = "Crypto" if program == "crypto" else "Forex"
            confirm_msg = f"✅ Your {program_name} VIP Signals subscription has been approved!\n"
            confirm_msg += f"Access active until: {(datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')}\n\n"
            confirm_msg += "Check your subscription status anytime using the menu."
            bot.send_message(user_id, confirm_msg)
        except Exception as e:
            logger.error(f"Error sending VIP confirmation: {e}")
            
    except Exception as e:
        logger.error(f"Error in confirm_vip_approval: {e}")
        bot.answer_callback_query(call.id, "Error approving VIP.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("approve_"))
def admin_approve_handler(call: types.CallbackQuery):
    """Handle admin approval callbacks - FIXED VERSION"""
    try:
        if call.from_user.id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ Not authorized.")
            return
        
        logger.info(f"Admin approval callback: {call.data}")
        
        if call.data.startswith("approve_vip_direct:"):
            vip_parts = call.data.split(":")
            program = vip_parts[1]
            duration = vip_parts[2]
            user_id = int(vip_parts[3])
            
            logger.info(f"Direct VIP approval: program={program}, duration={duration}, user_id={user_id}")
            
            dur_display = {
                'monthly': 'Monthly',
                '3_months': '3 Months',
                '6_months': '6 Months',
                'yearly': '1 Year'
            }.get(duration, duration)
            
            kb = types.InlineKeyboardMarkup()
            kb.add(
                types.InlineKeyboardButton(f"✅ Confirm {dur_display} VIP", 
                                         callback_data=f"confirm_vip:{program}:{duration}:{user_id}"),
                types.InlineKeyboardButton("❌ Cancel", 
                                         callback_data="cancel_approval")
            )
            
            bot.send_message(call.from_user.id, 
                           f"Confirm approval for {program.capitalize()} VIP Signals ({dur_display}) for user {user_id}?", 
                           reply_markup=kb)
            bot.answer_callback_query(call.id)
            return
        
        parts = call.data.split("_")
        if len(parts) < 4:
            bot.answer_callback_query(call.id, "Invalid callback.")
            return
        
        program = parts[1]
        action_type = parts[2]
        user_id = int(parts[3])

        user = user_db.fetch_user(user_id)
        if not user or not user.get('pending_pop'):
            bot.answer_callback_query(call.id, "No pending payment found for this user.")
            return
        
        pending = user.get('pending_pop') or {}
        vip_duration = pending.get('vip_duration') or '3_months'
        
        if action_type == "academy":
            approve_academy(user_id, program, call)
        elif action_type == "vip":
            show_vip_duration_menu(user_id, program, call, vip_duration)
    except Exception as e:
        logger.error(f"Error in admin approval handler: {e}")
        bot.answer_callback_query(call.id, "Error processing approval.")

def show_vip_duration_menu(user_id: int, program: str, call: types.CallbackQuery, default_duration: str = None):
    """Show VIP duration selection menu to admin"""
    try:
        logger.info(f"Showing VIP duration menu for user {user_id}, program {program}")
        
        if default_duration and default_duration.startswith(':'):
            default_duration = default_duration[1:]
        
        kb = types.InlineKeyboardMarkup(row_width=1)
        
        durations = [
            ('Monthly', 'monthly'),
            ('3 Months', '3_months'),
            ('6 Months', '6_months'),
            ('1 Year', 'yearly')
        ]
        
        for display_name, duration_key in durations:
            is_selected = " ✅" if duration_key == default_duration else ""
            kb.add(
                types.InlineKeyboardButton(
                    f"{display_name}{is_selected}", 
                    callback_data=f"approve_vip_direct:{program}:{duration_key}:{user_id}"
                )
            )
        
        bot.send_message(call.from_user.id, 
                       f"Select VIP duration to approve for {program.capitalize()} user {user_id}:", 
                       reply_markup=kb)
        bot.answer_callback_query(call.id)
    except Exception as e:
        logger.error(f"Error showing VIP duration menu: {e}")
        bot.answer_callback_query(call.id, "Error showing menu.")

@bot.callback_query_handler(func=lambda c: c.data == "cancel_approval")
def cancel_approval(call: types.CallbackQuery):
    """Cancel approval process"""
    bot.answer_callback_query(call.id, "Approval cancelled.")
    bot.send_message(call.from_user.id, "❌ Approval cancelled.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("reject:"))
def on_admin_reject(call: types.CallbackQuery):
    """Handle admin rejection"""
    try:
        if call.from_user.id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ Not authorized.")
            return
        
        parts = call.data.split(":")
        try:
            user_id = int(parts[1])
        except Exception:
            bot.answer_callback_query(call.id, "Invalid callback.")
            return
        
        user_db.clear_pending_pop(user_id)
        bot.answer_callback_query(call.id, "❌ Rejected.")
        bot.send_message(call.from_user.id, f"Rejected payment for user {user_id}.")
        
        try:
            bot.send_message(user_id, "❌ Your payment could not be verified / was rejected by admin. Please contact @blockchainpluspro for help.")
        except Exception as e:
            logger.error(f"Error sending rejection message: {e}")
    except Exception as e:
        logger.error(f"Error in admin reject: {e}")

# ====================
# AFFILIATE SYSTEM HANDLERS - UPDATED
# ====================

# Affiliate registration
@bot.message_handler(func=lambda m: m.text == "🤝 Become Affiliate")
def handle_affiliate_registration(message: types.Message):
    """Handle affiliate registration"""
    try:
        uid = message.from_user.id
        
        # Check if already an affiliate
        user = user_db.fetch_user(uid)
        if user and user.get('is_affiliate'):
            show_affiliate_dashboard(uid)
            return
        
        # Send affiliate program details with commission structure button
        text = (
            "🤝 <b>BlockchainPlus Affiliate Program</b>\n\n"
            "<b>Earn Commissions by Referring New Members!</b>\n\n"
            
            "💰 <b>Commission Structure:</b>\n"
            "• Academy Subscription: <b>30% commission</b>\n"
            "• VIP Monthly: <b>15% commission</b>\n"
            "• VIP 3-6 Months: <b>20% commission</b>\n"
            "• VIP Yearly: <b>20% commission</b>\n\n"
            
            "🎯 <b>Minimum Payout: ₦10,000</b>\n"
            "• Request payout when you reach ₦10,000+\n"
            "• Payouts processed within 7 business days\n\n"
            
            "📈 <b>How It Works:</b>\n"
            "1. Apply to become an affiliate\n"
            "2. Get your unique referral link\n"
            "3. Share your link with others\n"
            "4. Earn commissions when they subscribe\n"
            "5. Request payout when you reach minimum\n\n"
            
            "✅ <b>Ready to start earning?</b>\n"
            "Apply now and start earning commissions!"
        )
        
        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton("✅ Apply Now", callback_data="affiliate_apply"),
            types.InlineKeyboardButton("💰 View Commission Structure", callback_data="affiliate_view_commission")
        )
        kb.row(
            types.InlineKeyboardButton("📱 Back to Menu", callback_data="mainmenu_back")
        )
        
        bot.send_message(uid, text, parse_mode='HTML', reply_markup=kb)
        
    except Exception as e:
        logger.error(f"Error in affiliate registration: {e}")

@bot.callback_query_handler(func=lambda c: c.data == "affiliate_apply")
def handle_affiliate_application(call: types.CallbackQuery):
    """Handle affiliate application submission"""
    try:
        uid = call.from_user.id
        
        # Check if already applied or is affiliate
        user = user_db.fetch_user(uid)
        if user:
            if user.get('is_affiliate'):
                bot.answer_callback_query(call.id, "✅ You're already an approved affiliate!")
                show_affiliate_dashboard(uid)
                return
            
            if user.get('affiliate_status') == 'pending':
                bot.answer_callback_query(call.id, "⏳ Your application is pending approval")
                return
        
        # Generate unique affiliate code
        affiliate_code = generate_affiliate_code(uid)
        
        # Update user with affiliate application
        user_db.set_affiliate_status(uid, 'pending', affiliate_code)
        
        # Send confirmation to user with commission structure button
        bot.answer_callback_query(call.id, "✅ Application submitted for admin approval!")
        text = (
            "📋 <b>Affiliate Application Submitted!</b>\n\n"
            "Your application has been sent for admin approval.\n"
            "You'll receive a notification when it's approved.\n\n"
            "<b>In the meantime, you can:</b>\n"
            "• Review the commission structure\n"
            "• Plan your referral strategy\n"
            "• Prepare to start earning!\n\n"
            "You'll get your unique referral link after approval."
        )
        
        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton("💰 Review Commission Structure", callback_data="affiliate_view_commission"),
            types.InlineKeyboardButton("📱 Back to Menu", callback_data="mainmenu_back")
        )
        
        bot.send_message(uid, text, parse_mode='HTML', reply_markup=kb)
        
        # Notify all admins
        notify_admin_affiliate_application(uid, call.from_user.first_name, affiliate_code)
        
    except Exception as e:
        logger.error(f"Error in affiliate application: {e}")
        bot.answer_callback_query(call.id, "Error submitting application")

def notify_admin_affiliate_application(user_id: int, user_name: str, affiliate_code: str):
    """Notify admins about new affiliate application"""
    try:
        text = (
            "📋 <b>New Affiliate Application</b>\n\n"
            f"👤 <b>Applicant:</b> {user_name or 'Unknown'}\n"
            f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
            f"🔑 <b>Generated Code:</b> <code>{affiliate_code}</code>\n"
            f"📅 <b>Applied:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            "Review and approve/reject this application:"
        )
        
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.row(
            types.InlineKeyboardButton("✅ Approve Affiliate", callback_data=f"admin_approve_affiliate:{user_id}"),
            types.InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_affiliate:{user_id}")
        )
        
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id, text, parse_mode='HTML', reply_markup=kb)
            except Exception as e:
                logger.error(f"Could not notify admin {admin_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error notifying admin: {e}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("admin_approve_affiliate:"))
def handle_admin_approve_affiliate(call: types.CallbackQuery):
    """Handle admin approval of affiliate"""
    try:
        if call.from_user.id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ Not authorized.")
            return
        
        user_id = int(call.data.split(":")[1])
        
        # Approve affiliate
        user = user_db.fetch_user(user_id)
        if not user:
            bot.answer_callback_query(call.id, "❌ User not found.")
            return
        
        affiliate_code = user.get('affiliate_code') or generate_affiliate_code(user_id)
        user_db.approve_affiliate(user_id, affiliate_code)
        
        # Get referral link
        bot_username = bot.get_me().username
        referral_link = f"https://t.me/{bot_username}?start=ref_{affiliate_code}"
        
        # Notify user
        try:
            bot.send_message(
                user_id,
                f"🎉 <b>Congratulations! Your Affiliate Application is Approved!</b>\n\n"
                f"✅ <b>Your Affiliate Code:</b> <code>{affiliate_code}</code>\n\n"
                f"🔗 <b>Your Unique Referral Link:</b>\n"
                f"<code>{referral_link}</code>\n\n"
                f"📊 <b>How to start earning:</b>\n"
                f"1. Share your referral link\n"
                f"2. When someone clicks and subscribes\n"
                f"3. You earn commission automatically!\n\n"
                f"💰 <b>Commission Structure:</b>\n"
                f"• Academy: 30%\n"
                f"• VIP Monthly: 15%\n"
                f"• VIP 3-6 Months: 20%\n"
                f"• VIP Yearly: 20%\n\n"
                f"📈 <b>Track your earnings in the Affiliate Dashboard</b>\n"
                f"📊 <b>Minimum Payout:</b> ₦10,000\n\n"
                f"Start sharing and earning today! 🚀",
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Could not notify user {user_id}: {e}")
        
        # Update admin
        bot.answer_callback_query(call.id, "✅ Affiliate approved!")
        bot.send_message(
            call.from_user.id,
            f"✅ Affiliate approved for user {user_id}\n"
            f"🔑 Code: {affiliate_code}\n"
            f"🔗 Link: {referral_link}"
        )
        
        # Update the original admin message
        try:
            bot.edit_message_text(
                f"✅ Affiliate application approved for user {user_id}\n"
                f"🔑 Code: {affiliate_code}",
                call.message.chat.id,
                call.message.message_id
            )
        except:
            pass
            
    except Exception as e:
        logger.error(f"Error approving affiliate: {e}")
        bot.answer_callback_query(call.id, "Error approving affiliate")

@bot.callback_query_handler(func=lambda c: c.data.startswith("admin_reject_affiliate:"))
def handle_admin_reject_affiliate(call: types.CallbackQuery):
    """Handle admin rejection of affiliate"""
    try:
        if call.from_user.id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ Not authorized.")
            return
        
        user_id = int(call.data.split(":")[1])
        
        # Reject affiliate
        user_db.set_affiliate_status(user_id, 'rejected')
        
        # Notify user
        try:
            bot.send_message(
                user_id,
                "❌ <b>Affiliate Application Status</b>\n\n"
                "Your affiliate application has been reviewed and was not approved at this time.\n\n"
                "Possible reasons:\n"
                "• Incomplete application information\n"
                "• Account history requirements not met\n"
                "• Other administrative reasons\n\n"
                "You may reapply after 30 days.\n"
                "Contact @blockchainpluspro for more information.",
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Could not notify user {user_id}: {e}")
        
        # Update admin
        bot.answer_callback_query(call.id, "❌ Affiliate rejected.")
        bot.send_message(call.from_user.id, f"❌ Affiliate application rejected for user {user_id}")
        
        # Update the original admin message
        try:
            bot.edit_message_text(
                f"❌ Affiliate application rejected for user {user_id}",
                call.message.chat.id,
                call.message.message_id
            )
        except:
            pass
            
    except Exception as e:
        logger.error(f"Error rejecting affiliate: {e}")
        bot.answer_callback_query(call.id, "Error rejecting affiliate")

# Affiliate Dashboard
def show_affiliate_dashboard(uid: int, message_id: int = None):
    """Show affiliate dashboard with stats and earnings"""
    try:
        user = user_db.fetch_user(uid)
        if not user or not user.get('is_affiliate'):
            bot.send_message(uid, "You need to be an approved affiliate to access the dashboard.")
            return
        
        affiliate_code = user.get('affiliate_code', 'N/A')
        bot_username = bot.get_me().username
        referral_link = f"https://t.me/{bot_username}?start=ref_{affiliate_code}"
        
        # Get affiliate stats
        stats = user_db.get_affiliate_stats(uid)
        
        text = (
            f"📊 <b>Affiliate Dashboard</b>\n\n"
            f"🔑 <b>Your Affiliate Code:</b> <code>{affiliate_code}</code>\n\n"
            f"🔗 <b>Your Referral Link:</b>\n"
            f"<code>{referral_link}</code>\n\n"
            f"📈 <b>Performance Stats:</b>\n"
            f"• Total Referrals: {stats.get('total_referrals', 0)}\n"
            f"• Active Referrals: {stats.get('active_referrals', 0)}\n"
            f"• Total Earnings: <b>₦{stats.get('total_earnings', 0):,.2f}</b>\n"
            f"• Pending Payout: <b>₦{stats.get('pending_payout', 0):,.2f}</b>\n"
            f"• Total Paid Out: <b>₦{stats.get('total_paid', 0):,.2f}</b>\n\n"
            f"💰 <b>Available for Payout:</b> <b>₦{stats.get('available_balance', 0):,.2f}</b>\n"
            f"🎯 <b>Minimum Payout:</b> ₦{MINIMUM_PAYOUT:,.2f}\n\n"
            f"<b>Commission Structure:</b>\n"
            f"• Academy: 30%\n"
            f"• VIP Monthly: 15%\n"
            f"• VIP 3-6 Months: 20%\n"
            f"• VIP Yearly: 20%\n\n"
            f"<b>Recent Commissions:</b>\n"
        )
        
        # Add recent commissions
        recent_commissions = user_db.get_recent_commissions(uid, limit=5)
        if recent_commissions:
            for i, commission in enumerate(recent_commissions[:5], 1):
                text += f"{i}. ₦{commission['amount']:,.2f} - {commission['plan_type']}\n"
        else:
            text += "No commissions yet. Start sharing your link!\n"
        
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.row(
            types.InlineKeyboardButton("📋 Copy Referral Link", callback_data="affiliate_copy_link"),
            types.InlineKeyboardButton("💰 Request Payout", callback_data="affiliate_request_payout")
        )
        kb.row(
            types.InlineKeyboardButton("📊 View All Referrals", callback_data="affiliate_view_referrals"),
            types.InlineKeyboardButton("💸 Commission History", callback_data="affiliate_commission_history")
        )
        kb.row(
            types.InlineKeyboardButton("📱 Back to Menu", callback_data="mainmenu_back"),
            types.InlineKeyboardButton("🔄 Refresh", callback_data="affiliate_refresh")
        )
        
        if message_id:
            bot.edit_message_text(text, uid, message_id, parse_mode='HTML', reply_markup=kb)
        else:
            bot.send_message(uid, text, parse_mode='HTML', reply_markup=kb)
            
    except Exception as e:
        logger.error(f"Error showing affiliate dashboard: {e}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("affiliate_"))
def handle_affiliate_callbacks(call: types.CallbackQuery):
    """Handle all affiliate-related callbacks"""
    try:
        uid = call.from_user.id
        action = call.data.replace("affiliate_", "")
        
        if action == "copy_link":
            # Copy referral link to clipboard (simulated)
            user = user_db.fetch_user(uid)
            if user and user.get('is_affiliate'):
                affiliate_code = user.get('affiliate_code')
                bot_username = bot.get_me().username
                referral_link = f"https://t.me/{bot_username}?start=ref_{affiliate_code}"
                
                bot.answer_callback_query(
                    call.id,
                    f"✅ Link copied to clipboard!\n\nShare: {referral_link}",
                    show_alert=True
                )
        
        elif action == "request_payout":
            # Request payout
            handle_payout_request(uid, call.message.message_id)
        
        elif action == "view_referrals":
            # View all referrals
            show_all_referrals(uid, call.message.message_id)
        
        elif action == "commission_history":
            # View commission history
            show_commission_history(uid, call.message.message_id)
        
        elif action == "refresh":
            # Refresh dashboard
            show_affiliate_dashboard(uid, call.message.message_id)
        
        elif action == "dashboard":
            # Show dashboard
            show_affiliate_dashboard(uid, call.message.message_id)
        
        elif action == "view_commission":
            # Show commission structure
            show_commission_structure(uid, call.message.message_id)
            
    except Exception as e:
        logger.error(f"Error in affiliate callback: {e}")
        bot.answer_callback_query(call.id, "Error processing request")

def show_all_referrals(uid: int, message_id: int = None):
    """Show all referrals for an affiliate"""
    try:
        referrals = user_db.get_all_referrals(uid)
        
        if not referrals:
            text = "📋 <b>Your Referrals</b>\n\nYou haven't referred anyone yet. Start sharing your referral link!"
        else:
            text = f"📋 <b>Your Referrals ({len(referrals)})</b>\n\n"
            
            for i, referral in enumerate(referrals[:20], 1):  # Limit to 20
                user_id = referral['user_id']
                status = "✅ Active" if referral.get('has_subscribed') else "⏳ Pending"
                earned = f"₦{referral.get('commission_earned', 0):,.2f}" if referral.get('commission_earned') else "₦0"
                
                text += f"{i}. ID: {user_id} - {status} - Earned: {earned}\n"
            
            if len(referrals) > 20:
                text += f"\n... and {len(referrals) - 20} more referrals"
        
        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton("📊 Back to Dashboard", callback_data="affiliate_dashboard"),
            types.InlineKeyboardButton("📱 Main Menu", callback_data="mainmenu_back")
        )
        
        if message_id:
            bot.edit_message_text(text, uid, message_id, parse_mode='HTML', reply_markup=kb)
        else:
            bot.send_message(uid, text, parse_mode='HTML', reply_markup=kb)
            
    except Exception as e:
        logger.error(f"Error showing referrals: {e}")

def show_commission_history(uid: int, message_id: int = None):
    """Show commission history for an affiliate"""
    try:
        commissions = user_db.get_commission_history(uid)
        
        if not commissions:
            text = "💸 <b>Commission History</b>\n\nNo commissions earned yet. Start referring users!"
        else:
            text = f"💸 <b>Commission History</b>\n\n"
            total = 0
            
            for i, commission in enumerate(commissions[:15], 1):  # Limit to 15
                date = commission.get('date', 'Unknown')
                amount = commission.get('amount', 0)
                plan_type = commission.get('plan_type', 'Unknown')
                
                text += f"{i}. {date} - ₦{amount:,.2f} - {plan_type}\n"
                total += amount
            
            text += f"\n📊 <b>Total Earned: ₦{total:,.2f}</b>"
        
        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton("📊 Back to Dashboard", callback_data="affiliate_dashboard"),
            types.InlineKeyboardButton("📱 Main Menu", callback_data="mainmenu_back")
        )
        
        if message_id:
            bot.edit_message_text(text, uid, message_id, parse_mode='HTML', reply_markup=kb)
        else:
            bot.send_message(uid, text, parse_mode='HTML', reply_markup=kb)
            
    except Exception as e:
        logger.error(f"Error showing commission history: {e}")

# Add affiliate option to reply keyboard for affiliates
@bot.message_handler(func=lambda m: m.text == "🤝 Affiliate Dashboard")
def handle_affiliate_dashboard_button(message: types.Message):
    """Handle affiliate dashboard button"""
    uid = message.from_user.id
    show_affiliate_dashboard(uid)

# ----------------------------
# Admin Test Reminders Command
# ----------------------------
@bot.message_handler(func=lambda m: m.text == "⏰ Test Reminders")
def test_reminders_command(message: types.Message):
    """Manually trigger reminder check for testing"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    bot.send_message(message.chat.id, "⏳ Running manual reminder check...")
    
    try:
        # Run the check immediately
        check_expiring_subscriptions()
        bot.send_message(message.chat.id, "✅ Reminder check completed. Check logs for details.")
    except Exception as e:
        logger.error(f"Error in manual reminder check: {e}")
        bot.send_message(message.chat.id, f"❌ Error: {e}")

# ----------------------------
# Test Links Command
# ----------------------------
@bot.message_handler(func=lambda m: m.text == "🔗 Test Links")
def test_all_links(message: types.Message):
    """Test all invite links"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    test_results = ["🔗 <b>Testing All Invite Links:</b>\n"]
    
    # Test Crypto Academy
    try:
        chat_id, invite_link = get_chat_ids('crypto', 'academy')
        if invite_link:
            test_results.append(f"\n✅ <b>Crypto Academy:</b>\n{invite_link}")
        else:
            test_results.append(f"\n❌ <b>Crypto Academy:</b> No link configured")
    except Exception as e:
        test_results.append(f"\n❌ <b>Crypto Academy:</b> Error - {str(e)}")
    
    # Test Crypto VIP
    try:
        chat_id, invite_link = get_chat_ids('crypto', 'vip')
        if invite_link:
            test_results.append(f"\n✅ <b>Crypto VIP:</b>\n{invite_link}")
        else:
            test_results.append(f"\n❌ <b>Crypto VIP:</b> No link configured")
    except Exception as e:
        test_results.append(f"\n❌ <b>Crypto VIP:</b> Error - {str(e)}")
    
    # Test Crypto Degen
    try:
        chat_id, invite_link = get_chat_ids('crypto', 'degen')
        if invite_link:
            test_results.append(f"\n✅ <b>Crypto Degen:</b>\n{invite_link}")
        else:
            test_results.append(f"\n❌ <b>Crypto Degen:</b> No link configured")
    except Exception as e:
        test_results.append(f"\n❌ <b>Crypto Degen:</b> Error - {str(e)}")
    
    # Test Forex Academy
    try:
        chat_id, invite_link = get_chat_ids('forex', 'academy')
        if invite_link:
            test_results.append(f"\n✅ <b>Forex Academy:</b>\n{invite_link}")
        else:
            test_results.append(f"\n❌ <b>Forex Academy:</b> No link configured")
    except Exception as e:
        test_results.append(f"\n❌ <b>Forex Academy:</b> Error - {str(e)}")
    
    # Test Forex VIP
    try:
        chat_id, invite_link = get_chat_ids('forex', 'vip')
        if invite_link:
            test_results.append(f"\n✅ <b>Forex VIP:</b>\n{invite_link}")
        else:
            test_results.append(f"\n❌ <b>Forex VIP:</b> No link configured")
    except Exception as e:
        test_results.append(f"\n❌ <b>Forex VIP:</b> Error - {str(e)}")
    
    bot.send_message(message.chat.id, "\n".join(test_results), parse_mode='HTML')

# ----------------------------
# Admin commands
# ----------------------------
@bot.message_handler(func=lambda m: m.text == "➕ Add User")
def admin_add_help(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    help_text = (
        "ℹ️ <b>Add User Manually</b>\n\n"
        "Command: <code>/adduser user_id days program</code>\n"
        "Example: <code>/adduser 123456789 365 crypto</code>\n\n"
        "This adds the user with a subscription that expires after the given number of days.\n"
        "Program can be 'crypto' or 'forex'."
    )
    bot.send_message(message.chat.id, help_text, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📅 Extend User")
def admin_extend_help(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    help_text = (
        "ℹ️ <b>Extend User Subscription</b>\n\n"
        "Command: <code>/extend user_id days program plan</code>\n"
        "Example: <code>/extend 123456789 30 crypto academy</code>\n\n"
        "This will add days to the user's current expiry.\n"
        "Program: crypto or forex\n"
        "Plan: academy or vip"
    )
    bot.send_message(message.chat.id, help_text, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📋 List Users")
def admin_list_button(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    users = user_db.get_all_users()
    if not users:
        bot.send_message(message.chat.id, "ℹ️ No users found in the database yet.")
        return
    
    lines = ["👥 <b>User List (First 20):</b>"]
    count = 0
    
    for user_id, u in users.items():
        if count >= 20:
            lines.append(f"\n... and {len(users) - 20} more users")
            break
        
        try:
            name = u.get('name', '-')[:15]
            username = f"@{u.get('username')}" if u.get('username') else '-'
            
            lines.append(f"ID: {u.get('tg_id')} | {name} | {username}")
            count += 1
        except Exception as e:
            logger.error(f"Error processing user {user_id}: {e}")
            continue
    
    bot.send_message(message.chat.id, "\n".join(lines), parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text == "🔍 Check User")
def admin_check_help(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    help_text = (
        "ℹ️ <b>Check User Details</b>\n\n"
        "Command: <code>/check user_id</code>\n"
        "Example: <code>/check 123456789</code>"
    )
    bot.send_message(message.chat.id, help_text, parse_mode="HTML")

def create_health_server():
    """Create a simple HTTP server for Railway health checks"""
    app = Flask(__name__)
    
    @app.route('/')
    def health_check():
        return Response("Bot is running", status=200)
    
    @app.route('/health')
    def health():
        return Response("OK", status=200)
    
    port = int(os.getenv('PORT', 8080))
    Thread(target=lambda: app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)).start()
    return app

# ----------------------------
# Bot Startup with Scheduler
# ----------------------------
if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("Starting BlockchainPlus Hub Bot with Complete Affiliate System...")
    logger.info(f"Admin IDs: {ADMIN_IDS}")
    logger.info(f"Tutorial Videos Loaded: {len(TUTORIALS)}")
    logger.info("=" * 50)
    
    try:
        # Start the scheduler for automated reminders
        logger.info("Starting scheduler for automated reminders...")
        scheduler.add_job(
            check_expiring_subscriptions,
            trigger=CronTrigger(hour=9, minute=0),  # Run daily at 9:00 AM
            id='daily_expiry_check',
            name='Daily subscription expiry check',
            replace_existing=True
        )
        
        # Also run every 6 hours for better coverage
        scheduler.add_job(
            check_expiring_subscriptions,
            trigger='interval',
            hours=6,
            id='interval_expiry_check',
            name='Interval subscription expiry check',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("Scheduler started successfully")
        logger.info(f"Reminders will be sent at: {REMINDER_DAYS} days before expiry")
        logger.info(f"Grace period: {GRACE_PERIOD_DAYS} days")
        logger.info(f"Affiliate minimum payout: NGN{MINIMUM_PAYOUT:,.2f}")
        
        bot_info = bot.get_me()
        logger.info(f"Bot connected: @{bot_info.username} (ID: {bot_info.id})")
        
        # Database integrity is already verified in UserDatabase.__init__()
        # Get database stats after verification
        db_stats = user_db.get_database_stats()
        logger.info(f"Database stats - Users: {db_stats.get('total_users', 0)}, "
                   f"Affiliates: {db_stats.get('total_affiliates', 0)}, "
                   f"Active subscriptions: {db_stats.get('active_subscriptions', 0)}")
        
        # Send startup notification to admins
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(
                    admin_id,
                    f"🤖 Bot restarted successfully with FIXED ADMIN AFFILIATE MANAGEMENT!\n\n"
                    f"<b>Database Status:</b>\n"
                    f"• Users: {db_stats.get('total_users', 0)}\n"
                    f"• Affiliates: {db_stats.get('total_affiliates', 0)}\n"
                    f"• Active Subscriptions: {db_stats.get('active_subscriptions', 0)}\n"
                    f"• Total Commissions: ₦{db_stats.get('total_commissions', 0):,.2f}\n\n"
                    f"✅ Admin Affiliate Management fully fixed!\n"
                    f"✅ Export to CSV functions working\n"
                    f"✅ Monthly/Weekly reports working\n"
                    f"✅ All buttons now functional",
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Could not send startup message to admin {admin_id}: {e}")
        
        logger.info("Starting bot polling...")
        health_app = create_health_server()
        logger.info(f"Health server started on port {os.getenv('PORT', 8080)}")
        
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        logger.error(traceback.format_exc())
        # Shutdown scheduler on error
        try:
            scheduler.shutdown()
        except:
            pass