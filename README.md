# NP HW3

## 結構說明

```text
112550113_NP_HW3/
├── server/             # Server 端
│   ├── server.py         # 主啟動程式
│   ├── database.py       # 資料庫
│   ├── data/ (自動生成)
|       └── developer.json, downloads.json, games.json, players.json, rooms.json, reviews.json
│   └── uploaded_games/  (自動生成)
├── developer/          
│   ├── developer_client.py
│   └── games/          # 遊戲開發目錄
│         └── guess_number/  # CLI
|                 └── client.py
|                 └── server.py
|                 └── config.json
|         └── tic_tac_toe/   # GUI
|                 └── client.py
|                 └── server.py
|                 └── config.json
|         └── card_game/ # Multiplayer
|                 └── client.py
|                 └── server.py
|                 └── config.json
├── player/             
│   ├── player_client.py
│   └── downloads/      # 玩家下載目錄 (自動生成)
├── README.md           # 完整說明
├── Makefile           # 快速指令
├── requirements.txt   
```



## 快速啟動

### 1. 安裝依賴

```bash
# 安裝必要套件
pip install -r requirements.txt
```

### 2. 啟動服務器 (Server)

```bash
# 在終端機
# 方法1: 使用Makefile
make server

# 方法2: 直接執行
cd server
python server.py
```

### 3. 啟動開發者客戶端 (Developer)

```bash
# 在另一終端機
# 方法1: 使用Makefile
make dev 或 make developer

# 方法2: 直接執行
cd developer
python developer_client.py
```

### 4. 啟動玩家客戶端 (Player)

```bash
# 在另外多個終端機
# 方法1: 使用Makefile
make play 或 make player

# 方法2: 直接執行
cd developer
python player_client.py
```


## 階段一：開發者上架遊戲

### Step 1 : 開發者註冊與登入
1. 啟動developer_client.py
2. 註冊一個開發者帳號
3. 登入系統
### Step 2 : 上架新遊戲
1. 選擇【上架新遊戲】
2. 填寫遊戲資訊
    - 遊戲名稱 : Guess Number
    - 類型 : CLI
    - 版本號 : 1.0.0
    - 遊戲簡介 : (自行填寫)
3. 選擇遊戲資料夾 : developer/games/guess_number/
4. 點擊【上架】
5. 看到【上架成功】的訊息
### Step 3 : 上架第二款新遊戲
1. 返回主選單，再次選擇【上架新遊戲】
2. 填寫遊戲資訊
    - 遊戲名稱 : Tic Tac Toe
    - 類型 : GUI
    - 版本號 : 1.0.0
    - 遊戲簡介 : (自行填寫)
3. 選擇遊戲資料夾 : developer/games/tic_tac_toe/
4. 點擊【上架】
5. 看到【上架成功】的訊息
### Step 4 : 查看與管理遊戲
1. 選擇【我的遊戲】
2. 查看已上架的兩款遊戲
3. 可以進行
    - 更新版本
    - 下架遊戲 

## 階段二：玩家遊玩遊戲
### Step 1 : 玩家註冊與登入
1. 啟動兩個終端機player_client.py
2. 在兩個客戶端分別註冊 (A, B)
3. 分別登入

### Step 2 : 瀏覽與下載遊戲
1. Player A選擇【瀏覽遊戲商城】
2. 查看已上架的兩款遊戲
3. 點選【Guess Number】
4. 點選【下載遊戲】
5. 等待下載完成

### Step 3 : 建立房間 (Player A)
1. Player A返回主選單，選擇【大廳&房間】
2. 選擇【建立新房間】
3. 選擇遊戲(只能選有下載的)
4. 輸入房間名稱:(自行填寫)
5. 點擊【建立】

### Step 4 : 加入房間 (Player B)
1. Player B選擇【大廳&房間】
2. 選擇【瀏覽房間列表】
3. 點選(剛剛A填的房間名稱)的【加入名稱】
4. 若還沒下載遊戲，系統會自動下載
5. 成功加入房間

### Step 5 : 開始遊戲
1. 在Player A(房主)的房間畫面，點擊【開始遊戲】
2. 會自動啟動遊戲客戶端(在原本兩個終端機玩)
3. 實際遊玩猜數字遊戲

### Step 6 : 遊戲結束
1. 遊戲結束後會跳回GUI
2. 房間解散，玩家自動返回大廳畫面

### Step 7 : 評分遊戲
1. 在玩家主選單選擇【瀏覽遊戲商城】
2. 選擇剛剛玩的遊戲
3. 點擊【撰寫評論】
4. 輸入評分(1-5星)和評論
5. 送出後查看更新後的評論列表

## 階段三：遊戲版本更新
### Step 1：開發者更新遊戲
1. 回到developer_client.py
2. 選擇「我的遊戲」
3. 選擇【Guess Number】->【更新版本】
4. 輸入新版本號: 1.1.0
5. 選擇同一遊戲資料夾(或修改過的資料夾)
6. 點擊【更新】

### Step 2：玩家體驗版本更新
1. 回到Player A player_client.py
2. 選擇【檢查遊戲更新】
3. 系統會顯示有更新可用
4. 或嘗試建立房間時，系統會提示更新
5. 點擊【更新】按鈕下載新版本

## 階段四：下架遊戲
### Step 1：開發者下架遊戲
1. developer_client.py ->【我的遊戲】
2. 選擇要下架的遊戲 ->【下架遊戲】
3. 確認下架

### Step 2：玩家查看
1. Player重新載入遊戲商城
2. 已下架遊戲不會出現在商城列表
3. 已下載的遊戲會顯示【已下架】狀態
4. 無法為已下架的遊戲建立新房間

## 技術細節
### 通訊協定
- 訊息格式: JSON over TCP
- 封包結構: 4位元組長度標頭 + JSON內容
- 連線埠:
    - 開發者服務: 20113
    - 玩家大廳服務: 30113
     - 遊戲伺服器: 6000-7000 (動態分配)
- 資料持久化
    - 使用 JSON 檔案儲存
    - Server 重啟後資料不丟失
    - 包含：帳號、遊戲、房間、評論、下載記錄

### 遊戲規格
- 每個遊戲需要：

```bash
config.json - 遊戲配置 (名稱、類型、指令)
server.py - 遊戲伺服器 (接受 port 參數)
client.py - 遊戲客戶端 (接受 host, port 參數)
```

### 版本管理
- 開發者上傳版本 ->Server 儲存
- 玩家下載時取得最新版本
- 版本不匹配時強制更新
- 支援更新記錄 (version_history)

### 修改伺服器連線位置
- 預設：140.113.69.12 
- 修改位置：
```bash
Developer: developer_client.py __init__
Player: player_client.py __init__
Server: server.py __init__
```






