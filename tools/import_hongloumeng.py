"""从维基文库导入《红楼梦》全文，生成 MkDocs 章回页面与目录。

用法：
    python tools/import_hongloumeng.py

说明：
    - 《红楼梦》原文属于公有领域；
    - 脚本会下载 120 回，清理维基语法后写入 docs/红楼梦/；
    - 会自动更新 mkdocs.yml 末尾的「红楼梦」导航。
"""

from __future__ import annotations

import concurrent.futures
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "红楼梦"
MKDOCS = ROOT / "mkdocs.yml"

API = "https://zh.wikisource.org/w/index.php"
USER_AGENT = "My-Blog-Importer/1.0 (personal blog; contact: wangtaoknight)"
TOTAL = 120
VOLUMES = [(1, 20), (21, 40), (41, 60), (61, 80), (81, 100), (101, 120)]


def fetch_raw(n: int) -> str:
    title = f"紅樓夢/第{n:03d}回"
    url = f"{API}?{urllib.parse.urlencode({'title': title, 'action': 'raw'})}"
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8")
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(1 + attempt)
    raise RuntimeError(f"下载失败：{last_error}")


def extract_title(raw: str, n: int) -> str:
    text = re.sub(r"-\{(.*?)\}-", r"\1", raw, flags=re.S)
    match = re.search(r"\{\{center\|'''(.+?)'''\}\}", text, re.S)
    if match:
        return re.sub(r"\s+", " ", match.group(1)).strip()
    match = re.search(r"'''(.+?)'''", text, re.S)
    if match:
        return re.sub(r"\s+", " ", match.group(1)).strip()
    return f"第{n:03d}回"


def poem_to_quote(match: re.Match[str]) -> str:
    lines = [line.strip() for line in match.group(1).strip().splitlines() if line.strip()]
    return "\n".join(f"> {line}" for line in lines)


def ppoem_to_quote(match: re.Match[str]) -> str:
    return poem_to_quote(match)


def cleanup_residual(text: str) -> str:
    """清理第一次未覆盖到的带属性 poem 标签与 ppoem 模板。"""
    text = re.sub(r"<poem[^>]*>(.*?)</poem>", poem_to_quote, text, flags=re.S)
    text = re.sub(r"\{\{ppoem\|(?:start=follow\|)?(.*?)\}\}", ppoem_to_quote, text, flags=re.S)
    text = re.sub(r"</?poem[^>]*>", "", text)
    return text


def clean(raw: str, title: str) -> str:
    text = raw

    # wiki 模板
    text = re.sub(r"\{\{样式:[^}]*\}\}", "", text)
    text = re.sub(r"\{\{center\|'''(.+?)'''\}\}", r"\1", text, flags=re.S)
    text = re.sub(r"\{\{center\|(.+?)\}\}", r"\1", text, flags=re.S)
    text = re.sub(r"\{\{~+\|(.*?)\}\}", r"\1", text, flags=re.S)
    text = re.sub(r"\{\{ppoem\|(?:start=follow\|)?(.*?)\}\}", ppoem_to_quote, text, flags=re.S)
    text = re.sub(r"\{\{清朝作品\}\}", "", text)
    text = re.sub(r"\{\{[^{}]*\}\}", "", text)

    # 繁简转换标记 -{云}- -> 云
    text = re.sub(r"-\{(.*?)\}-", r"\1", text, flags=re.S)

    # 脚注、章节标签
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.S)
    text = re.sub(r"<ref[^>]*/>", "", text)
    text = re.sub(r"<references\s*/>", "", text)
    text = re.sub(r"<section[^>]*/>", "", text)
    text = re.sub(r"</?noinclude>|</?onlyinclude>", "", text)

    # 诗词转为引用块[^>]*
    text = re.sub(r"<poem>(.*?)</poem>", poem_to_quote, text, flags=re.S)

    # wiki 链接
    text = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", text)
    text = re.sub(r"\[\[([^\]]*)\]\]", r"\1", text)

    # 标题
    text = re.sub(r"^===\s*(.*?)\s*===\s*$", r"### \1", text, flags=re.M)
    text = re.sub(r"^==\s*(.*?)\s*==\s*$", r"## \1", text, flags=re.M)

    # 分隔线与导航行
    text = re.sub(r"^-{4,}\s*$", "", text, flags=re.M)
    text = re.sub(r"^\s*(?:上一回|下一回|回目录)?[\s　]*(?:上一回|下一回|回目录)[\s　]*$", "", text, flags=re.M)

    # 去掉重复的回目标题行
    escaped = re.escape(title)
    text = re.sub(rf"^\s*{escaped}\s*$", "", text, flags=re.M)

    # 压缩空行
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def build_index(titles: dict[int, str]) -> str:
    parts = [
        "# 红楼梦",
        "",
        "《红楼梦》，原名《石头记》，清代曹雪芹著，中国古典四大名著之一。"
        "本站收录一百二十回全文，按章回编排，便于逐回阅读。",
        "",
        '!!! note "文本说明"',
        "    底本为[维基文库](https://zh.wikisource.org/wiki/紅樓夢)所收公版文本（繁体）；"
        "《红楼梦》原文已进入公有领域。",
        "",
        "## 章回目录",
        "",
    ]
    for start, end in VOLUMES:
        parts.append(f"### 第 {start} — {end} 回")
        parts.append("")
        for n in range(start, end + 1):
            parts.append(f"- [{titles[n]}](第{n:03d}回.md)")
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def build_nav(titles: dict[int, str]) -> str:
    lines = [
        '  - 首页: "index.md"',
        "  - 文章:",
        '      - 我的第一篇文章: "posts/hello-world.md"',
        '  - 关于: "about.md"',
        "  - 红楼梦:",
        '      - 目录: "红楼梦/index.md"',
    ]
    for start, end in VOLUMES:
        lines.append(f'      - "第 {start} — {end} 回":')
        for n in range(start, end + 1):
            lines.append(f'          - "{titles[n]}": "红楼梦/第{n:03d}回.md"')
    lines.append('  - 使用说明: "使用说明.md"')
    return "\n".join(lines)


def update_mkdocs(titles: dict[int, str]) -> None:
    content = MKDOCS.read_text(encoding="utf-8")
    # 用整段 nav 覆盖旧 nav，避免残留旧条目
    pos = content.find("\nnav:")
    if pos != -1:
        content = content[:pos]
    content = content.rstrip() + "\n\nnav:\n" + build_nav(titles) + "\n"
    MKDOCS.write_text(content, encoding="utf-8")


def existing_title(path: Path) -> str | None:
    if not path.exists() or path.stat().st_size < 200:
        return None
    with path.open(encoding="utf-8") as fh:
        first = fh.readline().strip()
    return first[2:].strip() if first.startswith("# ") else None


def download_one(n: int) -> tuple[int, str, bool]:
    path = OUT_DIR / f"第{n:03d}回.md"
    cached = existing_title(path)
    if cached:
        return n, cached, False

    raw = fetch_raw(n)
    title = extract_title(raw, n)
    body = clean(raw, title)
    page = (
        f"# {title}\n\n"
        f"> 文本来源：[维基文库](https://zh.wikisource.org/wiki/紅樓夢/第{n:03d}回)\n\n"
        f"{body}\n"
    )
    path.write_text(page, encoding="utf-8")
    return n, title, True


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    titles: dict[int, str] = {}
    failed: list[int] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(download_one, n): n for n in range(1, TOTAL + 1)}
        for future in concurrent.futures.as_completed(futures):
            n = futures[future]
            try:
                num, title, downloaded = future.result()
            except Exception as exc:  # noqa: BLE001
                print(f"[FAIL] 第{n:03d}回：{exc}", file=sys.stderr)
                failed.append(n)
                continue
            titles[num] = title
            flag = "OK" if downloaded else "SKIP"
            print(f"[{flag}] 第{num:03d}回 {title}")

    if failed:
        print(f"\n有 {len(failed)} 回下载失败：{sorted(failed)}", file=sys.stderr)
        return 1

    (OUT_DIR / "index.md").write_text(build_index(titles), encoding="utf-8")
    update_mkdocs(titles)
    print(f"\n完成：{len(titles)} 回，已写入 {OUT_DIR}")
    return 0


def fix_all() -> int:
    """对已生成的章节做二次清理：去掉重复回目、处理残余模板。"""
    pattern = re.compile(r"第\d{3}回\.md$")
    for path in sorted(OUT_DIR.iterdir()):
        if not pattern.match(path.name):
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        if not lines or not lines[0].startswith("# "):
            continue

        title = lines[0][2:].strip()
        target = re.sub(r"\s+", "", title)
        result = [lines[0]]
        removed = False
        for line in lines[1:]:
            if not removed and line.strip() and re.sub(r"\s+", "", line) == target:
                removed = True
                continue
            result.append(line)

        text = cleanup_residual("\n".join(result))
        path.write_text(text.rstrip() + "\n", encoding="utf-8")

    print("已清理重复回目与残留标记")
    return 0


def rebuild_nav() -> int:
    """根据已生成的章节文件重建整个 nav。"""
    titles: dict[int, str] = {}
    for n in range(1, TOTAL + 1):
        title = existing_title(OUT_DIR / f"第{n:03d}回.md")
        if not title:
            print(f"缺少第{n:03d}回，无法重建导航", file=sys.stderr)
            return 1
        titles[n] = title
    update_mkdocs(titles)
    print("导航已重建")
    return 0


if __name__ == "__main__":
    if "--fix" in sys.argv:
        raise SystemExit(fix_all())
    if "--nav" in sys.argv:
        raise SystemExit(rebuild_nav())
    raise SystemExit(main())
