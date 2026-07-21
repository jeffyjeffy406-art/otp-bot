import os, re, httpx, asyncio
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from contextlib import asynccontextmanager

BOT_TOKEN = os.getenv("BOT_TOKEN")
SMS_API_KEY = os.getenv("SMS_API_KEY")
MY_NUMBER = os.getenv("MY_NUMBER")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Store user chat IDs for webhook replies
user_chat_ids = {}

@dp.message(Command("start"))
async def start(msg: types.Message):
    user_chat_ids[msg.from_user.id] = msg.chat.id
    await msg.answer("🤖 OTP Bot started! Use /get_otp +1234567890 to request an OTP.")

@dp.message(Command("get_otp"))
async def get_otp(msg: types.Message):
    user_chat_ids[msg.from_user.id] = msg.chat.id
    parts = msg.text.split()
    phone = parts[1] if len(parts) > 1 else None
    if not phone:
        await msg.answer("Usage: /get_otp +1234567890")
        return

    try:
        # Send OTP request to Telnyx
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.telnyx.com/v2/messages",
                headers={"Authorization": f"Bearer {SMS_API_KEY}"},
                json={
                    "from": MY_NUMBER,
                    "to": phone,
                    "text": "Your verification code is 123456"
                }
            )
        await msg.answer(f"✅ OTP sent to {phone}. Waiting for reply...")
    except Exception as e:
        await msg.answer(f"❌ Error sending OTP: {str(e)}")

app = FastAPI()

@app.post("/sms-webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        body = data.get("body", "")
        from_number = data.get("from", "")
        
        # Extract OTP from message
        otp_match = re.search(r'\b\d{4,6}\b', body)
        
        if otp_match:
            code = otp_match.group()
            # Send to all connected users
            for user_id, chat_id in user_chat_ids.items():
                try:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"📩 OTP received from {from_number}:\n\n`{code}`",
                        parse_mode="Markdown"
                    )
                except:
                    pass
        
        return {"status": "ok"}
    except Exception as e:
        print(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

# Polling task
async def polling_task():
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"Polling error: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start polling when app starts
    task = asyncio.create_task(polling_task())
    yield
    # Stop polling when app stops
    task.cancel()

app = FastAPI(lifespan=lifespan)

@app.post("/sms-webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        body = data.get("body", "")
        from_number = data.get("from", "")
        
        # Extract OTP from message
        otp_match = re.search(r'\b\d{4,6}\b', body)
        
        if otp_match:
            code = otp_match.group()
            # Send to all connected users
            for user_id, chat_id in user_chat_ids.items():
                try:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"📩 OTP received from {from_number}:\n\n`{code}`",
                        parse_mode="Markdown"
                    )
                except:
                    pass
        
        return {"status": "ok"}
    except Exception as e:
        print(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
