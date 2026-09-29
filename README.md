# 2026 美国中期选举 · 预测模型实时仪表盘

汇总主流选举预测模型与预测市场对 **2026 美国中期选举** 众议院 / 参议院控制权的民主党胜率，并把各模型之间的**真实方法论分歧**直接呈现出来。

> 在线版本：[https://voting.uichain.org](https://voting.uichain.org)
> （未配置自定义域名时回退到 GitHub Pages：https://leo-bone.github.io/us-2026-midterms-dashboard/ ）

## 它解决什么
市面上的"选举实时盘"很多，但很少把**不同模型给出不同答案**这件事本身讲清楚。本盘一次性展示：

- **预测市场**（Polymarket / Kalshi）：唯一秒级流式来源；
- **五大目标模型**：The Economist、Nate Silver (FLIPR)、FiftyPlusOne、Split Ticket、Race to the WH；
- **七个对照模型**：DDHQ、Scrutinel、Pollcast、Smarter.vote、VoteHub、Statsheet、VotePredictor。

当前众院民主党胜率从 **55%（Statsheet，最谨慎）** 到 **98%（FiftyPlusOne / Pollcast，最乐观）** —— 这是方法论分歧，不是误差。

## 功能
- 顶部"实时心跳"面板：预测市场民主党夺回众 / 参两院概率，并对比模型中枢；
- 12 张模型卡片：方法、读数时点、来源、自动 / 半自动 / 待抓取徽章；
- 两条概率漂移线（众院 / 参院）：基于公开报道的采样点（Silver、DDHQ、FiftyPlusOne、Kalshi 等）；
- 分歧快照：横条 + 区间带，一眼看出谁在分布两端。

## "实时"是怎么做的（诚实说明）
- **预测市场** 是唯一真正的秒级流。本盘通过 `data.json` + `fetcher.py` 接入其公开 API（Polymarket `gamma-api.polymarket.com` / Kalshi）后，面板自动从「演示模式」切换为「实时」。
- **统计模型** 全部是定时重算（FiftyPlusOne 4 次/天、Economist 每天、Silver 近每天、Split Ticket 周更、DDHQ / Scrutinel 每天）。前端用动画把离散快照呈现为连续流动——这是所有"选举实时盘"的真实做法。
- 当前仓库内置的是 **快照种子（`live=false`）**，因此线上默认显示「演示模式」。

## 本地运行
```bash
cd election-dashboard
python3 -m http.server 8080
# 浏览器打开 http://localhost:8080
```

## 自动刷新（接入真实数据）
```bash
python3 fetcher.py          # 抓取各模型 + 市场，写出 data.json（live=true）
python3 -m http.server 8080
```
注意：统计模型的公开页面多有反爬 / 地理封锁；在受限网络下，只有预测市场 API 稳定可得。可配合 cron / 定时任务周期性运行 `fetcher.py`。

## 数据来源与口径
详见 [ANALYSIS.md](ANALYSIS.md)。每个模型的 `source` 与 `as_of` 字段均标在卡片上。各模型口径不一（控制概率 / 席位中位 / 评级），本盘展示分歧，不做强行归一。

## 部署（GitHub Pages）
仓库根目录含 `CNAME`（voting.uichain.org）。在仓库 **Settings → Pages** 选择 `main` 分支、根目录发布；自定义域名 `voting.uichain.org` 需在 `uichain.org` 的 DNS 添加 **CNAME 记录**指向 `<user>.github.io`。

## 免责声明
本盘仅用于**方法学研判**，**不构成任何选举或投资建议**。数据来自各模型公开页面 / 访谈与公开报道，截至 2026-09-29，可能已过时，请以各模型官方最新发布为准。
