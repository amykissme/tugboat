"""
Пример бота для мини-приложения знакомств.
Запуск:  pip install -r requirements.txt
         BOT_TOKEN=123:ABC WEBAPP_URL=https://ваш-логин.github.io/репозиторий/ python bot.py
"""
import json
import os

from telegram import (
    KeyboardButton, LabeledPrice, ReplyKeyboardMarkup, Update, WebAppInfo,
    InlineKeyboardButton, InlineKeyboardMarkup,
)
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler,
    PreCheckoutQueryHandler, filters,
)

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBAPP_URL = os.environ["WEBAPP_URL"].rstrip("/") + "/"
PROFILES_FILE = "profiles.json"

PLANS = {
    "premium": {"title": "Premium", "stars": 299},
    "vip": {"title": "VIP", "stars": 599},
}


def load_profiles() -> dict:
    if os.path.exists(PROFILES_FILE):
        with open(PROFILES_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_profiles(data: dict) -> None:
    with open(PROFILES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # sendData() работает только при открытии через кнопку клавиатуры
    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("Открыть приложение", web_app=WebAppInfo(url=WEBAPP_URL))]],
        resize_keyboard=True,
    )
    await update.message.reply_text("Добро пожаловать. Нажмите кнопку ниже.", reply_markup=kb)


async def on_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    try:
        data = json.loads(msg.web_app_data.data)
    except json.JSONDecodeError:
        return

    if data.get("type") == "profile":
        profiles = load_profiles()
        profiles[str(update.effective_user.id)] = {
            "username": update.effective_user.username,
            "name": str(data.get("name", ""))[:30],
            "age": int(data.get("age", 0)),
            "gender": data.get("gender"),
            "city": str(data.get("city", ""))[:40],
            "about": str(data.get("about", ""))[:300],
        }
        save_profiles(profiles)
        await msg.reply_text("Анкета отправлена.")

    elif data.get("type") == "subscribe":
        plan = PLANS.get(data.get("plan"))
        if not plan:
            return
        await context.bot.send_invoice(
            chat_id=update.effective_chat.id,
            title=f"Подписка {plan['title']}",
            description="Доступ на 30 дней",
            payload=f"sub:{data['plan']}",
            provider_token="",          # для Telegram Stars токен пустой
            currency="XTR",
            prices=[LabeledPrice(plan["title"], plan["stars"])],
        )


async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)


async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payload = update.message.successful_payment.invoice_payload  # "sub:premium"
    plan = payload.split(":", 1)[1]
    # TODO: сохраните подписку в своей БД с датой окончания
    # Открываем приложение с параметром — оно активирует тариф
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(
        "Открыть приложение",
        web_app=WebAppInfo(url=f"{WEBAPP_URL}?plan={plan}"),
    )]])
    await update.message.reply_text("Оплата прошла. Подписка активирована.", reply_markup=kb)


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, on_webapp_data))
    app.add_handler(PreCheckoutQueryHandler(precheckout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, paid))
    app.run_polling()


if __name__ == "__main__":
    main()
