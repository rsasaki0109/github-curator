# github-curator

[![PyPI](https://img.shields.io/pypi/v/github-curator)](https://pypi.org/project/github-curator/)
[![Python](https://img.shields.io/pypi/pyversions/github-curator)](https://pypi.org/project/github-curator/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

GitHub リポジトリの追跡・キュレーション CLI ツール。
Awesome リストのスター数更新、トレンドリポジトリ検索、リンク切れチェックなどを行います。

姉妹プロジェクト [arxiv-curator](https://github.com/rsasaki0109/arxiv-curator) と組み合わせることで、論文とリポジトリの両方を統合管理できます。データ形式（JSON エクスポート）は相互運用可能です。

---

A CLI tool for tracking and curating GitHub repositories.
Update star counts in awesome lists, search trending repos, check for broken links, and export data.

Works alongside the companion project [arxiv-curator](https://github.com/rsasaki0109/arxiv-curator) for unified paper + repository management. Both tools share compatible JSON export formats.

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
