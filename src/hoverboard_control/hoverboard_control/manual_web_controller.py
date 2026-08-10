#!/usr/bin/env python3
"""
manual_web_controller.py - Manual Mode Web UI (Base + Head + Emotions)
Port 5000. Do NOT run alongside autonomous web_controller.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from flask import Flask, jsonify
import threading

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>Manual Robot Control</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
body{font-family:-apple-system,system-ui,sans-serif;background:#0a0e12;color:#ffb347;padding:16px;min-height:100vh}
h1{font-size:1.3rem;text-align:center;margin-bottom:4px;color:#ffb347}
.sub{text-align:center;color:#6a5a36;font-size:.8rem;margin-bottom:14px}
#modeBanner{text-align:center;padding:12px;border-radius:10px;font-weight:700;font-size:1rem;margin-bottom:16px;border:1px solid #ffb347;background:#2a1a06;color:#ffb347}
.label{font-size:.7rem;text-transform:uppercase;letter-spacing:.08em;color:#6a5a36;margin:18px 0 10px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
button{background:#0a1014;border:1px solid #3a2a06;color:#ffb347;padding:16px 6px;border-radius:10px;font-size:.95rem;cursor:pointer;transition:all .1s}
button:active{background:#3a2a06;border-color:#ffb347;transform:scale(.96)}
.pad{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;max-width:300px;margin:0 auto}
.pad .spacer{visibility:hidden}
.stop{border-color:#ff6666!important;color:#ff6666!important}
.head-pad{max-width:260px;margin:0 auto}
.head-btn{padding:14px 6px;font-size:.85rem}
#status{text-align:center;margin-top:16px;font-size:.8rem;color:#8a7a56;min-height:1.2em}
</style>
</head>
<body>
<h1>🎮 Manual Robot Control</h1>
<div class="sub">Base + Head - Safety overrides active</div>
<div id="modeBanner">🎮 MANUAL MODE</div>
<div class="label">Expressions</div>
<div class="grid" id="emoGrid"></div>
<div class="label">Base Movement</div>
<div class="pad">
<div class="spacer"></div><button onclick="move('F')">▲ Fwd</button><div class="spacer"></div>
<button onclick="move('L')">◀ Left</button><button class="stop" onclick="move('S')">■ Stop</button><button onclick="move('R')">Right ▶</button>
<div class="spacer"></div><button onclick="move('B')">▼ Back</button><div class="spacer"></div>
</div>
<div class="label">Head Pan / Tilt</div>
<div class="pad head-pad">
<div class="spacer"></div><button class="head-btn" data-head-command="U">▲ Up</button><div class="spacer"></div>
<button class="head-btn" data-head-command="Y">◀ Left</button><button class="head-btn stop" id="headHold">■ Hold</button><button class="head-btn" data-head-command="Z">Right ▶</button>
<div class="spacer"></div><button class="head-btn" data-head-command="D">▼ Down</button><div class="spacer"></div>
</div>
<div id="status">Ready</div>
<script>
var EMOTIONS=['love','happy','smile','excited','laugh','kiss','wink','surprised','sad','confused','angry','sleepy','talking','neutral'];
var grid=document.getElementById('emoGrid');
var statusEl=document.getElementById('status');
EMOTIONS.forEach(function(e){var b=document.createElement('button');b.textContent=e;b.onclick=function(){emotion(e)};grid.appendChild(b)});
function emotion(n){fetch('/emotion/'+n);statusEl.textContent='Expression: '+n}
function move(c){fetch('/move/'+c);statusEl.textContent='Base: '+c}
function sendHead(c){
fetch('/head/'+c).then(function(r){
if(!r.ok){throw new Error('HTTP '+r.status)}
return r.json()
}).then(function(d){
if(!d.ok){throw new Error(d.error||'command rejected')}
statusEl.textContent='Head: '+c
}).catch(function(e){
statusEl.textContent='Head failed: '+e.message
})
}
document.querySelectorAll('[data-head-command]').forEach(function(button){
button.addEventListener('click',function(){sendHead(button.dataset.headCommand)})
})
document.getElementById('headHold').addEventListener('click',function(){statusEl.textContent='Head: Holding (silence=stop)'})
setInterval(function(){fetch('/mode').then(function(r){return r.json()}).then(function(d){document.getElementById('modeBanner').textContent='🎮 '+d.mode}).catch(function(){})},1000);
</script>
</body>
</html>"""

app = Flask(__name__)
node = None


@app.route('/')
def index():
    return HTML_PAGE


@app.route('/emotion/<name>')
def emotion(name):
    if node:
        msg = String()
        msg.data = name
        node.eilik_pub.publish(msg)
    return jsonify({'ok': True})


@app.route('/move/<cmd>')
def move(cmd):
    if node and cmd in ('F', 'B', 'L', 'R', 'S'):
        msg = String()
        msg.data = cmd
        node.move_pub.publish(msg)
    return jsonify({'ok': True})


@app.route('/head/<cmd>')
def head(cmd):
    if cmd not in ('Y', 'Z', 'U', 'D'):
        return jsonify({'ok': False, 'error': 'invalid head command'}), 400
    if node is None:
        return jsonify({'ok': False, 'error': 'ROS node is unavailable'}), 503
    msg = String()
    msg.data = cmd
    node.head_pub.publish(msg)
    node.get_logger().info(f'Web head command published: {cmd}')
    return jsonify({'ok': True})


@app.route('/mode')
def mode():
    return jsonify({'mode': node.current_state if node else 'MANUAL'})


def run_flask():
    app.run(host='0.0.0.0', port=5000, threaded=True)


class ManualWebController(Node):
    def __init__(self):
        super().__init__('manual_web_controller')
        self.eilik_pub = self.create_publisher(String, '/eilik/command', 10)
        self.move_pub = self.create_publisher(String, '/app_command', 10)
        self.head_pub = self.create_publisher(String, '/head/command', 10)
        self.current_state = 'MANUAL'
        self.create_subscription(String, '/robot/state', self.state_callback, 10)
        self.get_logger().info('Manual Web Controller ready on http://0.0.0.0:5000')

    def state_callback(self, msg):
        self.current_state = msg.data


def main(args=None):
    global node
    rclpy.init(args=args)
    node = ManualWebController()
    threading.Thread(target=run_flask, daemon=True).start()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            node.destroy_node()
            rclpy.shutdown()
        except Exception:
            pass


if __name__ == '__main__':
    main()
