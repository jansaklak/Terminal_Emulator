from flask import Flask, request, jsonify, render_template_string
import json
import os
import csv
from io import StringIO
import unicodedata

app = Flask(__name__)
CONFIG_FILE = 'server_config.json'
USERS_FILE = 'users.json'

def remove_diacritics(text):
    chars = {'ą':'a','ć':'c','ę':'e','ł':'l','ń':'n','ó':'o','ś':'s','ź':'z','ż':'z',
             'Ą':'A','Ć':'C','Ę':'E','Ł':'L','Ń':'N','Ó':'O','Ś':'S','Ź':'Z','Ż':'Z'}
    for k, v in chars.items(): text = text.replace(k, v)
    nfkd_form = unicodedata.normalize('NFKD', text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"HOST": "0.0.0.0", "PORT": 51234, "CONFIGS": {}}
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def load_users():
    if not os.path.exists(USERS_FILE): return {}
    with open(USERS_FILE, 'r', encoding='utf-8') as f: return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

@app.route('/')
def index():
    return render_template_string("""
        <!DOCTYPE html>
        <html lang="pl">
        <head>
            <meta charset="UTF-8">
            <title>Panel Admina</title>
            <style>
                body { font-family: sans-serif; background: #1e1e2e; color: #cdd6f4; padding: 20px; }
                .container { display: flex; gap: 20px; flex-wrap: wrap; justify-content: center; }
                .card { background: #313244; padding: 20px; border-radius: 8px; width: 450px; }
                h1, h2 { text-align: center; color: #89b4fa; }
                input, select { background: #1e1e2e; border: 1px solid #585b70; color: white; padding: 8px; margin: 5px; border-radius: 4px; }
                button { background: #89b4fa; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer; font-weight: bold; }
                .row { background: #45475a; padding: 10px; margin-top: 10px; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; }
                .dot { height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 10px; }
                .online { background-color: #a6e3a1; box-shadow: 0 0 5px #a6e3a1; }
                .offline { background-color: #f38ba8; opacity: 0.4; }
                hr { border: none; border-top: 1px solid #585b70; margin: 20px 0; }
                .res-input { width: 60px; text-align: center; }
            </style>
        </head>
        <body>
            <h1>Panel Administracyjny</h1>
            
            <div class="container">
                <!-- SEKCJA UŻYTKOWNIKÓW -->
                <div class="card">
                    <h2>Użytkownicy</h2>
                    <div style="margin-bottom:10px;">
                        <select id="groupFilter" onchange="renderUsers()" style="width:100%">
                            <option value="all">Wszyscy</option>
                        </select>
                    </div>
                    <div id="userList" style="max-height: 400px; overflow-y: auto;">Ładowanie...</div>
                    <hr>
                    <h3>Dodaj</h3>
                    <input id="u" placeholder="Login" style="width:80px">
                    <input id="p" type="password" placeholder="Hasło" style="width:80px">
                    <input id="d" placeholder="Nazwa" style="width:80px">
                    <button onclick="addUser()">+</button>
                    <hr>
                    <h3>Import CSV</h3>
                    <input id="groupName" placeholder="Grupa">
                    <input type="file" id="csvFile" accept=".csv">
                    <button onclick="importCSV()">Importuj</button>
                </div>

                <!-- SEKCJA ZASOBÓW -->
                <div class="card">
                    <h2>Zasoby Docker</h2>
                    <div id="configList">Ładowanie...</div>
                    <p style="font-size:0.8em; color:#a6adc8; margin-top:20px;">
                        * CPU: np. 0.5 (pół rdzenia), 1.0 (cały rdzeń)<br>
                        * RAM: np. 256m, 1g (limity per kontener)
                    </p>
                </div>
            </div>

            <script>
                let cachedConfig = null, cachedUsers = null, cachedOnline = null;

                async function loadAll() {
                    const [c, u, o] = await Promise.all([
                        fetch('/api/config').then(r => r.json()),
                        fetch('/api/users').then(r => r.json()),
                        fetch('/api/online').then(r => r.json())
                    ]);
                    cachedConfig = c; cachedUsers = u; cachedOnline = o;
                    updateGroups(); renderUsers(); renderConfigs();
                }

                function updateGroups() {
                    const g = new Set();
                    Object.values(cachedUsers).forEach(u => (u.groups || []).forEach(grp => g.add(grp)));
                    const sel = document.getElementById('groupFilter');
                    const val = sel.value;
                    sel.innerHTML = '<option value="all">Wszyscy</option>';
                    Array.from(g).sort().forEach(grp => sel.innerHTML += `<option value="${grp}">${grp}</option>`);
                    sel.value = val;
                }

                function renderUsers() {
                    const grp = document.getElementById('groupFilter').value;
                    const online = new Set(Object.values(cachedOnline).map(s => s.user));
                    const list = Object.values(cachedUsers).filter(u => grp==='all' || (u.groups && u.groups.includes(grp)));
                    
                    document.getElementById('userList').innerHTML = list.map(u => `
                        <div class="row">
                            <span><span class="dot ${online.has(u.username)?'online':'offline'}"></span>${u.username}</span>
                            <button style="background:#f38ba8; padding:2px 8px;" onclick="delUser('${u.username}')">X</button>
                        </div>
                    `).join('') || 'Brak użytkowników';
                }

                function renderConfigs() {
                    const cfgs = cachedConfig.CONFIGS;
                    document.getElementById('configList').innerHTML = Object.keys(cfgs).map(key => `
                        <div class="row" style="flex-direction:column; align-items:flex-start; gap:10px;">
                            <strong style="color:#89b4fa">${key}</strong>
                            <div style="display:flex; gap:10px; width:100%; align-items:center;">
                                <span>CPU:</span>
                                <input id="cpu_${key}" class="res-input" value="${cfgs[key].cpu_limit || '0.5'}">
                                <span>RAM:</span>
                                <input id="mem_${key}" class="res-input" value="${cfgs[key].mem_limit || '256m'}">
                                <button onclick="saveRes('${key}')">Zapisz</button>
                            </div>
                        </div>
                    `).join('');
                }

                async function saveRes(key) {
                    const cpu = document.getElementById(`cpu_${key}`).value;
                    const mem = document.getElementById(`mem_${key}`).value;
                    await fetch('/api/resources', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({key, cpu, mem})
                    });
                    alert('Zapisano zasoby dla ' + key);
                    loadAll();
                }

                async function addUser() {
                    const payload = {
                        username: document.getElementById('u').value,
                        password: document.getElementById('p').value,
                        display_name: document.getElementById('d').value
                    };
                    await fetch('/api/users', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) });
                    loadAll();
                }

                async function delUser(name) {
                    if(confirm('Usunąć?')) { await fetch('/api/users/'+name, {method:'DELETE'}); loadAll(); }
                }

                async function importCSV() {
                    const fd = new FormData();
                    fd.append('file', document.getElementById('csvFile').files[0]);
                    fd.append('group', document.getElementById('groupName').value);
                    await fetch('/api/import', { method: 'POST', body: fd });
                    loadAll();
                }

                loadAll();
                setInterval(loadAll, 5000);
            </script>
        </body>
        </html>
    """)

@app.route('/api/config')
def get_config(): return jsonify(load_config())

@app.route('/api/users')
def get_users_api(): return jsonify(load_users())

@app.route('/api/resources', methods=['POST'])
def update_resources():
    data = request.json
    config = load_config()
    if data['key'] in config['CONFIGS']:
        config['CONFIGS'][data['key']]['cpu_limit'] = data['cpu']
        config['CONFIGS'][data['key']]['mem_limit'] = data['mem']
        save_config(config)
    return jsonify({"ok": True})

@app.route('/api/users', methods=['POST'])
def add_user():
    data = request.json
    users = load_users()
    users[data['username']] = { "username": data['username'], "password": data['password'], "display_name": data['display_name'], "groups": [] }
    save_users(users)
    return jsonify({"ok": True})

@app.route('/api/users/<username>', methods=['DELETE'])
def delete_user(username):
    users = load_users()
    if username in users:
        del users[username]
        save_users(users)
    return jsonify({"ok": True})

@app.route('/api/online')
def get_online():
    if not os.path.exists('online.json'): return jsonify({})
    with open('online.json', 'r') as f: return jsonify(json.load(f))

@app.route('/api/import', methods=['POST'])
def import_users_csv():
    file = request.files.get('file')
    group_name = request.form.get('group', 'Bez grupy')
    if not file: return jsonify({"ok": False}), 400
    stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
    csv_reader = csv.reader(stream, delimiter=';')
    users = load_users()
    for row in csv_reader:
        if len(row) < 2: continue
        nazwisko, imie = row[0].strip(), row[1].strip()
        u = remove_diacritics(imie.lower()) + "_" + remove_diacritics(nazwisko[:3].lower())
        if u not in users:
            users[u] = {"username": u, "password": os.urandom(4).hex(), "display_name": f"{imie}_{nazwisko}", "groups": [group_name]}
    save_users(users)
    return jsonify({"ok": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)