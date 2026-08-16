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

- `push: branches: ['**']` → **sự kiện** push trên bất kỳ branch nào (feature/*, develop, main...)
  sẽ được GitHub ghi nhận, nhưng **có thực sự build hay không còn tùy điều kiện `if:`** ở mục 4.3 bên dưới.
- `pull_request: branches: [main, develop]` → chạy khi có Pull Request nhắm vào `main` hoặc `develop`, để kiểm tra code trước khi merge.
- `workflow_dispatch` → thêm nút **"Run workflow"** trên giao diện GitHub, cho phép bấm chạy tay khi cần (không cần push code mới).

### 4.3. Điều kiện trigger thật sự (`if:`) — kết hợp PR-gate và commit tag

```yaml
jobs:
  build:
    name: Build (${{ matrix.preset }})
    runs-on: ubuntu-latest
    if: >
      github.event_name == 'pull_request' ||
      github.event_name == 'workflow_dispatch' ||
      (github.event_name == 'push' && contains(github.event.head_commit.message, '[build]'))
```

Đây là phần quan trọng nhất quyết định **khi nào job thực sự chạy build**, tránh
việc build tràn lan mỗi lần push code (tốn phút CI, gây nhiễu team). Quy tắc:

| Trường hợp | Có build không? | Vì sao |
|---|---|---|
| Mở/update Pull Request vào `main` hoặc `develop` | ✅ Luôn build | `github.event_name == 'pull_request'` — dùng làm cổng review bắt buộc trước khi merge |
| Bấm nút **"Run workflow"** trên GitHub | ✅ Luôn build | `github.event_name == 'workflow_dispatch'` — chủ động chạy tay khi cần |
| Push commit **có chứa `[build]`** trong commit message | ✅ Build | vế thứ 3 của điều kiện khớp |
| Push commit **không có `[build]`** trong commit message | ❌ Job hiển thị "Skipped", không build | vế thứ 3 không khớp, không rơi vào 2 vế trên |

**Cách dùng trong thực tế**: khi push code bình thường lên feature branch để lưu
tiến độ, cứ commit/push như thường — sẽ **không** tốn CI. Khi nào muốn GitHub
tự build thử (ví dụ vừa sửa xong 1 phần, muốn chắc chắn compile được trên máy
sạch), chỉ cần thêm `[build]` vào commit message, ví dụ:

```bash
git commit -m "feat: add debounce for button input [build]"
```

Khi mở Pull Request thì **không cần quan tâm tag này nữa** — PR luôn tự build
để đảm bảo code sắp merge vào `develop`/`main` là hợp lệ.

> Lưu ý: `github.event.head_commit.message` chỉ tồn tại với sự kiện `push`,
> không tồn tại ở `pull_request`/`workflow_dispatch` — đó là lý do điều kiện
> phải bọc `contains(...)` trong `(github.event_name == 'push' && ...)`, nếu
> không sẽ lỗi khi chạy trên PR.

### 4.4. Job và Matrix — build cả Debug lẫn Release

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

### 4.5. Các bước (steps) trong mỗi job

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

### 5.1. Artifact (.elf/.hex/.bin) được lưu ở đâu, tải về thế nào

File `.elf`/`.hex`/`.bin`/`.map` sau khi build **không được commit vào repo** —
chúng chỉ tồn tại dưới dạng **GitHub Actions Artifact**, gắn liền với từng lần
chạy (run) cụ thể của workflow.

**Cách tải về qua giao diện web (cách thường dùng nhất):**

1. Vào repo trên GitHub → tab **Actions**.
2. Chọn đúng run bạn cần (mỗi run ứng với 1 lần push/PR/chạy tay, xem theo tên
   commit hoặc branch để chọn đúng).
3. Trong trang chi tiết của run đó, kéo xuống **cuối trang** → mục **Artifacts**.
4. Sẽ thấy 2 mục: `stm32f4-Debug` và `stm32f4-Release` (đúng theo 2 giá trị
   trong `matrix.preset`). Bấm vào tên artifact để tải file `.zip` về máy.
5. Giải nén ra sẽ có: `STM32F4.elf`, `STM32F4.hex`, `STM32F4.bin`, `STM32F4.map`.

**Lưu ý quan trọng:**

- Artifact chỉ được giữ lại **14 ngày** kể từ lúc build (do cấu hình
  `retention-days: 14` trong bước "Upload build artifacts") rồi GitHub sẽ tự
  xóa — không tích lũy vô hạn theo thời gian.
- Mỗi lần workflow chạy lại (mỗi lần push mới) sẽ tạo ra **artifact mới**,
  độc lập với các lần chạy trước — không ghi đè lên artifact cũ.
- Nếu cần giữ file build **vĩnh viễn** (ví dụ để phát hành bản chính thức),
  nên dùng tính năng **GitHub Releases** thay vì trông chờ vào Artifact.

**Cách tải bằng `gh` CLI (dành cho ai đã cài GitHub CLI):**

```bash
# Xem danh sách các lần chạy gần nhất
gh run list

# Tải toàn bộ artifact của 1 run cụ thể (thay <run-id> bằng ID lấy từ lệnh trên)
gh run download <run-id>
```

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
| Job **self-hosted** đỏ ngay bước đầu tiên: `Error: pwsh: command not found` | `build.yml` khai báo `shell: pwsh` (PowerShell 7/Core), nhưng máy runner chỉ cài sẵn **Windows PowerShell 5.1** (`powershell.exe`) — Windows không tự có `pwsh.exe` | Đổi `shell: pwsh` thành `shell: powershell` trong `defaults.run` của job `build-self-hosted` (cú pháp PowerShell dùng trong các step này tương thích cả 2 bản), hoặc cài PowerShell 7 trên máy runner rồi giữ nguyên `pwsh` |
| Job **self-hosted** vẫn đỏ ở bước "Verify local toolchain is on PATH" **dù `cmake`/`ninja`/`arm-none-eabi-gcc` chạy tay bình thường**, fail rất nhanh (~1-2 giây), log không rõ lỗi gì | **PowerShell Execution Policy** ở scope `LocalMachine` đang là `Undefined`/`Restricted`, chặn chạy mọi file `.ps1` mà runner tự tạo ra cho từng bước `run:` — xem giải thích đầy đủ + cách kiểm tra + cách sửa ở **mục 9.5** bên dưới | `Set-ExecutionPolicy -Scope LocalMachine -ExecutionPolicy RemoteSigned -Force` (PowerShell as Administrator) |
| Đổi PATH cấp Machine hoặc quyền group cho `NETWORK SERVICE` xong nhưng job vẫn lỗi y hệt lỗi cũ | Windows chỉ nạp **PATH** và **group membership vào access token** tại thời điểm service *khởi động (logon)* — service đang chạy sẵn sẽ không tự thấy thay đổi — xem giải thích đầy đủ + cách kiểm tra ở **mục 9.6** bên dưới | Restart lại chính service runner: `Restart-Service -Name "actions.runner.<owner>-<repo>.<name>"` |

## 9. Self-hosted Runner — build ngay trên máy local (dùng cho license dạng USB dongle)

> Toàn bộ mục 9 (9.1–9.8) viết cho máy runner chạy **Windows**. Nếu máy có
> dongle/cần build local lại là **Linux**, xem riêng **mục 11** ở cuối tài
> liệu — các khái niệm nền tảng vẫn giống nhau, chỉ khác công cụ hệ điều hành.

### 9.1. Vì sao cần self-hosted runner

Máy ảo (`ubuntu-latest`) của GitHub chạy trên cloud, **không thể truy cập USB
dongle** cắm ở máy local (ví dụ license GHS). Giải pháp: cài 1 **agent runner**
ngay trên máy có dongle — agent này tự kết nối ra ngoài (outbound) tới GitHub
để nhận job, tự `git checkout` code về và build **ngay trên máy đó**, dùng
được mọi thứ đã cài sẵn (bao gồm dongle). Không cần mở port/inbound vào máy.

Job build trên self-hosted runner nằm ở job `build-self-hosted` trong
`build.yml`, dùng `runs-on: [self-hosted, stm32-local]` — `stm32-local` là
**label riêng** đặt cho máy này lúc đăng ký runner, đảm bảo job luôn chạy
đúng máy có toolchain/dongle, không bị đẩy sang máy self-hosted khác (nếu
sau này công ty có nhiều máy).

> Hiện tại job này đang dùng tạm `arm-none-eabi-gcc`/`cmake`/`ninja` (giống
> job cloud) để test luồng self-hosted trước. Khi chuyển sang GHS thật, xem
> hướng dẫn chi tiết ở mục 9.8 bên dưới.

### 9.2. Cài toolchain build độc lập trên máy runner

**Điều kiện trước tiên**: mở **PowerShell với quyền Administrator**
(chuột phải vào PowerShell → "Run as administrator") — thiếu quyền này,
lệnh sửa PATH cấp Machine ở bước dưới sẽ báo lỗi.

Cài 3 tool sau, **không phụ thuộc STM32CubeIDE**, để agent chạy nền dưới
quyền service vẫn tự gọi được: **CMake**, **Ninja**, **ARM GNU Toolchain**
(`arm-none-eabi-gcc`).

Copy nguyên khối lệnh dưới đây và chạy — nó tự tải, giải nén, dọn file `.zip`
tạm, cho cả 3 tool vào `C:\stm32-tools`:

```powershell
$root = "C:\stm32-tools"
New-Item -ItemType Directory -Force -Path $root | Out-Null

# 1) CMake 4.4.2
Invoke-WebRequest -Uri "https://github.com/Kitware/CMake/releases/download/v4.4.2/cmake-4.4.2-windows-x86_64.zip" -OutFile "$root\cmake.zip"
Expand-Archive -Path "$root\cmake.zip" -DestinationPath "$root\cmake" -Force
Remove-Item "$root\cmake.zip" -Force

# 2) Ninja 1.13.2
Invoke-WebRequest -Uri "https://github.com/ninja-build/ninja/releases/download/v1.13.2/ninja-win.zip" -OutFile "$root\ninja.zip"
Expand-Archive -Path "$root\ninja.zip" -DestinationPath "$root\ninja" -Force
Remove-Item "$root\ninja.zip" -Force

# 3) ARM GNU Toolchain 14.3.Rel1 (~280MB, có thể mất vài phút)
Invoke-WebRequest -Uri "https://armkeil.blob.core.windows.net/developer/Files/downloads/gnu/14.3.rel1/binrel/arm-gnu-toolchain-14.3.rel1-mingw-w64-i686-arm-none-eabi.zip" -OutFile "$root\arm-gcc.zip"
Expand-Archive -Path "$root\arm-gcc.zip" -DestinationPath "$root\arm-gcc" -Force
Remove-Item "$root\arm-gcc.zip" -Force

Write-Output "Xong. Kiểm tra 3 file .exe dưới đây có tồn tại:"
Get-ChildItem "$root\cmake" -Recurse -Filter "cmake.exe" | Select-Object -ExpandProperty FullName
Get-ChildItem "$root\ninja" -Filter "ninja.exe" | Select-Object -ExpandProperty FullName
Get-ChildItem "$root\arm-gcc" -Recurse -Filter "arm-none-eabi-gcc.exe" | Select-Object -ExpandProperty FullName
```

> Muốn bản mới hơn CMake/Ninja/ARM Toolchain? Trang tải chính thức:
> [cmake.org/download](https://cmake.org/download/),
> [github.com/ninja-build/ninja/releases](https://github.com/ninja-build/ninja/releases),
> [developer.arm.com/downloads/-/arm-gnu-toolchain-downloads](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads)
> — chỉ cần sửa lại số version/URL trong script trên.

**Bước tiếp theo — thêm cả 3 vào PATH cấp Machine** (không phải User) —
bắt buộc, vì Windows Service không chạy dưới tài khoản đăng nhập của bạn nên
**không thấy được User PATH**, chỉ thấy Machine PATH:

```powershell
$paths = @(
  "C:\stm32-tools\cmake\cmake-4.4.2-windows-x86_64\bin",
  "C:\stm32-tools\ninja",
  "C:\stm32-tools\arm-gcc\bin"
)
$machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$newPath = $machinePath.TrimEnd(';') + ';' + ($paths -join ';')
[Environment]::SetEnvironmentVariable("Path", $newPath, "Machine")

# Nạp lại PATH cho cửa sổ PowerShell hiện tại để test ngay, không cần mở lại
$env:Path += ";" + ($paths -join ';')

Write-Output "--- Kiểm tra ---"
cmake --version
ninja --version
arm-none-eabi-gcc --version
```

Nếu cả 3 lệnh cuối in ra version bình thường (không báo "not recognized") là
xong bước này.

### 9.3. Cài GitHub Actions Runner làm Windows Service

**Bước 1 — Lấy URL đăng ký + token (làm trên trình duyệt):**

1. Vào repo trên GitHub → **Settings → Actions → Runners**
2. Bấm **"New self-hosted runner"**
3. Chọn OS **Windows**, kiến trúc **x64**
4. Trang sẽ hiện sẵn 4 khối lệnh (Download / Extract / Configure / Run).
   Chỉ cần lấy **2 giá trị** từ khối "Configure": URL của repo và chuỗi
   token sau `--token` (dạng `AXXXXXXXXXXXXXXXXXXXXXXXXX`).
   ⚠️ Token này chỉ sống khoảng **1 giờ** kể từ lúc trang hiện ra — nếu để
   lâu quá phải bấm "New self-hosted runner" lại để lấy token mới.

**Bước 2 — Tải + giải nén runner (chạy trong PowerShell as Administrator):**

```powershell
$runnerDir = "C:\actions-runner"
New-Item -ItemType Directory -Force -Path $runnerDir | Out-Null

Invoke-WebRequest -Uri "https://github.com/actions/runner/releases/download/v2.336.0/actions-runner-win-x64-2.336.0.zip" -OutFile "$runnerDir\runner.zip"
Expand-Archive -Path "$runnerDir\runner.zip" -DestinationPath $runnerDir -Force
Remove-Item "$runnerDir\runner.zip" -Force
```
> Bản mới hơn: xem [github.com/actions/runner/releases](https://github.com/actions/runner/releases),
> sửa lại số version `2.336.0` và tên file trong URL trên cho khớp.

**Bước 3 — Đăng ký runner + cài làm Windows Service, chạy nền tự động:**

```powershell
Set-Location "C:\actions-runner"
./config.cmd --url "https://github.com/<owner>/<repo>" --token "<TOKEN_LẤY_Ở_BƯỚC_1>" `
  --name "stm32-local-runner" --labels "stm32-local" `
  --work "_work" --unattended --runasservice
```
Thay `<owner>/<repo>` và `<TOKEN_LẤY_Ở_BƯỚC_1>` bằng giá trị thật lấy ở
Bước 1. Cờ `--runasservice` giúp nó tự cài thành Windows Service luôn,
không cần giữ cửa sổ PowerShell mở, và tự khởi động lại cùng Windows.

Kết quả mong đợi ở cuối log: dòng
`Service actions.runner.<owner>-<repo>.<name> started successfully`.

**Bước 4 — Xác nhận runner đang hoạt động:**

```powershell
Get-Service "actions.runner.*" | Select-Object Name, Status, StartType
```
`Status` phải là `Running`, `StartType` là `Automatic`. Có thể xem log chi
tiết tại `C:\actions-runner\_diag\Runner_<timestamp>.log` — nếu chạy đúng sẽ
thấy dòng cuối `Listening for Jobs`.

Trên GitHub, vào lại **Settings → Actions → Runners** sẽ thấy runner của bạn
hiện chấm tròn **xanh (Idle)** thay vì xám.

### 9.4. Nếu gặp lỗi `UnauthorizedAccessException` khi service start

Hướng dẫn ở mục 9.2/9.3 đã cố tình dùng thư mục gốc ổ đĩa (`C:\stm32-tools`,
`C:\actions-runner`) thay vì nằm trong `C:\Users\<user>\...`, **để tránh
ngay từ đầu** lỗi dưới đây. Mục này chỉ cần đọc nếu bạn lỡ cài
`actions-runner` bên trong thư mục profile người dùng (ví dụ
`C:\Users\<user>\actions-runner`) và gặp lỗi khi service khởi động.

**Triệu chứng**: service ở trạng thái `Stopped` ngay sau khi cài/start, log
tại `actions-runner\_diag\Runner_*.log` báo:
```
System.UnauthorizedAccessException: Access to the path 'C:\Users\<user>' is denied.
```

**Nguyên nhân**: runner service mặc định chạy dưới tài khoản
`NT AUTHORITY\NETWORK SERVICE`. Tài khoản này **không có quyền list nội dung
thư mục profile người dùng** (`C:\Users\<user>`) dù `config.cmd` đã tự cấp
quyền cho *thư mục con* `actions-runner` — runner khi khởi động kiểm tra
quyền trên **toàn bộ đường dẫn cha**, nên vẫn fail ở `C:\Users\<user>`.
Thư mục gốc ổ đĩa (`C:\`) và `C:\actions-runner` không bị vấn đề này vì
`NETWORK SERVICE` vốn đã có quyền đọc mặc định ở đó.

**Cách fix** (nếu không muốn di chuyển lại thư mục) — cấp quyền List/Read
tối thiểu, không đệ quy, cho `NETWORK SERVICE` ngay trên thư mục profile:
```powershell
icacls "C:\Users\<user>" /grant "NT AUTHORITY\NETWORK SERVICE:(RX)"
Restart-Service -Name "actions.runner.<owner>-<repo>.<runner-name>"
```
Sau đó service sẽ chuyển sang `Running` và log hiện dòng
`Listening for Jobs` — runner đã sẵn sàng nhận job.

### 9.5. Nếu job self-hosted lỗi ngay bước đầu tiên có chạy lệnh, fail rất nhanh (~1-2 giây), không rõ lý do

**Triệu chứng** — nhận diện đúng lỗi này trước khi làm gì khác:

- Bước "Checkout repository" chạy xong bình thường (dấu tick xanh).
- Bước kế tiếp — bước **đầu tiên có chứa `run:`** (ví dụ "Verify local toolchain is on PATH") — báo đỏ (fail) chỉ sau khoảng 1-2 giây. Quá nhanh để là lỗi build/compile thật sự (build thật luôn mất ít nhất vài giây tới vài chục giây).
- Nếu bạn tự mở 1 cửa sổ PowerShell bình thường trên chính máy đó và gõ tay đúng những lệnh trong bước bị lỗi (ví dụ `cmake --version`), lệnh chạy **hoàn toàn bình thường**, không báo lỗi gì.
- Log của step lỗi trong GitHub Actions thường chỉ có 1 dòng ngắn gọn `Process completed with exit code 1.`, không có thông báo lỗi chi tiết nào khác.

Sự kết hợp "chạy tay OK nhưng CI vẫn fail, fail cực nhanh, log không rõ ràng" là dấu hiệu đặc trưng của lỗi này — nguyên nhân **không nằm ở toolchain** (`cmake`/`ninja`/`gcc`) mà nằm ở việc Windows đang chặn không cho chạy **bất kỳ file script `.ps1` nào**, ngay trước cả khi kịp gọi đến toolchain.

**Vì sao lại xảy ra — giải thích từ đầu cho người chưa biết PowerShell Execution Policy là gì:**

Mỗi khi workflow chạy tới 1 bước có `run: |` (một hoặc nhiều dòng lệnh PowerShell), GitHub Actions runner **không gõ lệnh trực tiếp vào cửa sổ console** như bạn tự làm — nó âm thầm làm 2 việc:

1. Ghi toàn bộ nội dung của `run:` đó ra **1 file tạm đuôi `.ps1`** (nằm trong `...\actions-runner\_work\_temp\`).
2. Gọi PowerShell để **chạy file `.ps1` đó** bằng kỹ thuật gọi là "dot-source": `. 'đường-dẫn-file.ps1'`.

Windows có sẵn 1 cơ chế bảo mật tên là **Execution Policy** (chính sách thực thi script), quyết định file `.ps1` có được phép chạy hay không (điều này KHÔNG áp dụng cho việc gõ lệnh trực tiếp vào console — đó là lý do tự gõ tay thì chạy được bình thường). Vài mức hay gặp:

| Execution Policy | Ý nghĩa |
|---|---|
| `Restricted` | Mức mặc định gốc của Windows. **Không cho chạy bất kỳ file `.ps1` nào**, kể cả file do chính máy tự tạo ra. |
| `RemoteSigned` | Cho chạy mọi file `.ps1` được tạo ra **trên chính máy đó** (không tải từ Internet về) mà không cần chữ ký số — đúng nhu cầu của máy chạy CI/CD tự sinh script. |

Windows lưu Execution Policy theo **4 phạm vi (scope)** tách biệt nhau, xem bằng lệnh:

```powershell
Get-ExecutionPolicy -List
```

Máy đang gặp lỗi này thường cho kết quả dạng:

```
        Scope ExecutionPolicy
        ----- ---------------
MachinePolicy       Undefined
   UserPolicy       Undefined
      Process          Bypass
  CurrentUser    RemoteSigned
 LocalMachine       Undefined
```

Điểm mấu chốt gây nhầm lẫn: dòng `CurrentUser` có thể đã là `RemoteSigned` (vì trước đây bạn từng tự đổi nó khi cài đặt máy dưới tài khoản của mình) — khiến bạn tưởng script đã được phép chạy. Nhưng dòng `LocalMachine` lại đang là `Undefined`, và khi `LocalMachine` là `Undefined`, Windows sẽ áp dụng mặc định gốc là `Restricted`.

Vấn đề nằm ở chỗ: Windows Service chạy runner (`actions.runner.*`, xem mục 9.3) **không chạy dưới tài khoản Windows mà bạn đang đăng nhập** — mặc định nó chạy dưới 1 tài khoản hệ thống riêng tên là `NT AUTHORITY\NETWORK SERVICE`. Tài khoản này có "hồ sơ" (registry hive) hoàn toàn tách biệt với tài khoản bạn dùng để mở PowerShell hằng ngày, nên **setting `CurrentUser: RemoteSigned` bạn từng đổi không có tác dụng gì với nó**. `NETWORK SERVICE` chỉ nhìn thấy scope `LocalMachine` (áp dụng chung cho toàn máy, mọi tài khoản) — và scope đó đang là `Restricted` → mọi file `.ps1` mà runner tạo ra để chạy từng bước `run:` đều bị chặn ngay từ dòng lệnh đầu tiên, trước cả khi kịp gọi tới `cmake`/`ninja`/`gcc`.

**Cách kiểm tra — xác nhận đúng là lỗi này trước khi sửa:**

1. Mở PowerShell (không cần quyền Administrator) ngay trên máy đang chạy runner.
2. Gõ:
   ```powershell
   Get-ExecutionPolicy -List
   ```
3. Nhìn đúng dòng `LocalMachine` — nếu giá trị là `Undefined` hoặc `Restricted`, gần như chắc chắn đây chính là nguyên nhân.

**Cách sửa:**

1. Mở **PowerShell với quyền Administrator** (chuột phải vào biểu tượng PowerShell → "Run as administrator").
2. Chạy đúng 1 lệnh sau:
   ```powershell
   Set-ExecutionPolicy -Scope LocalMachine -ExecutionPolicy RemoteSigned -Force
   ```
   - `-Scope LocalMachine`: bắt buộc phải dùng đúng scope này (không phải `CurrentUser`) — đây là scope áp dụng cho **toàn bộ máy**, mọi tài khoản, kể cả `NETWORK SERVICE`.
   - `RemoteSigned`: đủ an toàn (vẫn chặn script tải từ Internet về mà chưa có chữ ký số) trong khi cho phép chạy các script do chính máy tự sinh ra — đúng trường hợp GitHub Actions runner.
   - `-Force`: bỏ qua câu hỏi xác nhận "Are you sure you want to change the execution policy?".
3. Chạy lại `Get-ExecutionPolicy -List` để xác nhận cột `LocalMachine` giờ đã hiện `RemoteSigned`.

> **Không cần** khởi động lại (restart) service runner sau bước này. Execution Policy được Windows đọc lại **mỗi lần có 1 tiến trình PowerShell mới được tạo ra** (mỗi job/step CI đều là 1 tiến trình PowerShell mới) — khác với PATH và quyền group, vốn bị "đóng băng" theo vòng đời của service (xem mục 9.6 ngay dưới đây).

4. Trigger lại workflow (push 1 commit có chứa `[build]` trong message, hoặc vào tab Actions bấm "Run workflow") để xác nhận job self-hosted giờ đã chạy qua được bước đầu tiên.

### 9.6. Vừa đổi PATH cấp Machine / cấp thêm quyền cho NETWORK SERVICE xong nhưng job vẫn lỗi y hệt lỗi cũ

**Triệu chứng**: Bạn đã làm đúng các bước ở mục 9.2 (thêm PATH cấp Machine) hoặc vừa cấp thêm quyền NTFS (`icacls`) cho tài khoản/nhóm chạy runner, tự kiểm tra bằng `[Environment]::GetEnvironmentVariable(...)` hay `icacls` đều thấy thay đổi đã áp dụng đúng — nhưng chạy lại workflow thì job self-hosted **vẫn báo lỗi giống hệt như trước khi sửa** (ví dụ vẫn "not recognized"/không tìm thấy `cmake`, hoặc vẫn "Access is denied").

**Vì sao lại xảy ra — giải thích từ đầu cho người chưa biết "access token" của Windows là gì:**

Khi 1 Windows Service (như service chạy runner) khởi động, Windows tạo cho tiến trình đó 1 thứ gọi là **access token** — hiểu đơn giản như 1 "vé thông hành" được cấp đúng 1 lần tại thời điểm khởi động, trong đó ghi sẵn: tiến trình này chạy dưới tài khoản nào, tài khoản đó thuộc những nhóm (group) quyền nào, và **giá trị PATH cấp Machine tại đúng thời điểm đó**. Vé này được giữ nguyên suốt vòng đời của tiến trình — Windows **không tự động cấp lại vé mới** dù sau đó bạn có đổi PATH hay thêm tài khoản vào nhóm quyền khác.

Nói cách khác: nếu bạn đổi PATH hoặc quyền **sau khi** service đã khởi động, service đó (dù `Status` vẫn hiện `Running` bình thường, trông như không có gì bất thường) **vẫn đang dùng PATH/quyền phiên bản cũ** — thay đổi mới chỉ thật sự có hiệu lực từ **lần khởi động tiếp theo** của service.

**Cách kiểm tra** — xem service đã chạy từ lúc nào, so với lúc bạn thực hiện thay đổi:

```powershell
$svc = Get-CimInstance Win32_Service -Filter "Name LIKE 'actions.runner%'"
(Get-Process -Id $svc.ProcessId).StartTime
```

Nếu thời điểm in ra **sớm hơn** thời điểm bạn chạy lệnh đổi PATH (mục 9.2) hoặc lệnh `icacls` cấp quyền, thì đúng là cần restart lại service.

**Cách sửa** — restart lại chính service runner để nó khởi động lại và được cấp vé thông hành mới:

```powershell
# Xem đúng tên service (cột Name) trước
Get-Service "actions.runner.*" | Select-Object Name

# Restart, thay đúng tên lấy được ở lệnh trên
Restart-Service -Name "actions.runner.<owner>-<repo>.<runner-name>" -Confirm:$false
```

Kiểm tra lại service đã `Running`:
```powershell
Get-Service "actions.runner.*" | Select-Object Name, Status, StartType
```

> **Lưu ý**: đây chính là lý do thứ tự các bước ở mục 9.2 → 9.3 trong tài liệu này luôn khuyến nghị **cài đặt/cấp quyền toolchain xong trước, rồi mới cài & khởi động runner service** — tránh hẳn việc phải nhớ restart lại sau này. Nếu về sau bạn cần đổi PATH hoặc cấp thêm quyền trong lúc runner đã chạy sẵn từ trước (ví dụ khi chuyển sang cài GHS ở mục 9.8), hãy luôn nhớ restart service ngay sau đó bằng lệnh trên.

### 9.7. Lưu ý bảo mật

- Self-hosted runner chạy **bất kỳ code nào** trong workflow của repo — chỉ
  dùng cho repo **private/nội bộ**, tránh dùng cho repo public có PR từ
  người ngoài.
- Bật **Settings → Actions → General → "Require approval for all outside
  collaborators"** nếu repo có cộng tác viên bên ngoài.
- Máy chạy runner cần **luôn bật** để nhận job (service tự khởi động lại
  cùng Windows nhờ `StartType: Automatic`).

### 9.8. Chuyển sang dùng trình biên dịch GHS (Green Hills Software) qua license USB dongle

Mục 9.1–9.5 ở trên đã dựng xong hạ tầng self-hosted runner (máy có thể tự
chạy job ngay tại chỗ, truy cập được phần cứng cắm trực tiếp vào máy —
bao gồm USB dongle license). Phần này hướng dẫn thay trình biên dịch đang
dùng tạm (ARM GCC) bằng GHS thật.

**9.8.1. Vì sao chỉ self-hosted runner mới dùng được GHS dongle**

License GHS dạng USB dongle (thường dùng driver Sentinel/SafeNet HASP) chỉ
được phần mềm GHS "nhìn thấy" khi đồng thời thỏa 2 điều kiện:

- Dongle cắm vật lý vào đúng máy đang chạy trình biên dịch, và
- Driver dongle đã được cài trên máy đó.

Máy ảo cloud (`ubuntu-latest`) không thể đáp ứng cả 2 điều kiện này —
đây chính là lý do bắt buộc phải build qua job self-hosted (`build-self-hosted`,
label `stm32-local`) đã dựng ở mục 9, thay vì job cloud.

**9.8.2. Chuẩn bị GHS trên máy runner**

1. Cài phần mềm GHS (MULTI IDE + gói compiler cho kiến trúc ARM) — bộ cài
   thường tải qua tài khoản MyGHS của công ty, không có sẵn public.
2. Cài driver dongle đi kèm (Sentinel HASP hoặc tương đương) — thường được
   cài tự động cùng bộ cài GHS, hoặc cần cài riêng tùy loại dongle.
3. Cắm dongle vào đúng cổng USB của **máy đang chạy Windows Service
   `actions.runner.*`** (chính là máy đã cài ở mục 9.3) — không phải máy khác.
4. Kiểm tra license đã nhận được chưa, ví dụ chạy lệnh compiler kèm cờ version:
   ```powershell
   ccarm -version
   ```
   (`ccarm.exe` là ví dụ tên compiler C cho ARM của GHS — tên file thật tùy
   phiên bản/gói cài đã mua, thường nằm trong `C:\ghs\compXXXX\`, xem đúng
   tên trong thư mục cài GHS trên máy.) Nếu lệnh in ra số version + thông tin
   license (thay vì lỗi kiểu "no license found" / "dongle not found") tức là
   driver + dongle đã hoạt động đúng.

**9.8.3. Thêm GHS vào PATH cấp Machine**

Giống nguyên tắc ở mục 9.2 (bắt buộc PATH cấp **Machine**, vì Windows Service
chạy dưới `NETWORK SERVICE` không thấy được User PATH của tài khoản đăng nhập):

```powershell
$ghsBin = "C:\ghs\compXXXX"   # thay bằng đường dẫn cài GHS thật trên máy
$machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
[Environment]::SetEnvironmentVariable("Path", $machinePath.TrimEnd(';') + ';' + $ghsBin, "Machine")
$env:Path += ";$ghsBin"
ccarm -version
```

**9.8.4. Đổi bước build trong `build.yml`**

Job `build-self-hosted` hiện đang gọi CMake + `arm-none-eabi-gcc` (bản test
tạm, xem ghi chú ở mục 9.1). Có 2 hướng để chuyển sang GHS thật, tùy cách
project mô tả build:

- **Vẫn giữ CMake**: tạo thêm 1 toolchain file CMake riêng cho GHS (ví dụ
  `cmake/ghs-arm.cmake`, khai báo `CMAKE_C_COMPILER`/`CMAKE_CXX_COMPILER` trỏ
  tới `ccarm.exe`/`cxarm.exe` của GHS), rồi sửa bước Configure trong job
  self-hosted:
  ```yaml
  - name: Configure (GHS, ${{ matrix.preset }})
    run: cmake --preset ${{ matrix.preset }} -DCMAKE_TOOLCHAIN_FILE=cmake/ghs-arm.cmake
  ```
- **Dùng thẳng project GHS MULTI gốc** (file `.gpj`): bỏ hẳn bước CMake,
  gọi trực tiếp `gbuild` — công cụ build dòng lệnh của GHS, không cần mở IDE:
  ```yaml
  - name: Build with GHS MULTI
    run: gbuild -top path\to\project.gpj
  ```

Chọn phương án nào phụ thuộc việc project có chuyển hẳn cấu hình build sang
định dạng GHS (`.gpj`) hay vẫn giữ CMake và chỉ đổi compiler bên dưới —
nên thống nhất với team trước khi sửa `build.yml`.

**9.8.5. Lưu ý số lượng license (seat) khi build song song**

Job hiện dùng `matrix: preset: [Debug, Release]`, tức **build Debug và
Release song song cùng lúc trên cùng 1 máy**. License GHS dạng dongle
thường giới hạn số session compile đồng thời (tùy loại đã mua). Nếu dongle
chỉ cho phép **1 session tại 1 thời điểm**, bản Release sẽ báo lỗi kiểu
"license unavailable" ngay khi Debug đang chạy. Cách xử lý: kiểm tra với
bộ phận cấp phép GHS xem license cho phép bao nhiêu session song song; nếu
chỉ 1, thêm `max-parallel: 1` vào `strategy` để 2 preset chạy **tuần tự**
thay vì song song:

```yaml
strategy:
  fail-fast: false
  max-parallel: 1
  matrix:
    preset: [Debug, Release]
```

**9.8.6. Rủi ro cần lưu ý**

- Nếu dongle bị rút ra, hoặc máy runner khởi động lại và driver không tự
  nhận lại dongle, mọi job GHS sẽ fail đồng loạt cho tới khi cắm lại/khởi
  động lại driver — nên coi máy runner này là điểm phụ thuộc duy nhất
  (single point of failure) cho việc build bằng GHS.
- Không thể chạy build GHS song song trên máy runner thứ 2 trừ khi mua thêm
  dongle/license riêng — khác với ARM GCC (miễn phí, không giới hạn số máy).

## 10. Đem setup này sang 1 repo khác

Muốn dựng lại đúng pipeline này (cloud build + self-hosted runner) cho 1 repo
khác, cần phân biệt rõ 2 nhóm: **file có thể copy sang** và **phần phải làm
lại thủ công trên máy** (không nằm trong file nào cả).

### 10.1. File cần copy sang repo mới

| File | Copy nguyên hay phải sửa? |
|---|---|
| `.github/workflows/build.yml` | **Phải sửa** — dùng làm template, không copy y nguyên được |
| `doc/GithubActions/GithubActions_Setup.md` (chính file này) | Copy làm tài liệu tham khảo, sửa lại vài chỗ có tên project/file cụ thể (STM32F4, `.elf`...) |
| `.github/copilot-instructions.md` | Copy được luôn nếu repo mới cũng là project nhúng — chỉ cần điền lại phần "Project context" ở đầu file cho đúng MCU/board mới |

**Không cần đem theo**: `.claude/settings.local.json` — đây chỉ là quyền tool
cục bộ của Claude Code cho thư mục làm việc hiện tại, không liên quan gì tới
CI/CD của repo, đừng copy sang.

### 10.2. Trong `build.yml` cần sửa những gì

Nếu repo mới **cũng là project CMake + ARM GCC** (giống STM32F4 này): chỉ
cần đổi:

- `matrix: preset: [Debug, Release]` → đúng tên preset trong `CMakePresets.json`
  của repo mới.
- Đường dẫn artifact (`build/${{ matrix.preset }}/*.elf`...) → đúng cấu trúc
  thư mục build của repo mới.
- `runs-on: [self-hosted, stm32-local]` → đổi label nếu máy/label runner khác.

Nếu repo mới **khác hệ** (không phải CMake/ARM GCC): chỉ giữ lại phần khung
(`on:`, điều kiện `if:` dùng tag `[build]`, `matrix`, job self-hosted có
`shell: powershell`), còn các step Configure/Build/Generate `.hex` phải viết
lại hoàn toàn theo đúng toolchain thật của project đó.

### 10.3. Phần KHÔNG nằm trong file, phải làm lại thủ công trên máy

- **Runner self-hosted**: 1 runner = đăng ký cho **đúng 1 repo** (hoặc 1 org).
  Muốn repo mới cũng build local được, phải chạy lại `config.cmd` **với
  token mới** lấy từ chính repo mới (Settings → Actions → Runners → New
  self-hosted runner) — không dùng chung token/registration của repo cũ.
  Có thể cài thêm 1 instance runner riêng (thư mục khác, ví dụ
  `C:\actions-runner-<repo-moi>`) trên **cùng máy** nếu muốn cả 2 repo cùng
  build local song song, không xung đột nhau.
- **Toolchain (`cmake`/`ninja`/`arm-none-eabi-gcc`) + Execution Policy
  `RemoteSigned`** (xem mục 9.2 và 9.5): nếu setup trên **cùng máy này**,
  không cần làm lại — các setting này ở cấp **Machine**, dùng chung được cho
  mọi repo/runner cài trên máy. Nếu là **máy khác**, phải làm lại toàn bộ
  mục 9.2–9.3, và có khả năng gặp lại đúng 2 lỗi đã ghi ở mục 9.5–9.6.

## 11. Setup self-hosted runner trên Linux (thay vì Windows)

Toàn bộ mục 9 ở trên viết cho máy runner chạy **Windows** (PowerShell,
Windows Service, `icacls`...). Nếu máy có USB dongle (hoặc máy build local)
lại là **Linux** (Ubuntu/Debian...), cách làm tương tự nhưng công cụ hệ điều
hành khác hẳn. Mục này liệt kê đúng những điểm khác biệt, viết cho người
chưa quen Linux service cũng làm theo được.

### 11.1. Khác biệt cốt lõi so với Windows — vì sao không gặp lại y hệt các lỗi ở mục 9.5/9.6

| Chủ đề | Windows | Linux |
|---|---|---|
| Shell chạy từng bước `run:` | PowerShell (`.ps1`, cần khai báo `shell: powershell`) | **Bash** theo mặc định, không cần khai báo `shell:` |
| Chặn chạy script kiểu "Execution Policy" (mục 9.5) | Có — `Restricted` chặn mọi `.ps1` | **Không có khái niệm tương đương** — Bash không có execution-policy. Runner tự `chmod +x` file `.sh` tạm nó tạo ra trước khi chạy, nên bước này thường không gặp lỗi tương tự |
| PATH tách theo scope (Machine/User) (mục 9.2) | Có, phải sửa PATH cấp Machine | Không tách — nhưng service `systemd` **không đọc `~/.bashrc`/`~/.profile`** của user, nên vẫn phải khai báo PATH ở nơi service thấy được (xem mục 11.2) |
| Cache PATH/quyền vào access token lúc service khởi động (mục 9.6) | Có | **Vẫn có** — `systemd` cũng chỉ nạp môi trường 1 lần lúc service start; đổi `PATH`/quyền xong vẫn phải `systemctl restart` lại service runner, y hệt tinh thần mục 9.6 |

Tóm lại: Linux **tránh được** hẳn 1 lớp lỗi (Execution Policy), nhưng **vẫn có** lớp lỗi còn lại (service cache môi trường lúc start) — đừng chủ quan bỏ qua bước restart service sau khi đổi PATH/quyền.

### 11.2. Cài toolchain build trên máy Linux

Cách nhanh nhất — dùng trình quản lý gói có sẵn (ví dụ Ubuntu/Debian):

```bash
sudo apt update
sudo apt install -y cmake ninja-build gcc-arm-none-eabi
```

Kiểm tra:
```bash
cmake --version
ninja --version
arm-none-eabi-gcc --version
```

> Bản `gcc-arm-none-eabi` trong kho `apt` mặc định của Ubuntu thường là bản
> khá cũ. Nếu cần đúng phiên bản mới (ví dụ để khớp bản đang dùng trên
> Windows ở mục 9.2), tải thẳng gói `.tar.xz` từ
> [developer.arm.com/downloads/-/arm-gnu-toolchain-downloads](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads),
> giải nén vào `/opt/arm-gnu-toolchain`, rồi thêm `bin` của nó vào PATH như
> hướng dẫn ngay dưới đây.

**Thêm vào PATH cho toàn hệ thống** (tương đương PATH cấp Machine trên
Windows) — tạo 1 file trong `/etc/profile.d/`, áp dụng cho mọi user kể cả
user chạy service runner:

```bash
echo 'export PATH="$PATH:/opt/arm-gnu-toolchain/bin"' | sudo tee /etc/profile.d/arm-toolchain.sh
sudo chmod +x /etc/profile.d/arm-toolchain.sh
```

> Nếu cài bằng `apt` như trên, `cmake`/`ninja`/`arm-none-eabi-gcc` đã tự nằm
> ở `/usr/bin` (vốn đã có sẵn trong PATH mặc định của mọi user/service) —
> bước thêm PATH thủ công này chỉ cần khi tự giải nén toolchain vào 1 thư
> mục tùy ý như `/opt/...`.

### 11.3. Cài GitHub Actions Runner làm `systemd` service trên Linux

**Bước 1 — Lấy URL đăng ký + token**: làm y hệt mục 9.3 Bước 1 (vào
**Settings → Actions → Runners → New self-hosted runner**, chọn OS **Linux**
thay vì Windows, lấy token sau `--token`).

**Bước 2 — Tải, giải nén, đăng ký runner:**

```bash
mkdir -p ~/actions-runner && cd ~/actions-runner

curl -o actions-runner-linux-x64.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.336.0/actions-runner-linux-x64-2.336.0.tar.gz
tar xzf actions-runner-linux-x64.tar.gz

./config.sh --url "https://github.com/<owner>/<repo>" --token "<TOKEN_LẤY_Ở_BƯỚC_1>" \
  --name "stm32-linux-runner" --labels "stm32-local-linux" --work "_work" --unattended
```
> Bản mới hơn: xem [github.com/actions/runner/releases](https://github.com/actions/runner/releases)
> và sửa lại số version + tên file cho khớp, giống ghi chú ở mục 9.3.

**Bước 3 — Cài làm service để chạy nền, tự khởi động lại cùng máy:**

```bash
sudo ./svc.sh install
sudo ./svc.sh start
```

**Bước 4 — Xác nhận runner đang hoạt động:**

```bash
sudo ./svc.sh status
```
Phải thấy dòng dạng `active (running)`. Trên GitHub, vào lại
**Settings → Actions → Runners** sẽ thấy runner hiện chấm tròn **xanh (Idle)**.

### 11.4. Thêm job self-hosted cho Linux vào `build.yml`

Vì job `build-self-hosted` hiện tại khai báo cứng `shell: powershell` và
dùng cú pháp PowerShell (`Get-ChildItem`, `-replace`...) trong các step —
**không chạy được trên Linux runner**. Cần thêm 1 job **riêng** cho Linux,
dùng label khác (`stm32-local-linux` ở ví dụ Bước 2 trên) để job cũ (Windows)
và job mới (Linux) không bị gán nhầm máy:

```yaml
build-self-hosted-linux:
  name: Build on local Linux runner (${{ matrix.preset }})
  runs-on: [self-hosted, stm32-local-linux]
  if: >
    github.event_name == 'pull_request' ||
    github.event_name == 'workflow_dispatch' ||
    (github.event_name == 'push' && contains(github.event.head_commit.message, '[build]'))
  strategy:
    fail-fast: false
    matrix:
      preset: [Debug, Release]

  steps:
    - name: Checkout repository
      uses: actions/checkout@v4

    - name: Verify local toolchain is on PATH
      run: |
        cmake --version
        ninja --version
        arm-none-eabi-gcc --version

    - name: Configure (${{ matrix.preset }})
      run: cmake --preset ${{ matrix.preset }}

    - name: Build (${{ matrix.preset }})
      run: cmake --build --preset ${{ matrix.preset }}

    - name: Generate .hex / .bin
      working-directory: build/${{ matrix.preset }}
      run: |
        ELF=$(find . -maxdepth 1 -name '*.elf' | head -n1)
        arm-none-eabi-objcopy -O ihex "$ELF" "${ELF%.elf}.hex"
        arm-none-eabi-objcopy -O binary "$ELF" "${ELF%.elf}.bin"

    - name: Print firmware size
      working-directory: build/${{ matrix.preset }}
      run: |
        ELF=$(find . -maxdepth 1 -name '*.elf' | head -n1)
        arm-none-eabi-size "$ELF"

    - name: Upload build artifacts
      uses: actions/upload-artifact@v4
      with:
        name: stm32f4-${{ matrix.preset }}-local-linux
        path: |
          build/${{ matrix.preset }}/*.elf
          build/${{ matrix.preset }}/*.hex
          build/${{ matrix.preset }}/*.bin
          build/${{ matrix.preset }}/*.map
        if-no-files-found: error
        retention-days: 14
```

Điểm khác so với bản Windows: không cần khối `defaults: run: shell:`
(Bash là mặc định), và bước "Generate .hex / .bin"/"Print firmware size"
dùng lại đúng cú pháp Bash (`find`, `${ELF%.elf}`) giống hệt job `build`
chạy trên cloud ở mục 4.5 — vì cloud runner (`ubuntu-latest`) vốn cũng là
Linux.

### 11.5. Lỗi thường gặp riêng trên Linux

| Hiện tượng | Nguyên nhân | Cách xử lý |
|---|---|---|
| Job fail ở step đầu tiên với `Permission denied` khi chạy file script tạm | Thư mục chứa `_work/_temp` (hoặc `/tmp`) được mount với tùy chọn `noexec` (chặn thực thi file trong phân vùng đó) — khá phổ biến trên máy được hardening bảo mật | Kiểm tra bằng `mount \| grep $(df --output=target ~/actions-runner/_work \| tail -1)`, nếu thấy `noexec` trong danh sách option, đổi runner sang thư mục nằm trên phân vùng không có `noexec` (thường là `/home` hoặc `/opt`) |
| Đổi PATH/quyền xong (mục 11.2) mà job vẫn không thấy `cmake`/`gcc` | Giống hệt tinh thần mục 9.6 — `systemd` chỉ nạp môi trường 1 lần lúc service start | `sudo systemctl restart actions.runner.<owner>-<repo>.<name>.service` |
| `./svc.sh install` báo lỗi thiếu quyền | Cần chạy bằng `sudo` vì thao tác tạo `systemd` service yêu cầu quyền root | Thêm `sudo` trước `./svc.sh install` và `./svc.sh start` |
| Runner hiện `Offline` trên GitHub dù service `active (running)` | Máy không ra được Internet (firewall/proxy chặn outbound tới `github.com`/`*.actions.githubusercontent.com`) | Kiểm tra bằng `curl -I https://github.com`, mở firewall outbound nếu bị chặn — runner chỉ cần kết nối **ra ngoài**, không cần mở port inbound |

### 11.6. Bảo mật (bổ sung riêng cho Linux)

Áp dụng toàn bộ lưu ý ở mục 9.7, cộng thêm:

- Không cài/chạy runner dưới user `root`. Tạo 1 user riêng (ví dụ `ghrunner`)
  chỉ có đúng quyền cần thiết để cài + chạy runner, tránh trường hợp code
  trong workflow (chạy dưới quyền user này) vô tình/cố ý phá hỏng hệ thống.
- Nếu dùng GHS dongle trên Linux, driver dongle (Sentinel HASP bản Linux)
  thường yêu cầu cấu hình thêm `udev rule` để user không phải `root` truy
  cập được thiết bị USB — tương tự khái niệm ACL trên Windows ở mục 9.8.2,
  nhưng cơ chế cấp quyền trên Linux là qua group (`plugdev` hoặc group
  riêng) + `udev`, không phải `icacls`.
