#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2026 中期选举 · 模型数据定时抓取器（v2）
----------------------------------------
把统计模型 + 预测市场的"控制权概率（民主党 %）"抓成 data.json，供 index.html 消费。

分层：
  Tier1 真·实时  : Polymarket / Kalshi 公开 API（秒级）
  Tier2 免费可解析: FiftyPlusOne(Substack API 找最新帖) / DDHQ / Scrutinel / Pollcast / Smarter.vote
  Tier3 半自动    : The Economist(反爬) / Silver(付费墙) / Split Ticket(The Argument) / VoteHub / Statsheet / VotePredictor
                    —— 这些的"最近读数"以公开报道的常量带入，标 auto=false，需人工复核

每个源独立 try/except，单源失败不影响整体；解析失败标 pending 并保留来源戳。
只用标准库，零依赖。生产建议换 requests+bs4，并对反爬源用 headless/代理。

用法：
  python3 fetcher.py           # 抓取并写 data.json
  python3 fetcher.py --dry     # 只打印不写文件
cron（每小时）：
  0 * * * * cd /path/election-dashboard && python3 fetcher.py >> fetch.log 2>&1
"""

import json, re, sys, datetime, urllib.request, urllib.error

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
TIMEOUT = 12

def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        data = r.read()
    return data if binary else data.decode("utf-8", "ignore")

def numf(s):
    if s is None: return None
    m = re.search(r"(\d{1,3}(?:\.\d+)?)", str(s))
    return float(m.group(1)) if m else None

# ---------------------------------------------------------------------------
# Tier1：真·实时（预测市场公开 API）
# ---------------------------------------------------------------------------
def fetch_market():
    """Polymarket gamma API（公开、秒级）。美国地理封锁时可能需境外节点/代理。
    同时尝试 Kalshi 公开端点作为备用。"""
    try:
        j = get("https://gamma-api.polymarket.com/markets?active=true&limit=100")
        data = json.loads(j)
        out = {}
        for m in data:
            q = (m.get("question") or "").lower()
            prices = m.get("outcomePrices")
            if prices and "house" in q and "control" in q:
                out["house_d"] = round(float(prices.split(",")[0]) * 100, 1)
            if prices and "senate" in q and "control" in q:
                out["senate_d"] = round(float(prices.split(",")[0]) * 100, 1)
        if out:
            return out, "realtime"
    except Exception as e:
        pass
    # 备用：Kalshi 公开市场列表（部分无需鉴权）
    try:
        j = get("https://api.elections.kalshi.com/v2/markets?limit=100&status=open")
        # Kalshi 返回结构不同，这里只探测，真正解析需按返回字段适配
    except Exception:
        pass
    return None, "ERR:Polymarket 不可达（可能地理封锁/需代理）；回退种子值"

# ---------------------------------------------------------------------------
# Tier2：免费、可解析
# ---------------------------------------------------------------------------
def fetch_fiftyplusone():
    """FiftyPlusOne 跑在 Substack：用公开 posts API 找最新选举预测帖，再抓正文解析。"""
    try:
        posts = json.loads(get("https://blog.fiftyplusone.news/api/v1/posts?offset=0&limit=12"))
        slug = None
        for p in posts:
            t = (p.get("title") or "").lower()
            if any(k in t for k in ["forecast", "congressional", "midterm", "house", "senate", "control"]):
                slug = p.get("slug"); break
        if not slug:
            slug = "election-forecast-democrats-strongly-favored-house-tilt-senate"
        html = get(f"https://blog.fiftyplusone.news/p/{slug}")
        m = re.search(r"Democrats an (\d{1,3})% chance of winning the majority of seats in the House, and a (\d{1,3})% chance of winning control of the Senate", html)
        if m:
            return float(m.group(1)), float(m.group(2)), "auto", slug
        return None, None, "pending:正文句式未命中", slug
    except Exception as e:
        return None, None, f"ERR:{e}", None

def fetch_ddhq():
    """DDHQ × The Hill：免费页，但数字在 JS 渲染块里以 '72% Probability' 形式出现。"""
    try:
        html = get("https://votes.decisiondeskhq.com/forecast/2026")
        def grab(block, pat):
            mm = re.search(pat, block)
            return numf(mm.group(1)) if mm else None
        hb = html[html.find("House Control"): html.find("House Control")+700]
        sb = html[html.find("Senate Control"): html.find("Senate Control")+700]
        h = grab(hb, r"(\d{1,3})%\s*Probability")
        s = grab(sb, r"(\d{1,3})%\s*Probability")
        return h, s, ("auto" if (h or s) else "pending:未命中 Probability"), None
    except Exception as e:
        return None, None, f"ERR:{e}", None

def fetch_scrutinel():
    """Scrutinel：免费页，正文含 'U.S. House 85% chance Democrats win control'。"""
    try:
        html = get("https://scrutinel.com/")
        h = numf(re.search(r"U\.S\. House\s+(\d{1,3})%\s*chance Democrats win control", html))
        s = numf(re.search(r"U\.S\. Senate\s+(\d{1,3})%\s*chance Democrats win control", html))
        return h, s, ("auto" if (h or s) else "pending:未命中"), None
    except Exception as e:
        return None, None, f"ERR:{e}", None

def fetch_pollcast():
    """Pollcast：免费页，'chance of a Democratic majority 97.3%'。"""
    try:
        html = get("https://pollcast.net/house_forecast")
        h = numf(re.search(r"chance of a Democratic majority\s+([\d.]+)%", html))
        return h, None, ("auto" if h else "pending:未命中"), None
    except Exception as e:
        return None, None, f"ERR:{e}", None

def fetch_smartervote():
    """Smarter.vote：免费页，'Democratic control projected (71%)'。"""
    try:
        html = get("https://smarter.vote/forecast/")
        h = numf(re.search(r"Democratic control projected\s*\(\s*(\d{1,3})", html))
        return h, None, ("auto" if h else "pending:未命中"), None
    except Exception as e:
        return None, None, f"ERR:{e}", None

def fetch_racetothewh():
    """Race to the WH：Squarespace 静态站，topline 在 <iframe> 内嵌图表，静态 HTML 无数字。
    需 headless 渲染 iframe 才能取数；此处标 pending。可选：下方 headless 分支（需浏览器）。"""
    try:
        get("https://www.racetothewh.com/house/")  # 探活
        return None, None, "pending:iframe 内嵌，需 headless 渲染", None
    except Exception as e:
        return None, None, f"ERR:{e}", None

# ---------------------------------------------------------------------------
# Tier3：半自动（反爬 / 付费墙 / 二次报道常量）—— 带入最近读数，标 auto=false
# ---------------------------------------------------------------------------
MANUAL = {
    "economist":   {"house_d": 65, "senate_d": 58, "as_of": "2026-09-中旬", "note": "聚合源口径（65%H）；交互页头条措辞 1 in 2 口径不一"},
    "silver":      {"house_d": 91, "senate_d": 69, "as_of": "2026-09-26", "note": "免费帖 topline（USPollingRank 9/26 引述）"},
    "splitticket": {"house_d": 85, "senate_d": 55, "as_of": "2026-08末/09初", "note": "The Argument 播客 8/31 引述：D 85%H/55%S"},
    "votehub":     {"house_d": 77, "senate_d": 47, "as_of": "2026-08末", "note": "GD Politics 8/31 引述：D 77%H/47%S"},
    "statsheet":   {"house_d": 55, "senate_d": 28, "as_of": "2026-09", "note": "Noah News 引述（最谨慎一端）"},
    "votepredictor":{"house_d": 76, "senate_d": 25, "as_of": "2026-09", "note": "Noah News 引述：D 76%H/25%S"},
}

# 各模型静态属性（名称/方法/层级），避免每次重复
ATTR = {
    "fiftyplusone": {"name": "FiftyPlusOne", "author": "G. Elliott Morris（前 538）", "method": "贝叶斯模型堆叠 · 4次/天", "tier": "primary", "src_tpl": "Substack 渲染页（{f}）"},
    "economist":    {"name": "The Economist", "author": "经济学人模型", "method": "贝叶斯多层 · 25,001 次模拟/天", "tier": "primary", "src_tpl": "{f}"},
    "silver":       {"name": "Nate Silver · FLIPR", "author": "Silver Bulletin", "method": "加权民调+基本面 · 4万次联合模拟", "tier": "primary", "src_tpl": "{f}"},
    "splitticket":  {"name": "Split Ticket / The Argument", "author": "Lakshya Jain", "method": "MRP+蒙特卡洛 · 周更", "tier": "primary", "src_tpl": "{f}"},
    "racetothewh":  {"name": "Race to the WH", "author": "Logan Phillips", "method": "数据驱动 · 每日模拟", "tier": "primary", "src_tpl": "{f}"},
    "ddhq":         {"name": "DDHQ × The Hill", "author": "Decision Desk HQ", "method": "每日 · 免费嵌入", "tier": "contrast", "src_tpl": "votes.decisiondeskhq.com 免费页（{f}）"},
    "scrutinel":    {"name": "Scrutinel", "author": "Scrutinel", "method": "每日 · 免费", "tier": "contrast", "src_tpl": "scrutinel.com 免费页（{f}）"},
    "pollcast":     {"name": "Pollcast", "author": "Pollcast", "method": "每日 · 免费", "tier": "contrast", "src_tpl": "pollcast.net（{f}）"},
    "smartervote":  {"name": "Smarter.vote", "author": "Smarter.vote", "method": "AI 模型 · 免费", "tier": "contrast", "src_tpl": "smarter.vote/forecast（{f}）"},
    "votehub":      {"name": "VoteHub", "author": "Zachary Donnini", "method": "聚合民调+市场微调", "tier": "contrast", "src_tpl": "{f}"},
    "statsheet":    {"name": "Election Statsheet", "author": "贝叶斯模型", "method": "贝叶斯 · 偏谨慎", "tier": "contrast", "src_tpl": "{f}"},
    "votepredictor":{"name": "VotePredictor", "author": "VotePredictor", "method": "模拟", "tier": "contrast", "src_tpl": "{f}"},
}

def build():
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec="seconds")
    models = []

    # —— 自动源 ——
    h, s, flag, extra = fetch_fiftyplusone()
    a = ATTR["fiftyplusone"]; models.append({**mkbase("fiftyplusone", a), "house_d": h, "senate_d": s, "as_of": now[:10], "source": a["src_tpl"].format(f=flag), "auto": flag=="auto", "history": None})

    h, s, flag, extra = fetch_ddhq()
    a = ATTR["ddhq"]; models.append({**mkbase("ddhq", a), "house_d": h, "senate_d": s, "as_of": now[:10], "source": a["src_tpl"].format(f=flag), "auto": flag=="auto", "history": None})

    h, s, flag, extra = fetch_scrutinel()
    a = ATTR["scrutinel"]; models.append({**mkbase("scrutinel", a), "house_d": h, "senate_d": s, "as_of": now[:10], "source": a["src_tpl"].format(f=flag), "auto": flag=="auto", "history": None})

    h, s, flag, extra = fetch_pollcast()
    a = ATTR["pollcast"]; models.append({**mkbase("pollcast", a), "house_d": h, "senate_d": s, "as_of": now[:10], "source": a["src_tpl"].format(f=flag), "auto": flag=="auto", "history": None})

    h, s, flag, extra = fetch_smartervote()
    a = ATTR["smartervote"]; models.append({**mkbase("smartervote", a), "house_d": h, "senate_d": s, "as_of": now[:10], "source": a["src_tpl"].format(f=flag), "auto": flag=="auto", "history": None})

    h, s, flag, extra = fetch_racetothewh()
    a = ATTR["racetothewh"]; models.append({**mkbase("racetothewh", a), "house_d": h, "senate_d": s, "as_of": "未捕获（iframe 内嵌）", "source": a["src_tpl"].format(f=flag), "auto": flag=="auto", "history": None})

    # —— 半自动常量 ——
    for mid, info in MANUAL.items():
        a = ATTR[mid]; models.append({**mkbase(mid, a), "house_d": info["house_d"], "senate_d": info["senate_d"], "as_of": info["as_of"], "source": a["src_tpl"].format(f=info["note"]), "auto": False, "history": None})

    # —— 市场（实时）——
    mk, flag = fetch_market()
    markets = {"name": "预测市场（Kalshi / Polymarket）", "house_d": (mk or {}).get("house_d") or 88, "senate_d": (mk or {}).get("senate_d") or 56, "as_of": now[:10], "note": f"真·实时流式（{flag}）", "realtime": flag=="realtime", "history": None}

    return {"updated_at": now, "election_day": "2026-11-03",
            "note": "数值为各模型最近一次公开读数（民主党胜率 %）。来源见 source 字段。",
            "models": models, "markets": markets}

def mkbase(mid, a):
    return {"id": mid, "name": a["name"], "author": a["author"], "method": a["method"], "tier": a["tier"]}

if __name__ == "__main__":
    data = build()
    print(json.dumps(data, ensure_ascii=False, indent=2))
    if "--dry" not in sys.argv:
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("\n[written] data.json")
