# github-curator

[![PyPI](https://img.shields.io/pypi/v/github-curator)](https://pypi.org/project/github-curator/)
[![Python](https://img.shields.io/pypi/pyversions/github-curator)](https://pypi.org/project/github-curator/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

awesome-xxx リストのスター数更新・リンク切れチェック・トレンド検索を行う CLI ツールです。
Markdown ファイルを渡すだけで、記載されている全リポジトリの情報を一括で取得・更新できます。

```bash
# Markdown ファイルを渡すだけ。全リポジトリのスター数を一括更新。
$ github-curator update-stars awesome-slam.md
Changes (3):
  AtsushiSakai/PythonRobotics: 28,500 -> 28,909 (+409)
  cartographer-project/cartographer: 7,750 -> 7,801 (+51)

# リンク切れも一発チェック。
$ github-curator check-links awesome-slam.md
  OK   AtsushiSakai/PythonRobotics
  FAIL old-user/deleted-repo — Not Found
```

| こんな課題 | github-curator の解決策 |
|---|---|
| スター数が半年前のまま | `update-stars` で全リポジトリのスター数を一括更新 |
| リンク切れに気づかない | `check-links` で 404 になったリポジトリを検出 |
| 分野のトレンドを追いたい | `trending` でトピック・言語別にリポジトリを検索 |
| リストの統計が知りたい | `stats` で総スター数・言語分布などをサマリー表示 |
| 定期メンテを自動化したい | GitHub Actions で週次自動更新 |

姉妹プロジェクト [arxiv-curator](https://github.com/rsasaki0109/arxiv-curator)（arXiv 新着論文の自動提案）と組み合わせて使えます。

### gh CLI / GitHub API を直接使う場合との違い

GitHub CLI (`gh`) や GitHub REST API でもリポジトリ情報は取得できますが、awesome-list のメンテナンスに特化した機能はありません。

| やりたいこと | gh CLI / GitHub API | github-curator |
|---|---|---|
| Markdown 内の全リポのスター数を更新 | `gh api` を 1 リポずつ叩いて、自分で Markdown を書き換える | `github-curator update-stars awesome.md` で一括更新＋差分レポート |
| リンク切れを検出 | URL を 1 つずつ `gh api` で確認するスクリプトを書く | `github-curator check-links awesome.md` |
| トピック別トレンド検索 | `gh search repos --topic slam --sort stars` で検索可能 | `github-curator trending "topic:slam"` でリッチなテーブル表示＋JSON/Markdown 出力 |
| リストの統計サマリー | 自分で集計スクリプトを書く | `github-curator stats awesome.md` で総スター・言語分布を表示 |
| 定期的にスター数を更新 | GitHub Actions + 自作スクリプト | GitHub Actions テンプレート付き |
| awesome-list 形式で出力 | API レスポンスを自分で整形 | `--format markdown` でスターバッジ付き Markdown 出力 |

gh CLI は汎用ツールとして優秀ですが、「awesome-list の Markdown を渡して一括処理」というワークフローは github-curator が得意です。

### GitHub API の制限事項

| 制限 | 詳細 |
|---|---|
| レートリミット | 未認証: 60 回/時、認証済み: 5,000 回/時。`GITHUB_TOKEN` の設定を推奨 |
| プライベートリポジトリ | トークンにスコープがないとアクセス不可 |
| アーカイブ済みリポジトリ | 情報は取得できるが、活発度の判断は別途必要 |
| フォーク元の区別 | フォークかオリジナルかの判定はスター数では不十分な場合がある |

---

A CLI tool for updating star counts, checking broken links, and searching trending repos in awesome-xxx lists.
Pass a Markdown file and it fetches the latest info for all listed repositories.

### How This Differs from gh CLI / GitHub API

The GitHub CLI (`gh`) and REST API can fetch repository info, but they aren't designed for awesome-list maintenance workflows.

| Task | gh CLI / GitHub API | github-curator |
|---|---|---|
| Update star counts in Markdown | Call `gh api` per repo, manually rewrite Markdown | `github-curator update-stars awesome.md` — bulk update + diff report |
| Detect broken links | Script `gh api` checks one by one | `github-curator check-links awesome.md` |
| Search trending repos by topic | `gh search repos --topic slam --sort stars` | `github-curator trending "topic:slam"` with rich table + JSON/Markdown output |
| List statistics summary | Write your own aggregation script | `github-curator stats awesome.md` |
| Periodic star updates | GitHub Actions + custom script | GitHub Actions template included |
| Output in awesome-list format | Format API responses yourself | `--format markdown` with star badges |

gh CLI is a great general-purpose tool; github-curator is specialized for the "pass a Markdown file, process all repos" workflow.

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

Awesome リストの Markdown ファイル内のスター数バッジを更新します。

Update star count badges for all repos in an awesome-list markdown file:

```bash
github-curator update-stars awesome-robotics.md
github-curator update-stars awesome-robotics.md --dry-run  # 変更を確認のみ / preview only
```

### トレンドリポジトリ検索 / Trending Repos

GitHub 上のリポジトリをトピック・言語で検索します。

Search for trending repositories by topic or language:

```bash
github-curator trending "topic:robotics language:python"
github-curator trending "topic:llm" --sort stars --max 50
github-curator trending "topic:ros2" --output json
github-curator trending "topic:slam" --output markdown
```

### リンク切れチェック / Check Links

Markdown ファイル内の GitHub リンクが有効か検証します。

Verify all GitHub links in a markdown file are still alive:

```bash
github-curator check-links awesome-robotics.md
```

### エクスポート / Export

リポジトリ情報を JSON または Markdown 形式でエクスポートします。

Export repository data from a markdown file:

```bash
github-curator export awesome-robotics.md --format json --output repos.json
github-curator export awesome-robotics.md --format markdown --output repos.md
```

### 実行サンプル / Examples

#### トレンドリポジトリ検索 / Trending Repos

```
$ github-curator trending "topic:slam" --max 5
Searching: topic:slam (sort=stars, max=5)
                              GitHub Repositories
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┓
┃ Repository                         ┃  Stars ┃ Forks ┃ Language ┃ Updated  ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━┩
│ AtsushiSakai/PythonRobotics        │ 28,909 │ 7,239 │ Python   │ 2026-03  │
│ cartographer-project/cartographer  │  7,801 │ 2,328 │ C++      │ 2026-03  │
│ gaoxiang12/slambook                │  7,372 │ 3,317 │ C++      │ 2026-03  │
└────────────────────────────────────┴────────┴───────┴──────────┴──────────┘
```

#### 言語フィルタ付きトレンド / Trending with Language Filter

```
$ github-curator trending "topic:robotics" --language python --max 5
Searching: topic:robotics language:python (sort=stars, max=5)
                              GitHub Repositories
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┓
┃ Repository                  ┃  Stars ┃  Forks ┃ Language ┃ Updated  ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━┩
│ commaai/openpilot           │ 60,362 │ 10,714 │ Python   │ 2026-03  │
│ AtsushiSakai/PythonRobotics │ 28,909 │  7,239 │ Python   │ 2026-03  │
│ zauberzeug/nicegui          │ 15,524 │    910 │ Python   │ 2026-03  │
│ DLR-RM/stable-baselines3    │ 12,920 │  2,090 │ Python   │ 2026-03  │
│ kornia/kornia               │ 11,120 │  1,162 │ Python   │ 2026-03  │
└─────────────────────────────┴────────┴────────┴──────────┴──────────┘
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
