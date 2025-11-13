import time
import pandas as pd
from datetime import datetime, timedelta, timezone 
# --- THÊM THƯ VIỆN PATHLIB ---
from pathlib import Path 
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CÀI ĐẶT ---
MAX_SCROLLS = 3 
MAIN_CARD_SELECTOR = '[data-testid="property-card"]' 

# (BỌC TẤT CẢ CODE VÀO TRONG MỘT HÀM)
def run_booking_scraper():
    print("Đang cài đặt và khởi tạo Chrome Driver...")
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()

    options.add_argument('--headless')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--no-sandbox') # Bắt buộc cho headless
    options.add_argument('--disable-dev-shm-usage') # Bắt buộc cho headless
    options.add_argument('--disable-gpu') # TẮT GPU (Thường gây crash)
    options.add_argument('--disable-extensions') # Tắt các tiện ích
    options.add_argument('--disable-software-rasterizer')

    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(service=service, options=options)
    print("Khởi tạo Chrome Driver thành công.")
    
    hotels_data = []
    hotel_cards = [] 

    try:
        # --- 1. TRUY CẬP URL VỚI NGÀY ĐỘNG ---
        base_url = "https://www.booking.com/searchresults.html?aid=304142&label=gen173nr-10CAEoggI46AdIM1gEaPQBiAEBmAEzuAEXyAEP2AED6AEB-AEBiAIBqAIBuALr7tfIBsACAdICJGY3MGMzMTVkLTkxZGYtNDU4YS1hZGZhLTFkZTY4YmE1ZGFiM9gCAeACAQ&dest_id=-3730078&dest_type=city&group_adults=2&req_adults=2&no_rooms=1&group_children=0&req_children=0"
        
        VN_TZ = timezone(timedelta(hours=7))
        today_vn = datetime.now(VN_TZ)
        checkin_dt = today_vn + timedelta(days=2)
        checkout_dt = today_vn + timedelta(days=3)
        
        checkin_date = checkin_dt.strftime('%Y-%m-%d')
        checkout_date = checkout_dt.strftime('%Y-%m-%d')
        
        print(f"Ngày Check-in được đặt: {checkin_date}")
        print(f"Ngày Check-out được đặt: {checkout_date}")
        
        SEARCH_URL = f"{base_url}&checkin={checkin_date}&checkout={checkout_date}"
        
        print(f"Đang truy cập URL: {SEARCH_URL}")
        driver.get(SEARCH_URL)

        # --- 2. ĐÓNG POP-UP (NẾU CÓ) ---
        try:
            # Vẫn giữ bước này để phòng trường hợp pop-up hiện ra
            print("Chờ 5 giây cho pop-up (nếu có) xuất hiện...")
            time.sleep(5) 
            print("Gửi phím 'Escape' để đóng pop-up...")
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            print("Đã đóng pop-up. Chờ 2 giây...")
            time.sleep(2) 
        except Exception as e:
            print(f"Lỗi khi gửi phím Escape (Bỏ qua): {e}")

        # --- 3. THỰC HIỆN CUỘN (SCROLL) ĐỂ TẢI THÊM DỮ LIỆU ---
        print(f"--- BẮT ĐẦU {MAX_SCROLLS} LẦN CUỘN (SCROLL) ĐỂ TẢI THÊM ---")
        
        # Chờ các thẻ đầu tiên xuất hiện
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, MAIN_CARD_SELECTOR)))

        for scroll in range(1, MAX_SCROLLS + 1):
            print(f"Thực hiện cuộn lần {scroll}/{MAX_SCROLLS}...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            print("Đã cuộn. Chờ 5 giây cho khách sạn mới tải...")
            time.sleep(5) 
            
        print("Đã cuộn xong.")

        # --- 4. TÌM TẤT CẢ KHÁCH SẠN ĐÃ TẢI ---
        print("Bắt đầu tìm kiếm TẤT CẢ khách sạn đã tải...")
        hotel_cards = driver.find_elements(By.CSS_SELECTOR, MAIN_CARD_SELECTOR)
        print(f"Tìm thấy TỔNG CỘNG {len(hotel_cards)} thẻ trên trang.")

        # --- 5. LẶP VÀ LẤY DỮ LIỆU ---
        for card in hotel_cards:
            try:
                name = card.find_element(By.CSS_SELECTOR, '[data-testid="title"]').text
                
                try:
                    price = card.find_element(By.CSS_SELECTOR, '[data-testid="price-and-discounted-price"]').text
                except NoSuchElementException:
                    try:
                        price = card.find_element(By.CSS_SELECTOR, '[data-testid="price"]').text
                    except NoSuchElementException:
                        price = "N/A (Giá bị ẩn)"
                
                try:
                    score_element = card.find_element(By.CSS_SELECTOR, '[data-testid="review-score"]')
                    score = score_element.find_element(By.CSS_SELECTOR, '.dff2e52086').text
                except NoSuchElementException:
                    score = "N/A"
                
                try:
                    info = card.find_element(By.CSS_SELECTOR, '[data-testid="address"]').text
                except NoSuchElementException:
                    info = "N/A"
                
                hotels_data.append({
                    "TenKhachSan": name,
                    "SaoDanhGia": score,
                    "Gia": price,
                    "ThongTin": info 
                })
                print(f"Đã lấy: {name} | {score} | {price}")
                
            except NoSuchElementException:
                # Bỏ qua nếu là thẻ quảng cáo (không có 'title')
                print("--- Bỏ qua một thẻ (có thể là quảng cáo) ---")
                continue
            except Exception as e:
                print(f"Lỗi khi lấy thông tin một khách sạn: {e}")

    except (TimeoutException, Exception) as e:
        print(f"!!! LỖI KHÔNG MONG MUỐN !!!: {e}")
        # (Không cần lưu file debug .html và .png ở đây nữa, 
        #  trừ khi bạn muốn giữ nó)
    
    finally:
        # --- 7. (SỬA LẠI) TẠO ĐƯỜNG DẪN ĐỘNG TRƯỚC KHI LƯU ---
        print("Đang chuẩn bị đường dẫn lưu file...")
        
        # Lấy đường dẫn của file .py này (backend/src/services/scraping.py)
        script_dir = Path(__file__).resolve().parent 
        
        # Đi lùi 2 cấp (từ /services/ ra /src/ ra /backend/)
        backend_dir = script_dir.parent.parent 
        
        # Đường dẫn cho file HTML (lưu vào /backend/ cho dễ)
        html_output_path = backend_dir / "debug_page_booking.html"
        
        # Đường dẫn cho file CSV (theo yêu cầu của bạn)
        data_raw_dir = backend_dir / "data" / "raw"
        
        # Đảm bảo thư mục này tồn tại
        data_raw_dir.mkdir(parents=True, exist_ok=True)
        
        # Đường dẫn file output cuối cùng
        csv_output_path = data_raw_dir / "booking_com.csv"

        # --- 8. LƯU FILE HTML DEBUG ---
        print("Đang lưu file HTML cuối cùng...")
        try:
            with open(html_output_path, 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print(f"Đã lưu HTML vào '{html_output_path}'.")
        except Exception as e_save:
            print(f"Lỗi khi lưu file HTML: {e_save}")
            
        # --- 9. ĐÓNG TRÌNH DUYỆT ---
        driver.quit()
        print("Đã crawl xong. Đóng trình duyệt.")

        # --- 10. LƯU RA FILE CSV (ĐÃ SỬA ĐƯỜNG DẪN) ---
        if hotels_data:
            print(f"Đang lưu ra file CSV tại '{csv_output_path}'...")
            df = pd.DataFrame(hotels_data)
            df.index = df.index + 1
            
            # Dùng biến csv_output_path
            df.to_csv(csv_output_path, index_label="STT", encoding='utf-8-sig')
            
            print(f"--- HOÀN TẤT! ---")
            print(f"Đã lưu thành công {len(hotels_data)} khách sạn.")
        else:
            print("Không tìm thấy dữ liệu khách sạn nào để lưu.")