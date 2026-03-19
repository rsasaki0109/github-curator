# github-curator

[![PyPI](https://img.shields.io/pypi/v/github-curator)](https://pypi.org/project/github-curator/)
[![Python](https://img.shields.io/pypi/pyversions/github-curator)](https://pypi.org/project/github-curator/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

複数の GitHub リポジトリの健全性を一括チェックする CLI ツールです。
アーカイブ済み・長期放置・リンク切れ・フォーク重複をまとめて検出します。

入力: GitHub リポジトリの URL（直接指定 / ファイル / トピック検索）
出力: 健全性レポート、リンク切れ検出、重複検出、統計サマリー

```bash
# URL を直接指定
github-curator health https://github.com/org/repo1 https://github.com/org/repo2

# ファイルから（Markdown でも、URL リストでも）
github-curator health -f repos.md

# GitHub トピックから
github-curator health --topic slam --max 20
```

```bash
$ github-curator health --topic slam --only-problems --max 10
                              Repository Health
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Repo                         ┃  Stars ┃ Last Push  ┃ Status   ┃ Issues                   ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ xdspacelab/openvslam         │  3,200 │ 2022-01-15 │ critical │ Archived, >2 years stale │
│ laboshinl/loam_velodyne      │  1,700 │ 2021-08-10 │ critical │ No updates for >2 years  │
│ cartographer-project/carto…  │  7,801 │ 2023-11-20 │ warning  │ No updates for >1 year   │
└──────────────────────────────┴────────┴────────────┴──────────┴──────────────────────────┘
```

| 機能 | 説明 | 入力方法 |
|---|---|---|
| `health` | アーカイブ・長期未更新・ライセンス不明を一括検出 | URL / ファイル / トピック |
| `suggest-alternatives` | 非活発なリポジトリの代替（フォーク・類似リポ検索・confidence付き、`--json`対応） | URL / ファイル / トピック |
| `check-links` | リンク切れ（404）になったリポジトリを検出 | URL / ファイル / トピック |
| `dedupe` | 同一アップストリームのフォーク・重複を検出 | URL / ファイル / トピック |
| `stats` | 総スター数・言語分布などの統計サマリー | URL / ファイル / トピック |
| `export` | リポジトリ情報を JSON/Markdown でエクスポート | URL / ファイル / トピック |
| `trend` | スター成長率・活動トレンドを分析 | URL / ファイル / トピック |
| `update-stars` | Markdown 内のスター数を最新値に一括更新 | ファイルのみ |
| `diff` | ファイルの版間で追加・削除されたリポジトリを比較 | ファイルのみ |

姉妹プロジェクト [arxiv-curator](https://github.com/rsasaki0109/arxiv-curator)（arXiv 新着論文の自動発見）と組み合わせて使えます。

### gh CLI / GitHub API を直接使う場合との違い

GitHub CLI (`gh`) でもリポジトリの検索・情報取得は可能です（`gh search repos --topic slam --sort stars --json` など）。
github-curator の強みは「複数の GitHub リポジトリを一括処理し、問題を検出する」部分です。

**gh CLI でできること（github-curator と重複する領域）:**

```bash
# トピック検索 + JSON出力 + 言語フィルタ — gh CLI だけで可能
gh search repos --topic slam --sort stars --language python --limit 10 --json fullName,stargazersCount
# 単一リポの情報取得
gh api repos/AtsushiSakai/PythonRobotics --jq '{stars: .stargazers_count}'
```

**gh CLI だけではやりにくいこと（github-curator の強み）:**

| やりたいこと | gh CLI | github-curator |
|---|---|---|
| Markdown 内の全リポのスター数を一括更新 | リポ URL を手動で抽出 → 1 つずつ `gh api` → Markdown を自分で書き換え | `update-stars awesome.md` で一括 |
| リンク切れを一括検出 | スクリプトを書いて 1 つずつチェック | `check-links -f awesome.md` or `check-links --topic slam` |
| リポジトリの健全性チェック | 個別に `gh api` で確認 | `health -f awesome.md` or `health --topic slam` |
| リストの差分比較 | `git diff` + 手動で URL を抽出 | `diff awesome.md --ref HEAD~1` |
| フォーク重複検出 | 個別に fork 情報を確認 | `dedupe -f awesome.md` or `dedupe --topic slam` |
| リストの統計サマリー | 集計スクリプトを自作 | `stats -f awesome.md` or `stats --topic slam` |
| スターバッジ付き Markdown 出力 | API レスポンスを自分で整形 | `export --format markdown` |

つまり、**個別リポの検索・情報取得は gh CLI で十分**ですが、**複数リポの一括処理と問題検出**が必要なときに github-curator が役立ちます。

### GitHub API の制限事項

| 制限 | 詳細 |
|---|---|
| レートリミット | 未認証: 60 回/時、認証済み: 5,000 回/時。`GITHUB_TOKEN` の設定を推奨 |
| プライベートリポジトリ | トークンにスコープがないとアクセス不可 |
| アーカイブ済みリポジトリ | 情報は取得できるが、活発度の判断は別途必要 |
| フォーク元の区別 | フォークかオリジナルかの判定はスター数では不十分な場合がある |

---

A CLI tool for batch health-checking GitHub repositories.
Detects archived repos, stale repos, broken links, and fork duplicates.

Input: GitHub repository URLs (direct / file / topic search)
Output: Health reports, broken link detection, duplicate detection, statistics

### How This Differs from gh CLI / GitHub API

The GitHub CLI (`gh`) can search repos and fetch info per repo (`gh search repos`, `gh api repos/owner/repo`, etc.).
github-curator's strength is **batch-analyzing multiple repos at once and reporting problems across the entire list**.

**What gh CLI already does well (overlapping features):**

```bash
# Topic search + JSON + language filter — gh CLI can do this
gh search repos --topic slam --sort stars --language python --limit 10 --json fullName,stargazersCount
# Single repo info
gh api repos/AtsushiSakai/PythonRobotics --jq '{stars: .stargazers_count}'
```

**What gh CLI doesn't do easily (github-curator's strength):**

| Task | gh CLI | github-curator |
|---|---|---|
| Bulk update star counts in Markdown | Manually extract URLs, call `gh api` per repo, rewrite Markdown | `update-stars awesome.md` |
| Bulk broken link detection | Write a script to check each URL | `check-links -f awesome.md` or `check-links --topic slam` |
| Repository health check | Check each repo via `gh api` individually | `health -f awesome.md` or `health --topic slam` |
| List diff comparison | `git diff` + manually extract URLs | `diff awesome.md --ref HEAD~1` |
| Fork duplicate detection | Check fork info per repo individually | `dedupe -f awesome.md` or `dedupe --topic slam` |
| List statistics summary | Write your own aggregation script | `stats -f awesome.md` or `stats --topic slam` |
| Markdown output with star badges | Format API responses yourself | `export --format markdown` |

In short: **for individual repo lookups and search, gh CLI is sufficient**. github-curator is useful when you need **batch processing of multiple repos with problem detection**.

### GitHub API Limitations

| Limitation | Details |
|---|---|
| Rate limit | Unauthenticated: 60/hour, authenticated: 5,000/hour. Set `GITHUB_TOKEN` |
| Private repos | Requires token with appropriate scope |
| Archived repos | Info is accessible, but activity assessment needs separate logic |
| Fork detection | Star counts alone may not distinguish forks from originals |

Works alongside [arxiv-curator](https://github.com/rsasaki0109/arxiv-curator) (new paper suggestions from arXiv). Both tools share compatible JSON export formats.

## インストール / Installation

**Requirements:** Python 3.10+

```bash
pip install github-curator
```

開発環境:

```bash
git clone https://github.com/rsasaki0109/github-curator.git
cd github-curator
pip install -e ".[dev]"
```

## 認証 / Authentication

GitHub API のレート制限を緩和するために、Personal Access Token の設定を推奨します。

To increase API rate limits, set a GitHub Personal Access Token:

```bash
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"
```

## 使い方 / Usage

### 入力方法 / Input Methods

すべてのコマンド（`update-stars` と `diff` を除く）は 3 つの入力方法をサポートしています:

All commands (except `update-stars` and `diff`) support 3 input methods:

```bash
# 1. URL を直接指定 / Direct URLs as arguments
github-curator health https://github.com/org/repo1 https://github.com/org/repo2

# 2. ファイルから / From a file (Markdown or plain text with URLs)
github-curator health -f repos.md

# 3. GitHub トピックから / From a GitHub topic
github-curator health --topic slam --max 20

# 組み合わせも可能 / Combine methods
github-curator health https://github.com/org/repo1 -f repos.md --topic slam
```

### ヘルスチェック / Health Check

リポジトリの健全性（アーカイブ・放置・ライセンス不明など）を一括チェックします。

Check health status (archived, stale, no license) for repositories:

```bash
github-curator health https://github.com/org/repo1 https://github.com/org/repo2
github-curator health -f awesome-robotics.md
github-curator health --topic slam --max 20
github-curator health -f awesome-robotics.md --only-problems

# 健全性チェック + 代替リポジトリの提案 / Health check with alternative suggestions
github-curator health -f repos.md --suggest-alternatives
```

### 代替リポジトリの提案 / Suggest Alternatives

非活発・アーカイブ済みリポジトリの代替（活発なフォーク、親リポジトリ、類似リポジトリ）を提案します。
3つの検索戦略で代替を探します: (1) 活発なフォーク、(2) 親リポジトリ、(3) キーワード類似検索。
各提案には confidence（high / medium / low）が付きます。

Find active forks, parent repos, or similar repos for stale/archived repositories.
Three search strategies: (1) active forks, (2) parent repo, (3) keyword-based similar repo search.
Each suggestion includes a confidence level (high / medium / low).

```bash
github-curator suggest-alternatives https://github.com/xdspacelab/openvslam
github-curator suggest-alternatives -f repos.md
github-curator suggest-alternatives --topic slam --max 20

# JSON output for scripting
github-curator suggest-alternatives --topic slam --json
```

```
$ github-curator suggest-alternatives https://github.com/xdspacelab/openvslam

Original: xdspacelab/openvslam (archived, 2,985 stars, last push 2021-02)
                          Alternatives
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Repo                      ┃  Stars ┃ Last Push  ┃ Confidence ┃ Why                            ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ stella-cv/stella_vslam    │    800 │ 2026-01    │ medium     │ Active fork (800 stars)        │
│ other/visual-slam-lib     │  1,200 │ 2026-03    │ low        │ Similar repo (1,200 stars)     │
└───────────────────────────┴────────┴────────────┴────────────┴────────────────────────────────┘
```

### リンク切れチェック / Check Links

GitHub リンクが有効か検証します。

Verify all GitHub links are still alive:

```bash
github-curator check-links https://github.com/org/repo1
github-curator check-links -f awesome-robotics.md
github-curator check-links --topic slam --max 20
```

### 重複検出 / Dedupe

同一アップストリームのフォークなど、重複・関連リポジトリを検出します。

Detect duplicate and related repos (forks of the same upstream):

```bash
github-curator dedupe https://github.com/org/repo1 https://github.com/org/repo2
github-curator dedupe -f awesome-robotics.md
github-curator dedupe --topic slam
```

### トレンド分析 / Trend

リポジトリのスター成長率・活動トレンドを分析します。
`created_at` を使った実年齢ベースの成長率推定、比較分析、アクティビティ内訳を表示します。

Analyze star growth rate and activity trends for repositories.
Uses actual repo age (from `created_at`) for accurate growth estimation,
comparative analysis across repos, and activity breakdown (issues/stars, forks/stars ratios).

```bash
# トピックのリポジトリのトレンド分析（セクター比較付き）
github-curator trend --topic slam --max 20

# 特定リポジトリの分析
github-curator trend https://github.com/AtsushiSakai/PythonRobotics https://github.com/cartographer-project/cartographer

# ファイルから
github-curator trend -f awesome-robotics.md

# JSON 出力
github-curator trend --topic slam --max 10 -o trend-report.json
```

```
$ github-curator trend https://github.com/AtsushiSakai/PythonRobotics https://github.com/cartographer-project/cartographer https://github.com/hku-mars/FAST_LIO https://github.com/xdspacelab/openvslam

                               Repository Trends
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Repo                              ┃  Stars ┃ Stars/mo┃ Activity   ┃ Status    ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ AtsushiSakai/PythonRobotics       │ 28,914 │     238 │ ██████████ │ growing   │
│ hku-mars/FAST_LIO                 │  4,600 │      67 │ ██░░░░░░░░ │ declining │
│ cartographer-project/cartographer │  7,801 │      67 │ █░░░░░░░░░ │ inactive  │
│ xdspacelab/openvslam              │  2,985 │      36 │ ░░░░░░░░░░ │ inactive  │
└───────────────────────────────────┴────────┴─────────┴────────────┴───────────┘

1 growing, 0 stable, 1 declining, 2 inactive

Comparative Analysis
  Fastest growing: AtsushiSakai/PythonRobotics (238 stars/month)
  Most active: AtsushiSakai/PythonRobotics (pushed 3 days ago)
  Largest: AtsushiSakai/PythonRobotics (28,914 stars)
```

### 統計サマリー / Stats

総スター数・言語分布などの統計サマリーを表示します。

Show summary statistics for repositories:

```bash
github-curator stats https://github.com/org/repo1 https://github.com/org/repo2
github-curator stats -f awesome-robotics.md
github-curator stats --topic slam --max 20
```

### エクスポート / Export

リポジトリ情報を JSON または Markdown 形式でエクスポートします。

Export repository data to JSON or Markdown:

```bash
github-curator export -f awesome-robotics.md --format json --output repos.json
github-curator export --topic slam --format markdown --output repos.md
github-curator export https://github.com/org/repo1 --format json
```

### スター数の更新 / Update Stars (file only)

Markdown ファイル内のスター数バッジを更新します。

Update star count badges in a Markdown file:

```bash
github-curator update-stars awesome-robotics.md
github-curator update-stars awesome-robotics.md --dry-run
```

### 差分比較 / Diff (file only)

Markdown ファイルの変更差分（追加・削除されたリポジトリ）を表示します。

Compare repos in a Markdown file against a previous version:

```bash
github-curator diff awesome-robotics.md
github-curator diff awesome-robotics.md --ref main~3
github-curator diff awesome-robotics.md --against old.md
```

### 実行サンプル / Examples

#### ヘルスチェック / Health Check

```
$ github-curator health --topic slam --only-problems --max 10
Found 10 repositories.
Checking health of 10 repositories ...
                              Repository Health
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Repo                               ┃  Stars ┃ Last Push  ┃ Status   ┃ Issues                   ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ old-org/deprecated-lib             │    200 │ 2022-01-15 │ critical │ No updates for >2 years  │
│ someone/experimental               │    150 │ 2025-06-01 │ warning  │ No license               │
└────────────────────────────────────┴────────┴────────────┴──────────┴──────────────────────────┘
```

#### 差分比較 / Diff

```
$ github-curator diff awesome-robotics.md --ref HEAD~1

Added (2):
  + newowner/cool-project
  + another/new-repo

Removed (1):
  - oldowner/removed-repo

Common repos: 12
```

#### スター数更新 / Update Stars

```
$ github-curator update-stars awesome-robotics.md
Updating stars in awesome-robotics.md ...
  API rate limit remaining: 4985/5000

Changes (3):
  AtsushiSakai/PythonRobotics: 28,500 -> 28,909 (+409)
  cartographer-project/cartographer: 7,750 -> 7,801 (+51)

Updated awesome-robotics.md
```

#### リンク切れチェック / Check Links

```
$ github-curator check-links -f awesome-robotics.md
Found 15 repositories.
Checking 15 repositories ...
  OK  AtsushiSakai/PythonRobotics
  OK  cartographer-project/cartographer
  FAIL old-user/deleted-repo — Not Found

1 broken link(s) found:
  - old-user/deleted-repo: Not Found
```

## arxiv-curator との連携 / Interoperability with arxiv-curator

両ツールの JSON 出力は共通フォーマットを共有しています。

Both tools produce JSON with a shared structure, making it easy to build pipelines:

```bash
# 論文とリポジトリの両方を収集 / Collect both papers and repos
arxiv-curator search "SLAM" --format json --output papers.json
github-curator export -f awesome-slam.md --format json --output repos.json
```

## ライセンス / License

MIT License. See [LICENSE](LICENSE) for details.
