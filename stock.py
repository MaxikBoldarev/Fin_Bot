import requests
from bs4 import BeautifulSoup
import sqlite3
import datetime

class StockInfo:
    def __init__(self, message):
        self.message = message
        self.headers = {"User-Agent": "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6.1 Safari/605.1.15"}
        self.name = None
        self.price = None
        self.cap = None
        self.change = None

    def info_moex(self):
        url = f'http://iss.moex.com/iss/engines/stock/markets/shares/securities/{self.message}.xml'
        pages = requests.get(url, timeout=10, headers=self.headers)
        soup = BeautifulSoup(pages.text, 'xml') 
        info = (soup.find(id="marketdata").find(BOARDID="TQBR"))
        if info:
            try:
                ticker = self.message
                tickerlink = f"https://www.moex.com/ru/issue.aspx?code={ticker}"
                price = float(info.get('LAST'))
                change = round(price * 100 / (float(info.get('OPEN'))) - 100, 2)
                cap = float(info.get('ISSUECAPITALIZATION') if info.get('ISSUECAPITALIZATION') != '' else 0)
            except (IndexError, TypeError, ValueError):
                return print("Error")
        else:
            ticker, tickerlink, price, cap, change = None, None, None, None, None
        return self.set_info(ticker, tickerlink, price, cap, change)

    def set_info(self, ticker, tickerlink, price, cap, change):
        if ticker:
            self.createStockRecord(ticker, price, cap, change) 
            self.name = f"{ticker} - <a href='{tickerlink}'>open on MOEX\n</a>"
            self.price = f"\nPrice: <b>{price}</b> RUB" if price else 0
            self.cap = f"\nMarket Cap: <b>{cap / 10**9 // 0.1 / 10} </b>B" if cap != 0 else "\nMarketcap: <b>No information</b>"
            self.change = f"\nToday's change: <b>{change}</b>%"

    def get_info(self):
        self.info_moex() 
        if self.price:
            return f"{self.name} {self.price} {self.cap} {self.change}"
        else:
            return f"{self.message} - тикер не найден или сервер не отвечает."
        
    
    def createStockRecord(self, ticker, price, cap, change):
        date = datetime.datetime.now()
        date = date.strftime('%Y-%m-%d')
        conn = sqlite3.connect('./app_data/database.db')
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS stocks (
                       dataTime TEXT PRIMARY KEY,
                       message TEXT NOT NULL,
                       price INTEGER,
                       cap TEXT,
                       change TEXT
                       )''')
        cursor.execute('SELECT * FROM stocks WHERE dataTime = ?', (date,))
        db_data = cursor.fetchone()
        if db_data is None:
            cursor.execute('INSERT INTO stocks (dataTime, message, price, cap, change) VALUES (?,?,?,?,?)', (date, ticker, price, cap, change))
            conn.commit()
            conn.close()


        