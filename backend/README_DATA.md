
backend/
├─ src/ (hoặc app/, hoặc tên framework)
│  ├─ main.py / app.py / server.js / ...     # file chạy chính của backend API
│  ├─ api/ or controllers/                   # định nghĩa các endpoint:
│  │   ├─ hotels.py                          # /hotels, /search
│  │   ├─ recommend.py                       # /recommend
│  │   └─ chatbot.py (nếu có)
│  ├─ models/                                # cấu trúc dữ liệu / ORM models
│  │   └─ hotel.py, user_preference.py ...
│  ├─ services/                              # logic xử lý
│  │   ├─ recommender.py                     # thuật toán gợi ý
│  │   └─ booking_scraper.py                        # cào data (nếu backend xử lý)
│  ├─ data/                                  # file JSON/CSV giả lập, sqlite db nhỏ
│  ├─ config/                                # config DB, API key, constant
│  └─ utils/                                 # hàm phụ trợ (validate input, log,…)