🤖 Telegram Affiliate & Subscription Bot
A comprehensive Telegram bot for managing subscriptions, affiliate programs, and payments with support for multiple trading programs (Crypto & Forex).

✨ Features
🎯 Core Functionality
Dual Program Support: Crypto & Forex trading programs

Subscription Management: Academy and VIP tiers with expiry tracking

Trial System: Free trials for new users

Payment Processing: Multiple payment methods with proof of payment verification

💼 Affiliate System
Referral Program: Users can become affiliates and share referral links

Commission Tracking: Automated commission calculation for referrals

Payout Management: Request and process affiliate earnings

Performance Analytics: Detailed stats for affiliates and admins

👑 Admin Features
Dashboard: Comprehensive admin panel with statistics

User Management: View and manage all users

Affiliate Approval: Review and approve affiliate applications

Payout Processing: Handle affiliate payout requests

Commission Reports: Detailed revenue and performance reports

🚀 Quick Deployment
Deploy on Railway (Recommended)
https://railway.app/button.svg

Click the "Deploy on Railway" button above

Add Environment Variables:

BOT_TOKEN: Your Telegram bot token from @BotFather

ADMIN_IDS: Your Telegram user ID (comma-separated for multiple)

Add a Volume for persistent storage (mount path: /data)

Your bot will be live in 2 minutes!

🔧 Local Development
Prerequisites
Python 3.10+

Telegram Bot Token from @BotFather

Git

Installation
Clone the repository

bash
git clone https://github.com/Ellahjonnez/telegram-bot.git
cd telegram-bot
Create virtual environment

bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
Install dependencies

bash
pip install -r requirements.txt
Configure environment

bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
# Use any text editor to fill in your bot token and admin ID
Run the bot

bash
python main.py
⚙️ Configuration
Environment Variables
Create a .env file in the root directory:

env
# Required
BOT_TOKEN=your_bot_token_here

# Admin Configuration (comma-separated for multiple admins)
ADMIN_IDS=5403215154,123456789

# Database Configuration
DB_FILE=users.json

# Payment Details (optional - will use defaults if not set)
OPAY_NUMBER=8064369220
OPAY_NAME="Your Name"
MONIE_NUMBER=8064369220
MONIE_NAME="Your Name"
USDT_BEP20=0x...
USDT_TRON=TP...
TON_ADDR=UQ...

# Commission Rates (optional)
COMMISSION_ACADEMY=0.2
COMMISSION_VIP_3MONTH=0.3
COMMISSION_VIP_1YEAR=0.5
MIN_PAYOUT_AMOUNT=50
Chat Configuration (in config.py)
Update config.py with your actual Telegram chat IDs and invite links:

python
# Crypto Program
crypto_academy_chat_id = -1002445603763
crypto_vip_chat_id = -1002498229211
crypto_degen_chat_id = -1002410348779

# Forex Program
forex_academy_chat_id = -1003693059930
forex_vip_chat_id = -1001576547165
📁 Project Structure
text
telegram-bot/
├── main.py              # Main bot application
├── database.py          # Database management with JSON storage
├── config.py            # Configuration settings
├── handlers/            # Bot command handlers
│   ├── __init__.py
│   ├── user_handlers.py
│   ├── admin_handlers.py
│   └── affiliate_handlers.py
├── requirements.txt     # Python dependencies
├── Procfile            # Railway process definition
├── .env.example        # Example environment variables
├── .gitignore          # Git ignore rules
├── README.md           # This file
└── users.json          # Database file (created automatically)
🔒 Database
The bot uses a JSON-based database (users.json) with the following structure:

json
{
  "users": {},
  "payouts": {},
  "commissions": {},
  "referrals": {},
  "metadata": {
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00",
    "total_users": 0,
    "total_affiliates": 0,
    "total_commissions": 0,
    "total_payouts": 0
  }
}
Auto-save feature: Database automatically saves every 5 changes or 30 seconds.

💰 Payment Integration
Supported Payment Methods
OPay: Nigerian mobile money

MoniePoint: Nigerian mobile money

USDT: BEP20 and TRON networks

TON: The Open Network

Commission Structure
Academy Subscription: 20% commission

3-month VIP: 30% commission

1-year VIP: 50% commission

📊 Admin Commands
Basic Admin
/stats - View bot statistics

/users - List all users

/affiliates - List all affiliates

/payouts - View payout requests

Affiliate Management
/approve_affiliate [user_id] [code] - Approve affiliate application

/reject_affiliate [user_id] - Reject affiliate application

/affiliate_stats [user_id] - View affiliate statistics

Payout Management
/process_payout [payout_id] [proof_file_id] - Mark payout as paid

/reject_payout [payout_id] - Reject payout request

👥 User Commands
General
/start - Start the bot

/help - Show help message

/program - Select program (Crypto/Forex)

Subscriptions
/subscribe - View subscription options

/mytrial - Get free trial

/myplan - Check current subscription

/payment - Make payment

Affiliate System
/affiliate - Become an affiliate

/myref - Get referral link

/mystats - View affiliate statistics

/withdraw - Request payout

🚢 Deployment
Railway.app Deployment
Prepare your repository

bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/yourusername/telegram-bot.git
git push -u origin main
Deploy on Railway

Go to Railway.app

Click "New Project" → "Deploy from GitHub repo"

Select your repository

Add environment variables

Add volume for persistent storage (/data)

Configure Persistent Storage

Create volume named bot-data

Mount path: /data

Update DB_FILE variable to /data/users.json

Environment Variables for Railway
Variable	Required	Default	Description
BOT_TOKEN	✅	-	Telegram bot token from @BotFather
ADMIN_IDS	✅	-	Admin user IDs (comma-separated)
DB_FILE	❌	users.json	Database file path
OPAY_NUMBER	❌	8064369220	OPay phone number
OPAY_NAME	❌	Ellah Innocent A	OPay account name
...	...	...	...
🔍 Monitoring & Maintenance
View Logs
Railway Dashboard: Go to project → Deployments → Click deployment → View logs

CLI: railway logs (if using Railway CLI)

Database Backups
The bot automatically creates backups:

Auto-backup before each save

Manual backup: Use /backup command (admin only)

Corrupted file backup with timestamp

Cleanup
Expired subscriptions are automatically cleaned after 30 days

Pending POPs older than 7 days are cleared

🛠️ Troubleshooting
Common Issues
Bot doesn't start

Check if BOT_TOKEN is set correctly

Verify environment variables in Railway dashboard

Check logs for errors

Database resets on restart

Ensure volume is mounted at /data

Verify DB_FILE is set to /data/users.json

Commands not working

Check if user is in admin list

Verify bot has necessary permissions

Check logs for command errors

Payment verification fails

Ensure POP image is clear and readable

Check if admin has processed the payment

Logs Location
Railway: Dashboard → Deployments → Logs

Local: Console output

📈 Statistics & Reports
Admin Reports
/report - Generate commission report

/performance - View affiliate performance stats

/summary - Database summary

Metrics Tracked
Total users and active subscriptions

Affiliate conversion rates

Commission earnings by plan type

Payout requests and status

Referral performance

🤝 Contributing
Fork the repository

Create a feature branch

Make your changes

Test thoroughly

Submit a pull request

📄 License
This project is proprietary and confidential. All rights reserved.

🆘 Support
For support:

Check the Troubleshooting section

Review the logs in Railway dashboard

Contact the development team

Built with ❤️ for the trading community