"""言灵 · yanling.si 使用记录（每月自动跑一次，云中江树的个人项目）。

每次运行：
1. 抓取要留证的页面，存快照，算 SHA-256，写进 evidence/<日期>/snapshot-sha256.txt；
2. 请互联网档案馆（web.archive.org）存一份，记下存档链接；
3. 给 snapshot-sha256.txt 打 OpenTimestamps 时间证明（锚定比特币区块链，可独立验证）；
4. 把以前还没确认的 .ots 升级成完整证明；
5. 更新 evidence/LOG.md，提交并推送到 github.com/yzfly/yanling.si（GitHub 也会记下时间）。

只用标准库 + opentimestamps-client（.venv 里）。不碰任何别的仓库。
"""
from __future__ import annotations

import datetime as dt
import hashlib
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "evidence"
OTS = ROOT / ".venv" / "bin" / "ots"
URLS = ["https://yanling.si/", "https://www.yanling.si/", "https://github.com/yzfly/yanling.si"]
UA = "yanling.si-evidence/1.0 (+https://yanling.si)"
GIT_AUTHOR = ["-c", "user.name=yzfly", "-c", "user.email=zphyix@gmail.com"]


def log(*a):
    print(dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), *a, flush=True)


def fetch(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def wayback_save(url: str) -> str:
    """请 web.archive.org 存档 → 存档链接（失败返回说明，不中断）。"""
    for attempt in (1, 2, 3):
        try:
            req = urllib.request.Request("https://web.archive.org/save/" + url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=180) as r:
                loc = r.headers.get("Content-Location") or ""
                final = r.geturl()
            if loc:
                return "https://web.archive.org" + loc
            if "/web/" in final:
                return final
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            log("存档失败，稍后重试", url, type(exc).__name__, str(exc)[:120])
            time.sleep(30 * attempt)
    # 兜底：查一下最近的存档
    try:
        api = "https://archive.org/wayback/available?url=" + urllib.parse.quote(url, safe="")
        import json
        snap = json.loads(fetch(api)).get("archived_snapshots", {}).get("closest") or {}
        if snap.get("url"):
            return snap["url"] + "（最近一次存档）"
    except Exception as exc:  # noqa: BLE001
        log("查询存档失败", type(exc).__name__)
    return "（这次没存成，下次再试）"


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, **kw)


def main() -> int:
    now = dt.datetime.now(dt.timezone.utc)
    day = now.astimezone(dt.timezone(dt.timedelta(hours=8))).strftime("%Y-%m-%d")
    out = EVIDENCE / day
    out.mkdir(parents=True, exist_ok=True)

    lines = [f"# 言灵 · yanling.si 页面快照摘要（作者：云中江树）", f"抓取时间（UTC）：{now.isoformat(timespec='seconds')}", ""]
    for url in URLS:
        name = urllib.parse.urlsplit(url).netloc + urllib.parse.urlsplit(url).path.rstrip("/").replace("/", "_")
        try:
            body = fetch(url)
        except Exception as exc:  # noqa: BLE001
            lines.append(f"{url}\t抓取失败：{type(exc).__name__}")
            log("抓取失败", url, exc)
            continue
        snap = out / f"{name or 'root'}.html"
        snap.write_bytes(body)
        digest = hashlib.sha256(body).hexdigest()
        lines.append(f"{url}\t{snap.name}\t{len(body)} 字节\tsha256={digest}")
        log("快照", url, digest[:16])
    digest_file = out / "snapshot-sha256.txt"
    digest_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    archived = []
    for url in URLS:
        link = wayback_save(url)
        archived.append(f"{url}\t{link}")
        log("存档", url, link[:100])
    (out / "web-archive.txt").write_text("\n".join(archived) + "\n", encoding="utf-8")

    stamp = run([str(OTS), "stamp", str(digest_file)])
    log("时间证明", "ok" if stamp.returncode == 0 else stamp.stderr.strip()[:200])
    for ots in sorted(EVIDENCE.glob("*/*.ots")):
        up = run([str(OTS), "upgrade", str(ots)])
        if "Success" in (up.stdout + up.stderr):
            log("时间证明已确认", ots.relative_to(ROOT))

    log_md = EVIDENCE / "LOG.md"
    if not log_md.exists():
        log_md.write_text("# 使用记录\n\n| 日期 | 摘要文件 | 时间证明 | 互联网档案馆 |\n|---|---|---|---|\n", encoding="utf-8")
    first_link = archived[0].split("\t", 1)[1] if archived else ""
    row = (f"| {day} | [snapshot-sha256.txt]({day}/snapshot-sha256.txt) | "
           f"[.ots]({day}/snapshot-sha256.txt.ots) | {first_link} |\n")
    text = log_md.read_text(encoding="utf-8")
    if f"| {day} |" not in text:
        log_md.write_text(text + row, encoding="utf-8")

    run(["git", "add", "-A", "evidence"])
    commit = run(["git", *GIT_AUTHOR, "commit", "-q", "-m", f"evidence: {day} 页面快照、时间证明与存档链接"])
    if commit.returncode == 0:
        token = subprocess.run(["gh", "auth", "token", "--user", "yzfly"], text=True, capture_output=True).stdout.strip()
        if token:
            push = run(["git", "push", "-q", f"https://x-access-token:{token}@github.com/yzfly/yanling.si.git", "HEAD:main"])
            log("推送", "ok" if push.returncode == 0 else push.stderr.replace(token, "***").strip()[:200])
        else:
            log("推送跳过：没有 yzfly 的 gh 登录")
    else:
        log("没有新内容要提交")
    return 0


if __name__ == "__main__":
    sys.exit(main())
