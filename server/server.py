# server/server.py
import sys
import locale
import socket
import threading
import json
import os
import shutil
import zipfile
import subprocess
import time
import random
from datetime import datetime
from database import Database

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
else:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

class GameStoreServer:
    def __init__(self, host='0.0.0.0', dev_port=20113, lobby_port=30113):
        self.host = host
        self.dev_port = dev_port
        self.lobby_port = lobby_port
        self.db = Database()
        self.uploaded_games_dir = "uploaded_games"
        os.makedirs(self.uploaded_games_dir, exist_ok=True)
        self.public_ip=self.get_public_ip()
        
        self.active_sessions = {}  
        
        self.game_servers = {}
        self.game_ports = {}
        self.active_games = {}
        
    def start(self):
        dev_thread = threading.Thread(target=self.start_developer_server)
        dev_thread.daemon = True
        dev_thread.start()
        
        lobby_thread = threading.Thread(target=self.start_lobby_server)
        lobby_thread.daemon = True
        lobby_thread.start()
        
        print("="*60)
        print("Game Store Server Started")
        print("="*60)
        print(f"Dev Server: {self.host}:{self.dev_port}")
        print(f"Lobby Server: {self.host}:{self.lobby_port}")
        print(f"Games Directory: {os.path.abspath(self.uploaded_games_dir)}")
        print("="*60)
        print("Press Ctrl+C to stop")
        print("="*60)
        
        try:
            while True:
                self.cleanup_game_servers()
                threading.Event().wait(5)
        except KeyboardInterrupt:
            print("\n\nShutting down...")
            for room_id, process in self.game_servers.items():
                try:
                    process.terminate()
                except:
                    pass
    
    def get_public_ip(self):
        try:
            return "172.18.8.112"
        except:
            return self.host

    
    def cleanup_game_servers(self):
        rooms_to_remove = []
        for room_id, process in self.game_servers.items():
            if process.poll() is not None:
                rooms_to_remove.append(room_id)
                print(f"[Cleanup] Removing game server: {room_id}")
        
        for room_id in rooms_to_remove:
            del self.game_servers[room_id]
            if room_id in self.game_ports:
                del self.game_ports[room_id]
            if room_id in self.active_games:
                del self.active_games[room_id]
            
            self.db.update_room(room_id, {'status': 'finished'})
    
    def start_developer_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.dev_port))
        server.listen(5)
        
        print(f"[Dev Server] Listening...")
        
        while True:
            try:
                client, addr = server.accept()
                print(f"[Dev] Client connected: {addr}")
                thread = threading.Thread(target=self.handle_developer_client, args=(client,))
                thread.daemon = True
                thread.start()
            except Exception as e:
                print(f"[Dev Server] Error: {e}")
    
    def start_lobby_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.lobby_port))
        server.listen(5)
        
        print(f"[Lobby Server] Listening...")
        
        while True:
            try:
                client, addr = server.accept()
                print(f"[Lobby] Client connected: {addr}")
                thread = threading.Thread(target=self.handle_lobby_client, args=(client,))
                thread.daemon = True
                thread.start()
            except Exception as e:
                print(f"[Lobby Server] Error: {e}")
    
    def send_response(self, client, data):
        try:
            msg = json.dumps(data).encode('utf-8')
            client.sendall(len(msg).to_bytes(4, 'big') + msg)
        except Exception as e:
            print(f"[Send Response] Error: {e}")
    
    def recv_request(self, client):
        try:
            length_bytes = client.recv(4)
            if not length_bytes:
                return None
            length = int.from_bytes(length_bytes, 'big')
            
            data = b''            
            while len(data) < length:
                packet = client.recv(min(length - len(data), 4096))
                if not packet:
                    return None
                data += packet
            
            return json.loads(data.decode('utf-8'))
        except Exception as e:
            print(f"[Receive Request] Error: {e}")
            return None
    
    def handle_developer_client(self, client):
        try:
            while True:
                request = self.recv_request(client)
                if not request:
                    break
                
                action = request.get('action')
                print(f"[Dev] Action: {action}")
                
                if action == 'register':
                    success, msg = self.db.register_developer(
                        request['username'], request['password']
                    )
                    self.send_response(client, {'success': success, 'message': msg})
                
                elif action == 'login':
                    username = request['username']
                    dev_session_key = f'dev:{username}' 
                    
                    success, msg = self.db.login_developer(username, request['password'])
                    
                    if success and dev_session_key in self.active_sessions:
                        success, msg = False, "Developer already logged in elsewhere"
                    
                    if success:
                        self.active_sessions[dev_session_key] = 'developer'
                        print(f"[Dev] {username} logged in as developer")
                    else:
                        print(f"[Dev] Login failed: {msg}")
                    
                    self.send_response(client, {'success': success, 'message': msg})
                
                elif action == 'upload_game':
                    result = self.handle_game_upload(request)
                    self.send_response(client, result)
                
                elif action == 'get_my_games':
                    games = self.db.get_developer_active_games(request['developer'])
                    print(f"[Dev] Active Games: {len(games)}")
                    self.send_response(client, {'games': games})
                
                elif action == 'get_all_my_games':
                    games = self.db.get_developer_games(request['developer'])
                    print(f"[Dev] All Games: {len(games)}")
                    self.send_response(client, {'games': games})
                
                elif action == 'update_game':
                    result = self.handle_game_update(request)
                    self.send_response(client, result)
                
                elif action == 'remove_game':
                    game_id = request['game_id']
                    
                    game = self.db.get_game(game_id)
                    if not game:
                        self.send_response(client, {
                            'success': False,
                            'message': 'Game not found'
                        })
                        continue
                    
                    if game.get('developer') != request.get('developer'):
                        self.send_response(client, {
                            'success': False,
                            'message': 'Not your game'
                        })
                        continue
                    
                    rooms = self.db.get_all_rooms()
                    active_rooms = [r for r in rooms.values() 
                                   if r.get('game_id') == game_id and r.get('status') in ['waiting', 'playing']]
                    
                    if active_rooms:
                        self.send_response(client, {
                            'success': False,
                            'message': f'Cannot remove: {len(active_rooms)} active rooms'
                        })
                        continue
                    
                    success = self.db.delete_game(game_id)
                    self.send_response(client, {
                        'success': success,
                        'message': 'Game removed successfully' if success else 'Remove failed'
                    })
                
                elif action == 'logout':
                    username = request.get('username')
                    if username:
                        dev_session_key = f'dev:{username}'
                        if dev_session_key in self.active_sessions:
                            del self.active_sessions[dev_session_key]
                            print(f"[Dev] {username} logged out from developer")
                    break
                
                elif action == 'notify_version_update':
                    game_id = request.get('game_id')
                    new_version = request.get('version')
                    
                    print(f"[Dev] Version update notification: {game_id} -> {new_version}")
                    
                    self.send_response(client, {
                        'success': True,
                        'message': 'Version update recorded'
                    })
        
        except Exception as e:
            print(f"[Dev Client] Error: {e}")
        finally:
            try:
                client.close()
            except:
                pass
    
    def handle_lobby_client(self, client):
        try:
            while True:
                request = self.recv_request(client)
                if not request:
                    break
                
                action = request.get('action')
                print(f"[Lobby] Action: {action}")
                
                if action == 'register':
                    success, msg = self.db.register_player(
                        request['username'], request['password']
                    )
                    self.send_response(client, {'success': success, 'message': msg})
                
                elif action == 'login':
                    username = request['username']
                    player_session_key = f'player:{username}'  
                    
                    success, msg = self.db.login_player(username, request['password'])
                    
                    if success and player_session_key in self.active_sessions:
                        success, msg = False, "Player already logged in elsewhere"
                    
                    if success:
                        self.active_sessions[player_session_key] = 'player'
                        print(f"[Lobby] {username} logged in as player")
                    else:
                        print(f"[Lobby] Login failed: {msg}")
                    
                    self.send_response(client, {'success': success, 'message': msg})
                
                elif action == 'get_games':
                    games = self.db.get_all_games()
                    active_games = {k: v for k, v in games.items() 
                                   if v.get('status') != 'removed'}
                    print(f"[Lobby] Active Games: {len(active_games)}")
                    self.send_response(client, {'games': active_games})
                
                elif action == 'get_game_detail':
                    game_id = request['game_id']
                    game = self.db.get_game(game_id)
                    
                    if game and game.get('status') == 'removed':
                        self.send_response(client, {
                            'game': None,
                            'reviews': [],
                            'removed': True,
                            'message': 'This game has been removed by developer'
                        })
                        continue
                    
                    reviews = self.db.get_game_reviews(game_id)
                    self.send_response(client, {'game': game, 'reviews': reviews, 'removed': False})
                
                elif action == 'download_game':
                    result = self.handle_game_download(request, client)
                    self.send_response(client, result)
                
                elif action == 'check_version':
                    result = self.handle_check_version(request)
                    self.send_response(client, result)
                
                elif action == 'mark_as_latest':
                    result = self.handle_mark_as_latest(request)
                    self.send_response(client, result)
                
                elif action == 'add_review':
                    player = request['player']
                    game_id = request['game_id']
                    
                    game = self.db.get_game(game_id)
                    if game and game.get('status') == 'removed':
                        self.send_response(client, {
                            'success': False,
                            'message': 'Cannot review removed game'
                        })
                        continue
                    
                    if not self.db.has_player_played_game(player, game_id):
                        self.send_response(client, {
                            'success': False,
                            'message': 'Must play game before reviewing'
                        })
                        continue
                    
                    self.db.add_review(
                        request['game_id'],
                        request['player'],
                        request['rating'],
                        request['comment']
                    )
                    self.send_response(client, {'success': True, 'message': 'Review added'})
                
                elif action == 'create_room':
                    result = self.handle_create_room(request)
                    self.send_response(client, result)
                
                elif action == 'get_rooms':
                    rooms = self.db.get_all_rooms()
                    self.send_response(client, {'rooms': rooms})
                
                elif action == 'get_downloads':
                    downloads = self.db.get_player_downloads(request['player'])
                    self.send_response(client, {'downloads': downloads})
                
                elif action == 'record_play':
                    player = request['player']
                    game_id = request['game_id']
                    
                    game = self.db.get_game(game_id)
                    if game and game.get('status') == 'removed':
                        self.send_response(client, {
                            'success': False,
                            'message': 'Game has been removed'
                        })
                        continue
                    
                    success = self.db.record_play(player, game_id)
                    self.send_response(client, {'success': success})
                
                elif action == 'get_played_games':
                    player = request.get('player')
                    played_games = self.db.get_player_played_games(player)
                    self.send_response(client, {'played_games': played_games})
                
                elif action == 'check_can_review':
                    player = request.get('player')
                    game_id = request.get('game_id')
                    
                    game = self.db.get_game(game_id)
                    if game and game.get('status') == 'removed':
                        self.send_response(client, {'can_review': False})
                        continue
                    
                    can_review = self.db.has_player_played_game(player, game_id)
                    self.send_response(client, {'can_review': can_review})
                
                elif action == 'logout':
                    username = request.get('username')
                    if username:
                        player_session_key = f'player:{username}'
                        if player_session_key in self.active_sessions:
                            del self.active_sessions[player_session_key]
                            print(f"[Lobby] {username} logged out from player")
                    break
                
                elif action == 'get_room':
                    room_id = request.get('room_id')
                    room = self.db.get_room(room_id)
                    self.send_response(client, {'room': room})
                
                elif action == 'update_room':
                    result = self.handle_update_room(request)
                    self.send_response(client, result)
                
                elif action == 'delete_room':
                    result = self.handle_delete_room(request)
                    self.send_response(client, result)
                
                elif action == 'start_game':
                    result = self.handle_start_game(request)
                    self.send_response(client, result)
                
                elif action == 'get_game_connection':
                    result = self.handle_get_game_connection(request)
                    self.send_response(client, result)
        
        except Exception as e:
            print(f"[Lobby Client] Error: {e}")
        finally:
            try:
                client.close()
            except:
                pass
    
    def handle_game_upload(self, request):
        try:
            game_id = request['game_id']
            game_data = request['game_data']
            zip_data = bytes.fromhex(request['zip_data'])
            
            game_dir = os.path.join(self.uploaded_games_dir, game_id)
            
            if os.path.exists(game_dir):
                try:
                    shutil.rmtree(game_dir)
                except Exception as e:
                    print(f"[Upload] Warning: {e}")
            
            os.makedirs(game_dir, exist_ok=True)
            
            zip_path = os.path.join(game_dir, f"{game_id}.zip")
            with open(zip_path, 'wb') as f:
                f.write(zip_data)
            
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(game_dir)
            except Exception as e:
                return {'success': False, 'message': f'Extract failed: {str(e)}'}
            
            config_path = os.path.join(game_dir, 'config.json')
            if not os.path.exists(config_path):
                config_found = False
                for root, dirs, files in os.walk(game_dir):
                    if 'config.json' in files:
                        config_path = os.path.join(root, 'config.json')
                        config_found = True
                        break
                
                if not config_found:
                    return {'success': False, 'message': 'Missing config.json'}
            
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                required_fields = ['game_name', 'type', 'server_command', 'client_command']
                for field in required_fields:
                    if field not in config:
                        return {'success': False, 'message': f'Missing field: {field}'}
                
            except json.JSONDecodeError as e:
                return {'success': False, 'message': f'Invalid config.json: {str(e)}'}
            
            game_data['file_path'] = game_dir
            game_data['upload_time'] = datetime.now().isoformat()
            game_data['status'] = 'active'  
            self.db.add_game(game_id, game_data)
            
            return {'success': True, 'message': 'Upload successful'}
        
        except Exception as e:
            return {'success': False, 'message': f'Upload failed: {str(e)}'}
    
    def handle_game_update(self, request):
        try:
            game_id = request['game_id']
            
            game = self.db.get_game(game_id)
            if game and game.get('status') == 'removed':
                return {'success': False, 'message': 'Cannot update removed game'}
            
            new_version = request['version']
            zip_data = bytes.fromhex(request['zip_data'])
            
            game_dir = os.path.join(self.uploaded_games_dir, game_id)
            
            if os.path.exists(game_dir):
                backup_dir = f"{game_dir}_backup_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                shutil.move(game_dir, backup_dir)
            
            os.makedirs(game_dir, exist_ok=True)
            
            zip_path = os.path.join(game_dir, f"{game_id}.zip")
            with open(zip_path, 'wb') as f:
                f.write(zip_data)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(game_dir)
            
            success = self.db.update_game(game_id, {
                'version': new_version,
                'updated_at': datetime.now().isoformat()
            })
            
            if not success:
                return {'success': False, 'message': 'Update failed - game may be removed'}
            
            print(f"[Update] Game {game_id} updated to version {new_version}")
            
            return {'success': True, 'message': 'Update successful'}
        
        except Exception as e:
            return {'success': False, 'message': f'Update failed: {str(e)}'}
    
    def handle_check_version(self, request):
        try:
            player = request.get('player')
            game_id = request.get('game_id')
            
            if not player or not game_id:
                return {'success': False, 'message': 'Missing parameters'}
            
            game = self.db.get_game(game_id)
            if not game:
                return {'success': False, 'message': 'Game not found'}
            
            if game.get('status') == 'removed':
                return {
                    'success': True,
                    'update_available': False,
                    'removed': True,
                    'message': 'Game has been removed'
                }
            
            result = self.db.check_version_update(player, game_id)
            
            return {
                'success': True,
                'update_available': result.get('update_available', False),
                'local_version': result.get('local_version'),
                'server_version': result.get('server_version', game.get('version')),
                'game_name': result.get('game_name', game.get('name', 'Unknown'))
            }
        
        except Exception as e:
            return {'success': False, 'message': f'Version check failed: {str(e)}'}
    
    def handle_mark_as_latest(self, request):
        try:
            player = request.get('player')
            game_id = request.get('game_id')
            
            if not player or not game_id:
                return {'success': False, 'message': 'Missing parameters'}
            
            success = self.db.mark_as_latest(player, game_id)
            
            return {
                'success': success,
                'message': 'Marked as latest' if success else 'Failed to mark as latest'
            }
        
        except Exception as e:
            return {'success': False, 'message': f'Mark as latest failed: {str(e)}'}
    
    def handle_game_download(self, request, client):
        try:
            game_id = request['game_id']
            player = request['player']
            is_update = request.get('is_update', False)
            
            game = self.db.get_game(game_id)
            if not game:
                return {'success': False, 'message': 'Game not found'}
            
            if game.get('status') == 'removed':
                return {
                    'success': False,
                    'message': 'This game has been removed by developer',
                    'removed': True
                }
            
            game_dir = os.path.join(self.uploaded_games_dir, game_id)
            zip_path = os.path.join(game_dir, f"{game_id}.zip")
            
            if not os.path.exists(zip_path):
                return {'success': False, 'message': 'Game file missing'}
            
            with open(zip_path, 'rb') as f:
                zip_data = f.read()
            
            self.db.record_download(player, game_id, game['version'], is_update)
            
            return {
                'success': True,
                'zip_data': zip_data.hex(),
                'version': game['version'],
                'config': game.get('config', {})
            }
        
        except Exception as e:
            return {'success': False, 'message': f'Download failed: {str(e)}'}
    
    def handle_create_room(self, request):
        try:
            room_id = request['room_id']
            room_data = request['room_data']
            game_id = room_data.get('game_id')
            
            game = self.db.get_game(game_id)
            if game and game.get('status') == 'removed':
                return {
                    'success': False,
                    'message': 'Cannot create room for removed game'
                }
            
            player = room_data.get('host')
            if player and game_id:
                downloads = self.db.get_player_downloads(player)
                if game_id in downloads:
                    download_info = downloads[game_id]
                    if download_info.get('update_available') == True:
                        return {
                            'success': False,
                            'message': 'Please update to latest version before creating room',
                            'needs_update': True,
                            'local_version': download_info.get('version'),
                            'server_version': game.get('version')
                        }
            
            self.db.create_room(room_id, room_data)
            
            return {'success': True, 'message': 'Room created', 'room_id': room_id}
        
        except Exception as e:
            return {'success': False, 'message': f'Create failed: {str(e)}'}
    
    def handle_get_room(self, request):
        room_id = request.get('room_id')
        room = self.db.get_room(room_id)
        return {'room': room}
    
    def handle_update_room(self, request):
        room_id = request['room_id']
        room_data = request['room_data']
        
        success = self.db.update_room(room_id, room_data)
        return {'success': success}
    
    def handle_delete_room(self, request):
        room_id = request['room_id']
        success = self.db.delete_room(room_id)
        return {'success': success}
    
    def handle_start_game(self, request):
        try:
            room_id = request['room_id']
            player = request.get('player')
            
            room = self.db.get_room(room_id)
            if not room:
                return {'success': False, 'message': 'Room not found'}
            
            if room.get('host') != player:
                return {'success': False, 'message': 'Only host can start'}
            
            game_id = room.get('game_id')
            game_info = self.db.get_game(game_id)
            
            if not game_info:
                return {'success': False, 'message': 'Game not found'}
            
            if game_info.get('status') == 'removed':
                return {'success': False, 'message': 'Game has been removed'}
            
            for player_name in room.get('players', []):
                downloads = self.db.get_player_downloads(player_name)
                if game_id in downloads:
                    download_info = downloads[game_id]
                    if download_info.get('update_available') == True:
                        return {
                            'success': False,
                            'message': f'Player {player_name} needs to update to latest version',
                            'needs_update': True,
                            'player': player_name,
                            'local_version': download_info.get('version'),
                            'server_version': game_info.get('version')
                        }
            
            min_players = game_info.get('min_players', 1)
            if len(room.get('players', [])) < min_players:
                return {'success': False, 'message': f'Need at least {min_players} players'}
            
            self.db.update_room(room_id, {
                'status': 'starting',
                'start_time': datetime.now().isoformat()
            })
            
            result = self.launch_game_server(game_id, room_id, room.get('players', []))
            
            if result['success']:
                self.db.update_room(room_id, {
                    'status': 'playing',
                    'game_server_port': result['port'],
                    'game_server_pid': result['pid']
                })
                
                return {
                    'success': True,
                    'message': 'Game started',
                    'port': result['port'],
                    'game_info': game_info
                }
            else:
                self.db.update_room(room_id, {'status': 'waiting'})
                return result
            
        except Exception as e:
            return {'success': False, 'message': f'Start failed: {str(e)}'}
    
    def launch_game_server(self, game_id, room_id, players):
        try:
            game_port = self.find_available_port(6000, 7000)
            
            game_dir = os.path.join(self.uploaded_games_dir, game_id)
            if not os.path.exists(game_dir):
                return {'success': False, 'message': 'Game files missing'}
            
            config_path = os.path.join(game_dir, 'config.json')
            if not os.path.exists(config_path):
                return {'success': False, 'message': 'Config missing'}
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            server_script = config['server_command'].split()
            
            server_file = None
            
            if len(server_script) > 1:
                server_file = os.path.join(game_dir, server_script[1])
                if not os.path.exists(server_file):
                    server_file = None
            
            if not server_file:
                server_file = os.path.join(game_dir, 'server.py')
            
            if not os.path.exists(server_file):
                for root, dirs, files in os.walk(game_dir):
                    for file in files:
                        if file.lower() == 'server.py':
                            server_file = os.path.join(root, file)
                            break
                    if server_file and os.path.exists(server_file):
                        break
            
            if not server_file or not os.path.exists(server_file):
                return {'success': False, 'message': 'Server file missing'}
            
            game_dir = os.path.abspath(game_dir)
            server_file = os.path.abspath(server_file)
            
            cmd = [sys.executable, server_file, str(game_port)]
            
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            process = subprocess.Popen(
                cmd,
                cwd=game_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                universal_newlines=False,
                bufsize=1
            )
            
            time.sleep(3)
            
            if process.poll() is not None:
                try:
                    stdout, stderr = process.communicate(timeout=1)
                    error_msg = ""
                    
                    try:
                        if stderr:
                            error_msg = stderr.decode('utf-8', errors='replace')
                        elif stdout:
                            error_msg = stdout.decode('utf-8', errors='replace')
                    except:
                        try:
                            if stderr:
                                error_msg = stderr.decode('latin-1', errors='replace')
                        except:
                            error_msg = "Cannot read error"
                    
                    return {'success': False, 'message': f'Server start failed: {error_msg[:200]}'}
                
                except subprocess.TimeoutExpired:
                    return {'success': False, 'message': 'Server start timeout'}
            
            self.game_servers[room_id] = process
            self.game_ports[room_id] = game_port
            self.active_games[room_id] = {
                'game_id': game_id,
                'players': players,
                'start_time': datetime.now().isoformat()
            }
            
            return {
                'success': True,
                'port': game_port,
                'pid': process.pid,
                'game_info': config
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Launch error: {str(e)}'}
    
    def find_available_port(self, start_port, end_port):
        for port in range(start_port, end_port + 1):
            if port not in self.game_ports.values():
                return port
        return random.randint(start_port, end_port)
    
    def handle_get_game_connection(self, request):
        try:
            room_id = request['room_id']
            
            if room_id not in self.game_ports:
                return {'success': False, 'message': 'Game not running'}
            
            return {
                'success': True,
                'host': self.public_ip,
                'port': self.game_ports[room_id],
                'room_id': room_id
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def check_game_files(self, game_id):
        try:
            game_dir = os.path.join(self.uploaded_games_dir, game_id)
            
            if not os.path.exists(game_dir):
                return False, f"Directory missing: {game_dir}"
            
            config_path = os.path.join(game_dir, 'config.json')
            if not os.path.exists(config_path):
                for root, dirs, files in os.walk(game_dir):
                    if 'config.json' in files:
                        config_path = os.path.join(root, 'config.json')
                        break
            
            if not os.path.exists(config_path):
                return False, "config.json missing"
            
            server_found = False
            for root, dirs, files in os.walk(game_dir):
                for file in files:
                    if file.lower() == 'server.py':
                        server_found = True
                        break
                if server_found:
                    break
            
            if not server_found:
                return False, "server.py missing"
            
            client_found = False
            for root, dirs, files in os.walk(game_dir):
                for file in files:
                    if file.lower() == 'client.py':
                        client_found = True
                        break
                if client_found:
                    break
            
            if not client_found:
                return False, "client.py missing"
            
            return True, "Files OK"
        
        except Exception as e:
            return False, f"Check failed: {str(e)}"

if __name__ == '__main__':
    server = GameStoreServer()
    server.start()
