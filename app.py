
import json
import os
import traceback
from urllib.parse import urlparse

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

VAPID_SUBJECT = "mailto:pseyfollahi@gmail.com"


# ---------------------------------
# Supabase
# ---------------------------------

SUPABASE_URL = os.environ.get("SUPABASE_URL")

SUPABASE_SERVICE_ROLE_KEY = os.environ.get(
    "SUPABASE_SERVICE_ROLE_KEY"
)


print("================================")
print("SUPABASE CONFIG CHECK")
print(
    "SUPABASE_URL exists:",
    bool(SUPABASE_URL)
)
print(
    "SUPABASE_SERVICE_ROLE_KEY exists:",
    bool(SUPABASE_SERVICE_ROLE_KEY)
)
print("================================")


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
# Save Push Subscription
# ---------------------------------

@app.route("/subscribe", methods=["POST"])
def subscribe():

    subscription = request.get_json()

    print("================================")
    print("NEW PUSH SUBSCRIPTION RECEIVED")
    print("================================")

    try:

        print(
            json.dumps(
                subscription,
                indent=2,
                ensure_ascii=False
            )
        )

    except Exception:

        print(subscription)

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

        print("Checking Supabase...")

        existing = (
            supabase
            .table("subscriptions")
            .select("id")
            .eq("endpoint", endpoint)
            .execute()
        )

        print(
            "Existing:",
            existing.data
        )

        if existing.data:

            (
                supabase
                .table("subscriptions")
                .update({
                    "subscription": subscription
                })
                .eq("endpoint", endpoint)
                .execute()
            )

            print(
                "Subscription updated."
            )

            return jsonify({
                "success": True,
                "message": "Subscription updated"
            })

        (
            supabase
            .table("subscriptions")
            .insert({
                "endpoint": endpoint,
                "subscription": subscription
            })
            .execute()
        )

        print(
            "Subscription saved successfully."
        )

        return jsonify({
            "success": True
        })

    except Exception as error:

        print("================================")
        print("SUPABASE ERROR")
        print("================================")

        print(
            repr(error)
        )

        traceback.print_exc()

        print("================================")

        return jsonify({
            "success": False,
            "message": "خطا در ذخیره Subscription"
        }), 500


# ---------------------------------
# Send Push Notifications
# ---------------------------------

@socketio.on("button_pressed")
def button_pressed():

    message = {
        "text": "بیا بازی 🎮"
    }

    # ---------------------------------
    # Send to currently open pages
    # ---------------------------------

    socketio.emit(
        "birthday_message",
        message
    )

    # ---------------------------------
    # Push notification data
    # ---------------------------------

    push_data = json.dumps({

        "title": "پیام جدید 🎮",

        "body": "بیا بازی 🎮"

    })

    print("================================")
    print("STARTING PUSH NOTIFICATIONS")
    print("================================")

    try:

        result = (
            supabase
            .table("subscriptions")
            .select("id, endpoint, subscription")
            .execute()
        )

        subscriptions = result.data or []

        print(
            "Total subscriptions:",
            len(subscriptions)
        )

        # ---------------------------------
        # Send to every device
        # ---------------------------------

        for row in subscriptions:

            subscription = row.get(
                "subscription"
            )

            endpoint = row.get(
                "endpoint"
            )

            if not subscription:

                print(
                    "Empty subscription:",
                    row.get("id")
                )

                continue

            if not endpoint:

                print(
                    "Empty endpoint:",
                    row.get("id")
                )

                continue

            try:

                # ---------------------------------
                # Get push service origin
                # ---------------------------------

                parsed_url = urlparse(
                    endpoint
                )

                push_origin = (
                    f"{parsed_url.scheme}://"
                    f"{parsed_url.netloc}"
                )

                print("--------------------------------")
                print(
                    "Sending notification to:",
                    row.get("id")
                )
                print(
                    "Push origin:",
                    push_origin
                )

                # ---------------------------------
                # VAPID claims for THIS device
                # ---------------------------------

                vapid_claims = {

                    "sub": VAPID_SUBJECT,

                    "aud": push_origin

                }

                # ---------------------------------
                # Send notification
                # ---------------------------------

                webpush(

                    subscription_info=subscription,

                    data=push_data,

                    vapid_private_key=VAPID_PRIVATE_KEY,

                    vapid_claims=vapid_claims

                )

                print(
                    "Push sent successfully:",
                    row.get("id")
                )

            except WebPushException as error:

                print("--------------------------------")
                print(
                    "PUSH ERROR for subscription:",
                    row.get("id")
                )
                print(
                    repr(error)
                )

                traceback.print_exc()

                print("--------------------------------")

            except Exception as error:

                print("--------------------------------")
                print(
                    "GENERAL PUSH ERROR for subscription:",
                    row.get("id")
                )
                print(
                    repr(error)
                )

                traceback.print_exc()

                print("--------------------------------")

    except Exception as error:

        print("================================")
        print(
            "SUPABASE ERROR WHILE SENDING"
        )
        print("================================")

        print(
            repr(error)
        )

        traceback.print_exc()

        print("================================")


# ---------------------------------
# Start Server
# ---------------------------------

if __name__ == "__main__":

    socketio.run(

        app,

        host="0.0.0.0",

        port=5000,

        allow_unsafe_werkzeug=True

    )
