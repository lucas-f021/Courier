from flask import Flask, request, jsonify
import logging
import os
import threading

log = logging.getLogger(__name__)

app = Flask(__name__)

_conversation_history = []
_conversation_history_lock = threading.Lock()
_inbox = []
_inbox_lock = threading.Lock()


@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

def push_to_web(message):
    with _inbox_lock:
        _inbox.append(message)

def _get_run_web_agent():
    from agent.ai_agent import run_web_agent
    return run_web_agent

@app.route('/')
def index():
    return _HTML

@app.route('/inbox')
def inbox():
    with _inbox_lock:
        messages = list(_inbox)
        _inbox.clear()
    return jsonify({'messages': messages})

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    text = data.get('message', '').strip()
    if not text:
        return jsonify({'reply': ''})
    if len(text) > 4000:
        return jsonify({'reply': 'Message too long (max 4000 characters).'})
    log.info(f"web_request | msg_len={len(text)}")
    run_web_agent = _get_run_web_agent()
    try:
        reply = run_web_agent(text, _conversation_history)
    except Exception as e:
        log.error(f"web_agent_error | error={str(e)}")
        with _conversation_history_lock:
            if _conversation_history and _conversation_history[-1].get("role") == "user":
                _conversation_history.pop()
        return jsonify({'reply': 'An error occurred. Please try again.'})
    return jsonify({'reply': reply})

@app.route('/reset', methods=['POST'])
def reset():
    with _conversation_history_lock:
        _conversation_history.clear()
    log.info("web_conversation_reset")
    return jsonify({'status': 'ok'})

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Courier</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: sans-serif; background: #f4f4f4; display: flex; flex-direction: column; height: 100vh; }
  #chat { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 16px; }
  .row { display: flex; align-items: flex-end; gap: 8px; }
  .row.user { flex-direction: row-reverse; }
  .avatar { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: bold; flex-shrink: 0; }
  .avatar.agent { background: #1a1a2e; color: #fff; }
  .avatar.user { background: #0b93f6; color: #fff; }
  .bubble-wrap { display: flex; flex-direction: column; gap: 3px; max-width: 72%; }
  .row.user .bubble-wrap { align-items: flex-end; }
  .name { font-size: 11px; color: #888; padding: 0 4px; }
  .msg { padding: 10px 14px; border-radius: 12px; line-height: 1.5; white-space: pre-wrap; font-size: 14px; }
  .row.user .msg { background: #0b93f6; color: white; border-bottom-right-radius: 3px; }
  .row.agent .msg { background: white; color: #222; border: 1px solid #ddd; border-bottom-left-radius: 3px; }
  #input-row { display: flex; padding: 12px; gap: 8px; background: white; border-top: 1px solid #ddd; }
  #msg-input { flex: 1; padding: 10px; border: 1px solid #ccc; border-radius: 8px; font-size: 14px; resize: none; font-family: inherit; rows: 1; max-height: 120px; overflow-y: auto; }
  #send-btn { padding: 10px 20px; background: #0b93f6; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; }
  #send-btn:disabled { background: #aaa; cursor: not-allowed; }
</style>
</head>
<body>
<div id="chat"></div>
<div id="input-row">
  <textarea id="msg-input" rows="1" placeholder="Message your agent..." autofocus></textarea>
  <button id="send-btn" onclick="send()">Send</button>
</div>
<script>
  const chat = document.getElementById('chat');
  const input = document.getElementById('msg-input');
  const btn = document.getElementById('send-btn');

  input.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } });
  input.addEventListener('input', () => { input.style.height = 'auto'; input.style.height = input.scrollHeight + 'px'; });

  function addMsg(text, role) {
    const row = document.createElement('div');
    row.className = 'row ' + role;

    const av = document.createElement('div');
    av.className = 'avatar ' + role;
    av.textContent = role === 'agent' ? 'C' : 'You'[0];

    const wrap = document.createElement('div');
    wrap.className = 'bubble-wrap';

    const name = document.createElement('div');
    name.className = 'name';
    name.textContent = role === 'agent' ? 'Courier' : 'You';

    const bubble = document.createElement('div');
    bubble.className = 'msg';
    bubble.textContent = text;

    wrap.appendChild(name);
    wrap.appendChild(bubble);
    row.appendChild(av);
    row.appendChild(wrap);
    chat.appendChild(row);
    chat.scrollTop = chat.scrollHeight;
    return bubble;
  }

  setInterval(async () => {
    try {
      const res = await fetch('/inbox');
      const data = await res.json();
      for (const msg of data.messages) addMsg(msg, 'agent');
    } catch (_) {}
  }, 3000);

  async function send() {
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    input.style.height = 'auto';
    btn.disabled = true;
    addMsg(text, 'user');
    const pending = addMsg('...', 'agent');
    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });
      const data = await res.json();
      pending.textContent = data.reply || '(no response)';
    } catch (e) {
      pending.textContent = 'Error: could not reach agent.';
    }
    btn.disabled = false;
    input.focus();
  }
</script>
</body>
</html>"""


def start_web_server(port=5000):
    log.info(f"web_server_start | port={port}")
    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)
