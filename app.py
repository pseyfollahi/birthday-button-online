
import json
import os
import traceback
from urllib.parse import urlparse

from flask import Flask, render_template, send_from_directory, request, jsonify
from flask_socketio import SocketIO
from pywebpush import webpush, WebPushException
from supabase import create_client, Client


# =========================================================
# FLASK
# =========================================================

app = Flask(__name__)

app.config["SECRET_KEY"] = "secret"

socketio = SocketIO(
    app,
    cors_allowed_origins="*"
)


# =========================================================
# VAPID
# =========================================================

VAPID_PRIVATE_KEY = "/etc/secrets/vapid_private.pem"

VAPID_SUBJECT = "mailto:pseyfollahi@gmail.com"


# =========================================================
# SUPABASE
# =========================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL")

SUPABASE_SERVICE_ROLE_KEY = os.environ.get(
    "SUPABASE_SERVICE_ROLE_KEY"
)


print("================================")
print("SUPABASE CONFIG CHECK")
print("================================")

print(
    "SUPABASE_URL exists:",
    bool(SUPABASE_URL)
)

print(
    "SUPABASE_SERVICE_ROLE_KEY exists:",
    bool(SUPABASE_SERVICE_ROLE_KEY)
)

print("================================")


if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:

    raise RuntimeError(
        "Supabase environment variables are missing."
    )


supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY
)


# =========================================================
# PAGES
# =========================================================

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


@app.route("/receiver")
def receiver():

    return render_template(
        "receiver.html"
    )


@app.route("/sw.js")
def service_worker():

    return send_from_directory(
        ".",
        "sw.js"
    )


# =========================================================
# SAVE PUSH SUBSCRIPTION
# =========================================================

@app.route(
    "/subscribe",
    methods=["POST"]
)
def subscribe():

    subscription = request.get_json()

    print()
    print("================================")
    print("NEW PUSH SUBSCRIPTION RECEIVED")
    print("================================")

    if not subscription:

        print(
            "ERROR: Empty subscription"
        )

        return jsonify({
            "success": False,
            "message": "Subscription دریافت نشد"
        }), 400

    endpoint = subscription.get(
        "endpoint"
    )

    if not endpoint:

        print(
            "ERROR: Endpoint missing"
        )

        return jsonify({
            "success": False,
            "message": "Endpoint وجود ندارد"
        }), 400

    try:

        print(
            "Endpoint:",
            endpoint
        )

        # ---------------------------------------------
        # Check whether this device already exists
        # ---------------------------------------------

        existing = (
            supabase
            .table("subscriptions")
            .select("id")
            .eq(
                "endpoint",
                endpoint
            )
            .execute()
        )

        print(
            "Existing subscription:",
            existing.data
        )

        # ---------------------------------------------
        # Update existing subscription
        # ---------------------------------------------

        if existing.data:

            subscription_id = (
                existing.data[0]["id"]
            )

            (
                supabase
                .table("subscriptions")
                .update({
                    "subscription": subscription
                })
                .eq(
                    "id",
                    subscription_id
                )
                .execute()
            )

            print(
                "Subscription updated:",
                subscription_id
            )

            return jsonify({
                "success": True,
                "message": "Subscription updated"
            })

        # ---------------------------------------------
        # Save new subscription
        # ---------------------------------------------

        result = (
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

        print(
            "Inserted:",
            result.data
        )

        return jsonify({
            "success": True,
            "message": "Subscription saved"
        })

    except Exception as error:

        print()
        print("================================")
        print("SUPABASE ERROR WHILE SAVING")
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


# =========================================================
# SEND PUSH NOTIFICATIONS
# =========================================================

@socketio.on("button_pressed")
def button_pressed():

    print()
    print("================================")
    print("BUTTON PRESSED EVENT RECEIVED")
    print("================================")

    # =====================================================
    # MESSAGE FOR OPEN PAGES
    # =====================================================

    message = {
        "text": "بیا بازی 🎮"
    }

    socketio.emit(
        "birthday_message",
        message
    )

    print(
        "Socket message sent to currently connected pages."
    )

    # =====================================================
    # PUSH DATA
    # =====================================================

    push_data = json.dumps({

        "title": "پیام جدید 🎮",

        "body": "بیا بازی 🎮"

    })

    print()
    print("================================")
    print("STARTING PUSH NOTIFICATIONS")
    print("================================")

    try:

        # =================================================
        # GET ALL SUBSCRIPTIONS
        # =================================================

        result = (
            supabase
            .table("subscriptions")
            .select(
                "id, endpoint, subscription"
            )
            .execute()
        )

        subscriptions = (
            result.data or []
        )

        total = len(
            subscriptions
        )

        print(
            "Total subscriptions:",
            total
        )

        if total == 0:

            print(
                "NO SUBSCRIPTIONS FOUND."
            )

            return

        successful = 0
        failed = 0
        deleted = 0

        # =================================================
        # SEND TO EVERY DEVICE
        # =================================================

        for row in subscriptions:

            subscription_id = row.get(
                "id"
            )

            endpoint = row.get(
                "endpoint"
            )

            subscription = row.get(
                "subscription"
            )

            print()
            print("--------------------------------")
            print(
                "Processing subscription:",
                subscription_id
            )

            # -------------------------------------------------
            # Validate subscription
            # -------------------------------------------------

            if not subscription:

                print(
                    "SKIPPED: subscription data is empty."
                )

                failed += 1

                continue

            if not endpoint:

                print(
                    "SKIPPED: endpoint is empty."
                )

                failed += 1

                continue

            try:

                # =================================================
                # GET PUSH SERVICE ORIGIN
                # =================================================

                parsed_url = urlparse(
                    endpoint
                )

                push_origin = (
                    f"{parsed_url.scheme}://"
                    f"{parsed_url.netloc}"
                )

                print(
                    "Push origin:",
                    push_origin
                )

                # =================================================
                # VAPID CLAIMS
                # =================================================

                vapid_claims = {

                    "sub": VAPID_SUBJECT,

                    "aud": push_origin

                }

                print(
                    "Sending push..."
                )

                # =================================================
                # SEND PUSH
                # =================================================

                webpush(

                    subscription_info=subscription,

                    data=push_data,

                    vapid_private_key=VAPID_PRIVATE_KEY,

                    vapid_claims=vapid_claims

                )

                successful += 1

                print(
                    "PUSH SENT SUCCESSFULLY:",
                    subscription_id
                )

            except WebPushException as error:

                failed += 1

                print()
                print(
                    "PUSH ERROR:"
                )

                print(
                    "Subscription ID:",
                    subscription_id
                )

                print(
                    repr(error)
                )

                traceback.print_exc()

                # =================================================
                # DELETE DEAD SUBSCRIPTIONS
                # =================================================

                error_text = str(
                    error
                )

                if (
                    "404" in error_text
                    or
                    "410" in error_text
                ):

                    try:

                        (
                            supabase
                            .table("subscriptions")
                            .delete()
                            .eq(
                                "id",
                                subscription_id
                            )
                            .execute()
                        )

                        deleted += 1

                        print(
                            "Deleted expired subscription:",
                            subscription_id
                        )

                    except Exception as delete_error:

                        print(
                            "Could not delete expired subscription:"
                        )

                        print(
                            repr(delete_error)
                        )

            except Exception as error:

                failed += 1

                print()
                print(
                    "GENERAL PUSH ERROR:"
                )

                print(
                    "Subscription ID:",
                    subscription_id
                )

                print(
                    repr(error)
                )

                traceback.print_exc()

        # =====================================================
        # FINAL RESULT
        # =====================================================

        print()
        print("================================")
        print("PUSH PROCESS FINISHED")
        print("================================")

        print(
            "Total subscriptions:",
            total
        )

        print(
            "Successful:",
            successful
        )

        print(
            "Failed:",
            failed
        )

        print(
            "Deleted expired:",
            deleted
        )

        print("================================")

    except Exception as error:

        print()
        print("================================")
        print("SUPABASE ERROR WHILE SENDING")
        print("================================")

        print(
            repr(error)
        )

        traceback.print_exc()

        print("================================")


# =========================================================
# SOCKET CONNECTION LOG
# =========================================================

@socketio.on("connect")
def handle_connect():

    print(
        "Socket.IO client connected."
    )


@socketio.on("disconnect")
def handle_disconnect():

    print(
        "Socket.IO client disconnected."
    )


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    socketio.run(

        app,

        host="0.0.0.0",

        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),

        allow_unsafe_werkzeug=True

    )
