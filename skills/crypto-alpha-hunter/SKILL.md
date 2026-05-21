---
name: crypto-alpha-hunter
version: 2.0.0
description: "GMGN-based crypto alpha hunter — full-chain meme coin scanner with AI narrative focus. Filter, score, and report high-signal tokens. Skill-forged from real workflow."
author: Hermes Skill Forge
tags: [crypto, meme-coin, gmgn, alpha, scanner]
tested: true
quality_score: 1.00
---

# Crypto Alpha Hunter — 全链 Meme 币 Alpha 扫描

## 触发条件

当用户需要扫描币圈 meme 币 alpha 信号、挖早期项目、或设置定时推送时使用此技能。

关键词：alpha 扫描、meme 币、AI meme、gmgn 扫链、币圈热点、聪明钱。

## 前置条件

- `gmgn-cli >= 1.2.1`（npm 全局安装）
- `GMGN_API_KEY` 已配置在 `~/.config/gmgn/.env`
- 代理：`HTTP_PROXY=http://127.0.0.1:7897 HTTPS_PROXY=http://127.0.0.1:7897`

## 用户偏好

| 偏好 | 值 |
|------|-----|
| 链 | 全链 (Solana / Base / BSC) |
| 叙事 | AI meme 优先，排除名人/政治币 |
| 策略 | 偏稳健 + 预埋伏，MC $10万-$1000万最佳 |
| 风格 | 中文，简洁，带态度 |

## 扫描流程

### 1. 三链并行扫描

```bash
for chain in sol base bsc; do
  HTTP_PROXY=http://127.0.0.1:7897 HTTPS_PROXY=http://127.0.0.1:7897 \
    gmgn-cli market trending --chain $chain --interval 1h --limit 20 --raw
done
```

### 2. 筛选规则

**硬性排除：** 名人/政治币 (trump/biden/elon/musk/donald/kamala/obama/putin/president/politic/vote/party)

**质量门：** `rug_ratio < 0.2` AND `smart_degen_count ≥ 1` AND `is_wash_trading = false`

**AI meme 加分：** name/symbol 含 ai/agent/neural/brain/gpt/llm/deep/intelligence/bot/virtual/model/chat/assistant/cortex/mind

### 3. 评分模型

```
score = 0
if rug_ratio < 0.1: +30 elif < 0.2: +15 else: -50
score += min(smart_degen_count × 5, 30)
if renowned_count > 0: +10
if creator_close: +10
if 100k < market_cap < 500k: +15 elif < 5M: +10
if is_ai_meme: +20
```

### 4. 输出格式

**有信号时（≥ 2 个优质 token）：**

```
【🚨 实时 Alpha】

🤖 #1 TokenName | $SYMBOL | SOL/BASE/BSC
MC: $xxx万 | Vol1h: $xxx | 1h: +xx%
SM: X个 | KOL: X个 | rug: 0.xxx | LP: $xxx
Dev: creator_close/hold | Wash: false
https://gmgn.ai/{chain}/token/{address}
```

**无信号时：** `本轮无重大信号`

## Token 质量快判

| 信号 | 🟢 通过 | 🟡 观望 | 🔴 跳过 |
|------|---------|---------|---------|
| smart_degen_count | ≥ 3 | 1-2 | 0 |
| rug_ratio | < 0.1 | 0.1-0.3 | > 0.3 |
| creator_token_status | creator_close | — | creator_hold |
| is_wash_trading | false | — | true |
| liquidity | > $50k | $10k-$50k | < $10k |

## 注意事项

- 所有 gmgn-cli 命令必须加代理环境变量
- 输出严格使用中文
- meme 币极高风险，仅供信息参考，非投资建议
- 排除名人币和政治币是硬性规则
- 宁可无信号，不要推送垃圾

## 陷阱 (Pitfalls)

### Python `0.0` 是 falsy！
`rug_ratio = token.get('rug_ratio') or 1.0` 会把 `0.0` 当 `1.0`——因为 Python 中 `0.0` 是 falsy。
**正确写法：** `rug = token.get('rug_ratio'); rug = rug if rug is not None else 1.0`
或 `rug = float(token.get('rug_ratio', 0) or 0)` — 但推荐显式 None 判断。
同样影响 `score_token()` 和 `passes_quality_gate()` 中的所有数值字段。

### `price_change_percent*` 可为空字符串
GMGN 返回的 price_change 字段在新币上常为空字符串 `""`。用 `float(value or 0)` 而非 `float(value)`。
