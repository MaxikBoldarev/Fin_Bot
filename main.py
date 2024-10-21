from aiogram import Bot, Dispatcher, types, executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import sqlite3
import requests
from stock import StockInfo
from bs4 import BeautifulSoup
import reticker
import yfinance as yf
import mplfinance as mpf
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

api_token = os.getenv('API_TOKEN')

bot = Bot(token=api_token)

storage = MemoryStorage()

dp = Dispatcher(bot, storage=storage)


with open('./help.txt', 'r', encoding='utf-8') as file:
    help = file.read()


class CheckStockStates(StatesGroup):
    StockID = State()

class CheckTickerStates(StatesGroup):
    ticker = State()


class User:

    def __init__(self, telegram_id) -> None:
        self.telegram_id = telegram_id

    def checkUserRecord(self):
        conn = sqlite3.connect('./app_data/database.db')
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (telegram_id INTEGER PRIMARY KEY)''')
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (self.telegram_id,))
        db_data = cursor.fetchone()
        if db_data is None:
            result = None
            conn.close()
        else:
            result = db_data[0]
            conn.close()    
        return result
    
    def createUserRecord(self):
        insterted_id = None
        conn = sqlite3.connect('./app_data/database.db')
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (telegram_id INTEGER PRIMARY KEY)''')
        cursor.execute('INSERT INTO users (telegram_id) VALUES (?)', (self.telegram_id,))
        conn.commit()
        insterted_id = cursor.lastrowid
        conn.close()
        return insterted_id 
    
class CurrencyInfo:
    moex_dict = {"USD": 'USD000UTSTOM', #Американский доллар
                 "EUR": 'EUR_RUB__TOM', #Евро
                 "CNY": 'CNYRUB_TOM', #Китайский юань
                 "HKD": 'HKDRUB_TOM', #Гонконгский доллар
                 "TRY": 'TRYRUB_TOM', #Турецкая лира
                 "BYN": 'BYNRUB_TOM', #Белорусский рубль
                 "KZT": 'KZTRUB_TOM', #Казахстанский тенге
                 "AMD": 'AMDRUB_TOM'} #Армянский драм


    def __init__(self, message):
        self.message = message
        self.headers = {"User-Agent": "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6.1 Safari/605.1.15"}
        self.currency = None
        self.tickerlink = None
        self.price = None
        self.change = None

    def info_moex(self):
        url = f'https://iss.moex.com/iss/engines/currency/markets/selt/securities/' \
                  f'{self.moex_dict.get(self.message)}.xml'
        pages = requests.get(url, timeout=10, headers=self.headers)
        soup = BeautifulSoup(pages.text, 'xml')
        if self.moex_dict.get(self.message):
            info = (soup.find(id="marketdata").find_all('row'))
            lasts = [i.get('LAST') for i in info if len(i.get('LAST')) != 0]
            opens = [i.get('OPEN') for i in info if len(i.get('OPEN')) != 0]
            try:
                currency = self.message
                tickerlink = f'https://www.moex.com/en/issue/{self.moex_dict.get(self.message)}/CETS'
                price = float(lasts[0])
                change = round(price * 100 / (float(opens[0])) - 100, 2)
            except (IndexError, TypeError, ValueError):
                return print("Error")
        else:
            currency, tickerlink, price, change = None, None, None, None
        return self.set_info(currency, tickerlink, price, change)

    def set_info(self, currency, tickerlink, price, change):
        if currency:
            self.createCurrencyRecord(currency, price, change)
            self.currency = f"{currency} to RUB - <a href='{tickerlink}'>open on MOEX</a>\n"
            self.price = f"\nPrice: <b>{price}</b> RUB" if price else 0
            self.change = f"\nToday's change: <b>{change}</b>%"

    def get_info(self):
        self.info_moex()
        if self.price:
            return f"{self.currency} {self.price} {self.change}"
        else:
            return f"{self.message} - тикер не найден или сервер не отвечает."
        
    def createCurrencyRecord(self, currency, price, change):
        date = datetime.datetime.now()
        date = date.strftime('%Y-%m-%d')
        conn = sqlite3.connect('./app_data/database.db')
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS currency (
                       dataTime TEXT PRIMARY KEY,
                       currency TEXT NOT NULL,
                       price INTEGER,
                       change TEXT
                       )''')
        cursor.execute('SELECT * FROM currency WHERE dataTime = ?', (date,))
        db_data = cursor.fetchone()
        if db_data is None:
            cursor.execute('INSERT INTO currency (dataTime, currency, price, change) VALUES (?,?,?,?)', (date, currency, price, change))
            conn.commit()
            conn.close() 

    
#Приветствие
@dp.message_handler(commands=['help'])
async def send_welcome(message: types.Message):
    await message.reply(str(help))

#Регистрация
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    user = User(message.from_user.id)
    user_record = user.checkUserRecord()
    if user_record is None:
        user.createUserRecord() 
        await message.reply("Привет! Регистрация прошла успешно")
    else:
        await message.reply("Привет! Вы уже зарегистрированы")

    await message.reply("Чтобы получить список команд, введи /help")


# Вывод информации об акции
@dp.message_handler(commands=['stock'])
async def text_supergroup_stock(message: types.Message):
    extractor = reticker.TickerExtractor()
    ticker = extractor.extract(message.text)
    if len(ticker) == 0:
        markup = types.ReplyKeyboardMarkup()
        sberkey = types.KeyboardButton('/stock SBER')
        gazpkey = types.KeyboardButton('/stock GAZP')
        tcsgkey = types.KeyboardButton('/stock TCSG')
        exitkey = types.KeyboardButton('/exit')
        markup.row(sberkey, gazpkey, tcsgkey)
        markup.row(exitkey)
        return await message.reply("Чтобы получить информацию, пришлите мне тикер.\n\n<b>Example</b>: /stock SBER", parse_mode='HTML', reply_markup=markup)
    elif 3 > len(ticker[0]) or len(ticker[0]) > 7:
        return await message.reply(message, "Это неверный тикер! Попробуй еще раз.\n\n<b>Example</b>: /stock SBER", parse_mode='HTML', reply_markup=markup)
    check = StockInfo(ticker[0])
    await message.reply(str(check.get_info()), parse_mode='HTML')


# Вывод информации о валюте
@dp.message_handler(commands=['currency'])
async def text_supergroup_currency(message: types.Message):
    ticker = message.text[10:].upper().strip('')
    if len(ticker) == 0:
        markup = types.ReplyKeyboardMarkup()
        usdkey = types.KeyboardButton('/currency BYN')
        eurkey = types.KeyboardButton('/currency KZT')
        cnykey = types.KeyboardButton('/currency CNY')
        exitkey = types.KeyboardButton('/exit')
        markup.row(usdkey, eurkey, cnykey)
        markup.row(exitkey)
        return  await message.reply("Чтобы узнать курс валюты, пришлите мне тикер.\n\n<b>Example</b>: /currency EUR", parse_mode='HTML', reply_markup=markup)
    elif 3 > len(ticker) or len(ticker) > 3:
        return await message.reply("Это неверный тикер! Попробуй еще раз.\n\n<b>Example</b>: /currency EUR", parse_mode='HTML', reply_markup=markup)
    check = CurrencyInfo(ticker)
    await message.reply(check.get_info(), parse_mode='HTML')

#Запрос валютной пары
@dp.message_handler(commands=['stock_candlestick'])
async def getTicker_start(message: types.Message):
    await message.reply("Введите идентификатор валютной пары")
    await CheckTickerStates.ticker.set()

#График валютной пары
@dp.message_handler(state=CheckTickerStates.ticker)
async def stock_candlestick_command(message: types.Message, state: FSMContext):
    #Поулчение данных ввода пользователя
    ticker = message.text
    stock = yf.Ticker(ticker)

    #Исторические данные за посление 14 дней
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=14)
    data = stock.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))

    #Проверка наличия данных
    if data.empty:
        await message.reply(f"Не найдено данных для " + str(ticker) + ". Пожалуйста, проверьте символ тикера.")
        return

    #Получение актуальной цены
    latest_price = data['Close'].iloc[-1]

    #Формирование графика ввиде свечей
    chart_filename = f'{ticker}_candlestick_chart.png'
    mpf.plot(data, type='candle', mav=(3, 6), volume=True, show_nontrading=True, savefig=chart_filename)

    # Цена акции
    await message.reply(f'Текущая цена на {ticker} равна ${latest_price:.2f}.')

    # Отправка картинки с графиком
    with open(chart_filename, 'rb') as chart:
        await message.reply_photo(chart)

    # Ссылка на страницу Yahoo Finance для тикера
    yahoo_finance_url = f'https://finance.yahoo.com/quote/{ticker}'
    await message.reply(f'Более подробную информацию смотри здесь: {yahoo_finance_url}')
    os.remove(chart_filename)
    await state.finish()


# Выход
@dp.message_handler(commands=['exit'])
async def text_supergroup_currency(message):
    markup = types.ReplyKeyboardRemove(selective=False)
    await message.reply( "До новых встреч!", reply_markup=markup)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)