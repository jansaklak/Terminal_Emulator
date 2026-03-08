from flask import Flask, request, jsonify, render_template_string
import json
import os
import csv
from io import StringIO

app = Flask(__name__)
CONFIG_FILE = 'config.json'

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"HOST": "0.0.0.0", "PORT": 5000, "USERS": {}, "CONFIGS": {}}
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

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
                .card { background: #313244; padding: 20px; border-radius: 8px; max-width: 600px; margin: auto; }
                input, select { background: #1e1e2e; border: 1px solid #585b70; color: white; padding: 8px; margin: 5px; border-radius: 4px; }
                button { background: #89b4fa; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer; font-weight: bold; }
                .user-row { background: #45475a; padding: 10px; margin-top: 10px; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; }
                .dot { height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 10px; }
                .online { background-color: #a6e3a1; box-shadow: 0 0 5px #a6e3a1; }
                .offline { background-color: #f38ba8; opacity: 0.4; }
                hr { border: none; border-top: 1px solid #585b70; margin: 20px 0; }
                select { width: 100%; margin-bottom: 10px; }
                .filter-container { margin-bottom: 15px; padding: 10px; background: #45475a; border-radius: 4px; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>Zarządzanie Użytkownikami</h1>
                
                <div class="filter-container">
                    <label for="groupFilter" style="font-size: 0.8em; color: #a6adc8;">Filtruj według grupy:</label>
                    <select id="groupFilter" onchange="renderList()">
                        <option value="all">Wszyscy użytkownicy</option>
                    </select>
                </div>

                <div id="userList">Ładowanie...</div>
                
                <hr>
                <h3>Dodaj Użytkownika</h3>
                <input id="u" placeholder="Username">
                <input id="p" type="password" placeholder="Password">
                <input id="d" placeholder="Display Name">
                <button onclick="add()">Dodaj</button>
                
                <hr>
                <h3>Import zbiorczy (CSV)</h3>
                <div style="background: #1e1e2e; padding: 15px; border-radius: 5px;">
                    <p style="font-size: 0.85em; color: #a6adc8; margin-top:0;">Format: Nazwisko;Imię</p>
                    <input id="groupName" placeholder="Nazwa grupy">
                    <input type="file" id="csvFile" accept=".csv" style="border: none;">
                    <button onclick="importCSV()">Importuj</button>
                </div>
            </div>

            <script>
                let cachedData = null;
                let cachedOnline = null;

                async function load() {
                    try {
                        const [cfgRes, onlineRes] = await Promise.all([
                            fetch('/api/config'),
                            fetch('/api/online')
                        ]);
                        cachedData = await cfgRes.json();
                        cachedOnline = await onlineRes.json();
                        updateGroupDropdown();
                        renderList();
                    } catch (e) { console.error("Błąd ładowania danych:", e); }
                }

                function updateGroupDropdown() {
                    const filter = document.getElementById('groupFilter');
                    const currentSelection = filter.value;
                    const allGroups = new Set();
                    Object.values(cachedData.USERS).forEach(u => {
                        if (u.groups) u.groups.forEach(g => allGroups.add(g));
                    });
                    filter.innerHTML = '<option value="all">Wszyscy użytkownicy</option>';
                    Array.from(allGroups).sort().forEach(group => {
                        const opt = document.createElement('option');
                        opt.value = group; opt.textContent = group;
                        filter.appendChild(opt);
                    });
                    filter.value = currentSelection;
                }

                function renderList() {
                    if (!cachedData || !cachedOnline) return;
                    const selectedGroup = document.getElementById('groupFilter').value;
                    const onlineUsernames = new Set(Object.values(cachedOnline).map(s => s.user));

                    const filteredUsers = Object.values(cachedData.USERS).filter(user => {
                        if (selectedGroup === 'all') return true;
                        return user.groups && user.groups.includes(selectedGroup);
                    });

                    // POPRAWIONE: Usunięto backslashe przed znakami dolara
                    document.getElementById('userList').innerHTML = filteredUsers.map(user => {
                        const isOnline = onlineUsernames.has(user.username);
                        const statusClass = isOnline ? 'online' : 'offline';
                        const groupsHtml = (user.groups || []).map(g => 
                            `<small style="background:#585b70; padding:2px 5px; border-radius:3px; margin-left:5px;">${g}</small>`
                        ).join('');
                        
                        return `
                            <div class="user-row">
                                <span>
                                    <span class="dot ${statusClass}"></span>
                                    <strong>${user.username}</strong> (${user.display_name}) ${groupsHtml}
                                </span>
                                <button style="background:#f38ba8" onclick="del('${user.username}')">Usuń</button>
                            </div>
                        `;
                    }).join('') || '<div style="text-align:center; padding:10px;">Brak użytkowników.</div>';
                }

                async function add() {
                    const payload = {
                        username: document.getElementById('u').value,
                        password: document.getElementById('p').value,
                        display_name: document.getElementById('d').value
                    };
                    await fetch('/api/users', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(payload)
                    });
                    load();
                }

                async function del(name) {
                    if(confirm(`Czy na pewno usunąć użytkownika ${name}?`)) {
                        await fetch('/api/users/' + name, { method: 'DELETE' });
                        load();
                    }
                }

                async function importCSV() {
                    const fileInput = document.getElementById('csvFile');
                    const groupInput = document.getElementById('groupName');
                    if(!fileInput.files[0]) return alert("Wybierz plik!");

                    const formData = new FormData();
                    formData.append('file', fileInput.files[0]);
                    formData.append('group', groupInput.value);

                    const res = await fetch('/api/import', { method: 'POST', body: formData });
                    if((await res.json()).ok) {
                        alert("Zaimportowano pomyślnie!");
                        load();
                    }
                }

                load();
                setInterval(load, 3000);
            </script>
        </body>
        </html>
    """)

@app.route('/api/config')
def get_config():
    return jsonify(load_config())

@app.route('/api/users', methods=['POST'])
def add_user():
    data = request.json
    config = load_config()
    config['USERS'][data['username']] = {
        "username": data['username'],
        "password": data['password'],
        "display_name": data['display_name'],
        "groups": []
    }
    save_config(config)
    return jsonify({"ok": True})

@app.route('/api/users/<username>', methods=['DELETE'])
def delete_user(username):
    config = load_config()
    if username in config['USERS']:
        del config['USERS'][username]
        save_config(config)
    return jsonify({"ok": True})

@app.route('/api/online')
def get_online():
    if not os.path.exists('online.json'):
        return jsonify({})
    with open('online.json', 'r') as f:
        return jsonify(json.load(f))

@app.route('/api/import', methods=['POST'])
def import_users_csv():
    if 'file' not in request.files:
        return jsonify({"ok": False, "error": "Brak pliku"}), 400
    
    file = request.files['file']
    group_name = request.form.get('group', 'Bez grupy')
    
    if file.filename == '':
        return jsonify({"ok": False, "error": "Nie wybrano pliku"}), 400

    try:
        stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.reader(stream, delimiter=';')
        config = load_config()
        
        for row in csv_reader:
            if len(row) < 2: continue
            nazwisko, imie = row[0].strip(), row[1].strip()
            base_username = f"{imie.lower()}_{nazwisko[:3].lower()}"
            
            if base_username in config['USERS']:
                user_obj = config['USERS'][base_username]
                if 'groups' not in user_obj: user_obj['groups'] = []
                if group_name and group_name not in user_obj['groups']:
                    user_obj['groups'].append(group_name)
            else:
                username = base_username
                counter = 1
                while username in config['USERS']:
                    username = f"{base_username}{counter}"
                    counter += 1
                
                config['USERS'][username] = {
                    "username": username,
                    "password": os.urandom(4).hex(),
                    "display_name": f"{imie}_{nazwisko}",
                    "groups": [group_name] if group_name else []
                }
        
        save_config(config)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)