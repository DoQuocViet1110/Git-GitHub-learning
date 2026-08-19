# GitHub Actions CI — Setup Self-hosted Runner build bằng `build.bat`

| | |
|---|---|
| Document Title | GitHub Actions CI Setup for STM32F4 firmware build (self-hosted runner) |
| File workflow  | `.github/workflows/build.yml` (job `build-self-hosted`) |
| File build script | `build.bat` (gốc repo) |
| Mục đích       | Build firmware (Debug + Release) **ngay trên máy local** mỗi khi push (có tag `[build]`), tạo/cập nhật Pull Request, hoặc comment `[build]` trên PR |
| Đối tượng đọc  | Người **chưa từng dùng GitHub Actions**, cần tự làm lại được toàn bộ setup từ đầu, chỉ cần đọc và làm theo thứ tự từ trên xuống dưới |
| Phạm vi tài liệu | Tài liệu này tập trung **duy nhất** vào workflow mới: job self-hosted build bằng `build.bat`. Job build trên cloud (`ubuntu-latest`) và các hướng mở rộng khác (GHS dongle, Linux runner) được gom vào phần **Phụ lục** ở cuối, không bắt buộc đọc để hoàn thành setup chính. |

---

## 1. Tổng quan — luồng hoạt động sau khi setup xong

```
Bạn push code / mở PR / comment "[build]" trên PR
        │
        ▼
GitHub ghi nhận sự kiện, kiểm tra điều kiện trigger (mục 4)
        │  (nếu khớp điều kiện)
        ▼
Agent runner (cài sẵn, chạy nền trên máy local) tự nhận job
        │
        ▼
Runner tự "git checkout" đúng commit/branch cần build
        │
        ▼
Runner chạy "build.bat <Debug|Release>"
        │
        ▼
build.bat: cmake configure → cmake build → objcopy ra .hex/.bin → in size
        │
        ▼
Runner nén .elf/.hex/.bin/.map thành Artifact, upload lên GitHub
        │
        ▼
Bạn vào tab Actions trên GitHub, tải Artifact về
```

Khái niệm nền tảng (Workflow, Trigger, Job, Runner, Step, Artifact...) nếu
chưa quen, xem giải thích ngắn gọn ở **Phụ lục E**. Tài liệu chính bên dưới
giả định bạn đã biết sơ các khái niệm này và muốn bắt tay setup ngay.

## 2. Trước khi bắt đầu — chuẩn bị đủ quyền

Setup này cần quyền trên **2 hệ thống khác nhau**: GitHub (repo) và máy
Windows (nơi cài runner). Thiếu 1 trong các quyền dưới đây, bạn sẽ bị chặn
giữa chừng ở đúng bước cần quyền đó.

| # | Cần quyền gì | Dùng ở bước nào |
|---|---|---|
| 1 | Quyền **Admin** trên repo GitHub (hoặc Owner nếu repo thuộc Organization) | Bước 1 (bật Actions), Bước 3 (đăng ký runner) |
| 2 | Quyền **Local Administrator** trên máy Windows sẽ chạy runner | Bước 2 (cài toolchain, sửa PATH cấp Machine), Bước 3 (cài runner làm Windows Service), Bước 4 (đổi PowerShell Execution Policy) |
| 3 | Máy có thể ra Internet (tải toolchain + runner + kết nối tới GitHub) | Bước 2, Bước 3 |

> Nếu bạn đang setup trên **máy của khách hàng / repo private của khách
> hàng** (không phải máy/repo của chính bạn), 2 quyền trên thường phải xin
> khách hàng cấp trước — xem danh sách đầy đủ, chi tiết hơn (bao gồm cả các
> trường hợp có thể phát sinh do chính sách bảo mật nội bộ của khách hàng)
> ở **mục 8**.

## 3. Bước 1 — Bật GitHub Actions cho repo

Làm trên trình duyệt, cần tài khoản có quyền **Admin** trên repo.

1. Vào repo trên GitHub → bấm tab **Settings** (nằm ngang hàng Code, Issues,
   Pull requests — nếu không thấy tab này, tài khoản của bạn chưa có quyền
   Admin trên repo, cần xin cấp trước khi làm tiếp).
2. Trong menu bên trái, chọn **Actions → General**.
3. Mục **Actions permissions**: chọn **"Allow all actions and reusable
   workflows"**.
   > Nếu để "Disable actions", workflow sẽ không bao giờ chạy. Nếu chọn chế
   > độ chỉ cho phép "verified creators", 1 số action bên thứ ba (ví dụ dùng
   > trong job build trên cloud, xem Phụ lục A) có thể bị chặn.
4. Mục **Workflow permissions**: để mặc định **"Read repository contents
   permission"** — đủ dùng, vì workflow chỉ build và upload artifact, không
   cần ghi ngược lại repo.
5. Bấm **Save** nếu có thay đổi.

## 4. Bước 2 — Cài toolchain build trên máy local

Làm **trên chính máy Windows** sẽ chạy runner (không phải máy bạn đang gõ
lệnh từ xa qua RDP thì vẫn được, miễn RDP đúng vào máy đó).

**Mở PowerShell với quyền Administrator**: chuột phải vào biểu tượng
PowerShell → **"Run as administrator"**. Bắt buộc — thiếu quyền này, lệnh
sửa PATH cấp Machine ở dưới sẽ báo lỗi.

Copy nguyên khối lệnh dưới đây, dán vào PowerShell (Administrator) và Enter.
Lệnh này tự tải, giải nén, dọn file `.zip` tạm, cài cả 3 tool **CMake**,
**Ninja**, **ARM GNU Toolchain** vào `C:\stm32-tools`:

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

Write-Output "Xong. Kiem tra 3 file .exe duoi day co ton tai:"
Get-ChildItem "$root\cmake" -Recurse -Filter "cmake.exe" | Select-Object -ExpandProperty FullName
Get-ChildItem "$root\ninja" -Filter "ninja.exe" | Select-Object -ExpandProperty FullName
Get-ChildItem "$root\arm-gcc" -Recurse -Filter "arm-none-eabi-gcc.exe" | Select-Object -ExpandProperty FullName
```

Kết quả mong đợi: 3 dòng đường dẫn `.exe` in ra ở cuối, không có dòng lỗi đỏ.

> Muốn bản mới hơn? Trang tải chính thức:
> [cmake.org/download](https://cmake.org/download/),
> [github.com/ninja-build/ninja/releases](https://github.com/ninja-build/ninja/releases),
> [developer.arm.com/downloads/-/arm-gnu-toolchain-downloads](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads)
> — chỉ cần sửa lại số version/URL trong script trên.

**Thêm cả 3 tool vào PATH cấp Machine** (không phải User) — bắt buộc, vì
Windows Service (chạy runner ở Bước 3) không thấy được User PATH của tài
khoản đang đăng nhập, chỉ thấy Machine PATH. Vẫn trong cửa sổ PowerShell
(Administrator) đó, chạy tiếp:

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

Write-Output "--- Kiem tra ---"
cmake --version
ninja --version
arm-none-eabi-gcc --version
```

Nếu cả 3 lệnh cuối in ra version bình thường (không báo "not recognized") —
xong Bước 2. Nếu tên thư mục cmake giải nén ra khác `cmake-4.4.2-windows-x86_64`
(ví dụ do bạn tải bản version khác), sửa lại đúng tên thư mục thật trong biến
`$paths` ở trên trước khi chạy.

## 5. Bước 3 — Cho phép chạy PowerShell script (Execution Policy)

**Làm ngay từ bây giờ**, trước khi cài runner ở Bước 4 — nếu bỏ qua bước
này, job build đầu tiên trên GitHub sẽ fail rất nhanh (~1-2 giây) với lỗi
khó hiểu dù toolchain đã cài đúng (xem giải thích đầy đủ ở mục 10.1 nếu tò
mò tại sao).

Vẫn trong PowerShell (Administrator), chạy đúng 1 lệnh:

```powershell
Set-ExecutionPolicy -Scope LocalMachine -ExecutionPolicy RemoteSigned -Force
```

Kiểm tra lại:

```powershell
Get-ExecutionPolicy -List
```

Dòng `LocalMachine` phải hiện `RemoteSigned`.

## 6. Bước 4 — Cài GitHub Actions Runner làm Windows Service

### 6.1. Lấy URL đăng ký + token (làm trên trình duyệt)

1. Vào repo trên GitHub → **Settings → Actions → Runners**.
2. Bấm **"New self-hosted runner"**.
3. Chọn OS **Windows**, kiến trúc **x64**.
4. Trang sẽ hiện sẵn 4 khối lệnh (Download / Extract / Configure / Run).
   Chỉ cần lấy **2 giá trị** từ khối "Configure": URL của repo và chuỗi
   token sau `--token` (dạng `AXXXXXXXXXXXXXXXXXXXXXXXXX`).
   ⚠️ Token này chỉ sống khoảng **1 giờ** kể từ lúc trang hiện ra — nếu để
   lâu quá phải bấm "New self-hosted runner" lại để lấy token mới.

### 6.2. Tải + giải nén runner

Trong PowerShell **as Administrator** (có thể dùng lại cửa sổ ở Bước 2):

```powershell
$runnerDir = "C:\actions-runner"
New-Item -ItemType Directory -Force -Path $runnerDir | Out-Null

Invoke-WebRequest -Uri "https://github.com/actions/runner/releases/download/v2.336.0/actions-runner-win-x64-2.336.0.zip" -OutFile "$runnerDir\runner.zip"
Expand-Archive -Path "$runnerDir\runner.zip" -DestinationPath $runnerDir -Force
Remove-Item "$runnerDir\runner.zip" -Force
```
> Bản mới hơn: xem [github.com/actions/runner/releases](https://github.com/actions/runner/releases),
> sửa lại số version `2.336.0` và tên file trong URL trên cho khớp.

> Dùng đúng thư mục gốc ổ đĩa (`C:\actions-runner`), **không** đặt trong
> `C:\Users\<user>\...` — tránh lỗi `UnauthorizedAccessException` khi
> service khởi động, giải thích ở mục 10.3.

### 6.3. Đăng ký runner + cài làm Windows Service

```powershell
Set-Location "C:\actions-runner"
./config.cmd --url "https://github.com/<owner>/<repo>" --token "<TOKEN_LẤY_Ở_6.1>" `
  --name "stm32-local-runner" --labels "stm32-local" `
  --work "_work" --unattended --runasservice
```
Thay `<owner>/<repo>` và `<TOKEN_LẤY_Ở_6.1>` bằng giá trị thật. Cờ
`--runasservice` giúp nó tự cài thành Windows Service luôn, không cần giữ
cửa sổ PowerShell mở, và tự khởi động lại cùng Windows.

Kết quả mong đợi ở cuối log: dòng
`Service actions.runner.<owner>-<repo>.<name> started successfully`.

> Nhãn `--labels "stm32-local"` phải khớp đúng với `runs-on: [self-hosted,
> stm32-local]` khai báo trong `build.yml` (xem mục 8) — nếu đặt tên label
> khác, job sẽ mãi ở trạng thái "Waiting for a runner" vì không máy nào nhận.

### 6.4. Xác nhận runner đang hoạt động

```powershell
Get-Service "actions.runner.*" | Select-Object Name, Status, StartType
```
`Status` phải là `Running`, `StartType` là `Automatic`. Log chi tiết tại
`C:\actions-runner\_diag\Runner_<timestamp>.log` — nếu chạy đúng sẽ thấy
dòng cuối `Listening for Jobs`.

Trên GitHub, vào lại **Settings → Actions → Runners** sẽ thấy runner của
bạn hiện chấm tròn **xanh (Idle)** thay vì xám.

**Bước 4 hoàn tất — setup đã xong, xem mục 7-8 để hiểu workflow đang chạy gì
và cách test thử.**

## 7. Hiểu workflow mới: job `build-self-hosted` trong `build.yml`

File này **đã có sẵn** trong repo (`.github/workflows/build.yml`), không
cần tạo lại — mục này chỉ giải thích để bạn hiểu nó đang làm gì.

### 7.1. Khi nào job này chạy (trigger)

```yaml
if: >
  github.event_name == 'pull_request' ||
  github.event_name == 'workflow_dispatch' ||
  (github.event_name == 'push' && contains(github.event.head_commit.message, '[build]')) ||
  (github.event_name == 'issue_comment' && github.event.issue.pull_request != null &&
  contains(github.event.comment.body, '[build]') &&
  contains(fromJSON('["OWNER","MEMBER","COLLABORATOR"]'), github.event.comment.author_association))
```

| Trường hợp | Có build không? |
|---|---|
| Mở/update Pull Request vào `main` hoặc `develop` | ✅ Luôn build |
| Bấm nút **"Run workflow"** trên tab Actions (chạy tay) | ✅ Luôn build |
| Push commit **có chứa `[build]`** trong commit message | ✅ Build |
| Push commit **không có `[build]`** | ❌ Skip, không tốn build |
| Comment trên PR **có chứa `[build]`**, người comment là Owner/Member/Collaborator của repo | ✅ Build, dùng đúng code mới nhất của PR đó |
| Comment trên PR có `[build]` nhưng người comment **không** phải Owner/Member/Collaborator | ❌ Skip — chặn có chủ đích, xem lý do bảo mật ở mục 8 |
| Comment trên 1 Issue thường (không phải PR) dù có `[build]` | ❌ Skip — không có code/branch nào để build |

### 7.2. Các bước job thực hiện

```yaml
steps:
  - name: Checkout repository
    uses: actions/checkout@v4
    with:
      ref: ${{ github.event_name == 'issue_comment' && format('refs/pull/{0}/head', github.event.issue.number) || github.ref }}

  - name: Build (${{ matrix.preset }})
    run: |
      & .\build.bat ${{ matrix.preset }}
      if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

  - name: Upload build artifacts
    uses: actions/upload-artifact@v4
    with:
      name: stm32f4-${{ matrix.preset }}-local
      path: |
        build/${{ matrix.preset }}/*.elf
        build/${{ matrix.preset }}/*.hex
        build/${{ matrix.preset }}/*.bin
        build/${{ matrix.preset }}/*.map
      if-no-files-found: error
      retention-days: 14
```

1. **Checkout repository** — runner tự `git checkout` đúng commit cần build
   ngay trên máy local. Với trigger từ comment, ref phải tự dựng thành
   `refs/pull/<số PR>/head` (GitHub tự tạo sẵn ref này cho mọi PR) vì sự
   kiện `issue_comment` không tự mang theo thông tin branch như sự kiện
   `pull_request`; các trigger còn lại dùng `github.ref` — đúng bằng hành vi
   mặc định nếu không truyền `ref` gì cả.
2. **Build** — gọi `build.bat` (giải thích chi tiết ở mục 8) với đúng 1
   preset (`Debug` hoặc `Release`, lấy từ `matrix.preset`). Nếu script thoát
   với mã lỗi khác 0, dòng `if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }`
   đảm bảo step — và cả job — hiển thị đỏ đúng lúc trên GitHub.
3. **Upload build artifacts** — đóng gói `.elf/.hex/.bin/.map` từ
   `build/<preset>/` thành 1 artifact tên `stm32f4-<preset>-local`, lưu trên
   GitHub 14 ngày, tải về được từ tab Actions (cách tải: mục 10).

`strategy.matrix.preset: [Debug, Release]` (không đổi so với trước) khiến
job này chạy **song song 2 lần**, mỗi lần build đúng 1 preset — ra 2 job con
"Build on local runner (Debug)" và "Build on local runner (Release)".

## 8. `build.bat` — file thực hiện build, dùng chung cho CI và build tay

File `build.bat` nằm ở **gốc repo**, được cả job CI ở mục 7 lẫn chính bạn
(khi muốn build tay để debug) cùng gọi — đảm bảo build trên CI và build trên
máy bạn luôn chạy **y hệt nhau từng bước**.

**Cách dùng** (PowerShell hoặc Command Prompt, tại thư mục gốc repo, cần đã
xong Bước 2):

```powershell
.\build.bat            # build cả Debug lẫn Release, tuần tự
.\build.bat Debug       # chỉ build Debug
.\build.bat Release     # chỉ build Release
```

Mỗi lần build 1 preset, script tự làm theo đúng thứ tự:

1. Kiểm tra `cmake`/`ninja`/`arm-none-eabi-gcc` có trên PATH — báo lỗi rõ
   ràng và dừng ngay nếu thiếu công cụ nào, thay vì để lỗi mập mờ ở bước sau.
2. `cmake --preset <preset>` — configure, sinh thư mục `build\<preset>\`.
3. `cmake --build --preset <preset>` — build thật sự (biên dịch + link).
4. Tìm file `.elf` vừa sinh ra, dùng `arm-none-eabi-objcopy` xuất thêm
   `.hex` và `.bin` (định dạng dùng để nạp vào vi điều khiển).
5. In dung lượng firmware bằng `arm-none-eabi-size` (theo dõi firmware có
   phình to bất thường không).

Bất kỳ bước nào lỗi, script dừng ngay lập tức và thoát với mã lỗi khác 0 —
không chạy tiếp các bước sau, không tạo file `.hex/.bin` giả từ 1 build lỗi.

**Muốn thêm bước vào quy trình build** (chạy static analysis, ký số
firmware, copy thêm file...): sửa trực tiếp trong `build.bat`, **không**
cần đụng tới `build.yml` — mọi nơi gọi `build.bat` (CI lẫn build tay) tự
động có ngay bước mới.

## 9. Test thử — 3 cách trigger

### 9.1. Push kèm tag `[build]`

```bash
git commit -m "feat: thêm debounce cho nút bấm [build]"
git push
```

### 9.2. Mở Pull Request

Mở PR nhắm vào `main` hoặc `develop` — luôn tự build, không cần tag
`[build]`.

### 9.3. Comment `[build]` trên PR đang mở

Vào 1 PR đã mở sẵn, để lại comment bất kỳ có chứa `[build]`, ví dụ:

```
Sửa xong phần debounce rồi, [build] thử trên máy local xem sao.
```

Chỉ hoạt động nếu tài khoản comment có vai trò Owner/Member/Collaborator
trên repo (xem bảng mục 7.1) — comment từ tài khoản khác sẽ bị bỏ qua âm
thầm (không có gì chạy, cũng không báo lỗi gì).

### 9.4. Xem kết quả

1. Vào repo trên GitHub → tab **Actions**.
2. Chọn run mới nhất tên **"Build Firmware"**.
3. Sẽ thấy job con **"Build on local runner (Debug)"** và **"Build on local
   runner (Release)"** — dấu tick xanh = thành công, dấu X đỏ = lỗi (bấm
   vào để đọc log chi tiết, xử lý y hệt lỗi build trên máy local).
4. Nếu job xanh, kéo xuống cuối trang run → mục **Artifacts** → tải
   `stm32f4-Debug-local.zip` / `stm32f4-Release-local.zip` về, giải nén ra
   sẽ có `STM32F4.elf/.hex/.bin/.map`.

## 10. Troubleshooting

| Hiện tượng | Nguyên nhân | Cách xử lý |
|---|---|---|
| Không thấy workflow chạy trên tab Actions sau khi push | Actions đang Disable ở Settings (mục 3), hoặc chưa push lên đúng repo | Kiểm tra lại mục 3 |
| Job self-hosted mãi ở trạng thái **"Waiting for a runner"**, không bao giờ chạy | Không có runner nào online mang đúng label `stm32-local`, hoặc runner service đang Stopped | Kiểm tra `Get-Service "actions.runner.*"`, xem mục 6.4; kiểm tra label lúc `config.cmd` (mục 6.3) khớp đúng `stm32-local` |
| Job self-hosted đỏ **rất nhanh (~1-2 giây)**, log chỉ có `Process completed with exit code 1.`, không rõ lỗi gì, dù tự gõ tay các lệnh trong `build.bat` trên chính máy đó lại chạy bình thường | Quên làm Bước 3 (Execution Policy) — xem giải thích đầy đủ ở mục 10.1 | Chạy lại lệnh ở Bước 3 |
| Vừa đổi PATH cấp Machine (Bước 2) hoặc vừa cấp thêm quyền NTFS xong nhưng job vẫn lỗi y hệt lỗi cũ (`not recognized` / `Access is denied`) | Runner service đã khởi động **trước** khi bạn đổi PATH/quyền — xem giải thích đầy đủ ở mục 10.2 | `Restart-Service -Name "actions.runner.<owner>-<repo>.<name>"` |
| Lỗi `UnauthorizedAccessException` khi service start | Cài `actions-runner` trong `C:\Users\<user>\...` thay vì gốc ổ đĩa — xem mục 10.3 | Xem cách fix ở mục 10.3, hoặc chuyển thư mục ra gốc ổ đĩa |
| Job đỏ ở bước "Build" | Code có lỗi compile thật sự | Đọc log lỗi trong `build.bat`, sửa code y hệt như build lỗi trên máy local |
| Không thấy mục Artifacts dù job xanh | `if-no-files-found: error` báo không tìm thấy `.elf` | Kiểm tra `build.bat` có in đúng dòng "Build finished successfully" không, kiểm tra `build/<preset>/` có file `.elf` không |

### 10.1. Giải thích chi tiết: PowerShell Execution Policy chặn script

Mỗi khi workflow chạy tới 1 bước có `run: |`, runner **không gõ lệnh trực
tiếp vào console** — nó ghi nội dung ra 1 file tạm `.ps1` (trong
`...\actions-runner\_work\_temp\`), rồi chạy file đó bằng kỹ thuật
dot-source. Windows Service chạy runner mặc định dưới tài khoản
`NT AUTHORITY\NETWORK SERVICE`, tài khoản này chỉ nhìn thấy scope
`LocalMachine` của Execution Policy (không thấy `CurrentUser` của tài khoản
bạn đăng nhập hằng ngày, dù bạn từng tự đổi `CurrentUser` thành
`RemoteSigned` trước đó). Nếu `LocalMachine` đang là `Undefined`/`Restricted`
(mặc định gốc của Windows), mọi file `.ps1` runner tự tạo ra đều bị chặn
ngay từ dòng đầu tiên — trước cả khi kịp gọi tới `build.bat`. Đây là lý do
Bước 3 phải làm **trước khi** cài runner, tránh gặp lỗi này ngay lần chạy
đầu.

### 10.2. Giải thích chi tiết: PATH/quyền không có tác dụng cho service đang chạy sẵn

Khi 1 Windows Service khởi động, Windows cấp cho nó 1 "access token" — ghi
sẵn tài khoản chạy service, các nhóm quyền, và **giá trị PATH cấp Machine
tại đúng thời điểm khởi động**. Vé này giữ nguyên suốt vòng đời tiến trình;
Windows không tự cấp lại dù sau đó bạn đổi PATH hay quyền. Kiểm tra thời
điểm service start so với thời điểm bạn đổi PATH:

```powershell
$svc = Get-CimInstance Win32_Service -Filter "Name LIKE 'actions.runner%'"
(Get-Process -Id $svc.ProcessId).StartTime
```

Nếu thời điểm in ra **sớm hơn** lúc bạn đổi PATH/quyền, restart lại service
để nó được cấp vé thông hành mới — đây cũng là lý do tài liệu này khuyến
nghị làm đúng thứ tự Bước 2 → Bước 3 → Bước 4 (cài toolchain xong rồi mới
cài & khởi động runner service), tránh hẳn phải nhớ restart về sau.

### 10.3. Giải thích chi tiết: UnauthorizedAccessException lúc service start

**Triệu chứng**: service `Stopped` ngay sau khi cài/start, log tại
`actions-runner\_diag\Runner_*.log` báo
`System.UnauthorizedAccessException: Access to the path 'C:\Users\<user>' is denied.`

**Nguyên nhân**: `NETWORK SERVICE` không có quyền list nội dung thư mục
profile người dùng (`C:\Users\<user>`) dù `config.cmd` đã tự cấp quyền cho
thư mục con `actions-runner` — runner kiểm tra quyền trên **toàn bộ đường
dẫn cha**. Thư mục gốc ổ đĩa (`C:\`) không bị vấn đề này.

**Cách fix** (nếu không muốn di chuyển lại thư mục):
```powershell
icacls "C:\Users\<user>" /grant "NT AUTHORITY\NETWORK SERVICE:(RX)"
Restart-Service -Name "actions.runner.<owner>-<repo>.<runner-name>"
```

## 11. Danh sách quyền cần "raise" khi setup trên **repo private + máy của khách hàng**

Khi bạn không phải chủ repo/chủ máy (đi setup cho khách hàng), đây là toàn
bộ những chỗ **cần xin quyền/phê duyệt trước**, phân theo hệ thống — chuẩn
bị trước danh sách này để trao đổi với khách hàng 1 lần, tránh bị chặn giữa
chừng nhiều lần.

### 11.1. Quyền trên GitHub

| Việc cần làm | Quyền cần có | Ai cấp |
|---|---|---|
| Bật Actions, đổi Actions permissions / Workflow permissions (mục 3) | **Admin** trên repo | Chủ repo / Owner tổ chức |
| Tạo token đăng ký runner (Settings → Actions → Runners → New self-hosted runner) (mục 6.1) | **Admin** trên repo | Chủ repo / Owner tổ chức |
| Nếu repo thuộc **Organization**: chính sách tổ chức có thể **chặn self-hosted runner theo mặc định** ở cấp Organization (Organization Settings → Actions → General → "Policies") | **Owner của Organization** | Owner tổ chức |
| Nếu repo/tổ chức bật "Require approval for all outside collaborators" hoặc giới hạn action bên thứ ba ("Allow select actions") | **Admin** repo hoặc **Owner** tổ chức | Chủ repo / Owner tổ chức |
| Xem/tải Artifact, xem log Actions | Quyền **Read** trên repo là đủ (không cần Admin) | — |

### 11.2. Quyền trên máy Windows của khách hàng

| Việc cần làm | Quyền cần có | Lưu ý khi là máy khách hàng |
|---|---|---|
| Cài CMake/Ninja/ARM GCC, sửa PATH cấp Machine (mục 4) | **Local Administrator** | Cần khách hàng cấp tài khoản admin cục bộ, hoặc yêu cầu IT khách hàng thực hiện thay |
| Đổi PowerShell Execution Policy scope `LocalMachine` (mục 5) | **Local Administrator** | Nếu máy join Active Directory và có **Group Policy (GPO)** ép `MachinePolicy` từ domain, lệnh `Set-ExecutionPolicy` cục bộ **sẽ không có tác dụng** — cần IT khách hàng chỉnh GPO, xem `Get-ExecutionPolicy -List` cột `MachinePolicy` để biết có bị GPO khoá không |
| Cài GitHub Actions Runner làm Windows Service (mục 6.3) | **Local Administrator** (cài Windows Service luôn cần quyền admin) | — |
| Restart Windows Service khi cần (mục 10.2) | **Local Administrator**, hoặc tài khoản được cấp riêng quyền Start/Stop đúng service đó | Có thể xin cấp quyền hẹp hơn Admin toàn máy nếu khách hàng yêu cầu (qua `sc.exe sdset` hoặc Group Policy) |
| Truy cập được máy (RDP/tại chỗ) | Tài khoản đăng nhập máy + (nếu RDP) máy phải cho phép RDP từ xa | Xin khách hàng cấp quyền truy cập máy trước khi bắt đầu bất kỳ bước nào |

### 11.3. Quyền mạng / bảo mật doanh nghiệp (dễ bị bỏ sót)

| Việc cần làm | Rủi ro bị chặn | Cần xin gì |
|---|---|---|
| Tải toolchain, tải GitHub Actions Runner (mục 4, 6.2) | Firewall/proxy doanh nghiệp chặn outbound HTTPS tới `github.com`, `objects.githubusercontent.com`, `armkeil.blob.core.windows.net` | Xin IT khách hàng mở outbound tới các domain trên, hoặc cấu hình proxy công ty cho runner (biến môi trường `https_proxy` khi cài) |
| Runner kết nối liên tục ra GitHub để nhận job | Firewall chặn outbound tới `*.actions.githubusercontent.com` khiến runner hiện `Offline` dù service `Running` | Xin IT khách hàng whitelist domain trên (runner chỉ cần outbound, **không** cần mở port inbound) |
| Chạy PowerShell script tạm, chạy `.exe` toolchain mới tải về | Antivirus/EDR doanh nghiệp (Defender for Endpoint, CrowdStrike...) có thể quarantine file `.ps1`/`.exe` lạ, hoặc chặn "Mark of the Web" trên file tải từ Internet | Xin đội bảo mật khách hàng thêm loại trừ (exclusion) cho `C:\actions-runner`, `C:\stm32-tools`, hoặc yêu cầu `Unblock-File` sau khi tải |
| Runner service chạy nền liên tục 24/7 | Chính sách máy tự khoá/update/restart ngoài giờ của khách hàng có thể làm gián đoạn runner | Xin loại trừ máy khỏi lịch restart tự động bắt buộc, hoặc chấp nhận runner offline tạm thời sau mỗi lần restart máy (service tự chạy lại nhờ `StartType: Automatic`, không cần can thiệp tay) |

### 11.4. Phê duyệt quy trình nội bộ (không phải "quyền" kỹ thuật, nhưng nên xin trước)

- **Self-hosted runner chạy bất kỳ code nào trong workflow của repo ngay
  trên máy khách hàng** — về bản chất là cho phép GitHub (và bất kỳ ai đẩy
  được code/PR/comment hợp lệ vào repo) thực thi lệnh trên máy đó. Nên có
  **xác nhận bằng văn bản/email** từ khách hàng rằng họ hiểu và đồng ý mô
  hình này trước khi cài đặt, đặc biệt nếu máy đó còn dùng cho việc khác
  (không phải máy build chuyên dụng cách ly).
- Nếu repo **public** hoặc có cộng tác viên ngoài công ty khách hàng: nên
  đề xuất bật thêm **Settings → Actions → General → "Require approval for
  all outside collaborators"** để PR từ người lạ không tự động chạy trên
  máy khách hàng.
- Nếu máy khách hàng còn dùng để chạy phần mềm/license khác (ví dụ dongle
  GHS, xem Phụ lục B): xác nhận với khách hàng máy này được phép cài thêm
  phần mềm (CMake/Ninja/ARM GCC/Runner) mà không xung đột chính sách nội bộ
  của họ (ví dụ whitelist phần mềm được phép cài).

## 12. Cách chỉnh sửa / mở rộng sau này

- Muốn build thêm 1 preset khác → thêm tên preset vào
  `matrix: preset: [Debug, Release, ...]` trong `build.yml` (preset đó phải
  tồn tại sẵn trong `CMakePresets.json`) — không cần sửa `build.bat`, vì nó
  nhận preset qua tham số dòng lệnh.
- Muốn thêm bước vào quy trình build (test, ký số, copy file...) → sửa
  `build.bat`, không cần sửa `build.yml` (xem mục 8).
- Muốn đổi tên/label runner → sửa `--labels` lúc `config.cmd` (mục 6.3) và
  `runs-on: [self-hosted, ...]` trong `build.yml` cho khớp.
- Muốn bỏ tag `[build]`, để **mọi push** đều tự build → xoá điều kiện
  `(github.event_name == 'push' && contains(...))` trong `if:` (mục 7.1),
  cân nhắc kỹ vì sẽ build liên tục mỗi lần push, tốn tài nguyên máy local.

---

## Phụ lục A — Job build trên cloud (`ubuntu-latest`)

Ngoài job `build-self-hosted` (nội dung chính của tài liệu này), `build.yml`
còn có job `build` chạy trên máy ảo GitHub cấp miễn phí (`ubuntu-latest`),
**độc lập** với self-hosted runner — không cần cài đặt gì thêm, tự chạy
song song. Job này cài Ninja + ARM GNU Toolchain qua 2 action bên thứ ba
(`seanmiddleditch/gha-setup-ninja`, `carlosperate/arm-none-eabi-gcc-action`)
rồi build y hệt logic trong `build.bat` nhưng viết trực tiếp bằng Bash
trong YAML — dùng để có 1 lớp build "sạch, không phụ thuộc máy local" chạy
song song, đối chiếu khi nghi ngờ máy local bị thiếu/lệch cấu hình. Job này
**không** đọc `[build]` từ comment (chỉ push + PR + workflow_dispatch), và
**không** dùng `build.bat`.

## Phụ lục B — Chuyển sang trình biên dịch GHS (Green Hills Software) qua license USB dongle

Job `build-self-hosted` hiện đang dùng tạm `arm-none-eabi-gcc`/`cmake`/
`ninja` (giống job cloud) để test luồng self-hosted trước khi có GHS thật.
Máy ảo cloud không thể truy cập USB dongle cắm ở máy local — đây chính là
lý do bắt buộc phải build qua self-hosted runner khi dùng GHS.

**Chuẩn bị GHS trên máy runner**:
1. Cài phần mềm GHS (MULTI IDE + gói compiler ARM) — bộ cài qua tài khoản
   MyGHS của công ty, không có sẵn public.
2. Cài driver dongle (Sentinel HASP hoặc tương đương) — thường tự cài cùng
   GHS.
3. Cắm dongle vào đúng cổng USB của **máy đang chạy Windows Service
   `actions.runner.*`**.
4. Kiểm tra: `ccarm -version` (tên compiler thật tuỳ gói đã mua, thường
   trong `C:\ghs\compXXXX\`) — in ra version + license tức driver/dongle
   hoạt động đúng.

**Thêm GHS vào PATH cấp Machine** (giống nguyên tắc mục 4):
```powershell
$ghsBin = "C:\ghs\compXXXX"   # thay bằng đường dẫn cài GHS thật
$machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
[Environment]::SetEnvironmentVariable("Path", $machinePath.TrimEnd(';') + ';' + $ghsBin, "Machine")
$env:Path += ";$ghsBin"
ccarm -version
```

**Đổi `build.bat` để dùng GHS thay vì ARM GCC**: có 2 hướng, tuỳ project có
chuyển hẳn sang định dạng project GHS (`.gpj`) hay vẫn giữ CMake:
- **Vẫn giữ CMake**: tạo thêm 1 toolchain file CMake riêng cho GHS (ví dụ
  `cmake/ghs-arm.cmake`, khai báo `CMAKE_C_COMPILER`/`CMAKE_CXX_COMPILER`
  trỏ tới `ccarm.exe`/`cxarm.exe`), sửa dòng `cmake --preset %PRESET%` trong
  `build.bat` thành
  `cmake --preset %PRESET% -DCMAKE_TOOLCHAIN_FILE=cmake/ghs-arm.cmake`.
- **Dùng thẳng project GHS MULTI gốc** (`.gpj`): bỏ hẳn các dòng CMake trong
  `build.bat`, gọi trực tiếp `gbuild -top path\to\project.gpj`.

**Lưu ý số lượng license (seat) khi build song song**: `build.yml` build
Debug và Release song song trên cùng 1 máy (`matrix.preset`). Nếu dongle
GHS chỉ cho phép 1 session compile đồng thời, thêm `max-parallel: 1` vào
`strategy` của job `build-self-hosted` để 2 preset chạy tuần tự thay vì
song song.

**Rủi ro cần lưu ý**: dongle bị rút ra hoặc máy khởi động lại mà driver
không tự nhận lại dongle → mọi job GHS fail đồng loạt tới khi cắm lại/khởi
động lại driver. Không build GHS song song trên máy runner thứ 2 được trừ
khi mua thêm dongle/license riêng.

## Phụ lục C — Self-hosted runner trên Linux

Toàn bộ tài liệu chính viết cho máy runner **Windows**. Nếu máy có dongle
(hoặc máy build local) là **Linux**, khái niệm nền tảng giống hệt, chỉ khác
công cụ hệ điều hành:

| Chủ đề | Windows | Linux |
|---|---|---|
| Shell chạy từng bước `run:` | PowerShell (`.ps1`, cần `shell: powershell`) | Bash mặc định, không cần khai báo `shell:` |
| "Execution Policy" chặn script (mục 10.1) | Có | Không có khái niệm tương đương — runner tự `chmod +x` file `.sh` tạm |
| PATH tách theo scope Machine/User (mục 4) | Có | Không tách, nhưng `systemd` không đọc `~/.bashrc` — vẫn phải khai PATH ở nơi service thấy được (`/etc/profile.d/`) |
| Cache PATH/quyền vào access token lúc service start (mục 10.2) | Có | Vẫn có — `systemd` cũng chỉ nạp môi trường 1 lần lúc start, vẫn phải `systemctl restart` sau khi đổi PATH/quyền |

**Cài toolchain** (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install -y cmake ninja-build gcc-arm-none-eabi
```

**Cài runner làm `systemd` service**:
```bash
mkdir -p ~/actions-runner && cd ~/actions-runner
curl -o actions-runner-linux-x64.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.336.0/actions-runner-linux-x64-2.336.0.tar.gz
tar xzf actions-runner-linux-x64.tar.gz
./config.sh --url "https://github.com/<owner>/<repo>" --token "<TOKEN>" \
  --name "stm32-linux-runner" --labels "stm32-local-linux" --work "_work" --unattended
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh status   # phải thấy "active (running)"
```

Vì `build-self-hosted` hiện dùng `defaults.run.shell: powershell` và gọi
`build.bat` (không chạy được trên Linux), cần viết 1 file `build.sh` tương
đương và thêm 1 job riêng dùng label khác (ví dụ `stm32-local-linux`) —
chưa nằm trong `build.yml` hiện tại, chỉ thêm khi thật sự có máy Linux cần
build.

**Lỗi thường gặp riêng Linux**:

| Hiện tượng | Nguyên nhân | Cách xử lý |
|---|---|---|
| `Permission denied` khi chạy script tạm | Thư mục `_work/_temp` mount với `noexec` | Đổi runner sang phân vùng không có `noexec` (`/home`, `/opt`) |
| Đổi PATH/quyền xong mà job vẫn không thấy tool | `systemd` chỉ nạp môi trường 1 lần lúc start | `sudo systemctl restart actions.runner.<owner>-<repo>.<name>.service` |
| Runner `Offline` dù service `active (running)` | Firewall/proxy chặn outbound tới `github.com` | `curl -I https://github.com` để kiểm tra, mở firewall outbound nếu bị chặn |

**Bảo mật riêng Linux**: không chạy runner dưới `root` — tạo user riêng
(ví dụ `ghrunner`) chỉ đủ quyền cài + chạy runner.

## Phụ lục D — Đem setup này sang 1 repo khác

| File | Copy nguyên hay phải sửa? |
|---|---|
| `.github/workflows/build.yml` | **Phải sửa** — dùng làm template, không copy y nguyên |
| `build.bat` | **Phải sửa** nếu repo mới khác toolchain/preset/tên thư mục build; giữ nguyên nguyên tắc: kiểm tra tool trên PATH + thoát lỗi rõ ràng ở mỗi bước |
| `doc/GithubActions/GithubActions_Setup.md` (chính file này) | Copy làm tài liệu tham khảo, sửa lại tên project/file cụ thể (STM32F4, `.elf`...) |
| `.github/copilot-instructions.md` | Copy được luôn nếu repo mới cũng là project nhúng — điền lại "Project context" cho đúng MCU/board mới |

**Trong `build.yml` cần sửa**: `matrix.preset` đúng theo `CMakePresets.json`
repo mới; đường dẫn artifact đúng cấu trúc thư mục build mới; nhãn
`runs-on: [self-hosted, ...]` đổi theo label runner thật. Trigger
`issue_comment` + điều kiện `author_association` (mục 7.1) có thể giữ
nguyên, không phụ thuộc toolchain cụ thể.

**Phần KHÔNG nằm trong file, phải làm lại thủ công trên máy mới**: đăng ký
runner mới (1 runner = 1 repo/org, cần token mới lấy từ repo mới — mục 6.1);
nếu là máy khác, phải làm lại toàn bộ Bước 2–5 (toolchain + Execution
Policy) từ đầu.

## Phụ lục E — Khái niệm nền tảng (cho người mới hoàn toàn với GitHub Actions)

| Khái niệm | Giải thích |
|---|---|
| **Workflow** | Toàn bộ 1 file `.yml` trong `.github/workflows/`. Mỗi file là 1 quy trình tự động độc lập. |
| **Trigger (`on:`)** | Điều kiện để workflow được kích hoạt (push, pull request, comment, chạy tay...). |
| **Job** | Một nhóm công việc chạy trên 1 máy (runner). 1 workflow có thể có nhiều job. |
| **Runner** | Máy chạy job — có thể là máy ảo GitHub cấp miễn phí (`ubuntu-latest`), hoặc **self-hosted**: máy vật lý/ảo do bạn tự cài đặt và duy trì. |
| **Step** | Một bước cụ thể bên trong job (chạy lệnh shell, hoặc gọi 1 "Action" có sẵn). |
| **Action** | Đoạn script đóng gói sẵn, dùng lại được (`chủ-sở-hữu/tên-action@version`). |
| **Matrix** | Cơ chế cho phép 1 job chạy lặp lại nhiều lần với tham số khác nhau (ở đây: build song song bản Debug và Release). |
| **Artifact** | File kết quả (`.hex`, `.bin`...) lưu lại sau khi job chạy xong, tải về được từ tab Actions. |
