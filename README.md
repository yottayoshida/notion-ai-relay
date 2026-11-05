# Notion AI Relay

Run Notion agents and skills through MCP.

Notion Custom Agentの設定やNotion Skillsの手順を読み、手元のAIアシスタントがMCPで代行するAgent Skillです。対象ごとの業務手順をこのリポジトリに保存せず、実行時に取得します。

## インストール

[skills CLI](https://github.com/vercel-labs/skills)でインストールできます。

```bash
npx skills add yottayoshida/notion-ai-relay
```

手動で導入する場合は、このリポジトリを取得し、`notion-ai-relay`フォルダを利用するクライアントのSkillディレクトリへ配置してください。`SKILL.md`と`references/`を一緒に配置します。`agents/openai.yaml`は任意のCodex用表示情報です。

Skillのインストールとは別に、利用するAIアシスタントでNotion MCPを接続してください。実行する仕事が外部サービスを使う場合は、その操作に対応するMCP接続も必要です。

## 使い方

Skillを読み込んだアシスタントに、対象と今回の入力を指定します。

```text
参照できるNotion Custom AgentとNotion Skillsを一覧にして。

指定したCustom Agentの仕事を代行して。
Agent URL: <対象AgentのURL>
今回の入力: <対象ページ、期間、その他の必須入力>

このNotion Skillを使って指定資料を処理して。
Skill URL: <手順ページのURL>
対象資料: <処理する資料のURLまたは本文>

このAgentの処理をドライランして。外部への書き込みはしないで。
Agent URL: <対象AgentのURL>
今回の入力: <処理対象>
```

## 必要な機能と制限

このSkillは、実行環境が公開するMCPツールの説明と引数を確認して、必要な操作に対応付けます。Computer Use、ブラウザ操作、特定OS、自動化APIは必須ではありません。

| 操作 | 必要な情報・機能 |
|---|---|
| Custom Agentの一覧 | Agentを列挙するMCP機能。接続から取得できる範囲を表示します |
| Custom Agentの代行 | 指示本文、対象との対応、今回の処理に必要な設定・入力・MCP操作 |
| Notion Skillの代行 | 手順ページ、必要な参照資料・添付、今回の入力・MCP操作 |
| 定期実行 | 別途用意したスケジューラやイベント受信機能 |

MCP接続によっては、Agent設定全文やNotion Skills一覧を取得できません。その場合は指示ページURLや不足する設定本文を受け取ります。提供された設定を、確認できていない最新公開版と扱うことはありません。登録・有効化状態が取得できなくても、指定された手順本文と必要な入力を読めれば、その範囲で実行できます。

Notion側のAgentやAIを起動して処理を任せる機能は使いません。外部への書き込み・送信には、ユーザーの依頼と実行環境の認可条件を適用します。ドライランでは処理済み状態も更新しません。

このリポジトリは手順を配布するもので、MCPサーバーや常駐プロセスを含みません。クライアントごとのSkill読込方法と利用可能なMCP機能に依存し、全クライアントでの動作を保証するものではありません。

## ファイル

- [SKILL.md](SKILL.md)が対象の選択、設定読取、MCP実行、結果確認の共通手順です。
- [Custom Agentの設定取得](references/read-configuration.md)が一覧・設定・版・再開状態を扱います。
- [Notion Skillsの取得](references/read-skills.md)が手順ページと付属リソースを扱います。
- [MCPでの実行](references/execute-via-mcp.md)がツールへの対応付けと実行結果の検証を扱います。

## ライセンス

[MIT](LICENSE)。個人による非公式プロジェクトです。
