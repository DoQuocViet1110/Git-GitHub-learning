# build-watcher — Hướng dẫn cài đặt và sử dụng

> **Đọc file này từ trên xuống dưới.** Mỗi bước đều ghi rõ phải làm gì,
> gõ gì, và kết quả đúng trông như thế nào. Không cần biết lập trình.

---

## MỤC LỤC

| Mục | Nội dung |
|---|---|
| [1](#1-tool-này-làm-gì) | Tool này làm gì |
| [2](#2-cần-chuẩn-bị-gì-trước) | Cần chuẩn bị gì trước |
| [3](#3-các-file-trong-thư-mục-này) | Các file trong thư mục này |
| [4](#4-cài-đặt--làm-1-lần-duy-nhất) | **Cài đặt (làm 1 lần)** |
| [5](#5-chuẩn-bị-phía-github--làm-1-lần-duy-nhất) | **Chuẩn bị phía GitHub (làm 1 lần)** |
| [6](#6-dùng-hằng-ngày) | Dùng hằng ngày |
| [7](#7-lấy-kết-quả-build-ở-đâu) | Lấy kết quả build ở đâu |
| [8](#8-cho-tool-chạy-ngầm-không-cần-giữ-cửa-sổ) | Cho tool chạy ngầm |
| [9](#9-khắc-phục-sự-cố) | **Khắc phục sự cố** |
| [10](#10-đổi-sang-repo-khác--máy-khác) | Đổi sang repo khác / máy khác |
| [11](#11-các-phương-án-dự-phòng) | Các phương án dự phòng |
| [12](#12-checklist-in-ra-mang-theo) | **Checklist in ra mang theo** |
| [13](#13-dành-cho-người-kỹ-thuật) | Dành cho người kỹ thuật |

---

## 1. Tool này làm gì

Bình thường muốn build phần mềm, bạn phải ngồi trước máy build, mở thư mục,
chạy lệnh build. Tool này làm thay bạn: bạn chỉ cần **sửa 1 dòng chữ trên
GitHub**, máy build sẽ **tự động** tải code về, build, đóng gói kết quả và
đưa lên GitHub cho bạn tải.

**Quan trọng nhất**: tool này **không cần quyền vào phần Settings** của repo
khách hàng. Nó chỉ cần đúng những quyền bạn đã có: tải code về và đẩy code
lên (`git pull` / `git push`).

### Luồng hoạt động

```
BƯỚC A  Bạn sửa file Build_Infor.txt trên GitHub, thêm 1 dòng:
        [Build] - [ten-branch-can-build] - [Debug]
        rồi bấm push
                       │
BƯỚC B  Máy build tự kiểm tra mỗi 60 giây, thấy có yêu cầu mới
                       │
BƯỚC C  Máy build tự tải đúng branch đó về
                       │
BƯỚC D  Máy build tự chạy file build của dự án
                       │
BƯỚC E  Build xong, tự nén kết quả thành file .zip
                       │
BƯỚC F  Tự đưa file .zip lên GitHub (mục Releases)
        và gắn dấu tick xanh / dấu X đỏ lên GitHub
                       │
BƯỚC G  Bạn vào GitHub tải file .zip về
```

---

## 2. Cần chuẩn bị gì trước

Trước khi bắt đầu, máy build phải có **4 thứ** sau:

| # | Cần gì | Cách kiểm tra | Nếu chưa có |
|---|---|---|---|
| 1 | **Git** | Mở Command Prompt, gõ `git --version` → phải hiện số phiên bản | Tải tại https://git-scm.com/download/win, cài với mọi tuỳ chọn mặc định |
| 2 | **Đã đăng nhập GitHub trên máy đó** | Xem mục 2.1 ngay dưới | Xem mục 2.1 |
| 3 | **Bộ công cụ build của dự án** (CMake, Ninja, trình biên dịch...) | Thử build tay 1 lần xem có chạy không | Cài theo hướng dẫn riêng của dự án |
| 4 | **Kết nối Internet** | Mở trình duyệt vào github.com | Liên hệ IT công ty |

> **Không cần** quyền Administrator. **Không cần** cài Python (tool tự lo).

### 2.0. TRƯỚC TIÊN: máy đang dùng SSH hay HTTPS?

Đây là câu hỏi quyết định bạn phải làm gì tiếp theo. Cách kiểm tra:

Mở Command Prompt, vào thư mục đã clone repo khách hàng, gõ:
```
git remote -v
```

| Kết quả hiện ra bắt đầu bằng | Nghĩa là | Làm tiếp theo |
|---|---|---|
| `https://github.com/...` | Dùng **HTTPS** | Làm mục **2.1** ngay dưới |
| `git@github.com:...` | Dùng **SSH** | Làm mục **2.2** |

#### Vì sao phân biệt quan trọng

| | Tải/đẩy code (clone, fetch, push) | Đưa kết quả lên GitHub (Release, dấu tick) |
|---|---|---|
| **HTTPS** đã đăng nhập | ✅ Được | ✅ Được — tool tự mượn thông tin đăng nhập |
| **SSH key** | ✅ Được | ❌ **KHÔNG được** |

SSH key chỉ dùng để tải/đẩy code. GitHub **không chấp nhận SSH key** cho phần
tạo Release và gắn dấu tick — đó là 2 cơ chế hoàn toàn khác nhau.

> Đây là kết quả đã kiểm chứng thật, không phải suy đoán: gọi API bằng SSH key
> trả về lỗi `HTTP 401 Unauthorized`.

### 2.1. Nếu máy dùng HTTPS — đăng nhập GitHub (rất quan trọng)

Đây là bước hay bị bỏ sót nhất. Làm **1 lần duy nhất** trên máy build:

1. Mở **Command Prompt**
2. Gõ lệnh sau (thay `CHU-REPO/TEN-REPO` bằng repo thật của khách hàng):
   ```
   git clone https://github.com/CHU-REPO/TEN-REPO.git C:\test-clone
   ```
3. Một cửa sổ trình duyệt sẽ hiện ra → **đăng nhập GitHub như bình thường**
4. Chờ tải xong, rồi **xoá thư mục `C:\test-clone`** đi (không cần nữa)

Sau bước này, Windows đã ghi nhớ thông tin đăng nhập. Tool sẽ tự dùng lại
thông tin đó — **bạn không cần tạo "token" hay vào trang Settings nào cả.**

> ⚠️ **Đăng nhập bằng tài khoản Windows nào thì sau này phải chạy tool bằng
> đúng tài khoản Windows đó.** Xem mục 8 để hiểu vì sao.

### 2.2. Nếu máy dùng SSH — chọn 1 trong 2 hướng

Tool **vẫn tải code và build bình thường** qua SSH. Chỉ riêng phần đưa kết quả
lên GitHub là cần thêm token. Có 2 lựa chọn:

#### Hướng A — Không đưa kết quả lên GitHub (đơn giản nhất, không cần làm gì thêm)

Khi `setup.bat` hỏi *"Bat bao ket qua len GitHub?"* → **gõ `n`**.

Kết quả: tool vẫn tự phát hiện yêu cầu, tự tải code, tự build, tự tạo file
`.zip`. Bạn lấy file ở `C:\build-watcher\data\artifacts\`. Chỉ mất phần dấu
tick xanh và mục Releases trên GitHub.

> Có thể bật lại sau bất cứ lúc nào bằng cách làm Hướng B.

#### Hướng B — Tạo token để có đầy đủ tính năng

Bạn **đã từng làm việc tương tự rồi**: lúc tạo SSH key, bạn phải vào
`github.com/settings/keys` để thêm khoá. Tạo token cũng ở khu vực đó —
**Settings của tài khoản BẠN**, hoàn toàn không liên quan tới Settings repo
khách hàng (cái mà khách không cho bạn vào).

| Trang | Của ai | Bạn vào được không |
|---|---|---|
| `github.com/settings/keys` | Tài khoản bạn | ✅ Đã vào rồi (để thêm SSH key) |
| `github.com/settings/tokens` | Tài khoản bạn | ✅ Vào được, cùng khu vực |
| `github.com/<khách>/<repo>/settings` | Repo khách hàng | ❌ Khách không cho — **không dùng đến** |

**Các bước:**

1. Vào https://github.com/settings/tokens
2. Chọn **"Tokens (classic)"** → **"Generate new token (classic)"**
3. Đặt tên bất kỳ, ví dụ `build-watcher`
4. Chọn thời hạn (khuyên dùng **90 days**)
5. Tích vào ô **`repo`** (tích ô cha là đủ, các ô con tự tích theo)
6. Bấm **"Generate token"** → **copy chuỗi hiện ra ngay** (chỉ hiện 1 lần)
7. Trên máy build, mở **Command Prompt as Administrator**, chạy:
   ```
   setx BUILD_WATCHER_GITHUB_TOKEN "dan-chuoi-token-vao-day" /M
   ```
8. **Khởi động lại máy** (bắt buộc, để Windows nạp lại biến môi trường)
9. Chạy `check.bat` để kiểm tra

> 💡 **Lời khuyên bảo mật**: token loại `repo` có quyền trên **mọi** repo mà
> tài khoản đó truy cập được. Nếu tài khoản bạn còn tham gia repo của khách
> hàng khác, cân nhắc dùng 1 tài khoản GitHub riêng cho việc build và nhờ
> khách add tài khoản đó làm collaborator vào đúng 1 repo.

---

## 3. Các file trong thư mục này

| File | Dùng để làm gì | Bạn có cần đụng vào không |
|---|---|---|
| `setup.bat` | **Cài đặt.** Nhấn đúp 1 lần khi mới bắt đầu | ✅ Nhấn đúp |
| `run.bat` | **Chạy liên tục.** Nhấn đúp để tool bắt đầu theo dõi | ✅ Nhấn đúp |
| `build-once.bat` | **Kiểm tra 1 lần** rồi thoát. Dùng để thử nghiệm | ✅ Nhấn đúp |
| `check.bat` | **Kiểm tra cấu hình** có đúng không. Không build gì | ✅ Nhấn đúp |
| `config.json` | File cấu hình — `setup.bat` tự tạo ra | ⚙️ Chỉ sửa khi đổi repo |
| `Build_Infor.example.txt` | File mẫu để đưa lên GitHub | 📄 Copy nội dung |
| `README.md` | Chính là file bạn đang đọc | 📖 Đọc |
| `config.example.json` | File cấu hình mẫu | ❌ Không đụng |
| `setup_wizard.py` | Chương trình hỏi thông tin để tạo config | ❌ Không đụng |
| `build_watcher/` | Mã nguồn của tool | ❌ Không đụng |
| `tests/` | Các bài kiểm tra tự động | ❌ Không đụng |
| `python/` | Python — `setup.bat` tự tải về | ❌ Không đụng |
| `data/` | Nơi chứa code tải về, kết quả build, nhật ký | ❌ Không đụng |

---

## 4. Cài đặt — làm 1 lần duy nhất

### Bước 4.1 — Chép thư mục vào máy build

Chép **toàn bộ thư mục `build-watcher`** vào ổ C, đặt tên ngắn gọn:

```
C:\build-watcher
```

> ⚠️ **Đường dẫn phải NGẮN.** Đừng đặt vào `Desktop`, `Documents`, hay
> `C:\Users\ten-ban\...`. Windows có giới hạn độ dài đường dẫn 260 ký tự;
> đặt sâu quá sẽ làm build lỗi với thông báo rất khó hiểu.
>
> ✅ Đúng: `C:\build-watcher`
> ❌ Sai: `C:\Users\VietDQ\Desktop\Cong viec\Tool build\build-watcher`

### Bước 4.2 — Nhấn đúp vào `setup.bat`

Một cửa sổ đen sẽ hiện ra và tự làm 6 việc. Bạn chỉ cần **trả lời vài câu hỏi**
ở BƯỚC 5 của nó.

**Các câu hỏi sẽ được hỏi** (câu nào không rõ thì cứ **nhấn Enter** để dùng
giá trị mặc định trong dấu ngoặc vuông):

| Câu hỏi | Trả lời thế nào |
|---|---|
| Địa chỉ repo trên GitHub | Dán địa chỉ repo khách hàng, ví dụ `https://github.com/ten-khach/ten-repo` |
| Tên branch chứa file yêu cầu build | Nhấn Enter (dùng `build-requests`) |
| Tên file yêu cầu build | Nhấn Enter (dùng `Build_Infor.txt`) |
| Tên file script để build | Tên file build của dự án khách hàng. Nếu là `build.bat` thì nhấn Enter |
| Các preset cho phép | Nhấn Enter, hoặc gõ tên các cấu hình build của dự án |
| Đường dẫn file kết quả | Nhấn Enter nếu dự án sinh ra `build/<preset>/*.elf` |
| Bật báo kết quả lên GitHub? | Nhấn Enter (chọn Có) |
| Danh sách email được phép | Nhấn Enter (cho phép tất cả) |

### Bước 4.3 — Xem kết quả

Khi chạy đúng, bạn sẽ thấy:

```
[BUOC 1/6] Kiem tra Git...
  OK - Da cai Git:
git version 2.55.0.windows.1

[BUOC 2/6] Kiem tra tai khoan GitHub da dang nhap chua...
  OK - Da dang nhap bang tai khoan: TEN-TAI-KHOAN-CUA-BAN

[BUOC 3/6] Kiem tra Python...
  OK - Da cai:
Python 3.12.10

[BUOC 4/6] Kiem tra tool con nguyen ven...
  OK - Tat ca bai kiem tra deu dat:
Ran 54 tests in 0.185s

[BUOC 5/6] Tao file cau hinh...
  (các câu hỏi ở đây)

[BUOC 6/6] Kiem tra ket noi toi repo...
  check passed

====================================================================
  CAI DAT HOAN TAT
====================================================================
```

Thấy dòng **`CAI DAT HOAN TAT`** là xong. Nếu không thấy → xem **mục 9**.

---

## 5. Chuẩn bị phía GitHub — làm 1 lần duy nhất

Tool cần 1 branch riêng trên repo khách hàng để bạn đặt yêu cầu build vào đó.

> Bước này **không cần** quyền Settings. Chỉ cần quyền push code bình thường.

### Cách làm bằng giao diện web GitHub (dễ nhất)

1. Vào repo khách hàng trên GitHub
2. Bấm vào ô chọn branch (thường ghi `main` hoặc `master`)
3. Gõ tên mới: **`build-requests`** → bấm **"Create branch: build-requests"**
4. Bấm nút **"Add file"** → **"Create new file"**
5. Đặt tên file: **`Build_Infor.txt`**
6. Nội dung, gõ đúng như sau:
   ```
   # File yeu cau build
   # Them 1 dong "[Build] - [ten-branch] - [preset]" o cuoi roi luu lai
   ```
7. Kéo xuống, bấm **"Commit new file"**

Xong. Từ giờ chỉ cần sửa file này mỗi khi muốn build.

---

## 6. Dùng hằng ngày

### 6.1. Khởi động tool trên máy build

Nhấn đúp vào **`run.bat`**. Cửa sổ đen hiện ra và hiển thị:

```
   Tool dang theo doi repo. Khi co yeu cau build moi, no se tu build.
   GIU CUA SO NAY MO. Nhan Ctrl+C de dung.
```

**Giữ cửa sổ này mở.** Đóng cửa sổ = tool dừng.
(Muốn chạy ngầm không cần giữ cửa sổ → xem mục 8)

### 6.2. Yêu cầu build

Trên GitHub (từ máy nào cũng được, không cần ngồi máy build):

1. Vào repo khách hàng → chuyển sang branch **`build-requests`**
2. Bấm vào file **`Build_Infor.txt`**
3. Bấm biểu tượng **cây bút chì** (Edit)
4. **Thêm 1 dòng mới ở cuối**, theo đúng mẫu:

   ```
   [Build] - [ten-branch-can-build]
   ```
   hoặc, nếu muốn chỉ định cấu hình build cụ thể:
   ```
   [Build] - [ten-branch-can-build] - [Debug]
   ```

   Ví dụ thật:
   ```
   [Build] - [feature/them-nut-bam] - [Debug]
   ```

5. Bấm **"Commit changes"**

**Trong vòng 60 giây**, máy build sẽ tự bắt đầu build.

### 6.3. Quy tắc viết dòng yêu cầu

| Quy tắc | Đúng | Sai |
|---|---|---|
| Phải có dấu ngoặc vuông | `[Build] - [develop]` | `Build - develop` |
| Phải có dấu gạch ngang giữa các phần | `[Build] - [develop]` | `[Build] [develop]` |
| Tên branch phải chính xác | `[Build] - [feature/abc]` | `[Build] - [Feature/ABC]` |
| Dòng bắt đầu bằng `#` là ghi chú, bị bỏ qua | `# ghi chu` | — |
| Nếu có nhiều dòng `[Build]`, **dòng cuối cùng** được dùng | — | — |

---

## 7. Lấy kết quả build ở đâu

### Cách 1 — Trên GitHub (khuyên dùng)

1. Vào repo khách hàng trên GitHub
2. Bên phải màn hình, tìm mục **"Releases"** → bấm vào
3. Bấm vào bản mới nhất → kéo xuống mục **"Assets"**
4. Bấm vào file `.zip` để tải về

### Cách 2 — Xem build thành công hay thất bại

Vào trang commit của yêu cầu build, sẽ thấy:
- ✅ **Dấu tick xanh** = build thành công
- ❌ **Dấu X đỏ** = build thất bại
- 🟡 **Chấm vàng** = đang build

### Cách 3 — Ngay trên máy build

Các file `.zip` cũng được lưu tại:
```
C:\build-watcher\data\artifacts\
```

### Nếu build lỗi thì xem chi tiết ở đâu

Nhật ký chi tiết của từng lần build nằm ở:
```
C:\build-watcher\data\logs\
```
Mở file `.log` có tên trùng với branch bị lỗi để đọc thông báo lỗi.

---

## 8. Cho tool chạy ngầm (không cần giữ cửa sổ)

Nếu muốn tool tự chạy kể cả khi không ai đăng nhập, dùng **Task Scheduler**
có sẵn trong Windows.

> ⚠️ **ĐIỀU QUAN TRỌNG NHẤT CỦA MỤC NÀY**
>
> Phải cấu hình chạy **dưới đúng tài khoản Windows đã đăng nhập GitHub ở
> mục 2.1**. Nếu để mặc định (`SYSTEM`), tool sẽ **không tìm thấy thông tin
> đăng nhập** và không đưa được kết quả lên GitHub.
>
> **Lý do**: Windows cất thông tin đăng nhập riêng cho từng tài khoản, giống
> như mỗi người có 1 ngăn tủ khoá riêng. Tài khoản `SYSTEM` không có chìa
> mở ngăn tủ của bạn.

### Các bước

1. Nhấn phím **Windows**, gõ `Task Scheduler`, mở lên
2. Bên phải, bấm **"Create Task..."** (KHÔNG phải "Create Basic Task")
3. Tab **General**:
   - Name: `build-watcher`
   - Bấm **"Change User or Group..."** → gõ đúng tên tài khoản Windows của
     bạn → OK
   - Chọn **"Run whether user is logged on or not"**
   - ✅ Tích **"Run with highest privileges"**
4. Tab **Triggers** → **New...**:
   - Begin the task: **"At startup"** → OK
5. Tab **Actions** → **New...**:
   - Action: `Start a program`
   - Program/script: `C:\build-watcher\python\python.exe`
   - Add arguments: `-m build_watcher --config C:\build-watcher\config.json run`
   - Start in: `C:\build-watcher`
   - → OK
6. Tab **Settings**:
   - ✅ Tích **"If the task fails, restart every: 1 minute"**
   - ❌ **BỎ tích** "Stop the task if it runs longer than..."
7. Bấm **OK** → Windows sẽ hỏi **mật khẩu Windows** của tài khoản bạn → nhập vào

### Kiểm tra tool có đang chạy không

Mở Task Manager (Ctrl+Shift+Esc) → tab **Details** → tìm `python.exe`.

---

## 9. Khắc phục sự cố

### 9.1. Bảng tra nhanh

| Hiện tượng | Nguyên nhân | Cách sửa |
|---|---|---|
| `LOI: Khong tim thay Git` | Chưa cài Git | Cài Git, **đóng cửa sổ, mở lại**, chạy lại `setup.bat` |
| `CANH BAO: Chua tim thay thong tin dang nhap GitHub` | Chưa làm mục 2.1 | Làm theo mục 2.1 |
| `LOI: Khong tai duoc Python` | Mạng công ty chặn python.org | Xem 9.2 |
| `unknown revision or path` / `ambiguous argument` | Chưa tạo branch `build-requests` trên GitHub | Làm theo mục 5 |
| Đẩy yêu cầu lên rồi mà không thấy build | Xem 9.3 | |
| `cannot open ... for writing: No such file or directory` khi build | Đường dẫn quá dài | Chuyển thư mục về `C:\build-watcher` (mục 4.1) |
| Build chạy nhưng không thấy Release trên GitHub | Xem 9.4 | |
| `403` hoặc `Forbidden` trong nhật ký | Tài khoản không đủ quyền ghi vào repo | Nhờ khách cấp quyền Write (không phải Admin) |

### 9.2. Mạng công ty chặn tải Python

Nếu `setup.bat` báo không tải được Python:

1. Dùng máy khác (hoặc điện thoại) tải file này về:
   ```
   https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip
   ```
2. Chép file `.zip` sang máy build
3. Giải nén **toàn bộ nội dung** vào thư mục: `C:\build-watcher\python`
   (sau khi giải nén phải thấy file `python.exe` nằm ngay trong thư mục đó)
4. Chạy lại `setup.bat`

### 9.3. Đã đẩy yêu cầu lên nhưng không thấy build

Kiểm tra theo thứ tự:

1. **Tool có đang chạy không?** Cửa sổ `run.bat` còn mở không?
2. **Đây có phải lần chạy đầu tiên không?**
   → Lần đầu tiên tool chỉ ghi nhớ vị trí hiện tại, **không build**.
   Hãy đẩy thêm 1 yêu cầu **mới** nữa.
3. **Dòng yêu cầu có viết đúng mẫu không?** Xem lại mục 6.3.
4. **Đã đợi đủ 60 giây chưa?**
5. **Sửa file đúng branch chưa?** Phải là branch `build-requests`.
6. Mở file nhật ký `C:\build-watcher\data\logs\build-watcher.log`, xem
   dòng cuối cùng ghi gì.

### 9.4. Build xong nhưng không có Release trên GitHub

Mở `C:\build-watcher\data\logs\build-watcher.log`, tìm dòng có chữ `ERROR`:

| Trong nhật ký thấy | Nghĩa là | Cách sửa |
|---|---|---|
| `cloned over SSH, and SSH keys cannot be used for GitHub's API` | Repo dùng SSH — SSH key không đưa được kết quả lên GitHub | Làm mục **2.2** (chọn hướng A hoặc B) |
| `no GitHub token` | Chưa đăng nhập GitHub, hoặc đang chạy dưới sai tài khoản Windows | Làm mục 2.1; nếu chạy bằng Task Scheduler thì kiểm tra lại mục 8 |
| `HTTP 403` | Tài khoản không có quyền ghi | Nhờ khách cấp quyền **Write** cho tài khoản |
| `HTTP 404` | Sai tên repo trong `config.json` | Chạy lại `setup.bat` |
| `[no-github]` | Đang tắt tính năng báo cáo | Sửa `config.json`, đổi `"report_to_github": false` thành `true` |

### 9.5. Muốn build lại đúng yêu cầu cũ

Tool chỉ build các yêu cầu **mới**. Muốn build lại, hãy sửa `Build_Infor.txt`
thêm 1 dòng ghi chú bất kỳ rồi commit lại — như vậy tạo ra yêu cầu mới.

---

## 10. Đổi sang repo khác / máy khác

### 10.1. Đổi sang repo khác (cùng máy)

**Cách dễ nhất**: chạy lại `setup.bat`, nó sẽ hỏi lại từ đầu và ghi đè cấu hình.

**Hoặc** sửa tay file `config.json` (mở bằng Notepad), đổi 3 dòng:

```json
"repo_url": "https://github.com/CHU-REPO-MOI/TEN-REPO-MOI.git",
"owner": "CHU-REPO-MOI",
"repo": "TEN-REPO-MOI",
```

Sau khi đổi, **phải xoá 2 thứ** để tool bắt đầu lại từ đầu:
- Thư mục `C:\build-watcher\data\repo`
- File `C:\build-watcher\data\state.json`

Rồi chạy `check.bat` để kiểm tra.

### 10.2. Đem sang máy khác

Không chép thư mục cũ sang. Làm lại từ đầu cho sạch:

1. Chép thư mục `build-watcher` **gốc** (chưa cài) sang máy mới
2. **Xoá** thư mục `python` và `data`, và file `config.json` nếu có
3. Làm mục 2.1 (đăng nhập GitHub trên máy mới)
4. Chạy `setup.bat`

### 10.3. Bảng tra: cần đổi gì khi nào

| Tình huống | Cần làm gì |
|---|---|
| Đổi repo | Chạy lại `setup.bat` |
| Đổi tên branch chứa yêu cầu | Sửa `"trigger_branch"` trong `config.json` |
| Dự án dùng file build tên khác | Sửa `"build_script"` trong `config.json` |
| Dự án sinh file kết quả ở chỗ khác | Sửa `"artifact_globs"` trong `config.json` |
| Muốn build nhanh/chậm hơn | Sửa `"poll_interval_seconds"` (tính bằng giây) |
| Muốn giới hạn ai được build | Sửa `"allowed_committers"`, thay `"*"` bằng danh sách email |
| Đổi máy | Làm lại từ đầu theo 10.2 |

> **Không bao giờ cần sửa file nào trong thư mục `build_watcher/`.**
> Mọi thay đổi đều nằm trong `config.json`.

---

## 11. Các phương án dự phòng

Nếu gặp trở ngại không vượt qua được, đây là các phương án thay thế theo thứ
tự ưu tiên:

### Phương án A — Không đưa kết quả lên GitHub (dùng khi không đăng nhập được)

Mở `config.json`, đổi:
```json
"report_to_github": false
```

Kết quả: tool vẫn tự động build, vẫn tạo file `.zip`, nhưng **không** đưa lên
GitHub. Bạn lấy file ở `C:\build-watcher\data\artifacts\`.

| Vẫn hoạt động | Mất đi |
|---|---|
| Tự phát hiện yêu cầu build | Dấu tick xanh/đỏ trên GitHub |
| Tự tải code, tự build | File .zip trên mục Releases |
| Tự đóng gói file .zip | |

### Phương án B — Dùng token thủ công (nếu cách tự động không chạy)

Chỉ dùng khi mục 2.1 không thực hiện được:

1. Vào `https://github.com/settings/tokens` (Settings **của tài khoản bạn**,
   không phải của repo khách hàng)
2. Tạo token mới với quyền `repo`
3. Trên máy build, mở Command Prompt **as Administrator**, chạy:
   ```
   setx BUILD_WATCHER_GITHUB_TOKEN "dan-token-vao-day" /M
   ```
4. Khởi động lại máy (hoặc khởi động lại tác vụ trong Task Scheduler)

### Phương án C — Chạy tay khi cần

Không cho tool chạy liên tục. Mỗi khi cần build, nhấn đúp `build-once.bat`.

---

## 12. Checklist in ra mang theo

```
[ ] BƯỚC 1: Kiểm tra Git
        Mở Command Prompt, gõ:  git --version
        → Phải hiện số phiên bản

[ ] BƯỚC 1b: XÁC ĐỊNH SSH HAY HTTPS  ← LÀM TRƯỚC, quyết định các bước sau
        Vào thư mục đã clone repo khách, gõ:  git remote -v
        → Bắt đầu bằng https://    → làm BƯỚC 2-HTTPS
        → Bắt đầu bằng git@        → làm BƯỚC 2-SSH
        Ghi lại kết quả: ____________________

[ ] BƯỚC 2-HTTPS: Đăng nhập GitHub (làm 1 lần)
        git clone https://github.com/____/____.git C:\test-clone
        → Trình duyệt hiện ra, đăng nhập
        → Xoá thư mục C:\test-clone
        → GHI NHỚ đang dùng tài khoản Windows nào: ______________

[ ] BƯỚC 2-SSH: Chọn 1 trong 2
        [ ] A. Không cần Release/dấu tick
               → Ở BƯỚC 4, khi hỏi "Bat bao ket qua len GitHub?" gõ: n
        [ ] B. Muốn đầy đủ tính năng
               → Tạo token tại github.com/settings/tokens (quyền: repo)
               → Command Prompt as Admin:
                 setx BUILD_WATCHER_GITHUB_TOKEN "token" /M
               → KHỞI ĐỘNG LẠI MÁY

[ ] BƯỚC 3: Chép thư mục build-watcher vào  C:\build-watcher
        (Đường dẫn phải NGẮN, không để trong Desktop/Documents)

[ ] BƯỚC 4: Nhấn đúp  setup.bat
        Trả lời:
          - Địa chỉ repo: https://github.com/____/____
          - Các câu còn lại: nhấn Enter
        → Chờ thấy dòng  "CAI DAT HOAN TAT"

[ ] BƯỚC 5: Trên GitHub, tạo branch  build-requests
        và file  Build_Infor.txt  trong branch đó

[ ] BƯỚC 6: Nhấn đúp  check.bat
        → Phải thấy  "TAT CA DEU TOT"

[ ] BƯỚC 7: Nhấn đúp  build-once.bat  (lần 1)
        → Sẽ báo "processed 0 request" — ĐÂY LÀ ĐÚNG

[ ] BƯỚC 8: Trên GitHub, sửa Build_Infor.txt, thêm dòng:
        [Build] - [ten-branch-that] - [Debug]
        rồi Commit

[ ] BƯỚC 9: Nhấn đúp  build-once.bat  (lần 2)
        → Phải thấy dòng kết thúc bằng  "-> ok"

[ ] BƯỚC 10: Vào GitHub, mục Releases
        → Phải thấy file .zip vừa build

[ ] BƯỚC 11: Nhấn đúp  run.bat  để chạy liên tục
        (hoặc cấu hình Task Scheduler theo mục 8)
```

---

## 13. Dành cho người kỹ thuật

### 13.1. Cấu trúc mã nguồn

Mỗi module có phần giao tiếp nhỏ, phần thân dày, và có thể thay thế bằng
bản giả lập khi kiểm thử:

| Module | Giao tiếp | Che giấu điều gì |
|---|---|---|
| `git_repo.GitRepo` | `fetch` `remote_head` `ref_exists` `commits_touching` `file_at` `worktree` | toàn bộ lệnh git, phân tích kết quả, vòng đời worktree |
| `github_client.GitHubClient` | `set_commit_status` `publish_artifact` | xác thực, thử lại, xử lý release trùng tag |
| `git_credentials` | `fill_credential` `host_from_url` | mượn credential của git, chặn treo |
| `state.StateStore` | `last_sha` `advance` | ghi nguyên tử, phục hồi khi file hỏng |
| `request_format` | `parse_build_request` | định dạng, chống tiêm tham số vào git |
| `builder.Builder` | `run` | tìm script, gọi qua cmd.exe, hết giờ, ghi nhật ký |
| `packager.Packager` | `package` | tìm file kết quả, đặt tên zip |
| `pipeline.BuildPipeline` | `process` | trình tự, đảm bảo luôn kết thúc bằng đúng 1 trạng thái |
| `watcher.Watcher` | `poll_once` `run_forever` | vòng lặp, khôi phục, giãn nhịp khi lỗi |

### 13.2. Các quyết định thiết kế đáng lưu ý

| Quyết định | Lý do |
|---|---|
| Duyệt **git log** các commit chạm file, không đọc nội dung file hiện tại | 2 lần push liên tiếp giữa 2 chu kỳ vẫn ra 2 build, không mất |
| Tên script build lấy từ config máy, **không** từ nội dung request | Nội dung repo là dữ liệu không đáng tin — không cho nó chọn lệnh chạy |
| Mỗi build 1 worktree riêng, xoá sau khi xong | Tránh lẫn cache build giữa các branch → tránh ra firmware sai mà không báo lỗi |
| `target_commitish` = SHA thật đã checkout | Nếu bỏ trống, GitHub gắn tag vào branch mặc định — sai một cách âm thầm |
| Token mượn qua `git credential fill` | Không cần tạo PAT, không đụng trang Settings nào |
| `GCM_INTERACTIVE=never` + timeout | Nếu chưa có credential, GCM có thể mở trình duyệt và treo vô hạn |
| Chỉ dùng thư viện chuẩn của Python | Máy khách hàng thường chặn `pip install` |
| Không dùng `for /f` với lệnh trong `setup.bat` | Cách viết đó nuốt mất bàn phím người dùng — đã kiểm chứng |

### 13.3. Chạy kiểm thử

```
cd C:\build-watcher
python\python.exe -m unittest discover -s tests -t .
```

### 13.4. Đã kiểm chứng những gì

Chạy thật trên Windows 10 Pro, Python 3.12.10 bản rút gọn, repo GitHub thật:

| Kiểm chứng | Kết quả |
|---|---|
| 54 bài kiểm thử tự động | đạt |
| Cài từ thư mục sạch bằng `setup.bat` | đạt, gồm cả tải Python và tạo config |
| Đẩy 2 yêu cầu liên tiếp giữa 2 chu kỳ | cả 2 đều build, không mất |
| Yêu cầu từ email ngoài danh sách | bị chặn trước khi build |
| Build thất bại thật | báo lỗi đúng, không tạo Release |
| Build thành công | zip đúng 4 file, worktree được dọn |
| Đưa lên GitHub **không cần token thủ công** (repo HTTPS) | Release + Commit Status xuất hiện thật |
| `target_commitish` trỏ đúng commit đã build | xác nhận lại qua API |
| Clone + build qua **remote SSH** (`git@github.com:...`) | chạy được bình thường |
| SSH key dùng cho REST API | trả về `HTTP 401` — xác nhận không dùng được, phải có token |
| Thông báo lỗi khi SSH + bật báo cáo mà không có token | nêu đúng nguyên nhân SSH và cả 2 cách sửa |

### 13.5. Còn thiếu

- Chưa kiểm chứng khi chạy dưới Task Scheduler với tài khoản service
  (rủi ro: kho credential theo từng tài khoản Windows — xem mục 8)
- Chưa kiểm chứng trên mạng công ty (proxy, tường lửa, phần mềm diệt virus)
- Chưa có cơ chế báo "tool còn sống hay đã treo"
- Chưa tự dọn file kết quả và nhật ký cũ
