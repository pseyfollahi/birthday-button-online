import json
import os

from flask import Flask, render_template, send_from_directory, request, jsonify
from flask_socketio import SocketIO
from pywebpush import webpush, WebPushException


app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"

socketio = SocketIO(
    app,
    cors_allowed_origins="*"
)


VAPID_PRIVATE_KEY = "/etc/secrets/vapid_private.pem"

VAPID_CLAIMS = {
    "sub": "mailto:pseyfollahi@gmail.com"
}


subscriptions = []


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/receiver")
def receiver():
    return render_template("receiver.html")


@app.route("/sw.js")
def service_worker():
    return send_from_directory(".", "sw.js")


@app.route("/subscribe", methods=["POST"])
def subscribe():

    subscription = request.get_json()

    print("================================")
    print("NEW PUSH SUBSCRIPTION RECEIVED")
    print(json.dumps(subscription, indent=2))
    print("================================")

    if not subscription:
        return jsonify({
            "success": False,
            "message": "Subscription دریافت نشد"
        }), 400

    # جلوگیری از ثبت تکراری
    endpoint = subscription.get("endpoint")

    for old_subscription in subscriptions:
        if old_subscription.get("endpoint") == endpoint:
            print("Subscription already exists.")
            return jsonify({
                "success": True
            })

    subscriptions.append(subscription)

    print("Subscription saved successfully.")
    print("Total subscriptions:", len(subscriptions))

    return jsonify({
        "success": True
    })


@socketio.on("button_pressed")
def button_pressed():

    message = {
        "text": "بیا بازی 🎮"
    }

    # نمایش داخل صفحه Receiver
    socketio.emit(
        "birthday_message",
        message
    )

    # Push Notification
    push_data = json.dumps({
        "title": "پیام جدید 🎮",
        "body": "بیا بازی 🎮"
    })

    print("================================")
    print("SENDING PUSH NOTIFICATION")
    print("Subscriptions:", len(subscriptions))
    print("================================")

    for subscription in subscriptions:

        try:

            webpush(
                subscription_info=subscription,
                data=push_data,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS
            )

            print("Push notification sent successfully.")

        except WebPushException as error:

            print("PUSH ERROR:")
            print(error)


if __name__ == "__main__":

    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        allow_unsafe_werkzeug=True
    )
