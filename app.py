# language: Python, file: app.py, runtime: Python 3.10+
import os
import time
import threading
import random
import requests
from flask import Flask, request, jsonify, render_template_string
from instagrapi import Client

app = Flask(__name__)

STATE = {
    "total_sent": 0,
    "live_accounts": 0,
    "sessions": [],
    "target": "",
    "gc_link": "",
    "delay": 0,
    "locker_running": False,
    "is_running": False,
    "logs": []
}

try:
    with open("index.html", "r", encoding="utf-8") as f:
        HTML_TEMPLATE = f.read()
except Exception:
    HTML_TEMPLATE = "<h1>index.html missing</h1>"

FLAG_POOL = [
    "🇺🇸", "🇬🇧", "🇨🇦", "🇦🇺", "🇩🇪", "🇫🇷", "🇮🇳", "🇵🇰", 
    "🇧🇷", "🇲🇽", "🇯🇵", "🇰🇷", "🇨🇳", "🇷🇺", "🇿🇦", "🇳🇬", 
    "🇪🇬", "🇸🇦", "🇦🇪", "🇹🇷", "🇮🇩", "🇵🇭", "🇻🇳", "🇹🇭", 
    "🇮🇹", "🇪🇸", "🇳🇱", "🇸🇪", "🇳🇴", "🇵🇱", "🇺🇦", "🏴‍☠️"
]

PAYLOAD_TEMPLATE = """{target} 𝐂ʜᴜᴘ 𝐓ᴍᴋᴄ  <flag>
























{target} 𝐂ʜᴜᴘ 𝐓ᴍᴋᴄ <flag>































{target} 𝐂ʜᴜᴘ 𝐓ᴍᴋᴄ <flag>
























{target} 𝐂ʜᴜᴘ 𝐓ᴍᴋᴄ <flag>"""

LOCKER_TEMPLATE = "<tARGET> 𝙇𝙀𝙒𝙄𝙎 🇧‌🇦‌🇦‌🇵‌ ᵇᵒˡ <emoji>"

def log_msg(msg):
    timestamp = time.strftime("%H:%M:%S")
    STATE["logs"].append(f"[{timestamp}] {msg}")
    if len(STATE["logs"]) > 100:
        STATE["logs"].pop(0)

def keep_alive():
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url: return
    while True:
        time.sleep(300)
        try: requests.get(url, timeout=15)
        except: pass

if not any(t.name == "KeepAlive" for t in threading.enumerate()):
    threading.Thread(target=keep_alive, name="KeepAlive", daemon=True).start()

# --- SPAM WORKER ---
def session_worker(session_data, thread_id):
    cl = Client()
    if session_data.get('proxy'):
        cl.set_proxy(session_data['proxy'])
    
    try:
        cl.login_by_sessionid(session_data["session_id"])
        log_msg(f"✅ Thread Started: @{session_data['username']}")
    except Exception as e:
        log_msg(f"❌ Auth failed for @{session_data['username']}: {str(e)[:30]}")
        return

    uname = session_data['username']
    
    while STATE["is_running"]:
        random_flag = random.choice(FLAG_POOL)
        payload_text = PAYLOAD_TEMPLATE.format(target=STATE['target']).replace("<flag>", random_flag)
        
        try:
            cl.direct_send(payload_text, thread_ids=[thread_id])
            STATE["total_sent"] += 1
            current_delay = float(STATE.get("delay", 0))
            log_msg(f"📨 @{uname} sent payload.")
        except Exception as e:
            log_msg(f"❌ @{uname} failed: {str(e)[:40]}")
            if "login_required" in str(e).lower() or "challenge" in str(e).lower():
                log_msg(f"⚠️ @{uname} session invalid. Thread stopping.")
                break
        
        if current_delay > 0:
            time.sleep(current_delay)

# --- LOCKER WORKER ---
def locker_worker():
    if not STATE["sessions"]:
        log_msg("❌ Locker needs at least 1 session.")
        STATE["locker_running"] = False
        return
        
    s = STATE["sessions"][0]
    cl = Client()
    if s.get('proxy'):
        cl.set_proxy(s['proxy'])
        
    try:
        cl.login_by_sessionid(s["session_id"])
        log_msg(f"🔒 Locker Authenticated: @{s['username']}")
    except Exception as e:
        log_msg(f"❌ Locker Auth failed: {str(e)[:30]}")
        STATE["locker_running"] = False
        return

    try:
        raw_id = STATE['gc_link'].split('/t/')[-1].replace('/', '').split('?')[0]
        thread_id = str(raw_id).strip()
    except:
        log_msg("❌ Locker: Invalid GC Link.")
        STATE["locker_running"] = False
        return

    log_msg("🔒 Locker Mode Started")
    
    while STATE["locker_running"]:
        try:
            target_name = STATE.get('target', 'UNKNOWN')
            random_flag = random.choice(FLAG_POOL)
            
            # Format the template using the random flag for the emoji slot
            new_name = LOCKER_TEMPLATE.replace("<tARGET>", target_name).replace("<emoji>", random_flag)
            
            cl.direct_thread_update_title(thread_id, new_name)
            log_msg(f"🔒 Group name changed to: {new_name}")
        except Exception as e:
            log_msg(f"❌ Locker failed: {str(e)[:30]}")
            
        time.sleep(2)
        
    log_msg("🛑 Locker Mode Stopped")

# --- SPAM MASTER ---
def spam_master():
    log_msg("🔥 Spam Engine Started")
    
    try:
        raw_id = STATE['gc_link'].split('/t/')[-1].replace('/', '').split('?')[0]
        thread_id = str(raw_id).strip()
    except:
        STATE['is_running'] = False
        return

    if not STATE["sessions"]:
        STATE['is_running'] = False
        return

    for s in STATE["sessions"]:
        t = threading.Thread(target=session_worker, args=(s, thread_id), daemon=True)
        t.start()

    while STATE["is_running"]:
        time.sleep(1)
    log_msg("🛑 Spam Engine Stopped")

# --- ROUTES ---
@app.route('/')
def home(): return render_template_string(HTML_TEMPLATE)

@app.route('/api/state', methods=['GET'])
def get_state():
    STATE["live_accounts"] = len(STATE["sessions"])
    return jsonify(STATE)

@app.route('/api/session', methods=['POST'])
def add_session():
    data = request.json
    sid = data.get('session_id', '').strip().replace('"', '').replace("'", "")
    proxy = data.get('proxy', '').strip()
    
    if sid.startswith("sessionid="):
        sid = sid.replace("sessionid=", "")
    
    if not sid: return jsonify({"error": "Empty session"}), 400
    if any(s["session_id"] == sid for s in STATE["sessions"]):
        return jsonify({"error": "Session already added"}), 400

    try:
        cl = Client()
        if proxy: cl.set_proxy(proxy)
        cl.login_by_sessionid(sid)
        uname = cl.username
        
        STATE["sessions"].append({"session_id": sid, "username": uname, "proxy": proxy})
        log_msg(f"✅ Authenticated: @{uname}")
        return jsonify({"status": "ok", "username": uname})
    except Exception as e:
        return jsonify({"error": f"Auth failed: {str(e)[:40]}"}), 400

@app.route('/api/session/<sid>', methods=['DELETE'])
def remove_session(sid):
    STATE['sessions'] = [s for s in STATE['sessions'] if s["session_id"] != sid]
    return jsonify({"status": "ok"})

@app.route('/api/config', methods=['POST'])
def update_config():
    data = request.json
    STATE['target'] = data.get('target', STATE['target'])
    STATE['gc_link'] = data.get('gc_link', STATE['gc_link'])
    
    if 'delay' in data:
        try: STATE['delay'] = float(data['delay'])
        except: pass
    return jsonify({"status": "ok"})

@app.route('/api/toggle', methods=['POST'])
def toggle_spam():
    data = request.json
    if data.get('running') and not STATE['sessions']: return jsonify({"error": "No sessions"}), 400
    if data.get('running') and (not STATE['gc_link'] or not STATE['target']): return jsonify({"error": "Missing GC Link or Target"}), 400
        
    STATE['is_running'] = data.get('running', False)
    if STATE['is_running']:
        threading.Thread(target=spam_master, daemon=True).start()
    return jsonify({"status": "ok", "is_running": STATE['is_running']})

@app.route('/api/toggle_locker', methods=['POST'])
def toggle_locker():
    data = request.json
    if data.get('running') and not STATE['sessions']: return jsonify({"error": "No sessions"}), 400
    if data.get('running') and not STATE['gc_link']: return jsonify({"error": "Missing GC Link"}), 400
        
    STATE['locker_running'] = data.get('running', False)
    if STATE['locker_running']:
        threading.Thread(target=locker_worker, daemon=True).start()
    return jsonify({"status": "ok", "locker_running": STATE['locker_running']})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)