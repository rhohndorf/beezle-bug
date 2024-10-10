from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "mysecret"
socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")


# Serve the HTML client
@app.route("/")
def index():
    return render_template("index.html")


# Handle WebSocket connection
@socketio.on("connect")
def handle_connect():
    print("A user connected.")


# Handle new messages from clients
@socketio.on("send_message")
def handle_message(data):
    print(f"Received message: {data}")
    # Store the message in memory
    # Broadcast message to all connected clients
    emit("chat_message", data, broadcast=True)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
