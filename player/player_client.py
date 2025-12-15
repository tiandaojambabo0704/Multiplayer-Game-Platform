# player/player_client.py
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import socket
import json
import os
import zipfile
from datetime import datetime
import subprocess
import threading
import time
import sys
import locale

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
else:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

class PlayerClient:
    def __init__(self, host='172.18.8.112', port=30113):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.username = None
        self.download_dir = "downloads"
        os.makedirs(self.download_dir, exist_ok=True)
        
        self.root = tk.Tk()
        self.root.title("🎮 遊戲大廳")
        self.root.geometry("900x700")
        
        self.show_login_screen()
        self.game_starting = False
        self.current_game_process = None
        
        self.room_update_running = False
        self.current_room_id = None
        self.current_room_data = None
        
        # 版本檢查相關
        self.version_check_queue = []
        self.version_check_running = False
    
    def connect(self):
        try:
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            self.connected = True
            return True
        except Exception as e:
            messagebox.showerror("錯誤", f"無法連接到服務器: {str(e)}")
            self.connected = False
            return False
    
    def send_request(self, data):
        try:
            if not self.socket or not self.connected:
                return {'success': False, 'message': '未連接到服務器'}
            
            msg = json.dumps(data).encode('utf-8')
            self.socket.sendall(len(msg).to_bytes(4, 'big') + msg)
            
            length_bytes = self.socket.recv(4)
            if not length_bytes:
                self.connected = False
                return {'success': False, 'message': '連接已中斷'}
            
            length = int.from_bytes(length_bytes, 'big')
            response = b''            
            while len(response) < length:
                packet = self.socket.recv(min(length - len(response), 4096))
                if not packet:
                    self.connected = False
                    return {'success': False, 'message': '連接已中斷'}
                response += packet
            
            return json.loads(response.decode('utf-8'))
        except socket.timeout:
            self.connected = False
            return {'success': False, 'message': '連線超時'}
        except ConnectionError:
            self.connected = False
            return {'success': False, 'message': '連線錯誤'}
        except json.JSONDecodeError:
            return {'success': False, 'message': '回應格式錯誤'}
        except Exception as e:
            print(f"Send error: {str(e)}")
            self.connected = False
            return None
    
    def safe_send_request(self, data, show_error=True):
        response = self.send_request(data)
        if response is None:
            if show_error:
                messagebox.showerror("錯誤", "通訊失敗，請檢查連線")
            return None
        return response
    
    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()
    
    def show_login_screen(self):
        self.clear_window()
        
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(expand=True)
        
        ttk.Label(frame, text="🎮 遊戲大廳", font=("Arial", 24, "bold")).pack(pady=20)
        
        ttk.Label(frame, text="帳號:").pack(pady=5)
        username_entry = ttk.Entry(frame, width=30)
        username_entry.pack(pady=5)
        
        ttk.Label(frame, text="密碼:").pack(pady=5)
        password_entry = ttk.Entry(frame, width=30, show="*")
        password_entry.pack(pady=5)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=20)
        
        def do_login():
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            
            if not username or not password:
                messagebox.showwarning("警告", "請填寫所有欄位")
                return
            
            if not self.connect():
                return
            
            response = self.safe_send_request({
                'action': 'login',
                'username': username,
                'password': password
            })
            
            if response and response['success']:
                self.username = username
                player_download_dir = os.path.join(self.download_dir, username)
                os.makedirs(player_download_dir, exist_ok=True)
                messagebox.showinfo("成功", "登入成功！")
                
                # 登入後檢查所有下載遊戲的版本
                self.check_all_game_versions_after_login()
                
                self.show_main_menu()
            elif response:
                messagebox.showerror("錯誤", response['message'])
            else:
                messagebox.showerror("錯誤", "登入失敗")
        
        def do_register():
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            
            if not username or not password:
                messagebox.showwarning("警告", "請填寫所有欄位")
                return
            
            if not self.connect():
                return
            
            response = self.safe_send_request({
                'action': 'register',
                'username': username,
                'password': password
            })
            
            if response and response['success']:
                messagebox.showinfo("成功", "註冊成功！請登入")
            elif response:
                messagebox.showerror("錯誤", response['message'])
            else:
                messagebox.showerror("錯誤", "註冊失敗")
        
        ttk.Button(btn_frame, text="登入", command=do_login, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="註冊", command=do_register, width=12).pack(side=tk.LEFT, padx=5)
    
    def check_all_game_versions_after_login(self):
        """登入後檢查所有已下載遊戲的版本"""
        if not self.username:
            return
        
        def check_versions():
            try:
                # 取得所有下載的遊戲
                response = self.safe_send_request({
                    'action': 'get_downloads',
                    'player': self.username
                }, show_error=False)
                
                if not response:
                    return
                
                downloads = response.get('downloads', {})
                
                # 對每個遊戲檢查版本
                for game_id, download_info in downloads.items():
                    if download_info.get('status') == 'active':
                        self.check_single_game_version(game_id, silent=True)
                        
                        # 稍微延遲避免請求過於密集
                        time.sleep(0.5)
            
            except Exception as e:
                print(f"Version check error: {str(e)}")
        
        # 在背景執行緒中檢查版本
        thread = threading.Thread(target=check_versions, daemon=True)
        thread.start()
    
    def check_single_game_version(self, game_id, silent=False):
        """檢查單個遊戲的版本"""
        try:
            response = self.safe_send_request({
                'action': 'check_version',
                'player': self.username,
                'game_id': game_id
            }, show_error=False)
            
            if not response or not response.get('success'):
                return
            
            if response.get('removed'):
                # 遊戲已下架
                if not silent:
                    messagebox.showinfo("遊戲下架", "此遊戲已被開發者下架")
                return
            
            if response.get('update_available'):
                local_version = response.get('local_version')
                server_version = response.get('server_version')
                game_name = response.get('game_name', '遊戲')
                
                # 顯示更新提示
                self.root.after(0, lambda: self.show_update_prompt(
                    game_id, game_name, local_version, server_version
                ))
        
        except Exception as e:
            print(f"Version check error for {game_id}: {str(e)}")
    
    def show_update_prompt(self, game_id, game_name, local_version, server_version):
        """顯示更新提示對話框"""
        win = tk.Toplevel(self.root)
        win.title("🔄 遊戲更新可用")
        win.geometry("500x300")
        win.transient(self.root)
        win.grab_set()
        
        frame = ttk.Frame(win, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="🔄 遊戲更新通知", 
                 font=("Arial", 16, "bold")).pack(pady=10)
        
        info_text = f"""
遊戲: {game_name}

發現新版本！
目前版本: {local_version}
最新版本: {server_version}

有新版本可用，建議立即更新以獲得最佳遊戲體驗。
        """
        
        ttk.Label(frame, text=info_text.strip(), justify=tk.LEFT,
                 font=("Arial", 11)).pack(pady=10)
        
        warning_text = "⚠️ 注意：使用舊版本將無法建立新房間，也無法加入使用新版本的房間。"
        ttk.Label(frame, text=warning_text, justify=tk.LEFT,
                 font=("Arial", 10), foreground="orange", wraplength=400).pack(pady=10)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=20)
        
        def update_now():
            win.destroy()
            self.download_game_with_update(game_id, is_update=True)
        
        def remind_later():
            win.destroy()
        
        def ignore_update():
            win.destroy()
            # 標記為已忽略（暫時）
            pass
        
        ttk.Button(btn_frame, text="立即更新", command=update_now,
                  width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="稍後提醒", command=remind_later,
                  width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="忽略", command=ignore_update,
                  width=12).pack(side=tk.LEFT, padx=5)
    
    def download_game_with_update(self, game_id, is_update=False):
        """下載遊戲（可選是否為更新）"""
        response = self.safe_send_request({
            'action': 'download_game',
            'game_id': game_id,
            'player': self.username,
            'is_update': is_update
        })
        
        if not response or not response.get('success'):
            error_msg = response.get('message', '下載失敗') if response else '下載失敗'
            messagebox.showerror("錯誤", error_msg)
            return False
        
        try:
            zip_data = bytes.fromhex(response['zip_data'])
            player_dir = os.path.join(self.download_dir, self.username)
            game_dir = os.path.join(player_dir, game_id)
            
            # 如果是更新，備份舊版本
            if is_update and os.path.exists(game_dir):
                backup_dir = f"{game_dir}_backup_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                try:
                    import shutil
                    shutil.copytree(game_dir, backup_dir)
                except Exception as e:
                    print(f"Backup failed: {str(e)}")
            
            os.makedirs(game_dir, exist_ok=True)
            
            zip_path = os.path.join(game_dir, f"{game_id}.zip")
            with open(zip_path, 'wb') as f:
                f.write(zip_data)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(game_dir)
            
            os.remove(zip_path)
            
            # 標記為最新版本
            self.mark_game_as_latest(game_id)
            
            if is_update:
                messagebox.showinfo("成功", f"遊戲已更新到版本 {response['version']}")
            else:
                messagebox.showinfo("成功", f"遊戲已下載到: {game_dir}")
            
            return True
        
        except Exception as e:
            messagebox.showerror("錯誤", f"下載失敗: {str(e)}")
            return False
    
    def mark_game_as_latest(self, game_id):
        """標記遊戲為最新版本"""
        response = self.safe_send_request({
            'action': 'mark_as_latest',
            'player': self.username,
            'game_id': game_id
        }, show_error=False)
        
        return response and response.get('success')
    
    def show_main_menu(self):
        self.clear_window()
        
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(expand=True)
        
        ttk.Label(frame, text=f"👤 歡迎, {self.username}", font=("Arial", 18)).pack(pady=20)
        
        ttk.Button(frame, text="🎮 瀏覽遊戲商城", command=self.show_game_store, width=30).pack(pady=10)
        ttk.Button(frame, text="📥 我的遊戲", command=self.show_my_downloads, width=30).pack(pady=10)
        ttk.Button(frame, text="🏠 大廳 & 房間", command=self.show_lobby, width=30).pack(pady=10)
        ttk.Button(frame, text="🔄 檢查遊戲更新", command=self.check_all_versions, width=30).pack(pady=10)
        ttk.Button(frame, text="🚪 登出", command=self.logout, width=30).pack(pady=10)
    
    def check_all_versions(self):
        """手動檢查所有遊戲版本"""
        if not self.username:
            return
        
        def check_in_background():
            try:
                # 取得所有下載的遊戲
                response = self.safe_send_request({
                    'action': 'get_downloads',
                    'player': self.username
                }, show_error=False)
                
                if not response:
                    self.root.after(0, lambda: messagebox.showinfo("檢查完成", "無法連接到伺服器"))
                    return
                
                downloads = response.get('downloads', {})
                update_count = 0
                
                # 對每個遊戲檢查版本
                for game_id, download_info in downloads.items():
                    if download_info.get('status') == 'active':
                        time.sleep(0.3)  # 避免請求過於密集
                        
                        version_response = self.safe_send_request({
                            'action': 'check_version',
                            'player': self.username,
                            'game_id': game_id
                        }, show_error=False)
                        
                        if version_response and version_response.get('update_available'):
                            update_count += 1
                
                # 顯示結果
                self.root.after(0, lambda: self.show_check_result(update_count, len(downloads)))
            
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("錯誤", f"檢查失敗: {str(e)}"))
        
        messagebox.showinfo("檢查中", "正在檢查遊戲更新...")
        thread = threading.Thread(target=check_in_background, daemon=True)
        thread.start()
    
    def show_check_result(self, update_count, total_games):
        """顯示版本檢查結果"""
        if update_count == 0:
            messagebox.showinfo("檢查完成", f"所有 {total_games} 個遊戲都是最新版本！")
        else:
            messagebox.showinfo("檢查完成", 
                f"發現 {update_count} 個遊戲有更新可用！\n\n"
                f"當您嘗試建立房間或遊玩遊戲時，系統會提示您更新。")
    
    def show_game_store(self):
        self.clear_window()
        
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="🎮 遊戲商城", font=("Arial", 18, "bold")).pack(pady=10)
        
        response = self.safe_send_request({'action': 'get_games'})
        
        if not response:
            ttk.Label(frame, text="載入失敗").pack(pady=20)
            ttk.Button(frame, text="返回", command=self.show_main_menu).pack(pady=10)
            return
        
        games = response.get('games', {})
        
        if not games:
            ttk.Label(frame, text="目前沒有遊戲", font=("Arial", 14)).pack(pady=20)
            ttk.Button(frame, text="返回", command=self.show_main_menu).pack(pady=10)
            return
        
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        columns = ('name', 'developer', 'type', 'players', 'version')
        tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        tree.heading('name', text='遊戲名稱')
        tree.heading('developer', text='開發者')
        tree.heading('type', text='類型')
        tree.heading('players', text='人數')
        tree.heading('version', text='版本')
        
        tree.column('name', width=200)
        tree.column('developer', width=150)
        tree.column('type', width=80)
        tree.column('players', width=100)
        tree.column('version', width=80)
        
        for game_id, game_data in games.items():
            players_text = f"{game_data['min_players']}-{game_data['max_players']}"
            tree.insert('', tk.END, values=(
                game_data['name'],
                game_data['developer'],
                game_data['type'].upper(),
                players_text,
                game_data['version']
            ), tags=(game_id,))
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scrollbar.set)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)
        
        def view_detail():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("警告", "請選擇遊戲")
                return
            
            game_id = tree.item(selected[0])['tags'][0]
            self.show_game_detail(game_id)
        
        def download_game():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("警告", "請選擇遊戲")
                return
            
            game_id = tree.item(selected[0])['tags'][0]
            self.download_game_with_update(game_id, is_update=False)
        
        ttk.Button(btn_frame, text="查看詳情", command=view_detail, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="下載遊戲", command=download_game, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="返回", command=self.show_main_menu, width=12).pack(side=tk.LEFT, padx=5)
    
    def show_game_detail(self, game_id):
        self.clear_window()
        
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="📝 遊戲詳情", font=("Arial", 18, "bold")).pack(pady=10)
        
        response = self.safe_send_request({
            'action': 'get_game_detail',
            'game_id': game_id
        })
        
        if not response or not response.get('game'):
            ttk.Label(frame, text="載入失敗").pack(pady=20)
            ttk.Button(frame, text="返回", command=self.show_game_store).pack(pady=10)
            return
        
        game = response['game']
        reviews = response.get('reviews', [])
        
        ttk.Label(frame, text=game['name'], font=("Arial", 20, "bold")).pack(pady=10)
        
        info_frame = ttk.LabelFrame(frame, text="遊戲資訊", padding="10")
        info_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(info_frame, text=f"開發者: {game['developer']}").pack(anchor=tk.W, pady=2)
        ttk.Label(info_frame, text=f"類型: {game['type'].upper()}").pack(anchor=tk.W, pady=2)
        ttk.Label(info_frame, text=f"人數: {game['min_players']}-{game['max_players']}").pack(anchor=tk.W, pady=2)
        ttk.Label(info_frame, text=f"版本: {game['version']}").pack(anchor=tk.W, pady=2)
        
        self.current_game_id_for_review = game_id
        
        can_review_response = self.safe_send_request({
            'action': 'check_can_review',
            'player': self.username,
            'game_id': game_id
        }, show_error=False)
        
        self.can_review_current_game = False
        if can_review_response and can_review_response.get('can_review'):
            self.can_review_current_game = True
        
        desc_frame = ttk.LabelFrame(frame, text="遊戲簡介", padding="10")
        desc_frame.pack(fill=tk.X, pady=10)
        
        desc_text = scrolledtext.ScrolledText(desc_frame, width=60, height=4, wrap=tk.WORD)
        desc_text.insert("1.0", game.get('description', '無簡介'))
        desc_text.config(state=tk.DISABLED)
        desc_text.pack()
        
        review_frame = ttk.LabelFrame(frame, text=f"玩家評論 ({len(reviews)})", padding="10")
        review_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        if reviews:
            validated_reviews = [r for r in reviews if r.get('validated', True)]
            if validated_reviews:
                avg_rating = sum(r['rating'] for r in validated_reviews) / len(validated_reviews)
                ttk.Label(review_frame, text=f"⭐ 平均評分: {avg_rating:.1f}/5.0 (已驗證評論: {len(validated_reviews)}則)", 
                         font=("Arial", 12, "bold")).pack(pady=5)
            else:
                ttk.Label(review_frame, text=f"⭐ 尚無已驗證評論", 
                         font=("Arial", 12, "bold")).pack(pady=5)
            
            review_text = scrolledtext.ScrolledText(review_frame, width=60, height=8, wrap=tk.WORD)
            for r in reviews[:5]:
                verified_mark = "✅ " if r.get('validated', True) else "⚠️ "
                review_text.insert(tk.END, f"{verified_mark}{r['player']} - {'⭐' * r['rating']}\n")
                review_text.insert(tk.END, f"{r['comment']}\n\n")
            review_text.config(state=tk.DISABLED)
            review_text.pack(fill=tk.BOTH, expand=True)
        else:
            ttk.Label(review_frame, text="尚無評論").pack(pady=10)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)
        
        def add_review():
            if not self.can_review_current_game:
                messagebox.showwarning("無法評論", "你必須先玩過這款遊戲才能評論！\n\n請先下載並遊玩此遊戲後再試。")
                return
            self.show_add_review(game_id)
        
        def download():
            self.download_game_with_update(game_id, is_update=False)
        
        review_btn = ttk.Button(btn_frame, text="撰寫評論", command=add_review, width=12)
        if not self.can_review_current_game:
            review_btn.config(state=tk.DISABLED)
            ttk.Label(btn_frame, text="(需玩過遊戲)", foreground="gray").pack(side=tk.LEFT, padx=2)
        
        review_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="下載遊戲", command=download, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="返回", command=self.show_game_store, width=12).pack(side=tk.LEFT, padx=5)
    
    def show_add_review(self, game_id):
        win = tk.Toplevel(self.root)
        win.title("撰寫評論")
        win.geometry("400x300")
        
        frame = ttk.Frame(win, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="評分 (1-5):").pack(pady=5)
        rating_var = tk.IntVar(value=5)
        rating_frame = ttk.Frame(frame)
        rating_frame.pack(pady=5)
        for i in range(1, 6):
            ttk.Radiobutton(rating_frame, text=f"{i}⭐", variable=rating_var, value=i).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(frame, text="評論內容:").pack(pady=5)
        comment_text = scrolledtext.ScrolledText(frame, width=40, height=8)
        comment_text.pack(pady=5)
        
        def submit():
            rating = rating_var.get()
            comment = comment_text.get("1.0", tk.END).strip()
            
            if not comment:
                messagebox.showwarning("警告", "請輸入評論內容")
                return
            
            response = self.safe_send_request({
                'action': 'add_review',
                'game_id': game_id,
                'player': self.username,
                'rating': rating,
                'comment': comment
            })
            
            if response and response.get('success'):
                messagebox.showinfo("成功", "評論已送出")
                win.destroy()
                self.show_game_detail(game_id)
            elif response:
                messagebox.showerror("錯誤", response.get('message', '送出失敗'))
            else:
                messagebox.showerror("錯誤", "送出失敗")
        
        ttk.Button(frame, text="送出", command=submit, width=12).pack(pady=10)
    
    def show_my_downloads(self):
        self.clear_window()
        
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="📥 我的遊戲", font=("Arial", 18, "bold")).pack(pady=10)
        
        response = self.safe_send_request({
            'action': 'get_downloads',
            'player': self.username
        })
        
        if not response:
            ttk.Label(frame, text="載入失敗").pack(pady=20)
            ttk.Button(frame, text="返回", command=self.show_main_menu).pack(pady=10)
            return
        
        downloads = response.get('downloads', {})
        
        if not downloads:
            ttk.Label(frame, text="尚無下載遊戲", font=("Arial", 14)).pack(pady=20)
            ttk.Button(frame, text="返回", command=self.show_main_menu).pack(pady=10)
            return
        
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        for game_id, download_info in downloads.items():
            status = download_info.get('status', 'active')
            
            if status == 'removed':
                status_text = "已下架"
                status_color = "red"
                status_icon = "🚫"
                version_text = f"版本: {download_info.get('version', 'N/A')} (已下架)"
                can_play = False
            elif download_info.get('update_available'):
                status_text = "需更新"
                status_color = "orange"
                status_icon = "🔄"
                version_text = f"版本: {download_info.get('version', 'N/A')} → {download_info.get('server_version', 'N/A')}"
                can_play = False  # 需要更新才能玩
            else:
                status_text = "可遊玩"
                status_color = "green"
                status_icon = "✅"
                version_text = f"版本: {download_info.get('version', 'N/A')} (最新)"
                can_play = True
            
            game_frame = ttk.LabelFrame(scrollable_frame, text=f"{status_icon} {game_id}", padding="10")
            game_frame.pack(fill=tk.X, pady=5, padx=5)
            
            # 狀態標籤
            status_label = ttk.Label(game_frame, text=status_text, 
                                    font=("Arial", 10, "bold"),
                                    foreground=status_color)
            status_label.pack(anchor=tk.W)
            
            ttk.Label(game_frame, text=version_text).pack(anchor=tk.W)
            ttk.Label(game_frame, text=f"下載時間: {download_info['download_time'][:19]}").pack(anchor=tk.W)
            
            # 如果是需更新狀態，顯示更新按鈕
            if download_info.get('update_available'):
                update_frame = ttk.Frame(game_frame)
                update_frame.pack(fill=tk.X, pady=5)
                
                ttk.Label(update_frame, text="⚠️ 需要更新才能建立房間", 
                         foreground="orange").pack(side=tk.LEFT)
                
                ttk.Button(update_frame, text="立即更新", 
                          command=lambda gid=game_id: self.download_game_with_update(gid, is_update=True),
                          width=10).pack(side=tk.RIGHT)
            
            # 如果是已下架狀態
            elif status == 'removed':
                ttk.Label(game_frame, text="此遊戲已被開發者下架，無法遊玩", 
                         foreground="red").pack(anchor=tk.W, pady=5)
        
        if len(downloads) == 0:
            ttk.Label(scrollable_frame, text="尚無下載遊戲").pack(pady=20)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        ttk.Button(frame, text="🔄 重新整理", command=self.show_my_downloads).pack(pady=5)
        ttk.Button(frame, text="返回", command=self.show_main_menu).pack(pady=10)
    
    def show_lobby(self):
        self.clear_window()
        
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="🏠 遊戲大廳", font=("Arial", 18, "bold")).pack(pady=20)
        
        ttk.Label(frame, text=f"歡迎, {self.username}", 
                font=("Arial", 12), foreground="blue").pack(pady=5)
        
        quick_frame = ttk.LabelFrame(frame, text="快速操作", padding="15")
        quick_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(quick_frame, text="🎮 建立新房間", 
                command=self.show_create_room, width=20).pack(pady=5)
        
        ttk.Button(quick_frame, text="📋 瀏覽房間列表", 
                command=self.show_room_list, width=20).pack(pady=5)
        
        ttk.Button(quick_frame, text="🛒 瀏覽遊戲商城", 
                command=self.show_game_store, width=20).pack(pady=5)
        
        ttk.Button(quick_frame, text="📥 我的遊戲庫", 
                command=self.show_my_downloads, width=20).pack(pady=5)
        
        response = self.safe_send_request({'action': 'get_rooms'})
        if response and response.get('rooms'):
            rooms = response['rooms']
            waiting_rooms = {k: v for k, v in rooms.items() 
                            if v.get('status') == 'waiting'}
            
            if waiting_rooms:
                recent_frame = ttk.LabelFrame(frame, text="最近房間", padding="15")
                recent_frame.pack(fill=tk.X, pady=10)
                
                for room_id, room_data in list(waiting_rooms.items())[:3]:
                    room_text = f"{room_data['name']} ({len(room_data['players'])}/{room_data.get('max_players', 4)}人)"
                    
                    room_btn = ttk.Button(recent_frame, text=room_text, 
                                        command=lambda rid=room_id: self.join_existing_room(rid))
                    room_btn.pack(fill=tk.X, pady=2)
        
        ttk.Button(frame, text="🔙 返回主選單", command=self.show_main_menu, width=20).pack(pady=20)
    
    def show_create_room(self):
        self.clear_window()
        
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="🎮 建立房間", font=("Arial", 18, "bold")).pack(pady=10)
        
        # 取得已下載遊戲
        response = self.safe_send_request({
            'action': 'get_downloads',
            'player': self.username
        })
        
        if not response:
            ttk.Label(frame, text="載取下載紀錄失敗").pack(pady=20)
            ttk.Button(frame, text="返回", command=self.show_lobby).pack(pady=10)
            return
        
        downloads = response.get('downloads', {})
        
        if not downloads:
            ttk.Label(frame, text="你尚未下載任何遊戲", font=("Arial", 14)).pack(pady=20)
            ttk.Label(frame, text="請先到商城下載遊戲後再建立房間", font=("Arial", 12)).pack(pady=10)
            ttk.Button(frame, text="前往商城", command=self.show_game_store).pack(pady=5)
            ttk.Button(frame, text="返回大廳", command=self.show_lobby).pack(pady=5)
            return
        
        # 只顯示可遊玩的遊戲（未下架且是最新版本）
        playable_games = {}
        needs_update_games = {}
        
        for game_id, download_info in downloads.items():
            status = download_info.get('status', 'active')
            
            if status == 'removed':
                continue  # 跳過已下架的遊戲
            
            if download_info.get('update_available'):
                needs_update_games[game_id] = download_info
            else:
                playable_games[game_id] = download_info
        
        # 取得所有遊戲資訊來取得遊戲名稱
        games_response = self.safe_send_request({'action': 'get_games'})
        all_games = games_response.get('games', {}) if games_response else {}
        
        # 準備下拉選單資料
        game_options = []
        self.create_room_game_map = {}  # 映射顯示名稱到遊戲ID
        
        # 先加入可遊玩的遊戲
        for game_id in playable_games.keys():
            if game_id in all_games:
                game_info = all_games[game_id]
                display_name = f"{game_info['name']} (v{game_info['version']})"
                self.create_room_game_map[display_name] = game_id
                game_options.append(display_name)
        
        # 如果有需要更新的遊戲，顯示警告
        if needs_update_games:
            warning_frame = ttk.LabelFrame(frame, text="⚠️ 需要更新的遊戲", padding="10")
            warning_frame.pack(fill=tk.X, pady=10)
            
            for game_id in needs_update_games.keys():
                if game_id in all_games:
                    game_info = all_games[game_id]
                    download_info = needs_update_games[game_id]
                    
                    warning_text = f"{game_info['name']}: 版本 {download_info.get('version')} → {game_info.get('version')}"
                    
                    warning_item = ttk.Frame(warning_frame)
                    warning_item.pack(fill=tk.X, pady=2)
                    
                    ttk.Label(warning_item, text=warning_text, 
                             foreground="orange").pack(side=tk.LEFT)
                    
                    ttk.Button(warning_item, text="更新", 
                              command=lambda gid=game_id: self.download_game_with_update(gid, is_update=True),
                              width=8).pack(side=tk.RIGHT)
        
        if not game_options:
            ttk.Label(frame, text="沒有可用的遊戲", font=("Arial", 14)).pack(pady=20)
            
            if needs_update_games:
                ttk.Label(frame, text="請先更新上方的遊戲", font=("Arial", 12)).pack(pady=10)
            else:
                ttk.Label(frame, text="請到商城下載遊戲", font=("Arial", 12)).pack(pady=10)
            
            ttk.Button(frame, text="前往商城", command=self.show_game_store).pack(pady=5)
            ttk.Button(frame, text="返回大廳", command=self.show_lobby).pack(pady=5)
            return
        
        ttk.Label(frame, text="選擇遊戲:").pack(pady=5)
        
        self.create_room_game_var = tk.StringVar()
        self.create_room_game_combo = ttk.Combobox(frame, textvariable=self.create_room_game_var, 
                                                width=40, state='readonly')
        self.create_room_game_combo['values'] = game_options
        self.create_room_game_combo.pack(pady=5)
        
        if game_options:
            self.create_room_game_combo.current(0)
        
        ttk.Label(frame, text="房間名稱:").pack(pady=5)
        self.room_name_entry = ttk.Entry(frame, width=40)
        self.room_name_entry.pack(pady=5)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=20)
        
        def create():
            if not self.create_room_game_var.get() or not self.room_name_entry.get().strip():
                messagebox.showwarning("警告", "請填寫所有欄位")
                return
            
            selected = self.create_room_game_var.get()
            game_id = self.create_room_game_map.get(selected)
            
            if not game_id:
                messagebox.showerror("錯誤", "無效的遊戲選擇")
                return
            
            room_name = self.room_name_entry.get().strip()
            game_info = all_games.get(game_id, {})
            
            # 再次檢查版本（確保在創建前是最新版本）
            version_response = self.safe_send_request({
                'action': 'check_version',
                'player': self.username,
                'game_id': game_id
            }, show_error=False)
            
            if version_response and version_response.get('update_available'):
                local_version = version_response.get('local_version')
                server_version = version_response.get('server_version')
                
                if messagebox.askyesno("需要更新", 
                    f"遊戲 '{game_info.get('name', 'Unknown')}' 需要更新才能建立房間。\n\n"
                    f"目前版本: {local_version}\n"
                    f"最新版本: {server_version}\n\n"
                    f"是否立即更新？"):
                    
                    if self.download_game_with_update(game_id, is_update=True):
                        # 更新成功後重新載入頁面
                        self.show_create_room()
                    return
                else:
                    messagebox.showwarning("無法建立", "必須更新到最新版本才能建立房間")
                    return
            
            # 檢查本地遊戲檔案是否存在
            player_dir = os.path.join(self.download_dir, self.username)
            game_dir = os.path.join(player_dir, game_id)
            
            if not os.path.exists(game_dir):
                if messagebox.askyesno("下載遊戲", 
                    f"本地遊戲檔案不存在，需要下載才能建立房間。是否立即下載？"):
                    if self.download_game_with_update(game_id, is_update=False):
                        # 下載成功後重新載入頁面
                        self.show_create_room()
                    return
                else:
                    return
            
            import time
            room_id = f"room_{self.username}_{int(time.time())}"
            
            room_data = {
                'name': room_name,
                'game_id': game_id,
                'game_name': game_info.get('name', '未知遊戲'),
                'host': self.username,
                'players': [self.username],
                'max_players': game_info.get('max_players', 4),
                'status': 'waiting',
                'created_at': str(time.time()),
                'password': ''
            }
            
            response = self.safe_send_request({
                'action': 'create_room',
                'room_id': room_id,
                'room_data': room_data
            })
            
            if response and response.get('success'):
                messagebox.showinfo("成功", "房間建立成功！")
                self.show_room_waiting(room_id)
            elif response:
                error_msg = response.get('message', '建立失敗')
                
                # 處理需要更新的情況
                if response.get('needs_update'):
                    local_version = response.get('local_version')
                    server_version = response.get('server_version')
                    
                    if messagebox.askyesno("需要更新", 
                        f"必須更新到最新版本才能建立房間。\n\n"
                        f"目前版本: {local_version}\n"
                        f"最新版本: {server_version}\n\n"
                        f"是否立即更新？"):
                        
                        if self.download_game_with_update(game_id, is_update=True):
                            # 更新成功後重新嘗試建立房間
                            self.show_create_room()
                    else:
                        messagebox.showwarning("無法建立", "必須更新到最新版本才能建立房間")
                else:
                    messagebox.showerror("錯誤", error_msg)
            else:
                messagebox.showerror("錯誤", "建立失敗")
        
        def go_to_store():
            self.show_game_store()
        
        ttk.Button(btn_frame, text="建立", command=create, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="下載更多遊戲", command=go_to_store, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="返回", command=self.show_lobby, width=12).pack(side=tk.LEFT, padx=5)
    
    def show_room_list(self):
        self.clear_window()
        
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="📋 房間列表", font=("Arial", 18, "bold")).pack(pady=10)
        
        response = self.safe_send_request({'action': 'get_rooms'})
        
        if not response:
            ttk.Label(frame, text="載入失敗").pack(pady=20)
            ttk.Button(frame, text="返回", command=self.show_lobby).pack(pady=10)
            return
        
        rooms = response.get('rooms', {})
        
        if not rooms:
            ttk.Label(frame, text="目前沒有房間", font=("Arial", 14)).pack(pady=20)
            ttk.Button(frame, text="返回", command=self.show_lobby).pack(pady=10)
            return
        
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        for room_id, room_data in rooms.items():
            if room_data.get('status') != 'waiting':
                continue
                
            room_frame = ttk.LabelFrame(scrollable_frame, text=room_data['name'], padding="10")
            room_frame.pack(fill=tk.X, pady=5, padx=5)
            
            info_text = f"""
遊戲: {room_data['game_name']}
房主: {room_data['host']}
人數: {len(room_data['players'])}/{room_data.get('max_players', 4)}
狀態: {room_data['status']}
            """
            ttk.Label(room_frame, text=info_text.strip(), justify=tk.LEFT).pack(anchor=tk.W)
            
            ttk.Button(room_frame, text="加入房間", 
                      command=lambda rid=room_id: self.join_existing_room(rid)).pack(pady=5)
        
        if not any(room_data.get('status') == 'waiting' for room_data in rooms.values()):
            ttk.Label(scrollable_frame, text="目前沒有等待中的房間", font=("Arial", 14)).pack(pady=20)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        ttk.Button(frame, text="🔄 重新整理", command=self.show_room_list).pack(pady=5)
        ttk.Button(frame, text="返回", command=self.show_lobby).pack(pady=10)
    
    def join_existing_room(self, room_id):
        # 先取得房間的最新資料
        response = self.safe_send_request({
            'action': 'get_room',
            'room_id': room_id
        })
        
        if not response or not response.get('room'):
            messagebox.showerror("錯誤", "房間不存在或已關閉")
            return
        
        room_data = response['room']
        
        if self.username in room_data['players']:
            messagebox.showinfo("提示", "你已經在這個房間中了")
            self.show_room_waiting(room_id)
            return
        
        max_players = room_data.get('max_players', 4)
        if len(room_data['players']) >= max_players:
            messagebox.showerror("錯誤", "房間已滿")
            return
        
        game_id = room_data['game_id']
        
        # 檢查遊戲是否已下架 - 透過伺服器檢查
        game_response = self.safe_send_request({
            'action': 'get_game_detail',
            'game_id': game_id
        })
        
        if game_response and game_response.get('removed'):
            messagebox.showerror("錯誤", "此遊戲已被開發者下架，無法加入房間")
            return
        
        # 檢查遊戲版本
        version_response = self.safe_send_request({
            'action': 'check_version',
            'player': self.username,
            'game_id': game_id
        }, show_error=False)
        
        if version_response and version_response.get('update_available'):
            local_version = version_response.get('local_version')
            server_version = version_response.get('server_version')
            game_name = version_response.get('game_name', '遊戲')
            
            if messagebox.askyesno("需要更新", 
                f"加入房間需要最新版本的遊戲。\n\n"
                f"遊戲: {game_name}\n"
                f"目前版本: {local_version}\n"
                f"房間版本: {server_version}\n\n"
                f"是否立即更新？"):
                
                if self.download_game_with_update(game_id, is_update=True):
                    # 更新成功後重新嘗試加入
                    self.join_existing_room(room_id)
                return
            else:
                messagebox.showwarning("無法加入", "必須更新到最新版本才能加入房間")
                return
        
        player_dir = os.path.join(self.download_dir, self.username)
        game_dir = os.path.join(player_dir, game_id)
        
        if not os.path.exists(game_dir):
            if messagebox.askyesno("下載遊戲", 
                f"你尚未下載此遊戲，需要下載才能加入房間。是否立即下載？"):
                if self.download_game_with_update(game_id, is_update=False):
                    if not os.path.exists(game_dir):
                        messagebox.showerror("錯誤", "下載失敗，無法加入房間")
                        return
                    # 下載成功後重新嘗試加入
                    self.join_existing_room(room_id)
                return
            else:
                return
        
        # 更新房間資料，加入玩家
        room_data['players'].append(self.username)
        
        response = self.safe_send_request({
            'action': 'update_room',
            'room_id': room_id,
            'room_data': {
                'players': room_data['players']
            }
        })
        
        if response and response.get('success'):
            messagebox.showinfo("成功", f"已加入房間: {room_data['name']}")
            self.show_room_waiting(room_id)
        elif response:
            messagebox.showerror("錯誤", response.get('message', '加入房間失敗'))
        else:
            messagebox.showerror("錯誤", "加入房間失敗")
    
    def show_room_waiting(self, room_id):
        self.clear_window()
        
        self.stop_room_auto_update()
        
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        response = self.safe_send_request({
            'action': 'get_room',
            'room_id': room_id
        })
        
        if not response or not response.get('room'):
            messagebox.showerror("錯誤", "房間不存在")
            self.show_lobby()
            return
        
        self.current_room_id = room_id
        room_data = response['room']
        self.current_room_data = room_data
        
        title_frame = ttk.Frame(frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(title_frame, text="🕐 房間等待中", 
                font=("Arial", 18, "bold")).pack(side=tk.LEFT)
        
        room_id_label = ttk.Label(title_frame, 
                                text=f"房間ID: {room_id}", 
                                font=("Arial", 10),
                                foreground="gray")
        room_id_label.pack(side=tk.RIGHT)
        
        info_frame = ttk.LabelFrame(frame, text="房間資訊", padding="10")
        info_frame.pack(fill=tk.X, pady=10)
        
        info_grid = ttk.Frame(info_frame)
        info_grid.pack(fill=tk.X)
        
        ttk.Label(info_grid, text=f"房間名稱: {room_data['name']}", 
                font=("Arial", 11, "bold")).grid(row=0, column=0, sticky=tk.W, pady=2)
        
        ttk.Label(info_grid, text=f"遊戲: {room_data.get('game_name', room_data['game_id'])}",
                font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=2)
        
        ttk.Label(info_grid, text=f"房主: {room_data['host']}",
                font=("Arial", 10)).grid(row=2, column=0, sticky=tk.W, pady=2)
        
        status_text = "等待中" if room_data['status'] == 'waiting' else room_data['status']
        status_color = "green" if room_data['status'] == 'waiting' else "orange"
        status_label = ttk.Label(info_grid, text=f"狀態: {status_text}",
                            font=("Arial", 10), foreground=status_color)
        status_label.grid(row=2, column=1, sticky=tk.W, pady=2, padx=20)
        
        players_frame = ttk.LabelFrame(frame, text=f"玩家列表 ({len(room_data['players'])})", padding="10")
        players_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        canvas = tk.Canvas(players_frame)
        scrollbar = ttk.Scrollbar(players_frame, orient="vertical", command=canvas.yview)
        self.players_list_frame = ttk.Frame(canvas)
        
        self.players_list_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.players_list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def display_players(room_data):
            for widget in self.players_list_frame.winfo_children():
                widget.destroy()
            
            for i, player in enumerate(room_data['players']):
                player_frame = ttk.Frame(self.players_list_frame)
                player_frame.pack(fill=tk.X, pady=2)
                
                icon = "👑" if player == room_data['host'] else "👤"
                ttk.Label(player_frame, text=icon, font=("Arial", 14)).pack(side=tk.LEFT, padx=(0, 10))
                
                name_label = ttk.Label(player_frame, text=player, font=("Arial", 11))
                name_label.pack(side=tk.LEFT)
                
                if player == self.username:
                    ttk.Label(player_frame, text="(你)", 
                            font=("Arial", 10), foreground="blue").pack(side=tk.LEFT, padx=5)
        
        display_players(room_data)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)
        
        def start_game():
            if room_data['host'] != self.username:
                messagebox.showwarning("警告", "只有房主可以開始遊戲")
                return
            
            if not messagebox.askyesno("確認", "確定要開始遊戲嗎？"):
                return
            
            response = self.safe_send_request({
                'action': 'start_game',
                'room_id': room_id,
                'player': self.username
            })
            
            if response and response.get('success'):
                # 移除 "遊戲啟動中，請等待..." 的訊息框
                # 直接開始監控遊戲啟動狀態
                self.monitor_game_start(room_id)
            elif response:
                messagebox.showerror("錯誤", response.get('message', '啟動失敗'))
            else:
                messagebox.showerror("錯誤", "啟動失敗")
        
        def leave_room():
            if messagebox.askyesno("確認", "確定要離開房間嗎？"):
                self.stop_room_auto_update()
                
                if room_data['host'] == self.username:
                    response = self.safe_send_request({
                        'action': 'delete_room',
                        'room_id': room_id
                    })
                    if response and response.get('success'):
                        messagebox.showinfo("房間解散", "你已解散房間")
                    else:
                        messagebox.showinfo("房間解散", "你已離開房間")
                else:
                    room_data['players'].remove(self.username)
                    response = self.safe_send_request({
                        'action': 'update_room',
                        'room_id': room_id,
                        'room_data': {
                            'players': room_data['players']
                        }
                    })
                    messagebox.showinfo("離開房間", "你已離開房間")
                
                self.show_lobby()
        
        def copy_room_id():
            self.root.clipboard_clear()
            self.root.clipboard_append(room_id)
            self.root.update()
            messagebox.showinfo("複製成功", "房間ID已複製到剪貼簿")
        
        def invite_player():
            invite_window = tk.Toplevel(self.root)
            invite_window.title("邀請玩家")
            invite_window.geometry("400x200")
            
            frame = ttk.Frame(invite_window, padding="20")
            frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(frame, text="📨 邀請玩家加入房間", 
                    font=("Arial", 14, "bold")).pack(pady=10)
            
            ttk.Label(frame, text="請將以下資訊提供給其他玩家：").pack(pady=5)
            
            room_id_frame = ttk.Frame(frame)
            room_id_frame.pack(pady=5)
            ttk.Label(room_id_frame, text="房間ID:").pack(side=tk.LEFT)
            room_id_entry = ttk.Entry(room_id_frame, width=30)
            room_id_entry.insert(0, room_id)
            room_id_entry.config(state='readonly')
            room_id_entry.pack(side=tk.LEFT, padx=5)
            ttk.Button(room_id_frame, text="複製", command=copy_room_id).pack(side=tk.LEFT)
            
            info_text = f"""
房間名稱: {room_data['name']}
遊戲: {room_data.get('game_name', room_data['game_id'])}
房主: {room_data['host']}
人數: {len(room_data['players'])}/{room_data.get('max_players', 4)}
            """
            
            ttk.Label(frame, text=info_text.strip(), justify=tk.LEFT).pack(pady=10)
            
            ttk.Button(frame, text="關閉", command=invite_window.destroy).pack(pady=10)
        
        if room_data['host'] == self.username:
            ttk.Button(btn_frame, text="🎮 開始遊戲", command=start_game, 
                    width=15).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="📨 邀請玩家", command=invite_player, 
                width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🔄 重新整理", command=lambda: self.refresh_room_waiting(room_id), 
                width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🚪 離開房間", command=leave_room, 
                width=15).pack(side=tk.LEFT, padx=5)
        
        self.start_room_auto_update(room_id, display_players)
    
    def start_room_auto_update(self, room_id, display_players_callback):
        self.room_update_running = True
        self.current_room_id = room_id
        
        def update_room():
            if not self.room_update_running or not self.connected:
                return
            
            try:
                response = self.safe_send_request({
                    'action': 'get_room',
                    'room_id': room_id
                }, show_error=False)
                
                if response and response.get('room'):
                    new_room_data = response['room']
                    
                    if (new_room_data.get('players', []) != self.current_room_data.get('players', []) or
                        new_room_data.get('status') != self.current_room_data.get('status')):
                        
                        self.current_room_data = new_room_data
                        display_players_callback(new_room_data)
                    
                    if new_room_data['status'] in ['starting', 'playing']:
                        self.stop_room_auto_update()
                        
                        if new_room_data['status'] == 'starting':
                            self.monitor_game_start(room_id)
                        elif new_room_data['status'] == 'playing':
                            self.start_game_client(room_id)
                        return
                
                if self.room_update_running and self.connected:
                    self.root.after(2000, update_room)
            
            except Exception as e:
                print(f"Auto-update error: {str(e)}")
                if self.room_update_running and self.connected:
                    self.root.after(5000, update_room)
        
        self.root.after(1000, update_room)
    
    def stop_room_auto_update(self):
        self.room_update_running = False
        self.current_room_id = None
    
    def refresh_room_waiting(self, room_id):
        self.show_room_waiting(room_id)
    
    def monitor_game_start(self, room_id):
        def check_game_status():
            try:
                response = self.safe_send_request({
                    'action': 'get_room',
                    'room_id': room_id
                }, show_error=False)
                
                if response and response.get('room'):
                    room_data = response['room']
                    
                    if room_data['status'] == 'playing':
                        self.start_game_client(room_id)
                        return True
                    elif room_data['status'] == 'starting':
                        self.root.after(1000, check_game_status)
                    else:
                        messagebox.showerror("錯誤", f"啟動失敗，狀態: {room_data['status']}")
                        return False
                else:
                    return False
                
                return False
            
            except Exception as e:
                return False
        
        self.root.after(1000, check_game_status)
    
    def start_game_client(self, room_id):
        if self.game_starting:
            return
        
        try:
            self.game_starting = True
            
            room_response = self.safe_send_request({
                'action': 'get_room',
                'room_id': room_id
            })
            
            if not room_response or not room_response.get('room'):
                messagebox.showerror("錯誤", "無法取得房間資訊")
                return
            
            room_data = room_response['room']
            game_id = room_data['game_id']
            
            response = self.safe_send_request({
                'action': 'get_game_connection',
                'room_id': room_id
            })
            
            if not response or not response.get('success'):
                messagebox.showerror("錯誤", "無法取得遊戲連接資訊")
                return
            
            game_dir = os.path.join(self.download_dir, self.username, game_id)
            
            if not os.path.exists(game_dir):
                if messagebox.askyesno("下載遊戲", 
                    f"你尚未下載此遊戲，需要下載才能遊玩。是否立即下載？"):
                    self.download_game_file(game_id)
                    if not os.path.exists(game_dir):
                        messagebox.showerror("錯誤", "下載失敗，無法啟動遊戲")
                        return
                else:
                    return
            
            check_result, check_msg = self.check_game_files(game_dir)
            if not check_result:
                messagebox.showerror("錯誤", f"遊戲檔案不完整: {check_msg}")
                return
            
            config_path = os.path.join(game_dir, 'config.json')
            if not os.path.exists(config_path):
                messagebox.showerror("錯誤", "遊戲配置文件不存在")
                return
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            host = response['host']
            port = response['port']
            
            if config['type'] == 'cli':
                self.launch_cli_game(game_dir, config, host, port, room_id)
            elif config['type'] == 'gui':
                self.launch_gui_game(game_dir, config, host, port, room_id)
            else:
                messagebox.showerror("錯誤", f"不支援的遊戲類型: {config['type']}")
            
            record_response = self.safe_send_request({
                'action': 'record_play',
                'player': self.username,
                'game_id': game_id
            }, show_error=False)
            
        except Exception as e:
            messagebox.showerror("錯誤", f"啟動遊戲失敗: {str(e)}")
        finally:
            self.root.after(5000, lambda: setattr(self, 'game_starting', False))
    
    def launch_gui_game(self, game_dir, config, host, port, room_id):
        try:
            
            if host == '0.0.0.0':
                host = 'localhost'
                
            client_command = config['client_command'].split()
            
            client_file = None
            
            possible_paths = [
                os.path.join(game_dir, 'client.py'),
                os.path.join(game_dir, client_command[1] if len(client_command) > 1 else 'client.py')
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    client_file = path
                    break
            
            if not client_file:
                for root, dirs, files in os.walk(game_dir):
                    for file in files:
                        if file.lower() == 'client.py':
                            client_file = os.path.join(root, file)
                            break
                    if client_file:
                        break
            
            if not client_file or not os.path.exists(client_file):
                raise FileNotFoundError("找不到遊戲客戶端檔案")
            
            client_file = os.path.abspath(client_file)
            game_dir = os.path.abspath(game_dir)
            
            process = subprocess.Popen([
                sys.executable, client_file, host, str(port)
            ], cwd=game_dir)
            
            self.wait_for_game_end(process, room_id)
            
        except Exception as e:
            raise
    
    def launch_cli_game(self, game_dir, config, host, port, room_id):
        try:
            if host == '0.0.0.0':
                host = 'localhost'
            
            client_command = config['client_command'].split()
            
            client_file = None
            
            for root, dirs, files in os.walk(game_dir):
                for file in files:
                    if file.lower() == 'client.py':
                        client_file = os.path.join(root, file)
                        break
                if client_file:
                    break
            
            if not client_file or not os.path.exists(client_file):
                raise FileNotFoundError("找不到遊戲客戶端檔案")
            
            client_file = os.path.abspath(client_file)
            game_dir = os.path.abspath(game_dir)
            
            self.root.withdraw()
            
            try:
                original_cwd = os.getcwd()
                os.chdir(game_dir)
                
                process = subprocess.Popen(
                    [sys.executable, client_file, host, str(port)],
                    stdout=None,
                    stderr=None,
                    stdin=None,
                    bufsize=0,
                    universal_newlines=True,
                    creationflags=0
                )
                
                process.wait()
                
                os.chdir(original_cwd)
                
            except Exception as game_error:
                print(f"Game error: {str(game_error)}")
            finally:
                self.delete_room_and_return(room_id)
                
        except Exception as e:
            self.root.deiconify()
    
    def wait_for_game_end(self, process, room_id):
        def check_game_end():
            if process.poll() is None:
                self.root.after(1000, check_game_end)
            else:
                self.delete_room_and_return(room_id)
        
        self.root.after(1000, check_game_end)
    
    def delete_room_and_return(self, room_id):
        try:
            response = self.safe_send_request({
                'action': 'delete_room',
                'room_id': room_id
            }, show_error=False)
            
        except Exception as e:
            pass
        
        finally:
            self.root.after(500, lambda: self.return_to_lobby())
    
    def return_to_lobby(self):
        self.root.deiconify()
        self.show_lobby()
    
    def logout(self):
        try:
            self.stop_room_auto_update()
            
            if self.socket and self.connected:
                try:
                    self.send_request({'action': 'logout', 'username': self.username})
                except:
                    pass
        finally:
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
            self.socket = None
            self.connected = False
            self.username = None
            self.show_login_screen()
    
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
    
    def on_closing(self):
        self.stop_room_auto_update()
        
        if hasattr(self, 'room_update_job'):
            try:
                self.root.after_cancel(self.room_update_job)
            except:
                pass
        
        try:
            if self.socket and self.connected:
                self.socket.settimeout(1)
                self.send_request({'action': 'logout', 'username': self.username})
        except:
            pass
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        
        self.root.destroy()

    def check_game_files(self, game_dir):
        try:
            if not os.path.exists(game_dir):
                return False, "遊戲目錄不存在"
            
            required_files = ['config.json']
            
            for file in required_files:
                file_path = os.path.join(game_dir, file)
                if not os.path.exists(file_path):
                    found = False
                    for root, dirs, files in os.walk(game_dir):
                        if file in files:
                            found = True
                            break
                    if not found:
                        return False, f"找不到 {file}"
            
            return True, "遊戲檔案完整"
        except Exception as e:
            return False, f"檢查失敗: {str(e)}"

if __name__ == '__main__':
    client = PlayerClient()
    client.run()