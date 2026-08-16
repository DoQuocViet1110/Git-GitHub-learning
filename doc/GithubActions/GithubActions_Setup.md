# GitHub Actions CI — Hướng dẫn thiết lập & giải thích chi tiết

| | |
|---|---|
| Document Title | GitHub Actions CI Setup for STM32F4 firmware build |
| File workflow  | `.github/workflows/build.yml` |
| Mục đích       | Tự động build firmware (Debug + Release) mỗi khi có push/PR |
| Đối tượng đọc  | Người chưa từng dùng GitHub Actions, cần hiểu và tự làm lại được |

---

## 1. GitHub Actions là gì (tóm tắt nhanh)

GitHub Actions là dịch vụ **CI/CD (Continuous Integration)** tích hợp sẵn trong GitHub.
Nó cho phép bạn khai báo một quy trình (gọi là **workflow**) chạy tự động trên máy chủ
ảo của GitHub mỗi khi có sự kiện xảy ra trong repo (push code, tạo Pull Request, v.v.).

Trong project này, workflow được dùng để: **mỗi khi có code mới được push lên GitHub,
tự động build firmware bằng đúng toolchain ARM để kiểm tra code có compile được
không**, thay vì phải tự build tay trên máy local rồi mới biết có lỗi hay không.

## 2. Các khái niệm cần biết trước khi đọc file YAML

| Khái niệm | Giải thích |
|---|---|
| **Workflow** | Toàn bộ 1 file `.yml` trong `.github/workflows/`. Mỗi file là 1 quy trình tự động độc lập. |
| **Trigger (`on:`)** | Điều kiện để workflow được kích hoạt (push, pull request, chạy tay...). |
| **Job** | Một nhóm công việc chạy trên 1 máy ảo (runner). 1 workflow có thể có nhiều job. |
| **Runner** | Máy ảo mà GitHub cấp miễn phí để chạy job (ví dụ `ubuntu-latest`). |
| **Step** | Một bước cụ thể bên trong job (chạy lệnh shell, hoặc gọi 1 "Action" có sẵn). |
| **Action** | Một đoạn script đóng gói sẵn, dùng lại được (ví dụ: cài toolchain, checkout code). Được viết theo dạng `chủ-sở-hữu/tên-action@version`. |
| **Matrix** | Cơ chế cho phép 1 job chạy lặp lại nhiều lần với các tham số khác nhau (ở đây là chạy song song bản Debug và Release). |
| **Artifact** | File kết quả (ví dụ `.hex`, `.bin`) được lưu lại sau khi job chạy xong, có thể tải về từ tab Actions trên GitHub. |

## 3. File đã tạo

Đường dẫn: **`.github/workflows/build.yml`**

GitHub tự động quét mọi file `.yml`/`.yaml` nằm trong thư mục `.github/workflows/`
của repo — chỉ cần file nằm đúng chỗ này và cú pháp hợp lệ là nó sẽ tự chạy,
**không cần đăng ký hay bật thủ công ở đâu khác**.

## 4. Giải thích từng phần trong `build.yml`

### 4.1. Tên workflow

```yaml
name: Build Firmware
```

Đây là tên hiển thị trên tab **Actions** của GitHub. Đặt tên ngắn gọn, dễ nhận biết.

### 4.2. Trigger — khi nào workflow chạy

```yaml
on:
  push:
    branches:
      - '**'
  pull_request:
    branches:
      - main
      - develop
  workflow_dispatch:
```

- `push: branches: ['**']` → chạy khi push lên **bất kỳ branch nào** (feature/*, develop, main...).
- `pull_request: branches: [main, develop]` → chạy khi có Pull Request nhắm vào `main` hoặc `develop`, để kiểm tra code trước khi merge.
- `workflow_dispatch` → thêm nút **"Run workflow"** trên giao diện GitHub, cho phép bấm chạy tay khi cần (không cần push code mới).

### 4.3. Job và Matrix — build cả Debug lẫn Release

```yaml
jobs:
  build:
    name: Build (${{ matrix.preset }})
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        preset: [Debug, Release]
```

- `runs-on: ubuntu-latest` → job chạy trên máy ảo Ubuntu do GitHub cấp miễn phí.
- `matrix: preset: [Debug, Release]` → job này sẽ **tự nhân đôi**, chạy song song
  2 lần: 1 lần với `matrix.preset = Debug`, 1 lần với `matrix.preset = Release`.
  Đây chính là 2 preset đã có sẵn trong `CMakePresets.json` của project.
- `fail-fast: false` → nếu bản Debug lỗi thì bản Release vẫn tiếp tục chạy hết
  (không bị hủy theo), giúp thấy được toàn bộ lỗi cùng lúc.

### 4.4. Các bước (steps) trong mỗi job

**Bước 1 — Lấy code về máy ảo:**
```yaml
- name: Checkout repository
  uses: actions/checkout@v4
```
Máy ảo mặc định trống, không có code. Action `checkout` sẽ clone đúng
commit vừa được push về máy ảo để build.

**Bước 2 — Cài Ninja (build generator):**
```yaml
- name: Install Ninja
  uses: seanmiddleditch/gha-setup-ninja@v5
```
Project dùng `Ninja` làm generator cho CMake (khai báo trong `CMakePresets.json`,
mục `"generator": "Ninja"`), nên máy ảo cần được cài Ninja trước khi `cmake` chạy được.

**Bước 3 — Cài ARM GCC toolchain:**
```yaml
- name: Install ARM GNU Toolchain
  uses: carlosperate/arm-none-eabi-gcc-action@v1
  with:
    release: '13.2.Rel1'
```
Project build cho vi điều khiển ARM Cortex-M4 (STM32F411), cần trình biên dịch
`arm-none-eabi-gcc` — khác với gcc thường trên máy tính. Action này tự tải và
cài đúng phiên bản toolchain, tương tự việc bạn tự cài ARM toolchain trên máy
local để dùng với `cmake/gcc-arm-none-eabi.cmake`.

**Bước 4 — Configure CMake theo preset:**
```yaml
- name: Configure (${{ matrix.preset }})
  run: cmake --preset ${{ matrix.preset }}
```
Tương đương lệnh bạn gõ tay: `cmake --preset Debug` hoặc `cmake --preset Release`.
Kết quả sinh ra thư mục `build/Debug` hoặc `build/Release`.

**Bước 5 — Build:**
```yaml
- name: Build (${{ matrix.preset }})
  run: cmake --build --preset ${{ matrix.preset }}
```
Tương đương `cmake --build --preset Debug`. Đây là bước biên dịch thật sự;
nếu code có lỗi cú pháp/compile, job sẽ **fail (đỏ)** ngay tại bước này.

**Bước 6 — Xuất file `.hex` / `.bin`:**
```yaml
- name: Generate .hex / .bin
  working-directory: build/${{ matrix.preset }}
  run: |
    ELF=$(find . -maxdepth 1 -name '*.elf' | head -n1)
    arm-none-eabi-objcopy -O ihex "$ELF" "${ELF%.elf}.hex"
    arm-none-eabi-objcopy -O binary "$ELF" "${ELF%.elf}.bin"
```
Mặc định CMake trong project chỉ sinh ra file `.elf`. Bước này dùng lệnh
`objcopy` (đi kèm ARM toolchain) để chuyển `.elf` thành `.hex`/`.bin`, là các
định dạng thường dùng để nạp (flash) trực tiếp vào vi điều khiển.

**Bước 7 — In thông tin dung lượng firmware:**
```yaml
- name: Print firmware size
  working-directory: build/${{ matrix.preset }}
  run: |
    ELF=$(find . -maxdepth 1 -name '*.elf' | head -n1)
    arm-none-eabi-size "$ELF"
```
In ra dung lượng vùng `text` (flash) / `data` + `bss` (RAM) đã dùng, ngay
trong log của job — giúp theo dõi firmware có phình to bất thường không.

**Bước 8 — Upload artifact (lưu file để tải về):**
```yaml
- name: Upload build artifacts
  uses: actions/upload-artifact@v4
  with:
    name: stm32f4-${{ matrix.preset }}
    path: |
      build/${{ matrix.preset }}/*.elf
      build/${{ matrix.preset }}/*.hex
      build/${{ matrix.preset }}/*.bin
      build/${{ matrix.preset }}/*.map
    if-no-files-found: error
    retention-days: 14
```
Sau khi máy ảo build xong, mọi thứ trong máy ảo sẽ bị xóa. Bước này đóng gói
các file `.elf/.hex/.bin/.map` thành 1 artifact có tên `stm32f4-Debug` hoặc
`stm32f4-Release`, lưu lại trên GitHub **14 ngày**, tải về được từ tab Actions.

## 5. Cách kiểm tra workflow có chạy đúng không (từng bước cho người mới)

1. Push code (commit) lên GitHub — bất kỳ branch nào cũng kích hoạt workflow.
2. Vào trang repo trên GitHub → chọn tab **Actions** (nằm ngang hàng với Code, Issues, Pull requests).
3. Sẽ thấy 1 run mới tên **"Build Firmware"**, ứng với commit vừa push, đang có biểu tượng vàng (đang chạy).
4. Bấm vào run đó → sẽ thấy 2 job con: **Build (Debug)** và **Build (Release)**, chạy song song.
5. Bấm vào từng job để xem log chi tiết từng bước (checkout, cài toolchain, build...).
   - ✅ Dấu tick xanh ở step/job = thành công.
   - ❌ Dấu X đỏ = lỗi, bấm vào step bị đỏ để đọc log lỗi (thường là lỗi biên dịch, xử lý y hệt như build lỗi trên máy local).
6. Nếu cả 2 job đều xanh, kéo xuống cuối trang run đó sẽ thấy mục **Artifacts**,
   có thể tải `stm32f4-Debug.zip` / `stm32f4-Release.zip` chứa file `.elf/.hex/.bin/.map`.

## 6. Việc cần kiểm tra 1 lần trên GitHub (nếu workflow không tự chạy)

Vào **Settings → Actions → General** của repo trên GitHub, kiểm tra 2 mục sau
(mặc định GitHub đã để đúng, nhưng nếu tổ chức/repo bị khóa sẵn thì cần đổi lại):

- **Actions permissions**: chọn **"Allow all actions and reusable workflows"**.
  (Nếu để "Disable actions" thì workflow sẽ không bao giờ chạy; nếu để chế độ
  chỉ cho phép "verified creators" thì 2 action bên thứ ba dùng trong bài này
  — `carlosperate/arm-none-eabi-gcc-action` và `seanmiddleditch/gha-setup-ninja`
  — có thể bị chặn.)
- **Workflow permissions**: để mặc định **"Read repository contents permission"**
  là đủ, vì workflow này chỉ build và upload artifact, không cần ghi ngược lại repo.

## 7. Cách chỉnh sửa / mở rộng sau này

- Muốn build thêm 1 preset khác → thêm tên preset vào danh sách
  `matrix: preset: [Debug, Release, ...]` (preset đó phải tồn tại sẵn trong `CMakePresets.json`).
- Muốn giới hạn chỉ chạy trên `main`/`develop` thay vì mọi branch → sửa
  `push: branches: ['**']` thành `push: branches: [main, develop]`.
- Muốn đổi phiên bản ARM toolchain → sửa giá trị `release:` ở bước "Install ARM GNU Toolchain".
- Muốn thêm bước chạy unit test (nếu sau này project có test) → thêm 1 step
  `run: ...` mới, đặt sau bước Build.

## 8. Các lỗi thường gặp

| Hiện tượng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| Không thấy workflow chạy trên tab Actions sau khi push | Actions đang bị Disable ở Settings, hoặc file không nằm đúng `.github/workflows/` | Kiểm tra lại mục 6, kiểm tra đường dẫn file |
| Job đỏ ngay ở bước "Install ARM GNU Toolchain" | Actions permissions đang giới hạn "verified creators only" | Đổi sang "Allow all actions and reusable workflows" |
| Job đỏ ở bước "Build" | Code có lỗi compile thật sự | Đọc log lỗi, sửa code y hệt như build lỗi trên máy local |
| Không thấy mục Artifacts sau khi job xanh | Job vẫn chưa chạy xong hoàn toàn, hoặc `if-no-files-found: error` báo không tìm thấy file `.elf` | Kiểm tra bước Build có sinh đúng file `.elf` trong `build/<preset>/` không |
