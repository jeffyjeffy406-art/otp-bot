import os, re, httpx
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

BOT_TOKEN = os.getenv("BOT_TOKEN")
SMS_API_KEY = os.getenv("SMS_API_KEY")
SMS_API_SECRET = os.getenv("SMS_API_SECRET")
MY_NUMBER = os.getenv("MY_NUMBER")  # Your bought virtual number

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()

@dp.message(Command("get_otp"))
async def get_otp(msg: types.Message):
    parts = msg.text.split()
    phone = parts[1] if len(parts) > 1 else None
    if not phone:
        await msg.answer("Usage: /get_otp +1234567890")
        return

    # Send OTP request to your SMS provider (Telnyx example)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.telnyx.com/v2/messages",
            headers={"Authorization": f"Bearer {SMS_API_KEY}:{SMS_API_SECRET}"},
            json={
                "from": MY_NUMBER,
                "to": phone,
                "text": "Your verification code is 123456"
            }
        )
    await msg.answer(f"✅ OTP sent to {phone}. Reply with the code when it arrives.")

@app.post("/sms-webhook")
async def webhook(request: Request):
    data = await request.json()
    body = data.get("body", "")
    otp_match = re.search(r'\b\d{4,6}\b', body)
    if otp_match and 'otp' in body.lower():
        code = otp_match.group()
        # In a real app, you'd map the incoming number to the user's chat ID.
        # For now, it replies to everyone who uses /get_otp:
        await bot.send_message(chat_id="ALLUSERS", text=f"📩 OTP received for {MY_NUMBER}: `{code}`")
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
