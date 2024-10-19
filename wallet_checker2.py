import telebot
from mnemonic import Mnemonic
from eth_account import Account
from web3 import Web3
import time
import pickle
import os
from concurrent.futures import ThreadPoolExecutor

# Включаем HDWallet функции
Account.enable_unaudited_hdwallet_features()

# Ваши ключи
ALCHEMY_URL = 'https://eth-mainnet.g.alchemy.com/v2/wjdhNNgb-oha3HaUj1HNLk_qsP_SYqHu'
BOT_API_KEY = '7952618712:AAGoBIRhpt3i59WGex4V-0b8Ca9qAoQ1H0U'

# Подключение к Ethereum через Alchemy
w3 = Web3(Web3.HTTPProvider(ALCHEMY_URL))

if w3.is_connected():
    print("Успешно подключено к сети Ethereum")
else:
    print("Не удалось подключиться к сети Ethereum")

# Создание бота
bot = telebot.TeleBot(BOT_API_KEY)

# Путь к файлу для хранения кэша
CACHE_FILE = 'balance_cache.pkl'

# Функция для загрузки кэша из файла
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'rb') as f:
            return pickle.load(f)
    return {}

# Функция для сохранения кэша в файл
def save_cache(cache):
    with open(CACHE_FILE, 'wb') as f:
        pickle.dump(cache, f)

# Загружаем кэш при старте программы
balance_cache = load_cache()

# Функция генерации кошелька
def generate_wallet():
    mnemo = Mnemonic("english")
    seed_phrase = mnemo.generate(strength=128)  # 12 слов (128 бит энтропии)
    acct = Account.from_mnemonic(seed_phrase)
    address = acct.address
    return seed_phrase, address

# Функция проверки баланса с кэшированием
def check_balance(address):
    try:
        if address in balance_cache:
            return balance_cache[address]
        balance = w3.eth.get_balance(address)
        balance_eth = w3.from_wei(balance, 'ether')
        return balance_eth
    except Exception as e:
        print(f"Ошибка при проверке баланса для {address}: {e}")
        return 0  # Возвращаем 0, если произошла ошибка

# Функция для проверки баланса нескольких кошельков
def check_multiple_wallets(wallets):
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_results = executor.map(lambda wallet: (wallet, check_balance(wallet[1])), wallets)

        for wallet, balance in future_results:
            results.append((wallet[0], wallet[1], balance))
            # Добавляем в кэш только после всех операций
            balance_cache[wallet[1]] = balance

    # Сохраняем кэш после завершения всех проверок
    save_cache(balance_cache)
    return results

# Функция для проверки баланса тестового адреса с известным балансом и отправки результата в чат
def test_balance_check(message):
    test_address = '0x742d35Cc6634C0532925a3b844Bc454e4438f44e'  # Адрес с большим известным балансом
    balance = check_balance(test_address)
    response = f"Баланс тестового адреса {test_address}: {balance} ETH"
    print(response)  # Вывод в консоль для отладки
    bot.send_message(message.chat.id, response)  # Отправляем сообщение в чат

# Обработка команды /start
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет! Я могу генерировать ETH-адреса, проверять их балансы и предоставлять сид-фразы.")

# Обработка команды /generate
@bot.message_handler(commands=['generate'])
def generate(message):
    bot.send_message(message.chat.id, "Ищу кошельки с ненулевым балансом, это может занять некоторое время...")
    
    count = 0
    while True:
        wallets = [generate_wallet() for _ in range(10)]  # Генерация 10 кошельков
        balances = check_multiple_wallets(wallets)  # Проверка 10 кошельков

        for seed_phrase, address, balance in balances:
            count += 1

            if count % 1000 == 0:
                progress_message = f"Проверено {count} кошельков. Последний адрес: {address}, Баланс: {balance} ETH"
                bot.send_message(message.chat.id, progress_message)
                print(progress_message)  # Лог в консоль для удобства

            if balance > 0:
                response = f"Сгенерированная сид-фраза: {seed_phrase}\nАдрес: {address}\nБаланс: {balance} ETH"
                bot.send_message(message.chat.id, response)
                print("Кошелек найден!")  # Лог
                return  # Останавливаем цикл после нахождения кошелька с ненулевым балансом

# Обработка команды /test_balance
@bot.message_handler(commands=['test_balance'])
def test_balance(message):
    test_balance_check(message)  # Проверяем тестовый баланс и отправляем в чат

# Запуск бота
if __name__ == '__main__':
    print("Бот запущен и готов к работе.")
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
