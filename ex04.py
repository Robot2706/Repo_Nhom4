filename = input("Nhap ten file: ")

try:
    with open(filename, "r", encoding="utf-8") as file:
        content = file.read()
        print("\nNoi dung cua file:")
        print(content)
except FileNotFoundError:
    print("Loi: File khong ton tai hoac sai duong dan.")
except Exception as e:
    print(f"Da xay ra loi: {e}")
