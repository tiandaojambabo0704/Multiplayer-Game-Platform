# developer/developer_client.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import socket
import json
import os
import zipfile
from datetime import datetime

class DeveloperClient:
    def __init__(self, host='140.113.69.12', port=20113):
        self.host = host
        self.port = port
        self.socket = None
        self.username = None
        self.connected = False
        
        self.root = tk.Tk()
        self.root.title("🎮 開發者平台")
        self.root.geometry("800x600")
        
        self.show_login_screen()
    
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
        
        ttk.Label(frame, text="🎮 開發者平台", font=("Arial", 24, "bold")).pack(pady=20)
        
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
                messagebox.showinfo("成功", "登入成功！")
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
    
    def show_main_menu(self):
        self.clear_window()
        
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(expand=True)
        
        ttk.Label(frame, text=f"👤 歡迎, {self.username}", font=("Arial", 18)).pack(pady=20)
        
        ttk.Button(frame, text="📤 上架新遊戲", command=self.show_upload_game, width=30).pack(pady=10)
        ttk.Button(frame, text="📋 我的遊戲", command=self.show_my_games, width=30).pack(pady=10)
        ttk.Button(frame, text="🚪 登出", command=self.logout, width=30).pack(pady=10)
    
    def show_upload_game(self):
        self.clear_window()
        
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="📤 上架新遊戲", font=("Arial", 18, "bold")).pack(pady=10)
        
        info_frame = ttk.LabelFrame(frame, text="遊戲資訊", padding="10")
        info_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(info_frame, text="遊戲名稱:").grid(row=0, column=0, sticky=tk.W, pady=5)
        name_entry = ttk.Entry(info_frame, width=40)
        name_entry.grid(row=0, column=1, pady=5)
        
        ttk.Label(info_frame, text="遊戲類型:").grid(row=1, column=0, sticky=tk.W, pady=5)
        type_var = tk.StringVar(value="cli")
        type_frame = ttk.Frame(info_frame)
        type_frame.grid(row=1, column=1, sticky=tk.W, pady=5)
        ttk.Radiobutton(type_frame, text="CLI", variable=type_var, value="cli").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(type_frame, text="GUI", variable=type_var, value="gui").pack(side=tk.LEFT, padx=5)
        
        ttk.Label(info_frame, text="最小人數:").grid(row=2, column=0, sticky=tk.W, pady=5)
        min_players = ttk.Spinbox(info_frame, from_=1, to=10, width=10)
        min_players.set(2)
        min_players.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(info_frame, text="最大人數:").grid(row=3, column=0, sticky=tk.W, pady=5)
        max_players = ttk.Spinbox(info_frame, from_=1, to=10, width=10)
        max_players.set(2)
        max_players.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(info_frame, text="版本號:").grid(row=4, column=0, sticky=tk.W, pady=5)
        version_entry = ttk.Entry(info_frame, width=20)
        version_entry.insert(0, "1.0.0")
        version_entry.grid(row=4, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(info_frame, text="遊戲簡介:").grid(row=5, column=0, sticky=tk.W, pady=5)
        desc_text = scrolledtext.ScrolledText(info_frame, width=40, height=4)
        desc_text.grid(row=5, column=1, pady=5)
        
        file_frame = ttk.LabelFrame(frame, text="遊戲檔案", padding="10")
        file_frame.pack(fill=tk.X, pady=10)
        
        selected_dir = tk.StringVar(value="尚未選擇")
        ttk.Label(file_frame, textvariable=selected_dir).pack(pady=5)
        
        def select_directory():
            directory = filedialog.askdirectory(title="選擇遊戲資料夾")
            if directory:
                selected_dir.set(directory)
        
        ttk.Button(file_frame, text="選擇遊戲資料夾", command=select_directory).pack(pady=5)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=20)
        
        def do_upload():
            name = name_entry.get().strip()
            game_type = type_var.get()
            min_p = int(min_players.get())
            max_p = int(max_players.get())
            version = version_entry.get().strip()
            description = desc_text.get("1.0", tk.END).strip()
            game_dir = selected_dir.get()
            
            if not name or game_dir == "尚未選擇":
                messagebox.showwarning("警告", "請填寫所有必要欄位並選擇遊戲資料夾")
                return
            
            if not os.path.isdir(game_dir):
                messagebox.showerror("錯誤", "遊戲資料夾不存在")
                return
            
            game_id = f"{self.username}_{name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            zip_path = f"{game_id}.zip"
            
            try:
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(game_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, game_dir)
                            zipf.write(file_path, arcname)
                
                with open(zip_path, 'rb') as f:
                    zip_data = f.read()
                
                os.remove(zip_path)
                
                response = self.safe_send_request({
                    'action': 'upload_game',
                    'game_id': game_id,
                    'game_data': {
                        'name': name,
                        'developer': self.username,
                        'type': game_type,
                        'min_players': min_p,
                        'max_players': max_p,
                        'version': version,
                        'description': description,
                        'status': 'active',
                        'created_at': datetime.now().isoformat()
                    },
                    'zip_data': zip_data.hex()
                })
                
                if response and response['success']:
                    messagebox.showinfo("成功", "遊戲上架成功！")
                    self.show_main_menu()
                else:
                    messagebox.showerror("錯誤", response['message'] if response else "上架失敗")
            
            except Exception as e:
                messagebox.showerror("錯誤", f"上架失敗: {str(e)}")
        
        ttk.Button(btn_frame, text="上架", command=do_upload, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="返回", command=self.show_main_menu, width=12).pack(side=tk.LEFT, padx=5)
    
    def show_my_games(self):
        self.clear_window()
        
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="📋 我的遊戲", font=("Arial", 18, "bold")).pack(pady=10)
        
        response = self.safe_send_request({
            'action': 'get_all_my_games',  # 改為取得所有遊戲（包含已下架）
            'developer': self.username
        })
        
        if not response:
            ttk.Label(frame, text="載入失敗").pack(pady=20)
            ttk.Button(frame, text="返回", command=self.show_main_menu).pack(pady=10)
            return
        
        games = response.get('games', {})
        
        if not games:
            ttk.Label(frame, text="尚無遊戲", font=("Arial", 14)).pack(pady=20)
            ttk.Button(frame, text="返回", command=self.show_main_menu).pack(pady=10)
            return
        
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        columns = ('name', 'version', 'type', 'status')
        tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        tree.heading('name', text='遊戲名稱')
        tree.heading('version', text='版本')
        tree.heading('type', text='類型')
        tree.heading('status', text='狀態')
        
        tree.column('name', width=200)
        tree.column('version', width=100)
        tree.column('type', width=100)
        tree.column('status', width=100)
        
        for game_id, game_data in games.items():
            status = game_data.get('status', 'active')
            status_text = "已上架" if status == 'active' else "已下架"
            status_color = "green" if status == 'active' else "red"
            
            
            item = tree.insert('', tk.END, values=(
                game_data['name'],
                game_data['version'],
                game_data['type'],
                status_text,
            ), tags=(game_id, status))
            
            # 設置狀態顏色
            tree.tag_configure('removed', foreground='red')
            tree.tag_configure('active', foreground='green')
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scrollbar.set)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)
        
        def update_game():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("警告", "請選擇遊戲")
                return
            
            game_id = tree.item(selected[0])['tags'][0]
            status = tree.item(selected[0])['tags'][1] if len(tree.item(selected[0])['tags']) > 1 else 'active'
            
            # 檢查遊戲是否已下架
            if status == 'removed':
                messagebox.showwarning("警告", "已下架的遊戲無法更新版本")
                return
            
            self.show_update_game(game_id)
        
        def remove_game():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("警告", "請選擇遊戲")
                return
            
            game_id = tree.item(selected[0])['tags'][0]
            status = tree.item(selected[0])['tags'][1] if len(tree.item(selected[0])['tags']) > 1 else 'active'
            
            # 檢查遊戲是否已下架
            if status == 'removed':
                messagebox.showinfo("資訊", "此遊戲已經下架")
                return
            
            if not messagebox.askyesno("確認", "確定要下架此遊戲嗎？\n\n下架後：\n1. 將無法再更新版本\n2. 新玩家無法下載\n3. 已下載的玩家會看到標示"):
                return
            
            response = self.safe_send_request({
                'action': 'remove_game',
                'game_id': game_id,
                'developer': self.username
            })
            
            if response and response['success']:
                messagebox.showinfo("成功", "遊戲已下架")
                self.show_my_games()
            elif response:
                messagebox.showerror("錯誤", response['message'])
            else:
                messagebox.showerror("錯誤", "下架失敗")
        
        def view_game_detail():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("警告", "請選擇遊戲")
                return
            
            game_id = tree.item(selected[0])['tags'][0]
            self.show_game_detail(game_id)
        
        ttk.Button(btn_frame, text="更新版本", command=update_game, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="下架遊戲", command=remove_game, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="查看詳情", command=view_game_detail, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="返回", command=self.show_main_menu, width=12).pack(side=tk.LEFT, padx=5)
    
    def show_game_detail(self, game_id):
        self.clear_window()
        
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="📝 遊戲詳情", font=("Arial", 18, "bold")).pack(pady=10)
        
        # 這裡可以顯示遊戲的詳細資訊
        ttk.Label(frame, text=f"遊戲ID: {game_id}").pack(pady=5)
        
        ttk.Button(frame, text="返回", command=self.show_my_games).pack(pady=20)
    
    def show_update_game(self, game_id):
        self.clear_window()
        
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="🔄 更新遊戲版本", font=("Arial", 18, "bold")).pack(pady=10)
        
        ttk.Label(frame, text="新版本號:").pack(pady=5)
        version_entry = ttk.Entry(frame, width=30)
        version_entry.pack(pady=5)
        
        selected_dir = tk.StringVar(value="尚未選擇")
        ttk.Label(frame, textvariable=selected_dir).pack(pady=10)
        
        def select_directory():
            directory = filedialog.askdirectory(title="選擇遊戲資料夾")
            if directory:
                selected_dir.set(directory)
        
        ttk.Button(frame, text="選擇遊戲資料夾", command=select_directory).pack(pady=10)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=20)
        
        def do_update():
            version = version_entry.get().strip()
            game_dir = selected_dir.get()
            
            if not version or game_dir == "尚未選擇":
                messagebox.showwarning("警告", "請填寫版本號並選擇資料夾")
                return
            
            try:
                zip_path = f"{game_id}_update.zip"
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(game_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, game_dir)
                            zipf.write(file_path, arcname)
                
                with open(zip_path, 'rb') as f:
                    zip_data = f.read()
                
                os.remove(zip_path)
                
                response = self.safe_send_request({
                    'action': 'update_game',
                    'game_id': game_id,
                    'version': version,
                    'zip_data': zip_data.hex()
                })
                
                if response and response['success']:
                    messagebox.showinfo("成功", "遊戲更新成功！")
                    self.show_my_games()
                else:
                    error_msg = response['message'] if response else "更新失敗"
                    if "removed" in error_msg.lower():
                        messagebox.showerror("錯誤", "無法更新已下架的遊戲")
                    else:
                        messagebox.showerror("錯誤", error_msg)
            
            except Exception as e:
                messagebox.showerror("錯誤", f"更新失敗: {str(e)}")
        
        ttk.Button(btn_frame, text="更新", command=do_update, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="返回", command=self.show_my_games, width=12).pack(side=tk.LEFT, padx=5)
    
    def logout(self):
        try:
            if self.socket and self.connected:
                try:
                    self.send_request({'action': 'logout', 'username': self.username})
                except Exception as e:
                    print(f"Logout send error (non-critical): {str(e)}")
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
        try:
            if self.socket and self.connected:
                try:
                    self.socket.settimeout(1)
                    self.send_request({'action': 'logout', 'username': self.username})
                except Exception as e:
                    print(f"Closing send error (non-critical): {str(e)}")
        finally:
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
        
        self.root.destroy()

if __name__ == '__main__':
    client = DeveloperClient()
    client.run()