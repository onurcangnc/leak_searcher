# bot.py

import telebot
from telebot.types import Message
from elastic_manager import ElasticManager  # ElasticManager is used for search and list operations
import os
import logging

def save_results_to_file(results, filename):
    """
    Eşleşen sonuçları bir .txt dosyasına kaydeder.
    """
    with open(filename, 'w', encoding='utf-8') as file:
        for result in results:
            file.write(f"Satır: {result['line_number']}, İçerik: {result['content']}\n")
    return filename

# Logging Ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram Bot Token (Çevresel Değişkenlerden Alınması Güvenlik İçin Önerilir)
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7368855657:AAHwY8hmzNOyxd_TsDTb1Gy8WT4Qw-b77VA")  # Güvenlik nedeniyle tokenınızı gizli tutun
bot = telebot.TeleBot(BOT_TOKEN)

# Elasticsearch Manager
ES_HOST = os.getenv("ELASTIC_HOST", "http://localhost:9200")
ES_USERNAME = os.getenv("ELASTIC_USERNAME", None)
ES_PASSWORD = os.getenv("ELASTIC_PASSWORD", None)
INDEX_NAME = "*"  # Tüm indekslerde arama yapmak için '*' kullanın

try:
    es_manager = ElasticManager(host=ES_HOST, username=ES_USERNAME, password=ES_PASSWORD)
except Exception as e:
    logger.critical(f"Elasticsearch bağlantısı başarısız: {e}")
    exit(1)

# Authorized Users
authorized_users = set()

# Authorization Check
def is_authorized(user_id):
    return user_id in authorized_users

# /start Command
@bot.message_handler(commands=["start"])
def start_command(message: Message):
    bot.reply_to(message, "Leak Manager Bot'a hoş geldiniz! Erişim sağlamak için /authorize komutunu kullanın.")

# /authorize Command
@bot.message_handler(commands=["authorize"])
def authorize_user(message: Message):
    if message.chat.id not in authorized_users:
        authorized_users.add(message.chat.id)
        bot.reply_to(message, "Botu kullanmak için yetkilendirildiniz.")
        logger.info(f"Kullanıcı yetkilendirildi: {message.chat.id}")
    else:
        bot.reply_to(message, "Zaten yetkilisiniz.")

# /listleaks Command
@bot.message_handler(commands=["listleaks"])
def list_leaks(message: Message):
    if not is_authorized(message.chat.id):
        bot.reply_to(message, "Yetkisiz erişim.")
        logger.warning(f"Yetkisiz erişim denemesi: {message.chat.id}")
        return

    indices = es_manager.list_indices()
    if indices:
        bot.reply_to(message, "Mevcut indeksler:\n" + "\n".join(indices))
    else:
        bot.reply_to(message, "Hiç indeks bulunamadı.")

# /search Command
@bot.message_handler(commands=["search"])
def search_leaks(message: Message):
    if not is_authorized(message.chat.id):
        bot.reply_to(message, "Yetkisiz erişim.")
        logger.warning(f"Yetkisiz erişim denemesi: {message.chat.id}")
        return

    msg = bot.reply_to(message, "Aramak istediğiniz anahtar kelimeyi yazın:")

    # Register the next step handler
    bot.register_next_step_handler(msg, handle_query)

import re

def escape_markdown(text):
    """
    Telegram Markdown formatına uygun olmayan karakterlerden kaçmak için kullanılır.
    """
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)

def handle_query(message: Message):
    if not is_authorized(message.chat.id):
        bot.reply_to(message, "Yetkisiz erişim.")
        logger.warning(f"Yetkisiz erişim denemesi: {message.chat.id}")
        return

    query = message.text.strip()
    if not query:
        bot.reply_to(message, "Lütfen geçerli bir arama sorgusu girin.")
        return

    try:
        # Scroll API ile Elasticsearch'te arama yap
        results = []
        scroll_id = None

        # İlk sorguyu başlat
        response = es_manager.client.search(
            index=INDEX_NAME,
            query={
                "query_string": {
                    "query": f"*{query}*",
                    "fields": ["content"]
                }
            },
            size=1000,  # Her sorguda 1000 sonuç döndür
            scroll="2m"  # Scroll süresi
        )
        results.extend(response['hits']['hits'])
        scroll_id = response['_scroll_id']

        # Scroll döngüsü
        while True:
            response = es_manager.client.scroll(scroll_id=scroll_id, scroll="2m")
            if not response['hits']['hits']:
                break
            results.extend(response['hits']['hits'])
            scroll_id = response['_scroll_id']

        if results:
            # Tüm sonuçları bir dosyaya kaydet
            responses = []
            for hit in results:
                source = hit['_source']
                responses.append({
                    "line_number": source.get('line_number', 'Bilinmiyor'),
                    "content": source.get('content', '')
                })

            filename = f"search_results_{message.chat.id}.txt"
            save_results_to_file(responses, filename)
            with open(filename, 'rb') as file:
                bot.send_document(message.chat.id, file)
        else:
            response = "Hiçbir eşleşme bulunamadı."
            bot.reply_to(message, response)

    except Exception as e:
        logger.error(f"Arama sırasında hata oluştu: {e}")
        response = "Arama sırasında bir hata oluştu. Lütfen tekrar deneyin."
        bot.reply_to(message, response)


# /help Command
@bot.message_handler(commands=["help"])
def help_command(message: Message):
    help_text = (
        "📚 **Leak Manager Bot Komutları** 📚\n\n"
        "/start - Botu başlatır ve hoş geldiniz mesajı gösterir.\n"
        "/authorize - Botu kullanmak için yetkilendirilir.\n"
        "/listleaks - Mevcut indekslerin listesini gösterir. (Yetkilendirme gerektirir)\n"
        "/search - İçerik aramak için anahtar kelime girmenizi sağlar. (Yetkilendirme gerektirir)\n"
        "/help - Tüm komutları listeler."
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

# Bot Start
try:
    logger.info("Bot çalışıyor...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
except Exception as e:
    logger.critical(f"Bir hata oluştu: {e}")
