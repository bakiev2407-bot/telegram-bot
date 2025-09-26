import os
import logging
import json
import asyncio
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
API_ID = 23921954
API_HASH = 'e8b91c0c46c3edc7b063e8ef0096616f'
PHONE = '+79053089455'
BOT_TOKEN = '7576598515:AAG6_zf1315Oe9FFWd3TfhHbrdN4vrEYub4'
CHAT_TO_MONITOR = -1001484212179  # ДПС УЧАЛЫ🚔🚔🚔"

# Файл для хранения подписчиков
SUBSCRIBERS_FILE = "subscribers.json"

# Флаг для управления мониторингом
is_monitoring = True

# Инициализация клиентов
user_client = TelegramClient('user_session', API_ID, API_HASH)
bot_client = TelegramClient('bot_session', API_ID, API_HASH)

def load_subscribers():
    """Загружает список подписчиков из файла"""
    try:
        if os.path.exists(SUBSCRIBERS_FILE):
            with open(SUBSCRIBERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Ошибка загрузки подписчиков: {e}")
        return []

def save_subscribers(subscribers):
    """Сохраняет список подписчиков в файл"""
    try:
        with open(SUBSCRIBERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(subscribers, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения подписчиков: {e}")

async def send_to_all_subscribers(text, media=None):
    """Отправляет сообщение ВСЕМ подписчикам"""
    if not is_monitoring:
        return
        
    subscribers = load_subscribers()
    if not subscribers:
        logger.info("Нет подписчиков для отправки")
        return
    
    success_count = 0
    for user_id in subscribers:
        try:
            if media and os.path.exists(media):
                await bot_client.send_file(
                    user_id, 
                    media, 
                    caption=text[:2000] if text else None
                )
            else:
                await bot_client.send_message(user_id, text[:4000])
            success_count += 1
            logger.info(f"Сообщение отправлено пользователю {user_id}")
        except Exception as e:
            logger.error(f"Ошибка отправки пользователю {user_id}: {e}")
            # Если пользователь заблокировал бота, удаляем его из подписчиков
            if "bot was blocked" in str(e).lower():
                subscribers.remove(user_id)
                save_subscribers(subscribers)
                logger.info(f"Пользователь {user_id} удален из подписчиков (заблокировал бота)")
    
    logger.info(f"✅ Сообщения отправлены: {success_count}/{len(subscribers)} пользователей")

async def send_welcome_message():
    """Отправляет приветственное сообщение при запуске"""
    try:
        welcome_text = """🤖 **Бот мониторинга группы запущен!**

✅ Система мониторинга активна
👥 Готов к приему подписчиков

💡 Пользователи могут написать /start для подписки на уведомления"""
        
        # Отправляем себе уведомление о запуске
        me = await user_client.get_me()
        await bot_client.send_message(me.id, welcome_text)
        logger.info("Приветственное сообщение отправлено")
    except Exception as e:
        logger.error(f"Ошибка отправки приветствия: {e}")

@bot_client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    """Обработчик команды /start - подписка пользователя"""
    global is_monitoring
    
    user_id = event.sender_id
    subscribers = load_subscribers()
    
    # Добавляем пользователя в подписчики если его нет
    if user_id not in subscribers:
        subscribers.append(user_id)
        save_subscribers(subscribers)
        logger.info(f"Новый подписчик: {user_id}")
    
    is_monitoring = True
    
    welcome_text = """🤖 **Добро пожаловать!**

✅ Вы подписались на уведомления  "ДПС УЧАЛЫ".

📋 **Команды:**
/start - подписаться на уведомлени
/stop - отписаться от уведомлений
/status - статус мониторинга

💡 Теперь вы будете получать все новые сообщения о местоположение дпс в городе учалы  !"""
    
    await event.reply(welcome_text)
    logger.info(f"Пользователь {user_id} подписан на уведомления")

@bot_client.on(events.NewMessage(pattern='/stop'))
async def stop_handler(event):
    """Обработчик команды /stop - отписка пользователя"""
    user_id = event.sender_id
    subscribers = load_subscribers()
    
    if user_id in subscribers:
        subscribers.remove(user_id)
        save_subscribers(subscribers)
        await event.reply("❌ **Вы отписались от уведомлений!**\nВы больше не будете получать сообщения о местоположение дпс в городе учалы  ! ")
        logger.info(f"Пользователь {user_id} отписался")
    else:
        await event.reply("ℹ️ **Вы не были подписаны на уведомления.**")

@bot_client.on(events.NewMessage(pattern='/status'))
async def status_handler(event):
    """Обработчик команды /status"""
    subscribers = load_subscribers()
    total_subscribers = len(subscribers)
    user_status = "✅ подписан" if event.sender_id in subscribers else "❌ не подписан"
    
    status_text = f"""📊 **Статус мониторинга:**

🔔 Мониторинг: **{"✅ активен" if is_monitoring else "⏹️ остановлен"}**
👥 Всего подписчиков: **{total_subscribers}**
🔔 Ваш статус: **{user_status}**

💡 Используйте:
/start - подписаться на уведомления
/stop - отписаться от уведомлений"""
    
    await event.reply(status_text)

@bot_client.on(events.NewMessage(pattern='/stats'))
async def stats_handler(event):
    """Показывает детальную статистику (только для админа)"""
    try:
        me = await user_client.get_me()
        if event.sender_id != me.id:
            await event.reply("❌ Эта команда только для администратора")
            return
            
        subscribers = load_subscribers()
        status_text = f"""📈 **Детальная статистика:**

👥 Всего подписчиков: **{len(subscribers)}**
🔔 Мониторинг: **{"✅ активен" if is_monitoring else "⏹️ остановлен"}**
📊 ID подписчиков: {subscribers}"""
        
        await event.reply(status_text)
    except Exception as e:
        logger.error(f"Ошибка команды /stats: {e}")

@bot_client.on(events.NewMessage(pattern='/broadcast'))
async def broadcast_handler(event):
    """Отправляет сообщение всем подписчикам (только для админа)"""
    try:
        me = await user_client.get_me()
        if event.sender_id != me.id:
            await event.reply("❌ Эта команда только для администратора")
            return
            
        message_text = event.message.text.replace('/broadcast', '').strip()
        if not message_text:
            await event.reply("❌ Укажите сообщение после команды: /broadcast Ваше сообщение")
            return
            
        subscribers = load_subscribers()
        success_count = 0
        
        for user_id in subscribers:
            try:
                await bot_client.send_message(user_id, f"📢 **Объявление от администратора:**\n\n{message_text}")
                success_count += 1
            except Exception as e:
                logger.error(f"Ошибка отправки объявления пользователю {user_id}: {e}")
                
        await event.reply(f"✅ Объявление отправлено {success_count}/{len(subscribers)} подписчикам")
        
    except Exception as e:
        logger.error(f"Ошибка команды /broadcast: {e}")

@user_client.on(events.NewMessage(chats=CHAT_TO_MONITOR))
async def group_message_handler(event):
    """Обработчик новых сообщений из группы"""
    global is_monitoring
    
    if not is_monitoring:
        return  # Мониторинг остановлен
    
    try:
        message = event.message
        sender = await message.get_sender()
        
        # Получаем имя отправителя
        if hasattr(sender, 'title'):  # Для каналов/групп
            sender_name = sender.title
        elif hasattr(sender, 'username') and sender.username:
            sender_name = f"@{sender.username}"
        elif hasattr(sender, 'first_name'):
            sender_name = f"{sender.first_name or ''} {sender.last_name or ''}".strip()
        else:
            sender_name = "Неизвестный отправитель"
        
        # Формируем текст сообщения
        text = f"📩 **Новое сообщение из группы**\n"
        text += f"👤 **Отправитель:** {sender_name}\n"
        text += f"💬 **Текст:** {message.text or 'Нет текста'}\n"
        text += f"⏰ **Время:** {message.date.strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Обработка медиа
        media_path = None
        if message.media:
            try:
                if isinstance(message.media, (MessageMediaPhoto, MessageMediaDocument)):
                    media_path = await message.download_media(file='downloads/')
                    media_type = 'Фото' if isinstance(message.media, MessageMediaPhoto) else 'Документ'
                    text += f"\n📎 **Тип медиа:** {media_type}"
                    logger.info(f"Медиа файл загружен: {media_path}")
            except Exception as e:
                logger.error(f"Ошибка загрузки медиа: {e}")
        
        # Отправляем сообщение ВСЕМ подписчикам
        await send_to_all_subscribers(text, media_path)
        
        # Удаляем временный файл
        if media_path and os.path.exists(media_path):
            try:
                os.remove(media_path)
            except Exception as e:
                logger.error(f"Ошибка удаления файла: {e}")
            
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")

async def main():
    """Основная функция"""
    try:
        # Создаем папку для загрузок
        os.makedirs('downloads', exist_ok=True)
        
        # Запускаем бота первым
        logger.info("🔄 Запускаем бота...")
        await bot_client.start(bot_token=BOT_TOKEN)
        logger.info("✅ Бот запущен")
        
        # Запускаем клиент пользователя
        logger.info("🔄 Запускаем аккаунт пользователя...")
        await user_client.start(phone=PHONE)
        logger.info("✅ Аккаунт пользователя успешно запущен")
        
        # Получаем информацию о себе
        me = await user_client.get_me()
        logger.info(f"✅ Авторизован как {me.first_name} (id: {me.id})")
        
        # Отправляем приветственное сообщение
        await send_welcome_message()
        
        # Проверяем доступ к группе
        try:
            chat = await user_client.get_entity(CHAT_TO_MONITOR)
            logger.info(f"✅ Мониторинг группы: {chat.title} (id: {chat.id})")
        except Exception as e:
            logger.error(f"❌ Ошибка доступа к группе: {e}")
            return
        
        # Загружаем подписчиков
        subscribers = load_subscribers()
        logger.info(f"👥 Загружено подписчиков: {len(subscribers)}")
        
        logger.info("🚀 Бот начал мониторинг сообщений...")
        logger.info("💡 Пользователи могут писать /start для подписки")
        logger.info("⏹️ Для остановки нажмите Ctrl+C")
        
        # Ожидаем завершения обоих клиентов
        await asyncio.gather(
            user_client.run_until_disconnected(),
            bot_client.run_until_disconnected()
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка в основной функции: {e}")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")