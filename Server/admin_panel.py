import csv
import datetime
import json
import os
import unicodedata
from io import StringIO
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

app = Flask(__name__)

CONFIG_FILE = 'server_config.json'
IMAGES_DIR = 'images'
USERS_FILE = 'users.json'
COMMANDS_DIR = Path('commands').resolve()
LOGS_ROOT = Path('/var/log/terminal-server')


def get_log_dir():
    cfg = load_config()
    configured = cfg.get('LOG_DIR', str(LOGS_ROOT))
    path = Path(configured).resolve()
    if path.exists():
        return path
    fallback = Path('logs').resolve()
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def remove_diacritics(text):
    chars = {
        'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n', 'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z',
        'Ą': 'A', 'Ć': 'C', 'Ę': 'E', 'Ł': 'L', 'Ń': 'N', 'Ó': 'O', 'Ś': 'S', 'Ź': 'Z', 'Ż': 'Z',
    }
    for key, value in chars.items():
        text = text.replace(key, value)
    nfkd_form = unicodedata.normalize('NFKD', text)
    return ''.join(char for char in nfkd_form if not unicodedata.combining(char))


def load_config():
    cfg = {'HOST': '0.0.0.0', 'PORT': 51234, 'CONFIGS': {}}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as file_handle:
            cfg.update(json.load(file_handle))

    if os.path.exists(IMAGES_DIR):
        for entry in os.scandir(IMAGES_DIR):
            if not entry.is_dir():
                continue
            img_cfg_path = os.path.join(entry.path, 'config.json')
            if not os.path.exists(img_cfg_path):
                continue
            with open(img_cfg_path, 'r', encoding='utf-8') as file_handle:
                try:
                    cfg['CONFIGS'][entry.name] = json.load(file_handle)
                except Exception:
                    pass
    return cfg


def save_config(config):
    global_cfg = {key: value for key, value in config.items() if key != 'CONFIGS'}
    with open(CONFIG_FILE, 'w', encoding='utf-8') as file_handle:
        json.dump(global_cfg, file_handle, indent=4, ensure_ascii=False)

    if config.get('CONFIGS'):
        for img_name, img_cfg in config['CONFIGS'].items():
            img_dir = os.path.join(IMAGES_DIR, img_name)
            if not os.path.exists(img_dir):
                continue
            img_cfg_path = os.path.join(img_dir, 'config.json')
            with open(img_cfg_path, 'w', encoding='utf-8') as file_handle:
                json.dump(img_cfg, file_handle, indent=4, ensure_ascii=False)


def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, 'r', encoding='utf-8') as file_handle:
        return json.load(file_handle)


def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as file_handle:
        json.dump(users, file_handle, indent=4, ensure_ascii=False)


def safe_log_path(filename):
    log_dir = get_log_dir()

    if filename.endswith('.log'):
        candidate = (log_dir / os.path.basename(filename)).resolve()
        if log_dir not in candidate.parents and candidate != log_dir:
            return None
        return candidate if candidate.exists() and candidate.is_file() else None

    if filename.endswith('.cmds'):
        candidate = Path(filename).resolve()
        if COMMANDS_DIR not in candidate.parents and candidate != COMMANDS_DIR:
            return None
        return candidate if candidate.exists() and candidate.is_file() else None

    return None


@app.route('/')
def index():
    return render_template('admin_panel.html')


@app.route('/api/config')
def get_config():
    return jsonify(load_config())


@app.route('/api/users')
def get_users_api():
    return jsonify(load_users())


@app.route('/api/users', methods=['POST'])
def add_user():
    data = request.json or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    display_name = (data.get('display_name') or username).strip()
    group = (data.get('group') or '').strip()

    if not username:
        return jsonify({'ok': False, 'error': 'Brak nazwy użytkownika'}), 400

    users = load_users()
    if username in users:
        return jsonify({'ok': False, 'error': 'Użytkownik już istnieje'}), 400

    if not password:
        password = os.urandom(4).hex()

    groups = [group] if group else []

    users[username] = {
        'username': username,
        'password': password,
        'display_name': display_name,
        'groups': groups,
    }
    save_users(users)
    return jsonify({
        'ok': True,
        'username': username,
        'password': password,
        'display_name': display_name,
        'groups': groups
    })


@app.route('/api/users/<username>/reset-password', methods=['POST'])
def reset_password(username):
    data = request.json or {}
    new_password = (data.get('password') or '').strip() or os.urandom(4).hex()

    users = load_users()
    if username not in users:
        return jsonify({'ok': False, 'error': 'Użytkownik nie istnieje'}), 404

    users[username]['password'] = new_password
    save_users(users)
    return jsonify({
        'ok': True,
        'username': username,
        'password': new_password
    })


@app.route('/api/users/<username>', methods=['PUT'])
def update_user(username):
    data = request.json or {}
    users = load_users()
    if username not in users:
        return jsonify({'ok': False, 'error': 'Użytkownik nie istnieje'}), 404

    if 'display_name' in data:
        users[username]['display_name'] = data['display_name'].strip()
    if 'password' in data and data['password'].strip():
        users[username]['password'] = data['password'].strip()
    if 'groups' in data:
        raw_g = data['groups']
        if isinstance(raw_g, list):
            users[username]['groups'] = raw_g
        elif isinstance(raw_g, str):
            users[username]['groups'] = [g.strip() for g in raw_g.split(',') if g.strip()]

    save_users(users)
    return jsonify({'ok': True, 'user': users[username]})


@app.route('/api/users/<username>', methods=['DELETE'])
def delete_user(username):
    if not username:
        return jsonify({'ok': False, 'error': 'Brak nazwy użytkownika'}), 400

    users = load_users()
    if username in users:
        del users[username]
        save_users(users)
    return jsonify({'ok': True})


@app.route('/api/users/bulk-delete', methods=['POST'])
def bulk_delete_users():
    data = request.json or {}
    usernames = data.get('usernames') or []
    if not isinstance(usernames, list) or not usernames:
        return jsonify({'ok': False, 'error': 'Nie podano użytkowników do usunięcia'}), 400

    users = load_users()
    deleted_count = 0
    for username in usernames:
        if username in users:
            del users[username]
            deleted_count += 1

    if deleted_count > 0:
        save_users(users)

    return jsonify({'ok': True, 'deleted_count': deleted_count})


@app.route('/api/users/bulk-add-group', methods=['POST'])
def bulk_add_group():
    data = request.json or {}
    usernames = data.get('usernames') or []
    group = (data.get('group') or '').strip()

    if not isinstance(usernames, list) or not usernames:
        return jsonify({'ok': False, 'error': 'Nie podano użytkowników'}), 400

    if not group:
        return jsonify({'ok': False, 'error': 'Nie podano nazwy grupy'}), 400

    users = load_users()
    updated_count = 0
    for username in usernames:
        if username in users:
            user_groups = users[username].get('groups')
            if not isinstance(user_groups, list):
                user_groups = []
            if group not in user_groups:
                user_groups.append(group)
                users[username]['groups'] = user_groups
                updated_count += 1

    if updated_count > 0:
        save_users(users)

    return jsonify({'ok': True, 'updated_count': updated_count, 'group': group})



@app.route('/api/online')
def get_online():
    if not os.path.exists('online.json'):
        return jsonify({})
    with open('online.json', 'r', encoding='utf-8') as file_handle:
        return jsonify(json.load(file_handle))


@app.route('/api/logs')
def list_logs():
    log_dir = get_log_dir()
    items = []

    def build_file_info(rel_path, abs_path):
        try:
            st = abs_path.stat()
            mtime = st.st_mtime
            dt = datetime.datetime.fromtimestamp(mtime)
            date_str = dt.strftime('%Y-%m-%d')
            time_str = dt.strftime('%H:%M:%S')
            size_bytes = st.st_size
        except Exception:
            mtime = 0
            date_str = 'Brak daty'
            time_str = ''
            size_bytes = 0

        return {
            'filename': str(rel_path),
            'date': date_str,
            'time': time_str,
            'mtime': mtime,
            'size': size_bytes
        }

    if log_dir.exists():
        for log_file in log_dir.glob('*.log'):
            if log_file.is_file():
                items.append(build_file_info(log_file.name, log_file))

    items.sort(key=lambda x: x['mtime'], reverse=True)
    return jsonify(items)


@app.route('/api/logs/<path:filename>')
def get_log_content(filename):
    target_path = safe_log_path(filename)
    if not target_path:
        return jsonify({'ok': False, 'error': 'Plik nie istnieje'}), 404

    try:
        with open(target_path, 'r', encoding='utf-8', errors='replace') as file_handle:
            lines = file_handle.readlines()
            content = ''.join(lines[-200:])
        return jsonify({'ok': True, 'content': content})
    except Exception as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 500


@app.route('/api/logs/<path:filename>/download-cmds')
def download_cmds_log(filename):
    clean_filename = os.path.basename(filename)
    stem = Path(clean_filename).stem

    if not COMMANDS_DIR.exists():
        return jsonify({'ok': False, 'error': 'Katalog komend nie istnieje'}), 404

    matching_files = list(COMMANDS_DIR.glob(f"**/{stem}*.cmds"))
    if not matching_files:
        return jsonify({'ok': False, 'error': 'Nie znaleziono odpowiedniego pliku .cmds dla tego logu'}), 404

    target_cmds = matching_files[0]
    for candidate in matching_files:
        if candidate.name == f"{stem}.cmds":
            target_cmds = candidate
            break

    try:
        return send_file(str(target_cmds.resolve()), as_attachment=True, download_name=target_cmds.name)
    except TypeError:
        return send_file(str(target_cmds.resolve()), as_attachment=True, attachment_filename=target_cmds.name)


@app.route('/api/import', methods=['POST'])
def import_users_csv():
    file = request.files.get('file')
    group_name = request.form.get('group', 'Bez grupy').strip()
    if not file:
        return jsonify({'ok': False, 'error': 'Brak pliku CSV'}), 400

    stream = StringIO(file.stream.read().decode('UTF8'), newline=None)
    csv_reader = csv.reader(stream, delimiter=';')
    users = load_users()

    imported_users = []
    for row in csv_reader:
        if len(row) < 2:
            continue
        nazwisko, imie = row[0].strip(), row[1].strip()
        if not nazwisko or not imie:
            continue

        base_username = remove_diacritics(imie.lower()) + '_' + remove_diacritics(nazwisko[:3].lower())
        username = base_username
        counter = 1
        while username in users:
            username = f"{base_username}{counter}"
            counter += 1

        generated_pass = os.urandom(4).hex()
        users[username] = {
            'username': username,
            'password': generated_pass,
            'display_name': f'{imie}_{nazwisko}',
            'groups': [group_name] if group_name else [],
        }
        imported_users.append({
            'username': username,
            'password': generated_pass,
            'display_name': f'{imie}_{nazwisko}',
            'group': group_name
        })

    save_users(users)
    return jsonify({
        'ok': True,
        'imported_count': len(imported_users),
        'users': imported_users
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
