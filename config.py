from aiogram import Bot, Dispatcher
from os import getenv
from dotenv import load_dotenv
load_dotenv()
TOKEN = getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()
