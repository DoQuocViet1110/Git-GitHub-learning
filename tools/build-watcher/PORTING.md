# Hướng dẫn mang tool sang máy khác / repo khác

> File này dùng khi **triển khai lần đầu trên 1 máy mới**, hoặc **đổi sang
> repo GitHub / GitLab khác**. Làm theo thứ tự từ trên xuống.
>
> Hướng dẫn sử dụng hằng ngày nằm ở `README.md`.

---

## GIAI ĐOẠN 0 — Thu thập thông tin (làm trước, tại bàn)

Điền đủ bảng này **trước khi ngồi vào máy build**. Thiếu ô nào là sẽ bị kẹt
giữa chừng ở đúng ô đó.

### 0.1. Thông tin repo GitHub (nơi chứa code cần build)

| Cần biết | Cách lấy | Điền vào đây |
|---|---|---|
| Địa chỉ repo | Trang repo trên GitHub, nút **Code** | `______________________` |
| Giao thức: SSH hay HTTPS | Trên máy build: `git remote -v` | ☐ SSH ☐ HTTPS |
| Có quyền tạo branch mới không? | Thử tạo 1 branch test trên web | ☐ Có ☐ Không |
| Tên branch sẽ chứa yêu cầu build | Tự đặt, mặc định `build-requests` | `______________________` |

### 0.1b. Nếu khách KHÔNG cho ghi gì vào repo của họ

Ô "quyền tạo branch" là **Không**? Vẫn dùng được — đặt file yêu cầu build ở
**1 repo khác do bạn kiểm soát**. Khi đó repo khách chỉ bị **đọc**, không bị
ghi bất cứ thứ gì.

| | Repo khách hàng | Repo của bạn |
|---|---|---|
| Chứa code cần build | ✅ | ❌ |
| Chứa `Build_Infor.txt` | ❌ | ✅ |
| Bị ghi vào | **KHÔNG BAO GIỜ** | Có (chính bạn ghi) |
| Khai trong config | `repo_url` | `trigger_repo_url` |

Repo của bạn có thể là: repo cá nhân trên GitHub, repo nội bộ của team,
hoặc bất kỳ repo nào bạn tạo branch được.

| Cần biết | Điền vào đây |
|---|---|
| Địa chỉ repo của bạn (chứa yêu cầu build) | `______________________` |

> ⚠️ Repo chứa yêu cầu **phải cùng dịch vụ** với repo code nếu muốn có dấu
> ✅/❌ (cả hai cùng GitHub, hoặc cùng GitLab). Dấu tick sẽ gắn lên commit
> **trong repo của bạn**, không phải repo khách.
>
> Đã kiểm chứng thật: sau khi build xong, repo khách không hề có thêm branch
> hay commit nào.

### 0.2. Thông tin build của dự án (quan trọng nhất, hay bị bỏ sót)

Tool **không tự biết** dự án build thế nào. Nó chỉ gọi đúng 1 file script mà
bạn khai báo.

| Cần biết | Ghi chú | Điền vào đây |
|---|---|---|
| Tên file script để build | Phải **có sẵn trong repo**, ở gốc, trên **mọi branch cần build** | `______________________` |
| Nếu chưa có → phải viết mới | Xem mục 0.2.1 | ☐ Đã có ☐ Cần viết |
| Các "preset" (cấu hình build) | Ví dụ `Debug`, `Release`. Không có thì để trống | `______________________` |
| Đường dẫn file kết quả sau build | Ví dụ `build/*/*.elf`. Nhiều đường dẫn cách nhau bằng dấu phẩy | `______________________` |
| Build mất bao lâu | Để đặt thời gian chờ tối đa | `_______ phút` |

#### 0.2.1. Nếu repo chưa có file script build

Phải tạo 1 file (ví dụ `build.bat`) và commit vào repo, **ở mọi branch cần
build**. Yêu cầu duy nhất của tool:

- Nhận **1 tham số** là tên preset (nếu dùng preset)
- Build xong thì **thoát với mã 0**; lỗi thì thoát với mã **khác 0**

Mẫu tối giản:

```bat
@echo off
set "PRESET=%~1"
if "%PRESET%"=="" set "PRESET=Debug"

REM --- Thay phan nay bang lenh build that cua du an ---
call lenh-build-cua-du-an %PRESET%
if errorlevel 1 exit /b 1

exit /b 0
```

> Tham khảo file `build.bat` trong repo STM32F4 để xem ví dụ đầy đủ.

### 0.3. Thông tin GitLab (chỉ cần nếu lưu artifact trên GitLab)

| Cần biết | Cách lấy | Điền vào đây |
|---|---|---|
| Địa chỉ GitLab | `https://gitlab.com` hoặc GitLab nội bộ | `______________________` |
| **Project** ID | Mở trang chính của **project** (không phải group), số nằm dưới tên project | `______________________` |
| Token GitLab (quyền `api`) | Preferences → Access Tokens | ☐ Đã tạo |

> ⚠️ **Phải là Project, không phải Group.** Group là thư mục chứa nhiều
> project; file `.zip` upload vào 1 project cụ thể. Nếu chỉ có group, hãy
> tạo 1 project trống bên trong nó (ví dụ `build-artifacts`).

### 0.4. Quyết định: kết quả build lưu ở đâu

Chọn 1:

| Chọn | `artifact_target` | `report_to_github` | Dùng khi |
|---|---|---|---|
| ☐ A | `github` | `true` | Khách cho ghi vào repo họ, máy dùng HTTPS |
| ☐ B | `gitlab` | `false` | **Khách không cho ghi + máy dùng SSH** (hay gặp nhất) |
| ☐ C | `gitlab` | `true` | Khách không cho ghi file, nhưng vẫn muốn dấu tick (cần token GitHub) |
| ☐ D | `local` | `false` | Chỉ build, tự lấy file trên máy |

---

## GIAI ĐOẠN 1 — Chuẩn bị máy build

| # | Việc | Kiểm tra bằng lệnh | Kết quả đúng |
|---|---|---|---|
| 1.1 | Cài Git | `git --version` | Hiện số phiên bản |
| 1.2 | Cài toolchain build của dự án | Build tay 1 lần | Build thành công |
| 1.3 | Xác thực được với GitHub | Xem 1.3.1 / 1.3.2 | Xem bên dưới |
| 1.4 | Vào được Internet | Mở github.com | Trang hiện ra |

**Không cần** quyền Administrator ở giai đoạn này (chỉ cần nếu phải đặt token
ở Giai đoạn 5).

### 1.3.1. Nếu dùng HTTPS

Chạy 1 lần trên máy build:
```
git clone https://github.com/CHU-REPO/TEN-REPO.git C:\test-clone
```
→ Trình duyệt hiện ra, đăng nhập → xoá `C:\test-clone`.

**Ghi lại đang đăng nhập bằng tài khoản Windows nào**: `________________`
(cần cho Giai đoạn 8)

### 1.3.2. Nếu dùng SSH

```
ssh -T git@github.com
```
→ Phải hiện `Hi <tên-tài-khoản>!`

**Ghi lại tên tài khoản GitHub hiện ra**: `________________`

> Nếu báo `Permission denied` → chưa có SSH key trên máy này, phải tạo và
> thêm vào tài khoản GitHub (`github.com/settings/keys`).

---

## GIAI ĐOẠN 2 — Copy file

### 2.1. Lấy tool

```
git clone -b feature/Build_Watcher https://github.com/DoQuocViet1110/Git-GitHub-learning.git C:\temp-tool
```
Thư mục cần lấy: `C:\temp-tool\tools\build-watcher`

### 2.2. Copy vào đúng chỗ

Copy **toàn bộ** thư mục `build-watcher` thành:

```
C:\build-watcher
```

> ⚠️ **Đường dẫn phải ngắn.** Windows giới hạn 260 ký tự cho đường dẫn. Đặt
> trong `Desktop` hay `Documents` sẽ làm build lỗi với thông báo rất khó
> hiểu (`cannot open ... for writing`).
>
> ✅ `C:\build-watcher`   ❌ `C:\Users\ten\Desktop\Tool\build-watcher`

### 2.3. ⚠️ KHÔNG copy những thứ này từ máy cũ

Nếu bạn copy từ 1 máy đã cài rồi, **phải xoá** các mục sau trước khi chạy:

| Xoá | Vì sao |
|---|---|
| `python\` | Bản Python của máy cũ, để `setup.bat` tự tải bản mới |
| `data\` | Chứa code + lịch sử build của repo cũ |
| `config.json` | Cấu hình của repo cũ |

Sau khi xoá, trong `C:\build-watcher` chỉ còn:
```
setup.bat  run.bat  check.bat  build-once.bat  setup_wizard.py
README.md  PORTING.md  config.example.json  Build_Infor.example.txt
build_watcher\  tests\
```

---

## GIAI ĐOẠN 3 — Chạy cài đặt

Nhấn đúp **`setup.bat`**. Trả lời theo bảng đã điền ở Giai đoạn 0:

| Câu hỏi | Lấy từ ô nào |
|---|---|
| Địa chỉ repo trên GitHub | 0.1 |
| Tên branch chứa file yêu cầu build | 0.1 |
| Tên file yêu cầu build | Enter (mặc định `Build_Infor.txt`) |
| Tên file script để build | **0.2** |
| Các preset cho phép | **0.2** |
| Đường dẫn file kết quả | **0.2** |
| Bật báo kết quả lên GitHub? | 0.4 |
| Nơi lưu file .zip (1/2/3) | 0.4 |
| GitLab URL + Project ID | 0.3 (nếu chọn 2) |
| Danh sách email được phép | Enter (mặc định `*` = tất cả) |

Chờ đến khi thấy **`CAI DAT HOAN TAT`**.

> Nếu dừng ở bước 6 (kiểm tra kết nối) → bình thường, vì branch chứa yêu cầu
> build chưa được tạo. Làm tiếp Giai đoạn 4 rồi chạy `check.bat`.

---

## GIAI ĐOẠN 4 — Tạo branch trên GitHub

Làm trên web, **không cần quyền Settings**:

1. Vào repo trên GitHub
2. Bấm ô chọn branch → gõ tên branch (mặc định `build-requests`)
   → bấm **"Create branch: ..."**
3. **Add file** → **Create new file**
4. Tên file: `Build_Infor.txt`
5. Nội dung:
   ```
   # File yeu cau build
   # Them 1 dong "[Build] - [ten-branch] - [preset]" o cuoi roi luu lai
   ```
6. **Commit new file**

---

## GIAI ĐOẠN 5 — Đặt token (chỉ khi cần)

### 5.0. Trước hết: có cần token không?

Nhiều trường hợp **không cần token nào cả**. Tra bảng:

| Trường hợp | Token GitHub | Token GitLab |
|---|---|---|
| HTTPS + lưu trên GitHub | ❌ Không cần — tool tự mượn | ❌ |
| **SSH** + muốn dấu ✅/❌ trên GitHub | ✅ **Cần** | ❌ |
| **SSH** + `report_to_github: false` | ❌ Không cần | — |
| Lưu artifact trên **GitLab** | — | ✅ **Cần**¹ |
| `report_to_github: false` + `local` | ❌ | ❌ |

¹ Trừ khi máy build **đã từng `git push` lên GitLab đó qua HTTPS** — khi đó
tool tự mượn thông tin đăng nhập, giống hệt cách làm với GitHub.

> **Phương án B** (SSH + GitLab, hay dùng nhất): chỉ cần **1 token GitLab**,
> không cần token GitHub.

### 5.1. Token GitHub — lấy ở đâu, tích quyền gì

**Địa chỉ**: https://github.com/settings/tokens

> ⚠️ Đây là Settings **tài khoản của bạn**, khác hoàn toàn Settings repo
> khách hàng (`github.com/<khách>/<repo>/settings`) — cái khách không cho vào.
> Nếu bạn từng thêm SSH key thì đã vào khu vực này rồi.

| Bước | Làm gì |
|---|---|
| 1 | Vào link trên |
| 2 | Chọn tab **"Tokens (classic)"** — KHÔNG phải "Fine-grained tokens" |
| 3 | **"Generate new token"** → **"Generate new token (classic)"** |
| 4 | **Note**: gõ tên bất kỳ, ví dụ `build-watcher` |
| 5 | **Expiration**: chọn `90 days` |
| 6 | **Select scopes**: tích ô **`repo`** (tích ô cha là đủ) |
| 7 | Kéo xuống cuối → **"Generate token"** |
| 8 | Copy chuỗi bắt đầu bằng **`ghp_...`** — **chỉ hiện đúng 1 lần** |

Đặt vào máy — Command Prompt **as Administrator**:
```
setx BUILD_WATCHER_GITHUB_TOKEN "ghp_dan-chuoi-vao-day" /M
```

### 5.2. Token GitLab — lấy ở đâu, tích quyền gì

**Địa chỉ**: https://gitlab.com/-/user_settings/personal_access_tokens

Hoặc bấm tay: ảnh đại diện góc trên phải → **Preferences** → menu trái
**Access Tokens**

> Nếu dùng GitLab nội bộ công ty, thay `gitlab.com` bằng địa chỉ GitLab đó.

| Bước | Làm gì |
|---|---|
| 1 | Vào link trên |
| 2 | Bấm **"Add new token"** |
| 3 | **Token name**: gõ tên bất kỳ, ví dụ `build-watcher` |
| 4 | **Expiration date**: chọn ngày hết hạn |
| 5 | **Select scopes**: tích ô **`api`** |
| 6 | Bấm **"Create personal access token"** |
| 7 | Copy chuỗi bắt đầu bằng **`glpat-...`** — **chỉ hiện đúng 1 lần** |

Đặt vào máy — Command Prompt **as Administrator**:
```
setx BUILD_WATCHER_GITLAB_TOKEN "glpat-dan-chuoi-vao-day" /M
```

### 5.3. Bảng đối chiếu nhanh

| | GitHub | GitLab |
|---|---|---|
| Trang lấy token | `github.com/settings/tokens` | `gitlab.com/-/user_settings/personal_access_tokens` |
| Loại token | **Tokens (classic)** | Personal Access Token |
| Quyền cần tích | **`repo`** | **`api`** |
| Chuỗi bắt đầu bằng | `ghp_` | `glpat-` |
| Tên biến môi trường | `BUILD_WATCHER_GITHUB_TOKEN` | `BUILD_WATCHER_GITLAB_TOKEN` |

### 5.4. Sau khi đặt token

**Khởi động lại máy.** Bắt buộc.

> `setx` chỉ có hiệu lực với **cửa sổ mở sau đó**, không áp dụng cho cửa sổ
> đang mở. Nếu sau này chạy bằng Task Scheduler thì càng phải khởi động lại,
> vì service chỉ nạp biến môi trường 1 lần lúc khởi động.

Sau khi khởi động lại, chạy `check.bat` để xác nhận.

### 5.5. Lưu ý bảo mật

Token quyền `repo` (GitHub) có toàn quyền trên **mọi repo tài khoản đó truy
cập được — kể cả repo của khách hàng khác**. Token này lại nằm thường trực
trên máy build.

Nếu tài khoản bạn tham gia nhiều repo khách hàng, cân nhắc:
- Đặt hạn ngắn (90 ngày) và xoay vòng, **không** để vĩnh viễn
- Hoặc dùng 1 tài khoản GitHub riêng cho việc build, nhờ khách add làm
  collaborator vào **đúng 1 repo** — khi đó token chỉ chạm được 1 repo

---

## GIAI ĐOẠN 6 — Kiểm tra

Nhấn đúp **`check.bat`**. Kết quả đúng:

```
trigger branch build-requests is at xxxxxxxxxxxx
request file Build_Infor.txt found
allowlisted requesters: *
build script: build.bat
artifacts go to: gitlab
artifacts go to GitLab project 12345678      <- chỉ hiện nếu chọn GitLab
check passed
==> TAT CA DEU TOT. Co the chay run.bat.
```

Đỏ → tra bảng ở Giai đoạn 9.

---

## GIAI ĐOẠN 7 — Chạy thử

| Bước | Làm gì | Kết quả đúng |
|---|---|---|
| 7.1 | Nhấn đúp `build-once.bat` | `processed 0 request` — **đúng**, lần đầu chỉ ghi mốc |
| 7.2 | Trên GitHub, sửa `Build_Infor.txt`, thêm dòng `[Build] - [ten-branch-that]` rồi Commit | Commit thành công |
| 7.3 | Nhấn đúp `build-once.bat` lần 2 | Dòng cuối kết thúc bằng `-> ok` |
| 7.4 | Kiểm tra file kết quả | Xem bảng dưới |

Nơi tìm file `.zip` tuỳ lựa chọn ở 0.4:

| `artifact_target` | Tìm ở đâu |
|---|---|
| `github` | Repo GitHub → mục **Releases** |
| `gitlab` | Project GitLab → **Deploy** → **Package Registry** |
| `local` | `C:\build-watcher\data\artifacts\` |

---

## GIAI ĐOẠN 8 — Cho chạy liên tục

### Cách đơn giản
Nhấn đúp **`run.bat`**, giữ cửa sổ mở.

### Cách chạy ngầm (Task Scheduler)

> ⚠️ **Điểm quan trọng nhất**: phải chọn chạy dưới **đúng tài khoản Windows
> đã ghi ở mục 1.3**. Để mặc định `SYSTEM` là **không tìm thấy thông tin đăng
> nhập** — đã kiểm chứng thật: cùng máy, cùng lệnh, tài khoản đăng nhập thì
> thấy credential, `SYSTEM` thì không thấy gì.

1. Mở **Task Scheduler** → **Create Task...**
2. Tab **General**:
   - Name: `build-watcher`
   - **Change User or Group...** → gõ tài khoản ở mục 1.3
   - Chọn **Run whether user is logged on or not**
3. Tab **Triggers** → **New...** → **At startup**
4. Tab **Actions** → **New...**:
   - Program: `C:\build-watcher\python\python.exe`
   - Arguments: `-m build_watcher --config C:\build-watcher\config.json run`
   - Start in: `C:\build-watcher`
5. Tab **Settings**: tích **restart every 1 minute if fails**, bỏ tích
   **stop the task if it runs longer than...**
6. OK → nhập mật khẩu Windows

---

## GIAI ĐOẠN 9 — Bảng tra sự cố khi porting

| Hiện tượng | Nguyên nhân | Cách sửa |
|---|---|---|
| `Khong tim thay Git` | Chưa cài Git | Cài, **đóng cửa sổ, mở lại**, chạy lại |
| `Chua tim thay thong tin dang nhap GitHub` | Chưa làm 1.3 | Làm 1.3.1 hoặc 1.3.2 |
| `Khong tai duoc Python` | Mạng chặn python.org | Tải tay, giải nén vào `C:\build-watcher\python` (README mục 9.2) |
| `unknown revision` / `ambiguous argument` | Chưa tạo branch chứa yêu cầu | Làm Giai đoạn 4 |
| `cloned over SSH, and SSH keys cannot be used` | Máy dùng SSH mà bật báo cáo GitHub | Đặt token GitHub (5.1) hoặc `report_to_github: false` |
| `no GitLab token` | Chưa đặt token GitLab | Làm 5.2 |
| `HTTP 404` khi upload GitLab | Sai Project ID, hoặc điền nhầm ID của **Group** | Lấy lại ID trên trang **project** |
| `HTTP 401` khi upload GitLab | Token sai/hết hạn/thiếu quyền `api` | Tạo token mới, nhớ tích `api` |
| `cannot open ... for writing` khi build | Đường dẫn quá dài | Chuyển về `C:\build-watcher` (2.2) |
| Build chạy nhưng `build.bat not found on this branch` | Repo chưa có file script build ở branch đó | Xem 0.2.1 |
| Không có gì xảy ra sau khi push yêu cầu | Lần chạy đầu chỉ ghi mốc | Push thêm 1 yêu cầu **mới** nữa |

---

## Đổi sang repo khác trên **cùng** máy

Không cần cài lại. Làm 3 bước:

1. Chạy lại `setup.bat` (nó sẽ hỏi lại và ghi đè `config.json`)
2. **Xoá** thư mục `C:\build-watcher\data\repo`
3. **Xoá** file `C:\build-watcher\data\state.json`
4. Chạy `check.bat`

> Bước 2 và 3 bắt buộc: nếu không xoá, tool vẫn dùng code và mốc lịch sử của
> repo cũ.

---

## Bảng tra: đổi gì thì sửa ở đâu

| Muốn đổi | Sửa gì trong `config.json` |
|---|---|
| Repo khác | `repo_url`, `owner`, `repo` (+ xoá `data\repo` và `data\state.json`) |
| Khách không cho ghi vào repo họ | Thêm `trigger_repo_url` trỏ vào repo của bạn (mục 0.1b) |
| Tên branch chứa yêu cầu | `trigger_branch` |
| Tên file yêu cầu | `request_file` |
| File script build | `build_script` |
| Đường dẫn file kết quả | `artifact_globs` |
| Các preset | `allowed_presets` |
| Nhanh/chậm hơn | `poll_interval_seconds` (giây) |
| Thời gian chờ build tối đa | `build_timeout_seconds` (giây) |
| Giới hạn ai được build | `allowed_committers` (thay `"*"` bằng danh sách email) |
| Nơi lưu artifact | `artifact_target`: `github` / `gitlab` / `local` |
| GitLab khác | `gitlab_url`, `gitlab_project_id` |
| Bật/tắt dấu tick trên GitHub | `report_to_github` |

> **Không bao giờ cần sửa file nào trong thư mục `build_watcher\`.**

---

## Phương án khi bị chặn

| Bị chặn ở đâu | Phương án thay thế |
|---|---|
| **Khách không cho ghi gì vào repo họ** (không tạo được branch) | Thêm `trigger_repo_url` trỏ vào repo của bạn — xem mục 0.1b. Repo khách chỉ bị đọc |
| Khách không cho ghi gì vào repo họ | `artifact_target: gitlab` + `report_to_github: false` |
| Không tạo được token nào | `report_to_github: false` + `artifact_target: local` — vẫn build, tự lấy file trên máy |
| Mạng chặn python.org | Tải Python bằng máy khác, chép sang (README mục 9.2) |
| Không cài được Task Scheduler | Dùng `run.bat`, giữ cửa sổ mở |

---

## PHỤ LỤC — Ví dụ hoàn chỉnh từ đầu đến cuối

> Ví dụ này dùng số liệu giả định cụ thể để bạn hình dung. Thay các giá trị
> **in đậm** bằng giá trị thật của bạn.

### Bối cảnh giả định

| Thứ | Giá trị trong ví dụ |
|---|---|
| Repo khách hàng (**A**) | `https://github.com/acme-corp/vehicle-fw` |
| Clone bằng | **SSH** → `git@github.com:acme-corp/vehicle-fw.git` |
| GitLab của team (**B**) | `https://gitlab.com/my-team/build-artifacts` |
| GitLab Project ID | `61234567` |
| Máy build | Windows, tài khoản Windows `CORP\vietdq` |
| Dự án build bằng | `build.bat`, nhận tham số preset |
| Preset | `Debug`, `Release` |
| Kết quả build nằm ở | `out/Debug/firmware.hex`, `out/Release/firmware.hex` |

Vì máy dùng **SSH** và muốn lưu file trên **GitLab team** → chọn **phương án B**
(`report_to_github: false` + `artifact_target: gitlab`).

---

### BƯỚC 1 — Kiểm tra máy build

Mở **Command Prompt**, chạy từng lệnh:

```
git --version
```
> Kết quả mong đợi: `git version 2.45.0.windows.1`

```
ssh -T git@github.com
```
> Kết quả mong đợi: `Hi vietdq-acme! You've successfully authenticated...`
>
> Ghi lại tên tài khoản GitHub: `vietdq-acme`
> Ghi lại tài khoản Windows đang dùng (gõ `whoami`): `CORP\vietdq`

Kiểm tra dự án build tay được không:
```
cd C:\work\vehicle-fw
build.bat Debug
```
> Phải build thành công và sinh ra `out\Debug\firmware.hex`

---

### BƯỚC 2 — Lấy tool về và copy

```
git clone -b feature/Build_Watcher https://github.com/DoQuocViet1110/Git-GitHub-learning.git C:\temp-tool
```

Copy thư mục tool sang đúng chỗ:
```
xcopy /E /I C:\temp-tool\tools\build-watcher C:\build-watcher
```

Xoá thư mục tạm:
```
rmdir /S /Q C:\temp-tool
```

Kiểm tra đã copy đúng:
```
dir C:\build-watcher
```
> Phải thấy: `setup.bat`, `run.bat`, `check.bat`, `build-once.bat`,
> `setup_wizard.py`, `README.md`, `PORTING.md`, `build_watcher`, `tests`
>
> **Không được có**: `python`, `data`, `config.json`

---

### BƯỚC 3 — Lấy GitLab Project ID

1. Mở trình duyệt vào `https://gitlab.com/my-team/build-artifacts`
2. Ngay dưới tên project thấy dòng `Project ID: 61234567`
3. Ghi lại: **`61234567`**

> ⚠️ Phải là trang **project**, không phải trang group (`gitlab.com/my-team`).

---

### BƯỚC 4 — Tạo token GitLab

1. Vào `https://gitlab.com/-/user_settings/personal_access_tokens`
2. Bấm **Add new token**
3. **Token name**: `build-watcher`
4. **Expiration date**: chọn ngày cách 90 ngày
5. **Select scopes**: tích ô **`api`**
6. Bấm **Create personal access token**
7. Copy chuỗi hiện ra, ví dụ: `glpat-AbCdEf123456GhIjKl`

Mở **Command Prompt as Administrator** (chuột phải → Run as administrator):
```
setx BUILD_WATCHER_GITLAB_TOKEN "glpat-AbCdEf123456GhIjKl" /M
```
> Kết quả mong đợi: `SUCCESS: Specified value was saved.`

**Khởi động lại máy.**

---

### BƯỚC 5 — Chạy cài đặt

Nhấn đúp **`C:\build-watcher\setup.bat`**.

Trả lời các câu hỏi như sau:

```
Dia chi repo tren GitHub
   (vi du: https://github.com/ten-khach-hang/ten-repo): git@github.com:acme-corp/vehicle-fw.git
  -> Chu so huu : acme-corp
  -> Ten repo   : vehicle-fw
  -> Giao thuc  : SSH

Ten branch chua file yeu cau build [build-requests]:            <- nhấn Enter
Ten file yeu cau build [Build_Infor.txt]:                       <- nhấn Enter

Ten file script de build [build.bat]:                           <- nhấn Enter
Cac preset cho phep (cach nhau bang dau phay) [Debug,Release]:   <- nhấn Enter
Duong dan file ket qua [build/*/*.elf,...]: out/*/*.hex          <- GÕ VÀO

  !!! LUU Y QUAN TRONG - repo nay dung SSH !!!
  ...
Bat bao ket qua len GitHub? [y/N]:                              <- nhấn Enter (= No)

3b. LUU FILE KET QUA (.zip) O DAU
  1. github   2. gitlab   3. local
Chon 1, 2 hoac 3 [3]: 2                                         <- GÕ 2

Dia chi GitLab [https://gitlab.com]:                            <- nhấn Enter
Project ID (chi gom chu so): 61234567                           <- GÕ VÀO
Ten goi luu tru tren GitLab (Enter = tu dat theo ten branch):    <- nhấn Enter

Danh sach email duoc phep (* = tat ca) [*]:                     <- nhấn Enter
```

Chờ đến khi thấy:
```
====================================================================
  DA TAO XONG config.json
====================================================================
```

---

### BƯỚC 6 — Kiểm tra file cấu hình

Mở `C:\build-watcher\config.json` bằng **Notepad**. Nội dung phải giống:

```json
{
  "repo_url": "git@github.com:acme-corp/vehicle-fw.git",
  "owner": "acme-corp",
  "repo": "vehicle-fw",
  "trigger_branch": "build-requests",
  "request_file": "Build_Infor.txt",
  "poll_interval_seconds": 60,
  "root": "C:/build-watcher/data",
  "build_script": "build.bat",
  "build_timeout_seconds": 3600,
  "artifact_globs": [
    "out/*/*.hex"
  ],
  "allowed_committers": [
    "*"
  ],
  "allowed_presets": [
    "Debug",
    "Release"
  ],
  "report_to_github": false,
  "status_context": "build-watcher/local",
  "artifact_target": "gitlab",
  "gitlab_url": "https://gitlab.com",
  "gitlab_project_id": "61234567"
}
```

Sai chỗ nào thì sửa thẳng trong Notepad rồi **Save** (Ctrl+S).

---

### BƯỚC 7 — Tạo branch trên GitHub khách hàng

Làm trên **trình duyệt**:

1. Vào `https://github.com/acme-corp/vehicle-fw`
2. Bấm ô chọn branch (đang ghi `main`)
3. Gõ: `build-requests`
4. Bấm **"Create branch: build-requests from main"**
5. Bấm **Add file** → **Create new file**
6. Ô tên file gõ: `Build_Infor.txt`
7. Ô nội dung gõ:
   ```
   # File yeu cau build
   ```
8. Kéo xuống, bấm **Commit new file**

---

### BƯỚC 8 — Kiểm tra kết nối

Nhấn đúp **`C:\build-watcher\check.bat`**.

Kết quả đúng:
```
2026-08-23 09:15:02 INFO  build_watcher: trigger branch build-requests is at a1b2c3d4e5f6
2026-08-23 09:15:02 INFO  build_watcher: request file Build_Infor.txt found
2026-08-23 09:15:02 INFO  build_watcher: allowlisted requesters: *
2026-08-23 09:15:02 INFO  build_watcher: build script: build.bat
2026-08-23 09:15:02 INFO  build_watcher: artifacts go to: gitlab
2026-08-23 09:15:02 INFO  build_watcher: artifacts go to GitLab project 61234567 at https://gitlab.com
2026-08-23 09:15:02 INFO  build_watcher: check passed

  ==> TAT CA DEU TOT. Co the chay run.bat.
```

---

### BƯỚC 9 — Chạy thử lần 1 (ghi mốc)

Nhấn đúp **`build-once.bat`**.

```
2026-08-23 09:16:10 INFO  build_watcher.watcher: first run; baseline set to a1b2c3d4e5f6
2026-08-23 09:16:10 INFO  build_watcher: processed 0 request(s)
```

> `processed 0 request` là **ĐÚNG**. Lần đầu tool chỉ ghi nhớ vị trí hiện tại
> làm mốc, chưa build gì.

---

### BƯỚC 10 — Gửi yêu cầu build thật

Trên **trình duyệt**:

1. Vào `https://github.com/acme-corp/vehicle-fw`
2. Chuyển sang branch **`build-requests`**
3. Bấm vào file `Build_Infor.txt`
4. Bấm biểu tượng **cây bút chì** (Edit this file)
5. Thêm 1 dòng ở cuối:
   ```
   [Build] - [feature/them-canh-bao-nhiet-do] - [Debug]
   ```
   > Thay `feature/them-canh-bao-nhiet-do` bằng tên branch thật cần build
6. Bấm **Commit changes**

---

### BƯỚC 11 — Chạy thử lần 2 (build thật)

Nhấn đúp **`build-once.bat`**.

```
INFO  watcher: 1 new request commit(s) since a1b2c3d4e5f6
INFO  watcher: request feature-them-canh-bao-nhiet-do-Debug-f7e8d9c0b1a2 from vietdq@acme.com
INFO  builder: building ... C:\build-watcher\data\work\wt-3a4b5c6d7e8f\build.bat Debug
INFO  packager: packaged 1 file(s) into C:\build-watcher\data\artifacts\feature-them-canh-bao-nhiet-do-Debug-f7e8d9c0b1a2.zip
INFO  gitlab_client: uploaded ...zip to GitLab package feature-them-canh-bao-nhiet-do-Debug-f7e8d9c0b1a2/2026.823.91745
INFO  watcher: request ... -> ok (95s): built in 92s
INFO  build_watcher: processed 1 request(s)
```

Thấy **`-> ok`** là thành công.

---

### BƯỚC 12 — Lấy file kết quả

1. Vào `https://gitlab.com/my-team/build-artifacts`
2. Menu bên trái: **Deploy** → **Package Registry**
3. Thấy gói tên `feature-them-canh-bao-nhiet-do-Debug-f7e8d9c0b1a2`
4. Bấm vào → tải file `.zip` về
5. Giải nén → có `out/Debug/firmware.hex`

> File cũng được lưu sẵn trên máy tại
> `C:\build-watcher\data\artifacts\`

---

### BƯỚC 13 — Cho chạy liên tục

Nhấn đúp **`run.bat`** và giữ cửa sổ mở.

Từ giờ, mỗi khi ai đó thêm dòng `[Build] - [ten-branch]` vào `Build_Infor.txt`
và commit, máy build sẽ tự build trong vòng 60 giây và đẩy file lên GitLab.

Muốn chạy ngầm không cần giữ cửa sổ → xem Giai đoạn 8, nhớ chọn chạy dưới
tài khoản Windows `CORP\vietdq` (tài khoản đã ghi ở Bước 1).

---

### Tổng kết ví dụ: đã đụng vào những gì

| Nơi | Đã làm gì |
|---|---|
| Máy build | Copy tool vào `C:\build-watcher`, chạy `setup.bat`, đặt token GitLab |
| Repo GitHub khách (**A**) | Tạo branch `build-requests` + file `Build_Infor.txt`. **Không** ghi gì khác |
| GitLab team (**B**) | Nhận file `.zip` trong Package Registry |

Repo khách hàng chỉ bị thêm **1 branch chứa 1 file text**, ngoài ra code và
lịch sử của họ không bị đụng tới.

---

## Checklist rút gọn (in ra mang theo)

```
GIAI DOAN 0 - Thu thap thong tin
[ ] Dia chi repo GitHub:        ____________________________
[ ] SSH hay HTTPS:              ____________________________
[ ] Ten file script build:      ____________________________
[ ] Cac preset:                 ____________________________
[ ] Duong dan file ket qua:     ____________________________
[ ] GitLab Project ID (neu can):____________________________
[ ] Chon phuong an luu (A/B/C/D):___________________________

GIAI DOAN 1 - Chuan bi may
[ ] git --version chay duoc
[ ] Toolchain build da cai, build tay duoc
[ ] Xac thuc GitHub OK -> tai khoan Windows: ________________

GIAI DOAN 2 - Copy
[ ] Copy vao C:\build-watcher  (duong dan NGAN)
[ ] Da xoa: python\  data\  config.json  (neu copy tu may cu)

GIAI DOAN 3 - Cai dat
[ ] Nhan dup setup.bat -> thay "CAI DAT HOAN TAT"

GIAI DOAN 4 - GitHub
[ ] Tao branch chua yeu cau build
[ ] Tao file Build_Infor.txt trong branch do

GIAI DOAN 5 - Token (neu can)
[ ] Token GitHub da dat  (hoac: khong can)
[ ] Token GitLab da dat  (hoac: khong can)
[ ] DA KHOI DONG LAI MAY sau khi dat token

GIAI DOAN 6 - Kiem tra
[ ] check.bat -> "TAT CA DEU TOT"

GIAI DOAN 7 - Chay thu
[ ] build-once.bat lan 1 -> "processed 0 request"
[ ] Push 1 yeu cau build len GitHub
[ ] build-once.bat lan 2 -> "-> ok"
[ ] Tim thay file .zip dung noi da chon

GIAI DOAN 8 - Chay lien tuc
[ ] run.bat  HOAC  Task Scheduler (dung tai khoan o Giai doan 1)
```
