# # (Code của đồ án chính, ví dụ Flask)
# # from flask import Flask, render_template
# import pandas as pd

# # (MỚI) Import hàm cào (crawl) từ module của bạn
# from scrapers.booking_scraper import run_booking_scraper

# app = Flask(__name__)

# @app.route("/")
# def index():
#     return "Chào mừng đến với đồ án!"

# @app.route("/run-scraper")
# def start_scraping():
#     # Khi người dùng truy cập /run-scraper, nó sẽ chạy code cào
#     print("Bắt đầu chạy scraper...")
#     run_booking_scraper() # <-- Gọi hàm
#     return "Đã cào (crawl) xong!"

# @app.route("/show-data")
# def show_data():
#     # Đọc file CSV từ thư mục /data/ và hiển thị
#     try:
#         df = pd.read_csv("data/booking_com.csv")
#         return df.to_html() # Hiển thị dạng bảng
#     except FileNotFoundError:
#         return "Chưa có dữ liệu. Hãy chạy /run-scraper trước."

# if __name__ == "__main__":
#     app.run(debug=True)