# Windows User README Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thay README một dòng bằng hướng dẫn tiếng Việt giúp người dùng Windows cài, chạy và nhập PDF vào ứng dụng.

**Architecture:** README là tài liệu độc lập ở gốc repository, dùng đúng tên tệp và nhãn giao diện hiện có. Nội dung ưu tiên quick start, sau đó mới giải thích API key, luồng nhập sách và xử lý lỗi.

**Tech Stack:** GitHub Flavored Markdown, Windows, Python 3.12.9, PowerShell, Command Prompt.

## Global Constraints

- Chỉ hướng dẫn Windows.
- Không chứa API key thật, dữ liệu người dùng hoặc PDF.
- Không tuyên bố tính năng lưu crop đã hoàn tất khi mã chưa triển khai.
- Mọi lệnh và đường dẫn phải tồn tại trong repository.

---

### Task 1: Viết và xác minh README

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: `requirements.txt`, `chay-app.bat`, `chay-app-go-loi.bat`, `tao-shortcut.bat`
- Produces: README tiếng Việt hiển thị trên trang chính GitHub

- [ ] **Step 1: Kiểm chứng các tệp được nhắc tới**

Run:

```powershell
Get-Item requirements.txt,chay-app.bat,chay-app-go-loi.bat,tao-shortcut.bat,dict.sqlite
python --version
```

Expected: năm tệp tồn tại; Python hiện tại là 3.12.x.

- [ ] **Step 2: Viết README**

README phải có đúng các phần:

- Giới thiệu và tính năng.
- Yêu cầu Windows/Python.
- Quick start PowerShell.
- Phương án Command Prompt.
- Mở app và tạo shortcut.
- Cấu hình Gemini API key.
- Quy trình nhập PDF tám bước.
- Xử lý lỗi.
- Bảo mật và bản quyền.

- [ ] **Step 3: Kiểm tra nội dung và secret**

Run:

```powershell
rg -n "^#|git clone|py -3.12|chay-app|Gemini|429|user.sqlite" README.md
rg -n "AQ\\.|AIza" README.md
```

Expected: các mục bắt buộc xuất hiện; lệnh thứ hai không có kết quả.

- [ ] **Step 4: Kiểm tra lệnh khởi động**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
python -c "import hanzi_app.main; print('IMPORT_OK')"
```

Expected: `IMPORT_OK`.

- [ ] **Step 5: Commit và push**

```powershell
git add README.md docs/superpowers/plans/2026-07-29-windows-user-readme.md
git commit -m "docs: add Windows user guide"
git push
```

