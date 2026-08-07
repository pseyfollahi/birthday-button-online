from flask import Flask, render_template
from flask_socketio import SocketIO

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"

socketio = SocketIO(app, cors_allowed_origins="*")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/receiver")
def receiver():
    return render_template("receiver.html")


@socketio.on("button_pressed")
def button_pressed():
    socketio.emit("birthday_message", {
        "text": "🎉 تولدت مبارک 🎂"
    })


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
