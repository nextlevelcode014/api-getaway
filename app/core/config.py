import os
from dotenv import load_dotenv
from decimal import Decimal
from jinja2 import Environment, FileSystemLoader

load_dotenv()

env = Environment(loader=FileSystemLoader("app/services/mail/templates"))

SECRET_KEY = os.getenv("SECRET_KEY")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")

GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT")
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_ADDRESS = os.getenv("SMTP_FROM_ADDRESS")


DATABASE_PATH = "database"
VALUE_PER_REQUEST = Decimal(0.000005)
PRICE_PER_1K_TOKENS = 0.02
PRICE_PER_1M_TOKENS = 0.35
MAX_USER_CHARS = 500

CHAVE_PIX = os.getenv("CHAVE_PIX")
CIDADE_PIX = os.getenv("CIDADE_PIX")

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")

BASE_URL = "https://seuservidor.com"


RECEIPTS_DIR = "./receipts"
COMPANY_NAME = "API Getaway"
