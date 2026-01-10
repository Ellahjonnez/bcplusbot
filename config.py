# config.py - Updated for Railway Deployment with Environment Variables
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot Token (MUST be set as environment variable in production)
bot_token = os.getenv('BOT_TOKEN')
if not bot_token:
    raise ValueError("BOT_TOKEN environment variable is required")

# Admins (can be comma-separated list in environment)
admin_id_raw = os.getenv('ADMIN_IDS')
if not admin_id_raw:
    raise ValueError("ADMIN_IDS environment variable is required")
admin_ids = [int(id.strip()) for id in admin_id_raw.split(',') if id.strip()]
if not admin_ids:
    raise ValueError("ADMIN_IDS must contain at least one valid Telegram ID")
admin_id = admin_ids[0]

# Crypto Program Chat IDs (these are safe to keep in code)
crypto_academy_chat_id = -1002445603763   # Blockchainplus Crypto Academy
crypto_vip_chat_id = -1002498229211       # Blockchainplus Crypto VIP Signals
crypto_degen_chat_id = -1002410348779     # Blockchainplus DeGen

crypto_academy_invite = "https://t.me/+vSBSZ4MUbNhkNmNk"
crypto_vip_invite = "https://t.me/+RfokZW7mMHEzN2Nk"
crypto_degen_invite = "https://t.me/+78yKMh5YDl84NWRk"

# Forex Program Chat IDs
forex_academy_chat_id = -1003693059930    # BlockChainPlus FX Academy
forex_vip_chat_id = -1001576547165        # BlockChainPlus FX Signals

forex_academy_invite = "https://t.me/+1CjWA6W2z5M1YTI0"
forex_vip_invite = "https://t.me/+vagjgvcQFaRlMDc0"

# Payment details (Sensitive - MUST use environment variables)
opay_number = os.getenv('OPAY_NUMBER')
if not opay_number:
    raise ValueError("OPAY_NUMBER environment variable is required")

opay_name = os.getenv('OPAY_NAME')
if not opay_name:
    raise ValueError("OPAY_NAME environment variable is required")

monie_number = os.getenv('MONIE_NUMBER')
if not monie_number:
    raise ValueError("MONIE_NUMBER environment variable is required")

monie_name = os.getenv('MONIE_NAME')
if not monie_name:
    raise ValueError("MONIE_NAME environment variable is required")

usdt_bep20 = os.getenv('USDT_BEP20')
if not usdt_bep20:
    raise ValueError("USDT_BEP20 environment variable is required")

usdt_tron = os.getenv('USDT_TRON')
if not usdt_tron:
    raise ValueError("USDT_TRON environment variable is required")

ton_addr = os.getenv('TON_ADDR')
if not ton_addr:
    raise ValueError("TON_ADDR environment variable is required")

# Database configuration
DB_FILE = os.getenv('DB_FILE', 'users.json')

# Optional: Add logging configuration
import logging
def setup_logging():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )