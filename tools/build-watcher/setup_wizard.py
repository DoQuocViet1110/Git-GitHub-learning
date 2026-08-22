"""Interactive config.json builder, run by setup.bat.

Batch scripts are poor at producing valid JSON (quoting, escaping,
trailing commas), so the wizard lives here and setup.bat calls it once
Python is available. Every question has a default that is correct for the
STM32F4-style project this was built against, so an operator who does not
know the answers can press Enter throughout and still get a usable file.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"

# github.com/<owner>/<repo>(.git), with or without a trailing slash.
_HTTPS_REPO = re.compile(
    r"^https://(?P<host>[^/]+)/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$"
)
_SSH_REPO = re.compile(r"^(?:ssh://)?git@(?P<host>[^:/]+)[:/](?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$")


def ask(question: str, default: str = "") -> str:
    suffix = " [{0}]".format(default) if default else ""
    while True:
        try:
            answer = input("{0}{1}: ".format(question, suffix)).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nDa huy.")
            sys.exit(1)
        if answer:
            return answer
        if default:
            return default
        print("  -> Bat buoc nhap, khong duoc de trong.")


def ask_yes_no(question: str, default_yes: bool = True) -> bool:
    suffix = " [Y/n]" if default_yes else " [y/N]"
    answer = input("{0}{1}: ".format(question, suffix)).strip().lower()
    if not answer:
        return default_yes
    return answer.startswith("y")


def parse_repo_url(url: str):
    """Return (normalised_https_url, owner, repo), or None if unparseable.

    SSH URLs are converted rather than rejected: the tool's token
    borrowing asks git for an `https` credential, so an SSH remote would
    leave it with nothing to borrow.
    """
    url = url.strip()
    match = _HTTPS_REPO.match(url)
    if match:
        return (
            "https://{0}/{1}/{2}.git".format(
                match.group("host"), match.group("owner"), match.group("repo")
            ),
            match.group("owner"),
            match.group("repo"),
        )

    match = _SSH_REPO.match(url)
    if match:
        print()
        print("  ! Ban vua nhap dia chi dang SSH (git@...).")
        print("    Tool nay lay token qua giao thuc HTTPS, nen se doi sang HTTPS.")
        print("    Neu may nay chi cau hinh SSH, xem muc 'Khac phuc su co' trong README.")
        print()
        return (
            "https://{0}/{1}/{2}.git".format(
                match.group("host"), match.group("owner"), match.group("repo")
            ),
            match.group("owner"),
            match.group("repo"),
        )
    return None


def main() -> int:
    print()
    print("=" * 68)
    print("  TAO FILE CAU HINH (config.json)")
    print("=" * 68)
    print()
    print("Nhan Enter de dung gia tri mac dinh trong dau ngoac vuong.")
    print()

    if CONFIG_PATH.exists():
        print("File config.json DA TON TAI tai:")
        print("  {0}".format(CONFIG_PATH))
        print()
        if not ask_yes_no("Ghi de bang cau hinh moi?", default_yes=False):
            print("-> Giu nguyen file cu. Khong thay doi gi.")
            return 0
        print()

    # --- Repository ---------------------------------------------------
    print("-" * 68)
    print("1. THONG TIN REPO CAN THEO DOI")
    print("-" * 68)
    parsed = None
    while parsed is None:
        url = ask(
            "Dia chi repo tren GitHub\n"
            "   (vi du: https://github.com/ten-khach-hang/ten-repo)"
        )
        parsed = parse_repo_url(url)
        if parsed is None:
            print("  -> Khong doc duoc dia chi. Vi du dung:")
            print("     https://github.com/ten-khach-hang/ten-repo")
    repo_url, owner, repo = parsed
    print("  -> Chu so huu : {0}".format(owner))
    print("  -> Ten repo   : {0}".format(repo))
    print()

    trigger_branch = ask(
        "Ten branch chua file yeu cau build", "build-requests"
    )
    request_file = ask("Ten file yeu cau build", "Build_Infor.txt")
    print()

    # --- Build --------------------------------------------------------
    print("-" * 68)
    print("2. THONG TIN BUILD")
    print("-" * 68)
    print("Luu y: file build script nay phai CO SAN o goc moi branch can build,")
    print("nam trong repo cua khach hang (khong phai file cua tool nay).")
    print()
    build_script = ask("Ten file script de build", "build.bat")
    presets_raw = ask(
        "Cac preset cho phep (cach nhau bang dau phay)", "Debug,Release"
    )
    allowed_presets = [p.strip() for p in presets_raw.split(",") if p.strip()]

    print()
    print("Duong dan file ket qua can dong goi (cach nhau bang dau phay).")
    print("Mac dinh phu hop project CMake sinh ra build/<preset>/<ten>.elf ...")
    globs_raw = ask(
        "Duong dan file ket qua",
        "build/*/*.elf,build/*/*.hex,build/*/*.bin,build/*/*.map",
    )
    artifact_globs = [g.strip() for g in globs_raw.split(",") if g.strip()]
    print()

    # --- Reporting ----------------------------------------------------
    print("-" * 68)
    print("3. BAO KET QUA LEN GITHUB")
    print("-" * 68)
    print("Neu bat: sau khi build xong se tao Release chua file zip, va gan")
    print("dau tick xanh/do len commit da yeu cau build.")
    print("Neu tat: chi build va luu file zip tren may nay.")
    print()
    report_to_github = ask_yes_no("Bat bao ket qua len GitHub?", default_yes=True)
    print()

    # --- Access control -----------------------------------------------
    print("-" * 68)
    print("4. AI DUOC PHEP YEU CAU BUILD")
    print("-" * 68)
    print("Mac dinh: tin tat ca nhung ai co quyen push vao repo.")
    print("Neu muon gioi han, nhap danh sach email (cach nhau bang dau phay).")
    print()
    committers_raw = ask("Danh sach email duoc phep (* = tat ca)", "*")
    allowed_committers = [c.strip() for c in committers_raw.split(",") if c.strip()]
    print()

    config = {
        "repo_url": repo_url,
        "owner": owner,
        "repo": repo,
        "trigger_branch": trigger_branch,
        "request_file": request_file,
        "poll_interval_seconds": 60,
        "root": (APP_DIR / "data").as_posix(),
        "build_script": build_script,
        "build_timeout_seconds": 3600,
        "artifact_globs": artifact_globs,
        "allowed_committers": allowed_committers,
        "allowed_presets": allowed_presets,
        "report_to_github": report_to_github,
        "status_context": "build-watcher/local",
    }

    CONFIG_PATH.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # Load it back through the real loader: a file the tool cannot read is
    # worse than no file, and better caught here than at 3am on a Monday.
    sys.path.insert(0, str(APP_DIR))
    from build_watcher.config import Config, ConfigError

    try:
        Config.load(CONFIG_PATH)
    except ConfigError as exc:
        print("!" * 68)
        print("LOI: file cau hinh vua tao khong hop le:")
        print("  {0}".format(exc))
        print("!" * 68)
        return 1

    print("=" * 68)
    print("  DA TAO XONG config.json")
    print("=" * 68)
    print("Vi tri: {0}".format(CONFIG_PATH))
    print()
    print(json.dumps(config, indent=2, ensure_ascii=False))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
