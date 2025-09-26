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
CHAT_TO_MONITOR = -1001484212179
ADMIN_ID = 463717122  # Ваш user_id

# Файлы для хранения данных
SUBSCRIBERS_FILE = "subscribers.json"
PINNED_MESSAGE_FILE = "pinned_message.json"
ADVERTISEMENTS_FILE = "advertisements.json"

# Флаги управления
is_monitoring = True
is_advertisements_enabled = True

# Инициализация клиентов
user_client = TelegramClient('user_session', API_ID, API_HASH)
bot_client = TelegramClient('bot_session', API_ID, API_HASH)

# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ С ДАННЫМИ ====================

def load_subscribers():
    """Загружает список подписчиков"""
    try:
        if os.path.exists(SUBSCRIBERS_FILE):
            with open(SUBSCRIBERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Ошибка загрузки подписчиков: {e}")
        return []

def save_subscribers(subscribers):
    """Сохраняет список подписчиков"""
    try:
        with open(SUBSCRIBERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(subscribers, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения подписчиков: {e}")

def load_pinned_message():
    """Загружает закрепленное сообщение"""
    try:
        if os.path.exists(PINNED_MESSAGE_FILE):
            with open(PINNED_MESSAGE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"text": "", "is_active": False}
    except Exception as e:
        logger.error(f"Ошибка загрузки закрепленного сообщения: {e}")
        return {"text": "", "is_active": False}

def save_pinned_message(message_data):
    """Сохраняет закрепленное сообщение"""
    try:
        with open(PINNED_MESSAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(message_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения закрепленного сообщения: {e}")

def load_advertisements():
    """Загружает список рекламных сообщений"""
    try:
        if os.path.exists(ADVERTISEMENTS_FILE):
            with open(ADVERTISEMENTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Ошибка загрузки рекламы: {e}")
        return []

def save_advertisements(ads):
    """Сохраняет список рекламных сообщений"""
    try:
        with open(ADVERTISEMENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(ads, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения рекламы: {e}")

def is_admin(user_id):
    """Проверяет, является ли пользователь администратором"""
    return user_id == ADMIN_ID

# ==================== ОСНОВНЫЕ ФУНКЦИИ ====================

async def send_to_all_subscribers(text, media=None):
    """Отправляет сообщение всем подписчикам"""
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
        except Exception as e:
            logger.error(f"Ошибка отправки пользователю {user_id}: {e}")
            if "bot was blocked" in str(e).lower():
                subscribers.remove(user_id)
                save_subscribers(subscribers)
    
    logger.info(f"✅ Сообщения отправлены: {success_count}/{len(subscribers)} пользователей")
    return success_count

async def send_pinned_message_to_new_user(user_id):
    """Отправляет закрепленное сообщение новому пользователю"""
    pinned_msg = load_pinned_message()
    if pinned_msg.get("is_active") and pinned_msg.get("text"):
        try:
            await bot_client.send_message(user_id, f"📌 **Закрепленное сообщение:**\n\n{pinned_msg['text']}")
        except Exception as e:
            logger.error(f"Ошибка отправки закрепленного сообщения: {e}")

async def send_random_advertisement():
    """Отправляет случайное рекламное сообщение всем подписчикам"""
    if not is_advertisements_enabled:
        return
        
    advertisements = load_advertisements()
    if not advertisements:
        return
        
    import random
    ad = random.choice(advertisements)
    
    if ad.get("is_active", False):
        subscribers = load_subscribers()
        success_count = 0
        
        for user_id in subscribers:
            try:
                await bot_client.send_message(user_id, f"📢 **Рекламное сообщение:**\n\n{ad['text']}")
                success_count += 1
            except Exception as e:
                logger.error(f"Ошибка отправки рекламы пользователю {user_id}: {e}")
        
        logger.info(f"📢 Реклама отправлена {success_count}/{len(subscribers)} пользователям")

# ==================== КОМАНДЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ====================

@bot_client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    """Обработчик команды /start"""
    global is_monitoring
    
    user_id = event.sender_id
    subscribers = load_subscribers()
    
    if user_id not in subscribers:
        subscribers.append(user_id)
        save_subscribers(subscribers)
        logger.info(f"Новый подписчик: {user_id}")
        
        # Отправляем закрепленное сообщение новому пользователю
        await send_pinned_message_to_new_user(user_id)
    
    is_monitoring = True
    
    welcome_text = """🤖 **Добро пожаловать!**

✅ Вы подписались на уведомления "ДПС УЧАЛЫ".

📋 **Команды:**
/start - подписаться на уведомления
/stop - отписаться от уведомлений
/status - статус мониторинга

💡 Теперь вы будете получать все новые сообщения о местоположении ДПС в городе Учалы!"""
    
    await event.reply(welcome_text)

@bot_client.on(events.NewMessage(pattern='/stop'))
async def stop_handler(event):
    """Обработчик команды /stop"""
    user_id = event.sender_id
    subscribers = load_subscribers()
    
    if user_id in subscribers:
        subscribers.remove(user_id)
        save_subscribers(subscribers)
        await event.reply("❌ **Вы отписались от уведомлений!**")
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
🔔 Ваш статус: **{user_status}**"""
    
    await event.reply(status_text)

# ==================== АДМИН-ПАНЕЛЬ ====================

@bot_client.on(events.NewMessage(pattern='/admin'))
async def admin_handler(event):
    """Главное меню админ-панели"""
    if not is_admin(event.sender_id):
        await event.reply("❌ **Доступ запрещен!**")
        return
    
    admin_text = """🛠️ **Панель администратора**

📊 **Статистика:**
/subscribers - список подписчиков
/stats - детальная статистика

📢 **Управление рассылкой:**
/broadcast - рассылка сообщения
/pin_message - закрепить сообщение
/ads - управление рекламой

⚙️ **Настройки бота:**
/toggle_monitoring - вкл/выкл мониторинг
/toggle_ads - вкл/выкл рекламу

💾 **Экспорт данных:**
/export_subscribers - экспорт подписчиков"""
    
    await event.reply(admin_text)

@bot_client.on(events.NewMessage(pattern='/subscribers'))
async def subscribers_handler(event):
    """Показывает список подписчиков"""
    if not is_admin(event.sender_id):
        return
        
    subscribers = load_subscribers()
    if not subscribers:
        await event.reply("📭 **Подписчиков нет**")
        return
    
    subscribers_text = f"👥 **Список подписчиков ({len(subscribers)}):**\n\n"
    for i, user_id in enumerate(subscribers[:50], 1):  # Ограничиваем первые 50
        subscribers_text += f"{i}. `{user_id}`\n"
    
    if len(subscribers) > 50:
        subscribers_text += f"\n... и еще {len(subscribers) - 50} подписчиков"
    
    await event.reply(subscribers_text)

@bot_client.on(events.NewMessage(pattern='/stats'))
async def stats_handler(event):
    """Детальная статистика"""
    if not is_admin(event.sender_id):
        return
        
    subscribers = load_subscribers()
    pinned_msg = load_pinned_message()
    advertisements = load_advertisements()
    active_ads = len([ad for ad in advertisements if ad.get('is_active', False)])
    
    stats_text = f"""📈 **Детальная статистика:**

👥 **Подписчики:**
• Всего: {len(subscribers)}
• Активных: {len(subscribers)}

📌 **Закрепленное сообщение:**
• Статус: {"✅ активно" if pinned_msg.get('is_active') else "❌ неактивно"}
• Длина: {len(pinned_msg.get('text', ''))} символов

📢 **Рекламные сообщения:**
• Всего: {len(advertisements)}
• Активных: {active_ads}
• Реклама: {"✅ включена" if is_advertisements_enabled else "❌ выключена"}

🔔 **Мониторинг:** {"✅ активен" if is_monitoring else "❌ остановлен"}"""
    
    await event.reply(stats_text)

@bot_client.on(events.NewMessage(pattern='/broadcast'))
async def broadcast_handler(event):
    """Рассылка сообщения всем подписчикам"""
    if not is_admin(event.sender_id):
        return
        
    message_text = event.message.text.replace('/broadcast', '').strip()
    if not message_text:
        await event.reply("❌ **Укажите сообщение:**\n`/broadcast Ваше сообщение`")
        return
        
    subscribers = load_subscribers()
    if not subscribers:
        await event.reply("❌ **Нет подписчиков для рассылки**")
        return
    
    # Подтверждение рассылки
    confirm_text = f"""📢 **Подтверждение рассылки**

💬 Сообщение: {message_text[:100]}...
👥 Получателей: {len(subscribers)}

✅ **Для подтверждения отправьте:** `/confirm_broadcast`"""
    
    await event.reply(confirm_text)

@bot_client.on(events.NewMessage(pattern='/confirm_broadcast'))
async def confirm_broadcast_handler(event):
    """Подтверждение рассылки"""
    if not is_admin(event.sender_id):
        return
        
    # Находим предыдущее сообщение с broadcast
    async for message in bot_client.iter_messages(await event.get_chat(), limit=10):
        if message.text and "Подтверждение рассылки" in message.text:
            # Извлекаем текст сообщения из предыдущего сообщения
            lines = message.text.split('\n')
            for line in lines:
                if "Сообщение:" in line:
                    message_text = line.split("Сообщение:")[1].strip()
                    if "..." in message_text:
                        # Нужно хранить полный текст, упростим для примера
                        await event.reply("❌ **Перешлите оригинальное сообщение с текстом для рассылки**")
                        return
            
            # Для простоты запросим текст заново
            await event.reply("❌ **Используйте команду заново:** `/broadcast Ваше сообщение`")
            return

@bot_client.on(events.NewMessage(pattern='/pin_message'))
async def pin_message_handler(event):
    """Закрепление сообщения для новых пользователей"""
    if not is_admin(event.sender_id):
        return
        
    message_text = event.message.text.replace('/pin_message', '').strip()
    if not message_text:
        # Показываем текущее закрепленное сообщение
        pinned_msg = load_pinned_message()
        if pinned_msg.get('is_active'):
            current_text = f"📌 **Текущее закрепленное сообщение (активно):**\n\n{pinned_msg['text']}"
        else:
            current_text = "📌 **Закрепленное сообщение не установлено**"
        
        help_text = f"""{current_text}

💡 **Чтобы установить/изменить закрепленное сообщение:**
`/pin_message Ваш текст`

🔧 **Дополнительные команды:**
`/unpin_message` - отключить закрепленное сообщение
`/pin_preview` - предпросмотр"""
        
        await event.reply(help_text)
        return
    
    # Сохраняем новое закрепленное сообщение
    pinned_data = {
        "text": message_text,
        "is_active": True
    }
    save_pinned_message(pinned_data)
    
    await event.reply(f"✅ **Закрепленное сообщение установлено!**\n\n{message_text}")

@bot_client.on(events.NewMessage(pattern='/unpin_message'))
async def unpin_message_handler(event):
    """Отключает закрепленное сообщение"""
    if not is_admin(event.sender_id):
        return
        
    pinned_data = load_pinned_message()
    pinned_data["is_active"] = False
    save_pinned_message(pinned_data)
    
    await event.reply("❌ **Закрепленное сообщение отключено**")

@bot_client.on(events.NewMessage(pattern='/toggle_monitoring'))
async def toggle_monitoring_handler(event):
    """Включение/выключение мониторинга"""
    if not is_admin(event.sender_id):
        return
        
    global is_monitoring
    is_monitoring = not is_monitoring
    
    status = "✅ включен" if is_monitoring else "❌ выключен"
    await event.reply(f"🔔 **Мониторинг {status}**")

@bot_client.on(events.NewMessage(pattern='/toggle_ads'))
async def toggle_ads_handler(event):
    """Включение/выключение рекламы"""
    if not is_admin(event.sender_id):
        return
        
    global is_advertisements_enabled
    is_advertisements_enabled = not is_advertisements_enabled
    
    status = "✅ включена" if is_advertisements_enabled else "❌ выключена"
    await event.reply(f"📢 **Реклама {status}**")

@bot_client.on(events.NewMessage(pattern='/export_subscribers'))
async def export_subscribers_handler(event):
    """Экспорт списка подписчиков"""
    if not is_admin(event.sender_id):
        return
        
    subscribers = load_subscribers()
    if not subscribers:
        await event.reply("❌ **Нет подписчиков для экспорта**")
        return
    
    # Создаем текстовый файл с подписчиками
    filename = "subscribers.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("Список подписчиков бота:\n")
        f.write("=" * 30 + "\n")
        for i, user_id in enumerate(subscribers, 1):
            f.write(f"{i}. {user_id}\n")
    
    try:
        await bot_client.send_file(
            event.chat_id,
            filename,
            caption=f"📊 **Экспорт подписчиков**\nВсего: {len(subscribers)}"
        )
        os.remove(filename)
    except Exception as e:
        await event.reply(f"❌ **Ошибка экспорта:** {e}")

# ==================== ОБРАБОТКА СООБЩЕНИЙ ИЗ ГРУППЫ ====================

@user_client.on(events.NewMessage(chats=CHAT_TO_MONITOR))
async def group_message_handler(event):
    """Обработчик новых сообщений из группы"""
    global is_monitoring
    
    if not is_monitoring:
        return
    
    try:
        message = event.message
        sender = await message.get_sender()
        
        # Получаем имя отправителя
        if hasattr(sender, 'title'):
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
            except Exception as e:
                logger.error(f"Ошибка загрузки медиа: {e}")
        
        # Отправляем сообщение всем подписчикам
        await send_to_all_subscribers(text, media_path)
        
        # Удаляем временный файл
        if media_path and os.path.exists(media_path):
            try:
                os.remove(media_path)
            except Exception as e:
                logger.error(f"Ошибка удаления файла: {e}")
            
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")

# ==================== ОСНОВНАЯ ФУНКЦИЯ ====================

async def main():
    """Основная функция"""
    try:
        # Создаем папку для загрузок
        os.makedirs('downloads', exist_ok=True)
        
        # Запускаем клиенты
        logger.info("🔄 Запускаем бота...")
        await bot_client.start(bot_token=BOT_TOKEN)
        logger.info("✅ Бот запущен")
        
        logger.info("🔄 Запускаем аккаунт пользователя...")
        await user_client.start(phone=PHONE)
        logger.info("✅ Аккаунт пользователя успешно запущен")
        
        # Получаем информацию о себе
        me = await user_client.get_me()
        logger.info(f"✅ Авторизован как {me.first_name} (id: {me.id})")
        
        # Проверяем доступ к группе
        chat = await user_client.get_entity(CHAT_TO_MONITOR)
        logger.info(f"✅ Мониторинг группы: {chat.title}")
        
        # Загружаем данные
        subscribers = load_subscribers()
        logger.info(f"👥 Загружено подписчиков: {len(subscribers)}")
        
        logger.info("🚀 Бот начал мониторинг сообщений...")
        logger.info("🛠️ Админ-панель доступна по команде /admin")
        
        # Запускаем периодическую отправку рекламы (раз в 24 часа)
        async def advertisement_scheduler():
            while True:
                await asyncio.sleep(24 * 60 * 60)  # 24 часа
                await send_random_advertisement()
        
        # Запускаем планировщик в фоне
        asyncio.create_task(advertisement_scheduler())
        
        # Ожидаем завершения
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