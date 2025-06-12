from flask import Flask, render_template, request, jsonify
from hardware.led_button_fsm import FSMState

app = Flask(__name__)

# Stato globale per demo
current_state = FSMState.BOOTING.name

@app.route("/")
def index():
    return render_template("fsm_demo.html", state=current_state)

@app.route("/set_state", methods=["POST"])
def set_state():
    global current_state
    new_state = request.json.get("state")
    current_state = new_state
    return jsonify(success=True)

@app.route("/get_state")
def get_state():
    return jsonify(state=current_state)

if __name__ == "__main__":
    app.run(debug=True)