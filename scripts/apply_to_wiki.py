#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取 wiki-content/manifest.json，把每日简报合并进 wiki 仓库。

只做「追加」：不覆盖任何已有内容，按 URL 去重。
manifest 中可选的 fixes 字段用于订正已发布条目的链接（按标题关键字匹配后整行重建）。
运行于 GitHub Actions，工作目录为仓库根目录，wiki 已克隆到 ./wiki。
"""
import io
import json
import os
import re
import sys

MANIFEST = "wiki-content/manifest.json"
WIKI = "wiki"


def ensure_title(content, name, title):
    if not content.strip():
        return "## %s\n" % title
    if not re.search(r"^#{1,3} ", content, re.M):
        return "## %s\n\n%s" % (title, content)
    return content


def apply_fixes(m, date):
    """订正已发布条目的链接：按 match 匹配标题关键字，整行重建。"""
    done = 0
    for fix in m.get("fixes", []):
        path = os.path.join(WIKI, fix["file"])
        if not os.path.exists(path):
            continue
        lines = io.open(path, encoding="utf-8").read().splitlines()
        hit = False
        for i, ln in enumerate(lines):
            if fix["match"] in ln:
                if "title" in fix:
                    lines[i] = "- [%s] %s — %s — [链接](%s) %s" % (
                        fix.get("date", date), fix["title"], fix.get("note", ""),
                        fix["url"], fix.get("level", ""))
                else:
                    lines[i] = re.sub(r"\((https?://[^)]+)\)", "(%s)" % fix["url"], ln)
                hit = True
                break
        if hit:
            io.open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
            done += 1
            print("  订正 %s: %s" % (fix["file"], fix["match"]))
    return done


def main():
    if not os.path.exists(MANIFEST):
        print("manifest 不存在，跳过")
        return 0

    m = json.load(io.open(MANIFEST, encoding="utf-8"))
    date = m["date"]
    print("处理日期:", date)

    # 0) 先订正已有条目的链接
    apply_fixes(m, date)

    # 1) 分类页追加
    for fname, items in m.get("categories", {}).items():
        path = os.path.join(WIKI, fname)
        content = io.open(path, encoding="utf-8").read() if os.path.exists(path) else ""
        content = ensure_title(content, fname, m.get("titles", {}).get(fname, fname))
        lines = []
        for title, url, level, note in items:
            if url and url in content:
                continue
            lines.append("- [%s] %s — %s — [链接](%s) %s" % (date, title, note, url, level))
        if lines:
            if not content.endswith("\n"):
                content += "\n"
            content += "\n" + "\n".join(lines) + "\n"
            io.open(path, "w", encoding="utf-8").write(content)
            print("  %s: +%d 条" % (fname, len(lines)))

    # 2) 每日简报页
    daily_name = m["daily_page"] + ".md"
    io.open(os.path.join(WIKI, daily_name), "w", encoding="utf-8").write(m["daily_content"])
    print("  %s: 已写入" % daily_name)

    # 3) Home.md 索引
    home_path = os.path.join(WIKI, "Home.md")
    home = io.open(home_path, encoding="utf-8").read() if os.path.exists(home_path) else ""
    marker = "## 每日简报索引"
    entry = "- %s — [%s](https://github.com/%s/wiki/%s)" % (
        date, m.get("summary", date), os.environ.get("GITHUB_REPOSITORY", "wangzhenNJ/AIstudy"),
        m["daily_page"])
    if marker in home:
        head, _, tail = home.partition(marker)
        rest = ""
        mm = re.search(r"\n## ", tail)
        if mm:
            tail, rest = tail[:mm.start()], tail[mm.start():]
        entries = [l for l in tail.splitlines()
                   if l.startswith("- 20") and not l.startswith("- " + date)]
        entries.insert(0, entry)
        entries = entries[:30]
        home = head + marker + "\n\n" + "\n".join(entries) + "\n" + rest
    else:
        if not home.endswith("\n"):
            home += "\n"
        home += "\n%s\n\n%s\n" % (marker, entry)
    io.open(home_path, "w", encoding="utf-8").write(home)
    print("  Home.md: 索引已更新")
    return 0


if __name__ == "__main__":
    sys.exit(main())
