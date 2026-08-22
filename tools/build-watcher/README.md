# build-watcher — CI kéo (pull-based) cho repo không có quyền Settings

Build firmware trên máy local khi khách hàng **không thể cấp quyền Settings**
của repo (không đăng ký được self-hosted Actions runner, không tạo được
webhook). Thay vì GitHub đẩy job xuống máy build, máy build **tự kéo**: poll
1 branch chứa file yêu cầu, thấy yêu cầu mới thì checkout, build, đóng gói và
upload kết quả ngược lên GitHub.

Toàn bộ chỉ cần quyền **collaborator bình thường** (đọc/ghi code + commit
status) — đúng những quyền bạn vốn đã có vì đang push code được.

## Luồng hoạt động

```
Bạn: sửa Build_Infor.txt trên trigger branch -> push
                     │
                     ▼  (máy build poll mỗi 60s)
Watcher: git fetch, tìm commit MỚI đã chạm vào Build_Infor.txt
                     │
                     ▼
Parser: đọc "[Build] - [branch] - [preset]" tại đúng commit đó
                     │
                     ▼
Pipeline: kiểm tra allowlist -> đặt status "pending" trên commit
                     │
                     ▼
Builder: git worktree checkout branch -> chạy build.bat
                     │
                     ▼
Packager: gom .elf/.hex/.bin/.map -> zip theo tên branch
                     │
                     ▼
Uploader: tạo GitHub Release + upload zip -> đặt status success/failure
```

Kết quả hiện ngay trên GitHub: dấu ✅/❌ trên đúng commit đã yêu cầu build,
và file zip tải về được ở tab **Releases**.

## Vì sao thiết kế theo cách này

| Quyết định | Lý do |
|---|---|
| Duyệt **commit** đã chạm file, không đọc **nội dung hiện tại** của file | 2 lần push giữa 2 chu kỳ poll vẫn ra 2 build. Nếu đọc nội dung hiện tại, request đầu biến mất im lặng. Đây là bug khó phát hiện nhất của thiết kế polling ngây thơ |
| Request **không** chứa đường dẫn script | Nếu chứa, bất kỳ ai push được vào trigger branch đều chạy được lệnh tuỳ ý trên máy build. Script do config của máy build quyết định |
| Allowlist email người commit | Thay cho `author_association` mà GitHub Actions cấp sẵn — pull-based không có sẵn thứ đó |
| 1 tiến trình, 1 vòng lặp tuần tự | 1 máy build thì không có gì để song song, nhưng có cả 1 lớp bug checkout đè nhau để tránh |
| Lưu artifact ở **Releases**, không commit zip vào branch | Commit zip làm `.git` phình vô hạn theo thời gian |
| Commit Status API | Thay cho dấu tick xanh của Actions, không cần quyền Settings |
| `advance(sha)` sau **mỗi** request | Crash giữa batch thì resume đúng chỗ, không build lại cái đã xong |
| Chỉ dùng **stdlib** Python | Máy khách hàng thường chặn `pip install`. Không cần cài thêm gói nào |

## Cấu trúc module

Mỗi module là 1 *deep module*: interface nhỏ, phần thân dày. Thứ tự dưới đây
cũng là thứ tự phụ thuộc (trên không biết gì về dưới).

| Module | Interface | Giấu đi điều gì |
|---|---|---|
| `git_repo.GitRepo` | `fetch` `remote_head` `ref_exists` `commits_touching` `file_at` `worktree` | subprocess git, parse output, vòng đời worktree |
| `github_client.GitHubClient` | `set_commit_status` `publish_artifact` | token, retry/backoff, release đã tồn tại, upload asset |
| `state.StateStore` | `last_sha` `advance` | ghi atomic, khôi phục khi file hỏng |
| `request_format` | `parse_build_request` | format, validate chống option-injection |
| `builder.Builder` | `run` | tìm script, gọi qua cmd.exe, timeout, capture log |
| `packager.Packager` | `package` | tìm artifact theo glob, đặt tên zip |
| `pipeline.BuildPipeline` | `process` | trình tự + đảm bảo **luôn** kết thúc bằng đúng 1 status |
| `watcher.Watcher` | `poll_once` `run_forever` | poll, resume, backoff |
| `app.build_watcher` | — | composition root: nơi duy nhất biết adapter nào lắp vào seam nào |

Hai seam thật (mỗi cái có 2 adapter): `GitRepo` ↔ `FakeRepo`,
`GitHubClient` ↔ `NullGitHubClient`. Test chạy đúng `Watcher`/`BuildPipeline`
thật, chỉ thay adapter — không mock nội bộ.

## Python có bị policy chặn không?

Câu hỏi này quan trọng vì setup self-hosted runner trước đây từng bị
**PowerShell Execution Policy** chặn. Trả lời ngắn: **Execution Policy không
áp dụng cho Python** — nó chỉ chi phối `.ps1`. Nhưng có những cơ chế khác
*có thể* chặn, cần kiểm tra trên từng máy khách hàng:

| Cơ chế | Có chặn Python không? | Cách kiểm tra |
|---|---|---|
| PowerShell Execution Policy | **Không** — chỉ áp dụng cho `.ps1` | `Get-ExecutionPolicy -List` |
| AppLocker | **Có thể** — rule nhóm `Exe` chặn được `python.exe` (nhóm `Script` mặc định không bao gồm `.py`) | `Get-Service AppIDSvc`; `Get-AppLockerPolicy -Effective` |
| Software Restriction Policies | **Có thể** — chỉ khi `DefaultLevel` được đặt | `Get-ItemProperty "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Safer\CodeIdentifiers"` |
| WDAC / Device Guard | **Có thể** — chặn theo chữ ký/hash | `Get-CimInstance Win32_DeviceGuard -Namespace root\Microsoft\Windows\DeviceGuard` |
| Antivirus / EDR | **Có thể** — quarantine `python.exe` mới tải về | Hỏi đội bảo mật khách hàng |
| Chặn cài đặt (MSI/Store) | Né được bằng bản **embeddable** | `HKLM:\SOFTWARE\Policies\Microsoft\Windows\Installer` |

**Vì sao dùng bản embeddable zip**: không cần installer, không cần quyền
admin, không ghi registry, không cần `pip`. Chỉ giải nén là chạy. Điều này
chỉ khả thi vì tool viết **stdlib-only** — đó là lý do thật sự của ràng buộc
đó, không phải sở thích.

> Nếu máy khách hàng chặn cả `python.exe` ở mức AppLocker/WDAC thì mọi
> phương án script đều tắc như nhau (PowerShell còn tắc sớm hơn vì
> Execution Policy). Lúc đó phương án còn lại là xin whitelist theo đường
> dẫn/hash cho `python.exe`, hoặc biên dịch tool thành 1 `.exe` duy nhất
> rồi xin whitelist cho file đó.

## Cài đặt trên máy build

**Yêu cầu**: Python 3.8+ (bản **Windows**, không phải cygwin — cygwin khác
path semantics), git, và toolchain build của project (CMake/Ninja/ARM GCC —
xem `doc/GithubActions/GithubActions_Setup.md`).

```powershell
# 0) Cài Python embeddable (khong can admin, khong ghi registry)
$dst = "C:\build-watcher\python"
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip" -OutFile "$env:TEMP\py.zip" -UseBasicParsing
Expand-Archive "$env:TEMP\py.zip" -DestinationPath $dst -Force
# Ban embeddable co ay sys.path; phai them thu muc app vao ._pth
Add-Content "$dst\python312._pth" "C:\build-watcher\app"

# 1) Chép thư mục này vào máy build
Copy-Item -Recurse tools\build-watcher C:\build-watcher\app

# 2) Tạo config từ mẫu
Copy-Item C:\build-watcher\app\config.example.json C:\build-watcher\config.json
notepad C:\build-watcher\config.json   # sửa owner/repo/trigger_branch/allowed_committers

# 3) Đặt token (fine-grained PAT, chỉ Contents + Commit statuses read/write)
[Environment]::SetEnvironmentVariable("BUILD_WATCHER_GITHUB_TOKEN", "<token>", "Machine")

# 4) Kiểm tra setup trước khi chạy thật
cd C:\build-watcher\app
python -m build_watcher --config C:\build-watcher\config.json check

# 5) Chạy thử 1 vòng, không đụng gì tới GitHub
python -m build_watcher --config C:\build-watcher\config.json --dry-run once

# 6) Chạy thật
python -m build_watcher --config C:\build-watcher\config.json run
```

> Token đọc từ biến môi trường cấp **Machine** — Windows Service không thấy
> User PATH/biến môi trường của tài khoản đăng nhập. Cùng đúng 1 bài học đã
> gặp khi setup self-hosted runner trước đây: đổi biến môi trường xong phải
> **restart service**, vì service chỉ nạp môi trường 1 lần lúc khởi động.

> ⚠️ **Giữ `root` ngắn** (mặc định `C:\build-watcher`). Build chạy trong
> `<root>\work\wt-<12 hex>\`, và project C nhiều tầng thư mục còn thêm
> ~120 ký tự nữa — vượt giới hạn **MAX_PATH 260 ký tự** của Windows là
> compiler báo lỗi kiểu `cannot open ... .su for writing: No such file or
> directory`, rất khó đoán ra nguyên nhân. Lệnh `check` sẽ cảnh báo nếu
> đường dẫn workspace quá dài. Đây là lỗi đã gặp thật khi test tool này.

## Chuẩn bị phía repo khách hàng

Chỉ cần 1 branch và 1 file — không đụng Settings:

```bash
git checkout --orphan build-requests
git rm -rf .
cp Build_Infor.example.txt Build_Infor.txt
git add Build_Infor.txt && git commit -m "chore: add build request file"
git push -u origin build-requests
```

Sau đó, mỗi lần muốn build: thêm 1 dòng vào cuối `Build_Infor.txt` rồi push.

## Chạy nền như Windows Service

Dùng NSSM (đơn giản nhất, không cần code thêm):

```powershell
nssm install BuildWatcher "C:\Python312\python.exe" "-m build_watcher --config C:\build-watcher\config.json run"
nssm set BuildWatcher AppDirectory "C:\build-watcher\app"
nssm set BuildWatcher Start SERVICE_AUTO_START
nssm start BuildWatcher
```

## Test

```bash
python -m unittest discover -s tests -t .
```

## Đã kiểm chứng trên máy thật

Chạy end-to-end trên Windows 10 Pro với Python 3.12.10 embeddable, dùng 1
bare repo đóng vai repo khách hàng và branch `feature/Github_Actions_V2`
thật của project này:

| Kiểm chứng | Kết quả |
|---|---|
| 36 unit test trên Windows Python | pass |
| `check` — clone, đọc trigger branch, tìm request file | pass |
| Lần poll đầu tiên chỉ baseline, không build lại lịch sử | pass |
| Push **2 request liên tiếp** giữa 2 lần poll | cả 2 đều được build, không mất cái nào |
| Request từ email ngoài allowlist | bị chặn **trước khi** chạm builder, có status failure |
| Build thất bại thật (MAX_PATH) | báo failure kèm exit code, ghi log, **không** publish artifact |
| Build thành công | zip đúng 4 file `.elf/.hex/.bin/.map`, worktree được dọn sạch |

Phần **chưa** kiểm chứng: đường đi HTTP thật tới GitHub (`GitHubClient`) —
mọi lần chạy trên đều dùng `--dry-run`, tức `NullGitHubClient`. Cần 1 token
thật để kiểm chứng nốt việc tạo Release và đặt Commit Status.

## Còn thiếu (roadmap)

- [ ] Kiểm chứng `GitHubClient` với token thật (Release + Commit Status)
- [ ] Heartbeat định kỳ để biết máy build còn sống (pull-based không có
      "chấm xanh Idle" như trang Runners của Actions)
- [ ] Dọn artifact/log cũ theo tuổi
- [ ] Đọc token từ Windows Credential Manager thay vì biến môi trường
- [ ] Chạy như Windows Service và kiểm chứng lại dưới tài khoản service
      (PATH/quyền khác với tài khoản đăng nhập — xem bài học mục 10.2 của
      `GithubActions_Setup.md`)
