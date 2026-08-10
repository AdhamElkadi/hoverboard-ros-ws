#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from flask import Flask, jsonify
import threading

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>Robot Control</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
body { font-family: -apple-system, system-ui, sans-serif; background: #0a0e12; color: #00e8ff; padding: 16px; min-height: 100vh; }
h1 { font-size: 1.3rem; text-align: center; margin-bottom: 4px; }
.sub { text-align: center; color: #3a5a66; font-size: 0.8rem; margin-bottom: 14px; }
#modeBanner { text-align: center; padding: 12px; border-radius: 10px; font-weight: 700; font-size: 1rem; margin-bottom: 16px; border: 1px solid #1e3a44; transition: all 0.3s; }
#modeBanner.auto { background: #062028; color: #00e8ff; border-color: #00e8ff; }
#modeBanner.manual { background: #2a1a06; color: #ffb347; border-color: #ffb347; }
#modeBanner.paused { background: #3a0606; color: #ff6666; border-color: #ff6666; }
.label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em; color: #3a5a66; margin: 18px 0 10px; }
.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
button { background: #0a1014; border: 1px solid #1e3a44; color: #00e8ff; padding: 16px 6px; border-radius: 10px; font-size: 0.95rem; cursor: pointer; transition: all 0.1s; }
button:active { background: #0a3a4a; border-color: #00e8ff; transform: scale(0.96); }
.pad { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; max-width: 300px; margin: 0 auto; }
.pad .spacer { visibility: hidden; }
.stop { border-color: #ff6666; color: #ff6666; }
.pause-btn { display: block; width: 100%; max-width: 300px; margin: 10px auto; background: #2a0606; border-color: #ff6666; color: #ff6666; font-weight: 700; }
.pause-btn.active { background: #062a06; border-color: #00ff88; color: #00ff88; }
.auto-btn { display: block; width: 100%; max-width: 300px; margin: 14px auto 0; background: #062028; border-color: #00ff88; color: #00ff88; font-weight: 700; }
#status { text-align: center; margin-top: 16px; font-size: 0.8rem; color: #4a8a96; min-height: 1.2em; }
</style>
</head>
<body>
<h1>🤖 Robot Control</h1>
<div class="sub">Movement buttons take over from the robot's brain</div>
<div id="modeBanner" class="auto">🤖 Autonomous</div>
<button id="pauseBtn" class="pause-btn" onclick="togglePause()">⏸️ Pause Movement</button>
<div class="label">Expressions</div>
<div class="grid" id="emoGrid"></div>
<div class="label">Movement (Manual Override)</div>
<div class="pad">
<div class="spacer"></div><button onclick="move('F')">▲ Fwd</button><div class="spacer"></div>
<button onclick="move('L')">◀ Left</button><button class="stop" onclick="move('S')">■ Stop</button><button onclick="move('R')">Right ▶</button>
<div class="spacer"></div><button onclick="move('B')">▼ Back</button><div class="spacer"></div>
</div>
<button class="auto-btn" onclick="move('AUTO')">🤖 Return to Autonomous</button>
<div id="status">Ready</div>
<script>
const EMOTIONS = ['love','happy','smile','excited','laugh','kiss','wink','surprised','sad','confused','angry','sleepy','talking','neutral'];
const grid = document.getElementById('emoGrid');
const status = document.getElementById('status');
const banner = document.getElementById('modeBanner');
const pauseBtn = document.getElementById('pauseBtn');
let isPaused = false;

EMOTIONS.forEach(e => {
const b = document.createElement('button'); b.textContent = e; b.onclick = () => emotion(e); grid.appendChild(b);
});

function emotion(name) { fetch('/emotion/' + name); status.textContent = 'Expression: ' + name; }
function move(cmd) {
if (isPaused && cmd !== 'PAUSE') return; 
// ✅ HAPTIC FEEDBACK
if (navigator.vibrate) navigator.vibrate(50); 
fetch('/move/' + cmd);
status.textContent = cmd === 'AUTO' ? 'Returning to autonomous…' : 'Move: ' + cmd;
}
function togglePause() {
isPaused = !isPaused;
pauseBtn.classList.toggle('active');
pauseBtn.textContent = isPaused ? '▶️ Resume Movement' : '⏸️ Pause Movement';
fetch('/move/PAUSE');
status.textContent = isPaused ? 'Movement PAUSED' : 'Movement RESUMED';
}
window.onload = function() {
    fetch('/is_paused').then(r => r.json()).then(d => { isPaused = d.paused; updatePauseUI(); });
};
function updatePauseUI() {
    pauseBtn.classList.toggle('active', isPaused);
    pauseBtn.textContent = isPaused ? '▶️ Resume Movement' : '⏸️ Pause Movement';
}
setInterval(() => {
fetch('/mode').then(r => r.json()).then(d => {
const manual = d.mode === 'MANUAL'; const paused = d.mode === 'PAUSED';
banner.className = paused ? 'paused' : (manual ? 'manual' : 'auto');
if (paused) banner.textContent = '⏸️ PAUSED';
else banner.textContent = manual ? '🎮 Manual Control' : '🤖 Autonomous (' + d.mode + ')';
}).catch(() => {});
}, 1000);
</script>
</body>
</html>
"""

app = Flask(__name__)
node = None

@app.route('/')
def index(): return HTML_PAGE
@app.route('/is_paused')
def is_paused(): return jsonify({'paused': node.current_state == 'PAUSED' if node else False})
@app.route('/emotion/<name>')
def emotion(name):
    if node:
        msg = String(); msg.data = name; node.eilik_pub.publish(msg)
    return jsonify({'ok': True})
@app.route('/move/<cmd>')
def move(cmd):
    if node:
        msg = String(); msg.data = cmd; node.move_pub.publish(msg)
    return jsonify({'ok': True})
@app.route('/mode')
def mode(): return jsonify({'mode': node.current_state if node else 'UNKNOWN'})

def run_flask(): app.run(host='0.0.0.0', port=5000, threaded=True)

class WebController(Node):
    def __init__(self):
        super().__init__('web_controller')
        self.eilik_pub = self.create_publisher(String, '/eilik/command', 10)
        self.move_pub = self.create_publisher(String, '/app_command', 10)
        self.current_state = 'ROAMING'
        self.create_subscription(String, '/robot/state', self.state_callback, 10)
    def state_callback(self, msg): self.current_state = msg.data

def main(args=None):
    global node
    rclpy.init(args=args)
    node = WebController()
    threading.Thread(target=run_flask, daemon=True).start()
    try: rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally:
        try: node.destroy_node(); rclpy.shutdown()
        except rclpy._rclpy_pybind11.RCLError: pass

if __name__ == '__main__':
    main()
