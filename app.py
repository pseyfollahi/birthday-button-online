
import json
import os

from flask import Flask, render_template, send_from_directory, request, jsonify
from flask_socketio import SocketIO
from pywebpush import webpush, WebPushException
from supabase import create_client, Client


app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"


socketio = SocketIO(
    app,
    cors_allowed_origins="*"
)


# ---------------------------------
# VAPID
# ---------------------------------

VAPID_PRIVATE_KEY = "/etc/secrets/vapid_private.pem"

VAPID_CLAIMS = {
    "sub": "mailto:pseyfollahi@gmail.com"
}


# ---------------------------------
# Supabase
# ---------------------------------

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get(
    "SUPABASE_SERVICE_ROLE_KEY"
)

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY
)


# ---------------------------------
# Pages
# ---------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/receiver")
def receiver():
    return render_template("receiver.html")


@app.route("/sw.js")
def service_worker():
    return send_from_directory(".", "sw.js")


# ---------------------------------
# Save Subscription
# ---------------------------------

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

    endpoint = subscription.get("endpoint")

    if not endpoint:

        return jsonify({
            "success": False,
            "message": "Endpoint وجود ندارد"
        }), 400

    try:

        # Check if subscription already exists

        existing = (
            supabase
            .table("subscriptions")
            .select("id")
            .eq("endpoint", endpoint)
            .execute()
        )

        if existing.data:

            print("Subscription already exists.")

            # Update subscription in case
            # browser refreshed its keys

            (
                supabase
                .table("subscriptions")
                .update({
                    "subscription": subscription
                })
                .eq("endpoint", endpoint)
                .execute()
            )

            return jsonify({
                "success": True,
                "message": "Subscription already exists"
            })

        # Insert new subscription

        (
            supabase
            .table("subscriptions")
            .insert({
                "endpoint": endpoint,
                "subscription": subscription
            })
            .execute()
        )

        print("Subscription saved to Supabase.")

        return jsonify({
            "success": True
        })

    except Exception as error:

        print("SUPABASE ERROR:")
        print(error)

        return jsonify({
            "success": False,
            "message": "خطا در ذخیره Subscription"
        }), 500


# ---------------------------------
# Button
# ---------------------------------

@socketio.on("button_pressed")
def button_pressed():

    message = {
        "text": "بیا بازی 🎮"
    }

    # Send message to currently connected pages

    socketio.emit(
        "birthday_message",
        message
    )

    push_data = json.dumps({
        "title": "پیام جدید 🎮",
        "body": "بیا بازی 🎮"
    })

    print("================================")
    print("SENDING PUSH NOTIFICATION")
    print("================================")

    try:

        # Get all subscriptions from Supabase

        result = (
            supabase
            .table("subscriptions")
            .select("id, subscription")
            .execute()
        )

        subscriptions = result.data or []

        print(
            "Subscriptions:",
            len(subscriptions)
        )

        # Send Push to every subscription

        for row in subscriptions:

            subscription = row["subscription"]

            try:

                webpush(
                    subscription_info=subscription,
                    data=push_data,
                    vapid_private_key=VAPID_PRIVATE_KEY,
                    vapid_claims=VAPID_CLAIMS
                )

                print(
                    "Push notification sent successfully."
                )

            except WebPushException as error:

                print("PUSH ERROR:")
                print(error)

    except Exception as error:

        print("SUPABASE ERROR:")
        print(error)


# ---------------------------------
# Start server
# ---------------------------------

if __name__ == "__main__":

    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        allow_unsafe_werkzeug=True
    )
