# github-curator

[![PyPI](https://img.shields.io/pypi/v/github-curator)](https://pypi.org/project/github-curator/)
[![Python](https://img.shields.io/pypi/pyversions/github-curator)](https://pypi.org/project/github-curator/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

複数の GitHub リポジトリの健全性を一括チェックする CLI ツールです。
Markdown ファイルに書かれたリポジトリ URL を自動抽出し、アーカイブ・放置・リンク切れ・フォーク重複をまとめて検出します。

```bash
$ github-curator health awesome-slam.md --only-problems
                              Repository Health
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Repo                         ┃  Stars ┃ Last Push  ┃ Status   ┃ Issues                   ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ xdspacelab/openvslam         │  3,200 │ 2022-01-15 │ critical │ Archived, >2 years stale │
│ laboshinl/loam_velodyne      │  1,700 │ 2021-08-10 │ critical │ No updates for >2 years  │
│ cartographer-project/carto…  │  7,801 │ 2023-11-20 │ warning  │ No updates for >1 year   │
└──────────────────────────────┴────────┴────────────┴──────────┴──────────────────────────┘
```

| 機能 | 説明 |
|---|---|
| `health` | アーカイブ・長期未更新・ライセンス不明を一括検出 |
| `check-links` | リンク切れ（404）になったリポジトリを検出 |
| `dedupe` | 同一アップストリームのフォーク・重複を検出 |
| `update-stars` | Markdown 内のスター数を最新値に一括更新 |
| `diff` | ファイルの版間で追加・削除されたリポジトリを比較 |
| `stats` | 総スター数・言語分布などの統計サマリー |

姉妹プロジェクト [arxiv-curator](https://github.com/rsasaki0109/arxiv-curator)（arXiv 新着論文の自動発見）と組み合わせて使えます。

### gh CLI / GitHub API を直接使う場合との違い

GitHub CLI (`gh`) でもリポジトリの検索・情報取得は可能です（`gh search repos --topic slam --sort stars --json` など）。
github-curator の強みは「GitHub リポジトリの URL を含む Markdown ファイルを入力として一括処理する」部分です。

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
| Markdown 内の全リポのスター数を一括更新 | リポ URL を手動で抽出 → 1 つずつ `gh api` → Markdown を自分で書き換え | `update-stars awesome.md` で抽出〜更新〜差分レポートまで一括 |
| リンク切れを一括検出 | スクリプトを書いて 1 つずつチェック | `check-links awesome.md` |
| リポジトリの健全性チェック | 個別に `gh api` で確認 | `health awesome.md` でアーカイブ・放置・ライセンス不明を検出 |
| リストの差分比較 | `git diff` + 手動で URL を抽出 | `diff awesome.md --ref HEAD~1` で追加・削除を一覧 |
| フォーク重複検出 | 個別に fork 情報を確認 | `dedupe awesome.md` で同一アップストリームをグループ化 |
| リストの統計サマリー | 集計スクリプトを自作 | `stats awesome.md` で総スター・言語分布を表示 |
| スターバッジ付き Markdown 出力 | API レスポンスを自分で整形 | `--format markdown` でバッジ付き出力 |

つまり、**個別リポの検索・情報取得は gh CLI で十分**ですが、**Markdown ファイルを起点にした一括処理**が必要なときに github-curator が役立ちます。

### GitHub API の制限事項

| 制限 | 詳細 |
|---|---|
| レートリミット | 未認証: 60 回/時、認証済み: 5,000 回/時。`GITHUB_TOKEN` の設定を推奨 |
| プライベートリポジトリ | トークンにスコープがないとアクセス不可 |
| アーカイブ済みリポジトリ | 情報は取得できるが、活発度の判断は別途必要 |
| フォーク元の区別 | フォークかオリジナルかの判定はスター数では不十分な場合がある |

---

A CLI tool for batch health-checking multiple GitHub repositories.
It automatically extracts repo URLs from a Markdown file and detects archived repos, stale repos, broken links, and fork duplicates.

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
| Bulk update star counts in Markdown | Manually extract URLs, call `gh api` per repo, rewrite Markdown | `update-stars awesome.md` — extract, update, diff report in one command |
| Bulk broken link detection | Write a script to check each URL | `check-links awesome.md` |
| Repository health check | Check each repo via `gh api` individually | `health awesome.md` — detect archived, stale, unlicensed repos |
| List diff comparison | `git diff` + manually extract URLs | `diff awesome.md --ref HEAD~1` — show added/removed repos |
| Fork duplicate detection | Check fork info per repo individually | `dedupe awesome.md` — group repos by upstream |
| List statistics summary | Write your own aggregation script | `stats awesome.md` — total stars, language distribution |
| Markdown output with star badges | Format API responses yourself | `--format markdown` with star badges |

In short: **for individual repo lookups and search, gh CLI is sufficient**. github-curator is useful when you need **batch processing with a Markdown file as input**.

### GitHub API Limitations

| Limitation | Details |
|---|---|
| Rate limit | Unauthenticated: 60/hour, authenticated: 5,000/hour. Set `GITHUB_TOKEN` |
| Private repos | Requires token with appropriate scope |
| Archived repos | Info is accessible, but activity assessment needs separate logic |
| Fork detection | Star counts alone may not distinguish forks from originals |

Works alongside [arxiv-curator](https://github.com/rsasaki0109/arxiv-curator) (new paper suggestions from arXiv). Both tools share compatible JSON export formats.

## インストール / Installation

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

### スター数の更新 / Update Stars

GitHub リポジトリの URL を含む Markdown ファイル内のスター数バッジを更新します。

Update star count badges for all repos in a Markdown file containing GitHub URLs:

```bash
github-curator update-stars awesome-robotics.md
github-curator update-stars awesome-robotics.md --dry-run  # 変更を確認のみ / preview only
```

### ヘルスチェック / Health Check

リスト内リポジトリの健全性（アーカイブ・放置・ライセンス不明など）を一括チェックします。

Check health status (archived, stale, no license) for all repos in a Markdown file:

```bash
github-curator health awesome-robotics.md
github-curator health awesome-robotics.md --only-problems  # 問題のあるリポのみ表示 / show only problematic repos
```

### 差分比較 / Diff

Markdown ファイルの変更差分（追加・削除されたリポジトリ）を表示します。

Compare repos in a Markdown file against a previous version:

```bash
github-curator diff awesome-robotics.md                    # HEAD~1 と比較 / compare against HEAD~1
github-curator diff awesome-robotics.md --ref main~3       # 特定コミットと比較 / compare against specific ref
github-curator diff awesome-robotics.md --against old.md   # 別ファイルと比較 / compare against another file
```

### 重複検出 / Dedupe

同一アップストリームのフォークなど、重複・関連リポジトリを検出します。

Detect duplicate and related repos (forks of the same upstream):

```bash
github-curator dedupe awesome-robotics.md
```

### リンク切れチェック / Check Links

Markdown ファイル内の GitHub リンクが有効か検証します。

Verify all GitHub links in a Markdown file are still alive:

```bash
github-curator check-links awesome-robotics.md
```

### エクスポート / Export

リポジトリ情報を JSON または Markdown 形式でエクスポートします。

Export repository data from a Markdown file:

```bash
github-curator export awesome-robotics.md --format json --output repos.json
github-curator export awesome-robotics.md --format markdown --output repos.md
```

### 実行サンプル / Examples

#### ヘルスチェック / Health Check

```
$ github-curator health awesome-robotics.md --only-problems
Checking health of 15 repositories ...
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
$ github-curator check-links awesome-robotics.md
Checking 15 repositories ...
  OK  AtsushiSakai/PythonRobotics
  OK  cartographer-project/cartographer
  FAIL old-user/deleted-repo — Not Found

1 broken link(s) found:
  - old-user/deleted-repo: Not Found
```

> **Note**: update-stars and check-links examples are illustrative (not real output).

## arxiv-curator との連携 / Interoperability with arxiv-curator

両ツールの JSON 出力は共通フォーマットを共有しています。

Both tools produce JSON with a shared structure, making it easy to build pipelines:

```bash
# 論文とリポジトリの両方を収集 / Collect both papers and repos
arxiv-curator search "SLAM" --format json --output papers.json
github-curator export awesome-slam.md --format json --output repos.json
```

## ライセンス / License

MIT License. See [LICENSE](LICENSE) for details.
