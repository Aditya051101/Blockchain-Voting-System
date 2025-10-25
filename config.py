# MySQL database configuration
MYSQL_HOST = "127.0.0.1"
MYSQL_PORT = "3306"
MYSQL_USER = "root"
MYSQL_PASSWORD = "root"   # ← change this
MYSQL_DB = "voting_db"
SECRET_KEY = "5654247ef698ef8df050e6dbb84acdfb185fcbef59a3a77809ce1c689090ce767"
# use for create secret key
# python -c "import secrets; print(secrets.token_hex(32))"
# config.py
BLOCKCHAIN_FILE = "blockchain_data/chain.json"
POW_DIFFICULTY = 3  # number of leading zeros required (tune for demo)