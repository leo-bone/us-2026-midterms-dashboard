#!/usr/bin/env python3
"""每日同步 2026 中期选举预测市场数据到 data.json。

数据源：Polymarket 公共 Gamma API（无需密钥）
输出：data.json 的 markets 块 + markets.history + updated_at
期限：2026-11-04（北京时间）之后自动跳过（选举 11/3 结束，站点转入静态归档）

用法：
    python3 scripts/update_market.py            # 正常同步
    python3 scripts/update_market.py --dry-run  # 只打印，不写文件
    python3 scripts/update_market.py --self-test# 用内置样本验证解析逻辑（不联网）
"""

import json
import sys
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

BJ = timezone(timedelta(hours=8))
CUTOFF = datetime(2026, 11, 4, 23, 59, 59, tzinfo=BJ)  # 之后不再更新
GAMMA = "https://gamma-api.polymarket.com"
DATA_FILE = "data.json"
UA = {"User-Agent": "midterms-dashboard/1.0 (+github actions)", "Accept": "application/json"}


# ---------------------------------------------------------------- 网络

def get_json(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _loads(v):
    if isinstance(v, list):
        return v
    if isinstance(v, str) and v.strip():
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            return []
    return []


def dem_price(market):
    """从单个 market 里取民主党一侧的价格（百分比 0-100）。"""
    outs = [str(x).strip().lower() for x in _loads(market.get("outcomes"))]
    prices = _loads(market.get("outcomePrices"))
    q = str(market.get("question") or "").lower()

    for i, o in enumerate(outs):
        if "democrat" in o and i < len(prices):
            try:
                return float(prices[i]) * 100
            except (TypeError, ValueError):
                return None

    # 二元 Yes/No 市场：问题指向民主党时取 Yes
    if outs[:1] == ["yes"] and "democrat" in q and prices:
        try:
            return float(prices[0]) * 100
        except (TypeError, ValueError):
            return None
    return None


def event_score(event, kind):
    """给事件打分，选出真正代表「控制权」的那个市场。"""
    title = str(event.get("title") or "").lower()
    if kind not in title:
        return -1
    score = 0
    if "control" in title or "majority" in title or "win" in title:
        score += 5
    if "2026" in title or "midterm" in title:
        score += 3
    if "balance of power" in title:
        score -= 4  # 组合市场单独处理
    try:
        score += min(float(event.get("volume24hr") or 0) / 100000.0, 4)
    except (TypeError, ValueError):
        pass
    return score


def pick_event(events, kind):
    ranked = sorted(events, key=lambda e: event_score(e, kind), reverse=True)
    for e in ranked:
        if event_score(e, kind) < 0:
            break
        for m in e.get("markets") or []:
            if dem_price(m) is not None or "democrat" in str(m.get("question", "")).lower():
                return e
    return None


def collect_events():
    """拉取候选事件：先用搜索接口，失败则退回高成交额列表。"""
    events = []
    for q in ("house control", "senate control", "balance of power", "democratic sweep", "2026 midterms"):
        try:
            d = get_json(f"{GAMMA}/public-search?q={urllib.parse.quote(q)}&limit_per_type=20")
            events.extend(d.get("events") or [])
        except Exception as e:  # noqa: BLE001
            print(f"  · 搜索 '{q}' 失败：{e}")
    if not events:
        try:
            events = get_json(f"{GAMMA}/events?closed=false&limit=100&order=volume24hr&ascending=false")
        except Exception as e:  # noqa: BLE001
            print(f"  ! 事件列表拉取失败：{e}")
            return []
    # 去重
    seen, uniq = set(), []
    for e in events:
        key = e.get("slug") or e.get("id")
        if key and key not in seen:
            seen.add(key)
            uniq.append(e)
    return uniq


def pick_sweep(events, house=None, senate=None):
    """从事件里找「民主党两院全胜」概率；只认 2026 周期，找不到返回 None。"""
    PAST = ("2020", "2022", "2024")
    for ev in events:
        ident = f"{ev.get('slug') or ''} {ev.get('title') or ''}".lower()
        if any(y in ident for y in PAST):
            continue
        for m in ev.get("markets") or []:
            q = str(m.get("question") or "").lower()
            if "democrat" not in q:
                continue
            if not (("sweep" in q) or ("both chambers" in q) or ("house" in q and "senate" in q)):
                continue
            p = dem_price(m)
            if p is None or p < 1 or p > 100:   # <1% 基本是已结算旧市场的噪声
                continue
            if house and senate and p > min(house, senate) + 1:
                continue                        # 全胜不可能比任一单院更可能
            print(f"  ✓ 全胜 sweep：Dem {round(p,1)}%  ← {ev.get('slug')}")
            return round(p, 1)
    return None


def fetch_markets():
    events = collect_events()
    if not events:
        return {}

    out = {}
    for kind, label in (("house", "众院"), ("senate", "参院")):
        ev = pick_event(events, kind)
        if not ev:
            print(f"  · 未找到{label}控制权事件")
            continue
        best = None
        for m in ev.get("markets") or []:
            p = dem_price(m)
            if p is not None and 0 < p <= 100:
                if best is None or float(m.get("volume") or 0) > best[0]:
                    best = (float(m.get("volume") or 0), p)
        if best:
            out[kind] = round(best[1], 1)
            print(f"  ✓ {label}：Dem {out[kind]}%  ← {ev.get('slug')}")

    sweep = pick_sweep(events, out.get("house"), out.get("senate"))
    if sweep is not None:
        out["sweep"] = sweep
    elif "house" in out and "senate" in out:
        out["sweep"] = round(out["house"] * out["senate"] / 100, 1)
        out["sweep_derived"] = True
        print(f"  ~ 全胜 sweep 未找到对应市场，按乘积估算：{out['sweep']}%")
    return out


# ---------------------------------------------------------------- 写回

def update_history(hist, key, day, value):
    arr = hist.setdefault(key, [])
    if arr and arr[-1].get("d") == day:
        arr[-1]["v"] = value
    else:
        arr.append({"d": day, "v": value})
    # 只保留最近 40 个点，避免文件无限增长
    if len(arr) > 40:
        del arr[: len(arr) - 40]


def apply(data, live):
    now = datetime.now(BJ)
    mk = data.setdefault("markets", {})
    day = now.strftime("%m-%d")

    house = live.get("house", mk.get("house_d"))
    senate = live.get("senate", mk.get("senate_d"))
    sweep = live.get("sweep")
    if sweep is None or not (1 <= sweep <= 100):
        prev = mk.get("sweep")
        sweep = prev if isinstance(prev, (int, float)) and prev >= 1 else None
        if sweep is None and house and senate:
            sweep = round(house * senate / 100, 1)
            live["sweep_derived"] = True

    mk["house_d"] = house
    mk["senate_d"] = senate
    if sweep is not None:
        mk["sweep"] = sweep

    src = "Polymarket（GitHub Actions 每日同步）" if live else "Polymarket 快照（本次抓取失败，沿用上次）"
    derived = bool(live.get("sweep_derived"))
    mk["as_of"] = day
    mk["as_of_en"] = f"{now.strftime('%Y-%m-%d %H:%M')} Asia/Shanghai · {'live fetch' if live else 'last snapshot'}"
    mk["note"] = (
        f"Polymarket 实时抓取：民主党夺回众院 {house}%、夺回参院 {senate}%"
        + (f"、两院全胜 {sweep}%{'（按两院概率乘积估算）' if derived else ''}" if sweep is not None else "")
        + "。数值为交易价格隐含概率，非民调。"
    )
    mk["note_en"] = (
        f"Live from Polymarket: Democrats {house}% for the House, {senate}% for the Senate"
        + (f", {sweep}% for a sweep{' (derived from both-chamber prices)' if derived else ''}" if sweep is not None else "")
        + ". Prices imply probabilities; not polls."
    )
    mk["realtime"] = True

    hist = mk.setdefault("history", {})
    if house is not None:
        update_history(hist, "house", day, house)
    if senate is not None:
        update_history(hist, "senate", day, senate)
    if sweep is not None:
        update_history(hist, "sweep", day, sweep)

    data["updated_at"] = now.isoformat(timespec="seconds")
    data["live"] = True
    return data


# ---------------------------------------------------------------- 自检

def self_test():
    sample = [
        {
            "slug": "house-control-2026",
            "title": "Which party will control the House after the 2026 midterms?",
            "volume24hr": 500000,
            "markets": [
                {"question": "Will Democrats control the House?", "outcomes": '["Yes", "No"]',
                 "outcomePrices": '["0.93", "0.07"]', "volume": 9000000},
            ],
        },
        {
            "slug": "senate-control-2026",
            "title": "Which party will control the Senate after the 2026 midterms?",
            "volume24hr": 300000,
            "markets": [
                {"question": "Senate control?", "outcomes": '["Democratic", "Republican"]',
                 "outcomePrices": '["0.705", "0.295"]', "volume": 5000000},
            ],
        },
        {
            "slug": "balance-of-power",
            "title": "2026 Balance of Power",
            "volume24hr": 100000,
            "markets": [
                {"question": "Democratic Sweep", "outcomes": '["Yes", "No"]',
                 "outcomePrices": '["0.67", "0.33"]', "volume": 2000000},
            ],
        },
    ]
    assert dem_price(sample[0]["markets"][0]) == 93.0, dem_price(sample[0]["markets"][0])
    assert dem_price(sample[1]["markets"][0]) == 70.5, dem_price(sample[1]["markets"][0])
    assert pick_event(sample, "house")["slug"] == "house-control-2026"
    assert pick_event(sample, "senate")["slug"] == "senate-control-2026"
    assert dem_price(sample[2]["markets"][0]) == 67.0
    print("self-test OK")


def main():
    if "--self-test" in sys.argv:
        self_test()
        return

    now = datetime.now(BJ)
    if now > CUTOFF and "--force" not in sys.argv:
        print(f"已过 {CUTOFF:%Y-%m-%d}（选举结束），跳过更新。")
        return

    print(f"同步时间：{now:%Y-%m-%d %H:%M} (Asia/Shanghai)")
    live = fetch_markets()
    if not live:
        print("未取到任何有效数据，保留现有 data.json 不写入。")
        sys.exit(0)

    data = json.load(open(DATA_FILE, encoding="utf-8"))
    old = (data.get("markets", {}).get("house_d"), data.get("markets", {}).get("senate_d"))
    data = apply(data, live)
    new = (data["markets"].get("house_d"), data["markets"].get("senate_d"))

    print(f"众院 {old[0]} → {new[0]} / 参院 {old[1]} → {new[1]}")
    for k, v in live.items():
        if not (0 < v <= 100):
            print(f"! {k} 数值异常：{v}")

    if "--dry-run" in sys.argv:
        print("dry-run：不写文件")
        return

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("data.json 已更新")


if __name__ == "__main__":
    main()
