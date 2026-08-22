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

## Cài đặt trên máy build

**Yêu cầu**: Python 3.8+ (bản Windows, không phải cygwin), git, và toolchain
build của project (CMake/Ninja/ARM GCC — xem `doc/GithubActions/GithubActions_Setup.md`).

```powershell
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

## Còn thiếu (roadmap)

- [ ] Heartbeat định kỳ để biết máy build còn sống (pull-based không có
      "chấm xanh Idle" như trang Runners của Actions)
- [ ] Dọn artifact/log cũ theo tuổi
- [ ] Đọc token từ Windows Credential Manager thay vì biến môi trường
- [ ] Test end-to-end với 1 repo git thật (hiện GitRepo mới chỉ được dùng
      qua fake trong test)
