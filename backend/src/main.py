import sys
from pathlib import Path

# --- 1. Cấu hình đường dẫn (Path) ---

# Lấy đường dẫn của file main.py này (tức là 'backend/')
project_root = Path(__file__).resolve().parent

# Tạo đường dẫn đến thư mục 'src' (tức là 'backend/src')
src_path = project_root / "src"

# Thêm đường dẫn 'src' vào danh sách import của Python
# để chúng ta có thể import "from services..."
sys.path.append(str(src_path))

print(f"Đã thêm '{src_path}' vào hệ thống.")

# --- 2. Import Scraper (Sau khi đã sửa đường dẫn) ---
try:
    # Bây giờ Python có thể tìm thấy module 'services'
    from services.booking_scraper import run_booking_scraper
except ImportError:
    print(f"LỖI: Không thể tìm thấy 'booking_scraper.py'.")
    print(f"Hãy đảm bảo file của bạn nằm ở: {src_path / 'services' / 'booking_scraper.py'}")
    sys.exit(1) # Thoát nếu không import được

# --- 3. Chạy hàm main ---
if __name__ == "__main__":
    print("--- CHUẨN BỊ CHẠY SCRAPER TỪ MAIN.PY ---")
    
    try:
        # Gọi hàm cào (crawl)
        run_booking_scraper()
        
        print("--- MAIN.PY: SCRAPER ĐÃ CHẠY XONG ---")
        
    except Exception as e:
        print(f"--- MAIN.PY: ĐÃ XẢY RA LỖI KHI CHẠY SCRAPER ---")
        print(f"LỖI: {e}")