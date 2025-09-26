import os
import logging
import json
import asyncio
import sys
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument

# 📍 Пути для Timeweb Cloud
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config", ".env")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# Настройка логирования
os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'bot.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def load_config():
    """Загрузка конфигурации для Timeweb"""
    config = {}
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        config[key] = value.strip()
        else:
            logger.error(f"❌ Файл конфигурации не найден: {CONFIG_PATH}")
            
        return config
    except Exception as e:
        logger.error(f"Ошибка загрузки конфига: {e}")
        return {}

# Загрузка конфигурации
config = load_config()

# Конфигурация
API_ID = int(config.get('API_ID', 0))
API_HASH = config.get('API_HASH', '')
PHONE = config.get('PHONE', '')
BOT_TOKEN = config.get('BOT_TOKEN', '')
CHAT_TO_MONITOR = int(config.get('CHAT_TO_MONITOR', 0))
YOUR_USER_ID = int(config.get('YOUR_USER_ID', 0))

# Проверка конфигурации
if not all([API_ID, API_HASH, BOT_TOKEN, CHAT_TO_MONITOR]):
    logger.error("❌ Не все переменные установлены в .env файле!")
    logger.error("Проверьте путь: " + CONFIG_PATH)
    sys.exit(1)

logger.info("✅ Конфигурация загружена успешно")

# Файлы для хранения данных
SUBSCRIBERS_FILE = os.path.join(BASE_DIR, "subscribers.json")
ADMINS_FILE = os.path.join(BASE_DIR, "admins.json")
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")

class ForwardBot:
    def __init__(self):
        self.is_monitoring = True
        # Используем разные файлы сессий для стабильности
        session_dir = os.path.join(BASE_DIR, "sessions")
        os.makedirs(session_dir, exist_ok=True)
        
        self.user_client = TelegramClient(
            os.path.join(session_dir, 'user_session'), 
            API_ID, 
            API_HASH
        )
        self.bot_client = TelegramClient(
            os.path.join(session_dir, 'bot_session'), 
            API_ID, 
            API_HASH
        )
        
    def load_data(self, filename):
        """Загружает данные из JSON файла"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Ошибка загрузки {filename}: {e}")
            return []
    
    def save_data(self, data, filename):
        """Сохраняет данные в JSON файл"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения {filename}: {e}")
    
    def load_subscribers(self):
        return self.load_data(SUBSCRIBERS_FILE)
    
    def save_subscribers(self, subscribers):
        self.save_data(subscribers, SUBSCRIBERS_FILE)
    
    def load_admins(self):
        admins = self.load_data(ADMINS_FILE)
        if YOUR_USER_ID and YOUR_USER_ID not in admins:
            admins.append(YOUR_USER_ID)
            self.save_data(admins, ADMINS_FILE)
        return admins
    
    async def is_admin(self, user_id):
        admins = self.load_admins()
        return user_id in admins
    
    async def send_to_subscribers(self, text, media=None):
        if not self.is_monitoring:
            return
            
        subscribers = self.load_subscribers()
        if not subscribers:
            logger.info("Нет подписчиков для отправки")
            return
        
        success_count = 0
        failed_users = []
        
        for user_id in subscribers:
            try:
                if media and os.path.exists(media):
                    await self.bot_client.send_file(
                        user_id, 
                        media, 
                        caption=text[:2000] if text else None
                    )
                else:
                    await self.bot_client.send_message(user_id, text[:4000])
                success_count += 1
                await asyncio.sleep(0.2)  # Увеличиваем задержку для стабильности
                
            except Exception as e:
                error_msg = str(e).lower()
                if any(msg in error_msg for msg in ['blocked', 'deactivated', 'invalid']):
                    failed_users.append(user_id)
                logger.error(f"Ошибка отправки пользователю {user_id}: {e}")
        
        if failed_users:
            updated_subscribers = [uid for uid in subscribers if uid not in failed_users]
            self.save_subscribers(updated_subscribers)
            logger.info(f"Удалено недоступных пользователей: {len(failed_users)}")
        
        logger.info(f"✅ Сообщения отправлены: {success_count}/{len(subscribers)}")
        return success_count

    async def setup_handlers(self):
        """Настройка обработчиков событий"""
        
        @self.bot_client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            user_id = event.sender_id
            subscribers = self.load_subscribers()
            
            if user_id not in subscribers:
                subscribers.append(user_id)
                self.save_subscribers(subscribers)
                logger.info(f"Новый подписчик: {user_id}")
            
            welcome_text = """🤖 **Добро пожаловать!**

✅ Вы подписались на уведомления "ДПС УЧАЛЫ".

📋 **Команды:**
/start - подписаться на уведомления
/stop - отписаться от уведомлений
/status - статус мониторинга

💡 Теперь вы будете получать все новые сообщения!"""
            
            await event.reply(welcome_text)
        
        @self.bot_client.on(events.NewMessage(pattern='/stop'))
        async def stop_handler(event):
            user_id = event.sender_id
            subscribers = self.load_subscribers()
            
            if user_id in subscribers:
                subscribers.remove(user_id)
                self.save_subscribers(subscribers)
                await event.reply("❌ **Вы отписались от уведомлений!**")
                logger.info(f"Пользователь {user_id} отписался")
            else:
                await event.reply("ℹ️ **Вы не были подписаны.**")
        
        @self.bot_client.on(events.NewMessage(pattern='/status'))
        async def status_handler(event):
            subscribers = self.load_subscribers()
            user_status = "✅ подписан" if event.sender_id in subscribers else "❌ не подписан"
            
            status_text = f"""📊 **Статус мониторинга:**

🔔 Мониторинг: **{"✅ активен" if self.is_monitoring else "⏹️ остановлен"}**
👥 Подписчиков: **{len(subscribers)}**
🔔 Ваш статус: **{user_status}**"""
            
            await event.reply(status_text)

        @self.user_client.on(events.NewMessage(chats=CHAT_TO_MONITOR))
        async def group_message_handler(event):
            if not self.is_monitoring:
                return

            try:
                message = event.message
                
                text = f"📩 **Новое сообщение из группы**\n"
                text += f"💬 **Текст:** {message.text or 'Нет текста'}\n"
                text += f"⏰ **Время:** {message.date.strftime('%H:%M:%S')}"
                
                media_path = None
                if message.media:
                    try:
                        media_path = await message.download_media(file=DOWNLOADS_DIR)
                        text += f"\n📎 **Медиа вложения**"
                    except Exception as e:
                        logger.error(f"Ошибка загрузки медиа: {e}")
                
                await self.send_to_subscribers(text, media_path)
                
                if media_path and os.path.exists(media_path):
                    try:
                        os.remove(media_path)
                    except Exception as e:
                        logger.error(f"Ошибка удаления файла: {e}")
                    
            except Exception as e:
                logger.error(f"Ошибка обработки сообщения: {e}")

    async def start(self):
        """Запуск бота на Timeweb"""
        try:
            # Создаем необходимые папки
            os.makedirs(DOWNLOADS_DIR, exist_ok=True)
            
            logger.info("🔄 Запускаем бота на Timeweb Cloud...")
            
            # Запускаем бота
            await self.bot_client.start(bot_token=BOT_TOKEN)
            logger.info("✅ Бот запущен")
            
            # Запускаем пользовательский клиент
            await self.user_client.start(phone=PHONE)
            logger.info("✅ Аккаунт пользователя запущен")
            
            # Получаем информацию об аккаунте
            me = await self.user_client.get_me()
            logger.info(f"✅ Авторизован как {me.first_name}")
            
            # Настройка обработчиков
            await self.setup_handlers()
            
            # Уведомление о запуске
            try:
                await self.bot_client.send_message(
                    YOUR_USER_ID, 
                    "🤖 **Бот запущен на Timeweb Cloud!**\n✅ Мониторинг активен"
                )
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления: {e}")
            
            logger.info("🚀 Бот начал мониторинг...")
            
            # Бесконечный цикл с обработкой ошибок
            while True:
                try:
                    await asyncio.gather(
                        self.user_client.run_until_disconnected(),
                        self.bot_client.run_until_disconnected()
                    )
                except Exception as e:
                    logger.error(f"❌ Ошибка соединения: {e}")
                    logger.info("🔄 Переподключение через 10 секунд...")
                    await asyncio.sleep(10)
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}")

async def main():
    bot = ForwardBot()
    await bot.start()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен")
    except Exception as e:
        logger.error(f"💥 Фатальная ошибка: {e}")