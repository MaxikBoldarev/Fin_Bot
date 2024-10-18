import sqlite3
import unittest
import main as bot
import sqlite3
import stock

#Test класса User
class UserTestCase(unittest.TestCase):
    check_telegram_id = 123456789
    create_telegram_id = 123456788

    def setUp(self) -> None:
        conn = sqlite3.connect('./app_data/database.db')
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (telegram_id INTEGER PRIMARY KEY)''')
        cursor.execute('INSERT INTO users (telegram_id) VALUES (?)', (self.check_telegram_id,))
        conn.commit()
        conn.close()

    def tearDown(self) -> None:
        conn = sqlite3.connect('./app_data/database.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE telegram_id = ?', (self.check_telegram_id,))
        cursor.execute('DELETE FROM users WHERE telegram_id = ?', (self.create_telegram_id,))
        conn.commit()
        conn.close()

    def test_check_user_data(self):
        user = bot.User(self.check_telegram_id)
        result = user.checkUserRecord()
        self.assertEqual(result, self.check_telegram_id)

    def test_create_user_record(self):
        user = bot.User(self.create_telegram_id)
        result = user.createUserRecord()
        self.assertEqual(result, self.create_telegram_id)


#Тест класса Stock
class TestStockInfo(unittest.TestCase):

    def tearDown(self) -> None:
        conn = sqlite3.connect('./app_data/database.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM stocks WHERE message = ?',("TEST",))
        conn.commit()
        conn.close()

    def test_set_moex(self):
        assertion = "ticker - <a href='tickerlink'>open on MOEX\n</a>"
        stocks = stock.StockInfo('SBER')
        stocks.set_info("ticker", "tickerlink", "price", 90, "change")
        result = stocks.name
        self.assertEqual(result, assertion)

    def test_get_info(self):
        stocks = stock.StockInfo('SBER')
        result = stocks.get_info()
        self.assertIsNotNone(result)
 
    def test_info_moex(self):
        stocks = stock.StockInfo('SBER')
        stocks.info_moex()
        result = stocks.price
        self.assertIsNotNone(result)


    def test_createStockRecord(self):
        stock.StockInfo.createStockRecord(self, "TEST", 100.0, "10000000", "5.26")
        conn = sqlite3.connect('./app_data/database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT price FROM stocks WHERE message = ?',("TEST",))
        result = cursor.fetchall()
        conn.commit()
        conn.close()
        self.assertIsNotNone(result)

#Тест класса CurrencyInfo
class TestCurrencyInfo(unittest.TestCase):

    test_currency_id = 'KZTRUB_TOM'
    test_url = f'https://iss.moex.com/iss/engines/currency/markets/selt/securities/KZTRUB_TOM.xml' 
                
    test_response = {'KZTRUB_TOM'}


    def tearDown(self) -> None:
        conn = sqlite3.connect('./app_data/database.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM currency WHERE currency = ?',("TEST",))
        conn.commit()
        conn.close()

    def test_info_moex(self):
        currency = bot.CurrencyInfo("KZT")
        currency.info_moex()
        result = currency.price
        self.assertIsNotNone(result)


    def test_set_info(self):
        assertion = "currency to RUB - <a href='tickerlink'>open on MOEX</a>\n"
        currency = bot.CurrencyInfo("KZT")
        currency.set_info("currency", "tickerlink", "price", "change")
        result = currency.currency
        self.assertEqual(result, assertion)

    def test_get_info(self):
        currency = bot.CurrencyInfo("KZT")
        result = currency.get_info()
        self.assertIsNotNone(result)

    def test_createStockRecord(self):
        bot.CurrencyInfo.createCurrencyRecord(self, "TEST", 500, "1.1")
        conn = sqlite3.connect('./app_data/database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT price FROM currency WHERE currency = ?',("TEST",))
        result = cursor.fetchall()
        conn.commit()
        conn.close()
        self.assertIsNotNone(result)



if __name__ == '__main__':
    unittest.main()
