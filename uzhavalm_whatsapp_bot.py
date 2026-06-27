"""
UZHAVALM WHATSAPP BOT
======================
Handles: Welcome -> Plan selection -> Family size -> Price -> Payment -> FAQ
Tech: Flask + WhatsApp Cloud API (Meta) + Google Sheets (optional)

SETUP STEPS:
1. Create Meta Business account -> business.facebook.com
2. Go to developers.facebook.com -> Create App -> Add WhatsApp product
3. Get: ACCESS_TOKEN, PHONE_NUMBER_ID, VERIFY_TOKEN (you choose this)
4. Deploy this file on Railway.app (free tier)
5. Set Webhook URL in Meta dashboard to: https://your-app.up.railway.app/webhook
6. Set Verify Token in Meta dashboard to match VERIFY_TOKEN below

Run locally to test: python app.py
"""

from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# ── CONFIG (fill these in / use environment variables on Railway) ──
ACCESS_TOKEN = os.environ.get("WHATSAPP_TOKEN", "PUT_YOUR_TOKEN_HERE")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "PUT_YOUR_PHONE_ID_HERE")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "uzhavalm2026")
ADMIN_PHONE = os.environ.get("ADMIN_PHONE", "91XXXXXXXXXX")  # your number, no +
GPAY_NUMBER = "9XXXXXXXXX"

WHATSAPP_API_URL = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"

# Stores each customer's current step in conversation (in-memory; resets on restart)
user_state = {}

PRICES = {
    "1": {"label": "1 Person", "1day": 449, "3day": 1199},
    "2": {"label": "2 Person", "1day": 699, "3day": 1999},
    "3": {"label": "4 Person", "1day": 1299, "3day": 3499},
    "4": {"label": "5 Person", "1day": 1499, "3day": 4299},
}

MONDAY_BOX = "Drumstick, Beans, Potato, Seerukeerai, Snake Gourd"
WEDNESDAY_BOX = "Ladies Finger, Carrot, Raw Banana, Spinach, Cluster Beans"
FRIDAY_BOX = "Brinjal, Cabbage, Beetroot, Ridge Gourd, Radish"

FAQ = {
    "veggies": (
        "🌿 We provide *32+ varieties* of fresh vegetables sourced daily from "
        "Attur farmers! Every box has 5 different vegetables, rotated weekly "
        "so you never get the same box twice. Seasonal specials added too!"
    ),
    "fresh": (
        "🚛 We pick up from Attur market at 6:30 AM and deliver to your door "
        "by 10 AM the same day — zero cold storage!"
    ),
    "payment": (
        f"💳 Pay via GPay to *{GPAY_NUMBER}* — full month advance. "
        "Delivery starts only after payment confirmation."
    ),
    "delivery": (
        "📅 Boxes delivered Monday, Wednesday, Friday between 8–10 AM. "
        "We'll WhatsApp you the night before with tomorrow's vegetable list!"
    ),
    "cancel": (
        "😔 Sorry to hear that! Reply *CANCEL* with your registered number "
        "and we'll process it within 24 hours. No questions asked."
    ),
}

# ── Helper: send a WhatsApp text message ──
def send_message(to, text):
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    requests.post(WHATSAPP_API_URL, headers=headers, json=payload)


def notify_admin(text):
    send_message(ADMIN_PHONE, f"🔔 New Uzhavalm order:\n{text}")


# ── Main conversation logic ──
def handle_message(sender, text):
    text = text.strip().lower()
    state = user_state.get(sender, {"step": "start"})

    # FAQ keywords work at any time
    if "veg" in text or "vegetable" in text:
        send_message(sender, FAQ["veggies"]); return
    if "fresh" in text:
        send_message(sender, FAQ["fresh"]); return
    if "pay" in text or "gpay" in text:
        send_message(sender, FAQ["payment"]); return
    if "deliver" in text or "time" in text:
        send_message(sender, FAQ["delivery"]); return
    if "cancel" in text:
        send_message(sender, FAQ["cancel"]); return
    if "box" in text and ("monday" in text or "mon" in text):
        send_message(sender, f"📦 Monday Box: {MONDAY_BOX}"); return
    if "box" in text and ("wednesday" in text or "wed" in text):
        send_message(sender, f"📦 Wednesday Box: {WEDNESDAY_BOX}"); return
    if "box" in text and ("friday" in text or "fri" in text):
        send_message(sender, f"📦 Friday Box: {FRIDAY_BOX}"); return

    # ── Step: start ──
    if state["step"] == "start" or "hi" in text or "hello" in text:
        send_message(sender,
            "🌾 *Welcome to Uzhavalm!* உழவளம்\n\n"
            "Fresh vegetables from Attur farmers, straight to your door 🥦\n\n"
            "Select your plan:\n"
            "1️⃣ 1 Day/Week\n"
            "2️⃣ 3 Days/Week\n\n"
            "_(You can also ask: vegetables, fresh, payment, delivery)_"
        )
        user_state[sender] = {"step": "plan"}
        return

    # ── Step: plan selection ──
    if state["step"] == "plan":
        if text in ["1", "2"]:
            plan = "1day" if text == "1" else "3day"
            user_state[sender] = {"step": "size", "plan": plan}
            send_message(sender,
                "Select your family size:\n"
                "1️⃣ 1 Person\n2️⃣ 2 Person\n3️⃣ 4 Person ⭐\n4️⃣ 5 Person"
            )
        else:
            send_message(sender, "Please reply 1️⃣ or 2️⃣ to choose your plan 🙂")
        return

    # ── Step: family size selection ──
    if state["step"] == "size":
        if text in PRICES:
            plan = state["plan"]
            info = PRICES[text]
            price = info[plan]
            plan_label = "1 Day/Week" if plan == "1day" else "3 Days/Week"
            user_state[sender] = {"step": "confirm", "plan": plan, "size": text, "price": price}
            send_message(sender,
                f"✅ *{info['label']} · {plan_label}*\n"
                f"Monthly price: ₹{price}\n\n"
                f"💳 Pay via GPay: *{GPAY_NUMBER}*\n"
                "After payment, send your *payment screenshot* here to confirm! 📲"
            )
        else:
            send_message(sender, "Please reply 1️⃣, 2️⃣, 3️⃣ or 4️⃣ to choose family size 🙂")
        return

    # ── Step: waiting for payment confirmation ──
    if state["step"] == "confirm":
        if "screenshot" in text or "paid" in text or "done" in text:
            send_message(sender,
                "🎉 Thank you! Your subscription is confirmed.\n"
                "Your first box arrives this Monday, 8–10 AM 🌿\n"
                "We'll WhatsApp you tonight with tomorrow's vegetable list!"
            )
            notify_admin(
                f"Customer: {sender}\nPlan: {state['plan']}\n"
                f"Size: {PRICES[state['size']]['label']}\nPrice: ₹{state['price']}"
            )
            user_state[sender] = {"step": "done"}
        else:
            send_message(sender, "Waiting for your payment screenshot to confirm the order 📲")
        return

    # ── Default fallback ──
    send_message(sender,
        "🌾 Type *Hi* to start a new order, or ask about: vegetables, fresh, payment, delivery"
    )


# ── Webhook verification (Meta calls this once when you set up) ──
@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge"), 200
    return "Invalid verify token", 403


# ── Webhook receiver (Meta sends incoming messages here) ──
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    try:
        entry = data["entry"][0]["changes"][0]["value"]
        if "messages" in entry:
            msg = entry["messages"][0]
            sender = msg["from"]
            text = msg["text"]["body"]
            handle_message(sender, text)
    except (KeyError, IndexError):
        pass
    return jsonify(status="ok"), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
