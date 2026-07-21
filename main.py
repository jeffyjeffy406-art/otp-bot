import os, re, httpx, asyncio, json
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
    print(f"User {msg.from_user.id} started bot")
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
                auth=(SMS_API_KEY, ""),
                json={
                    "from": MY_NUMBER,
                    "to": phone,
                    "text": "Your verification code is 123456"
                }
            )
            print(f"Telnyx response: {resp.status_code}")
            print(f"Telnyx body: {resp.text}")
        await msg.answer(f"✅ OTP sent to {phone}. Waiting for reply...")
    except Exception as e:
        print(f"Error: {e}")
        await msg.answer(f"❌ Error sending OTP: {str(e)}")

polling_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global polling_task
    # Start polling when app starts
    print("Starting bot polling...")
    polling_task = asyncio.create_task(dp.start_polling(bot))
    yield
    # Stop polling when app stops
    print("Stopping bot polling...")
    polling_task.cancel()
    try:
        await polling_task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

@app.post("/sms-webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        print(f"Webhook received: {json.dumps(data, indent=2)}")
        
        # Handle different Telnyx payload formats
        body = data.get("body") or data.get("text") or data.get("data", {}).get("body") or ""
        from_number = data.get("from") or data.get("source_number") or data.get("data", {}).get("from") or ""
        
        print(f"Extracted - Body: {body}, From: {from_number}")
        
        # Extract OTP from message
        otp_match = re.search(r'\b\d{4,6}\b', body)
        
        if otp_match:
            code = otp_match.group()
            print(f"OTP found: {code}")
            print(f"Stored user chat IDs: {user_chat_ids}")
            # Send to all connected users
            for user_id, chat_id in user_chat_ids.items():
                try:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"📩 OTP received from {from_number}:\n\n`{code}`",
                        parse_mode="Markdown"
                    )
                    print(f"Message sent to user {user_id}")
                except Exception as e:
                    print(f"Failed to send to {user_id}: {e}")
        else:
            print("No OTP pattern found in message")
        
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
