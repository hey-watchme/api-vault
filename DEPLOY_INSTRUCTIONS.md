# 🚀 Vault API - CI/CDデプロイ実施手順

このドキュメントは、**あなた（ユーザー）が実施する必要がある作業**をまとめたものです。

---

## ✅ 現在の状態

以下の作業は**完了済み**です：

- ✅ `.github/workflows/deploy-to-ecr.yml` 作成済み（CI/CDワークフロー）
- ✅ `run-prod.sh` 作成済み（デプロイスクリプト）
- ✅ `docker-compose.prod.yml` 既存（本番用Docker Compose設定）
- ✅ `Dockerfile.prod` 既存（本番用Dockerfile）
- ✅ ECRリポジトリ `watchme-api-vault` 作成済み
- ✅ EC2ディレクトリ `/home/ubuntu/watchme-vault-api` 作成済み
- ✅ Dockerネットワーク `watchme-network` 作成済み

---

## ⚠️ あなたが実施する必要がある作業

### 1️⃣ GitHub Secretsの確認

以下のSecretsがGitHubリポジトリに設定されているか確認してください。

**設定場所**:
```
https://github.com/{organization}/vault/settings/secrets/actions
```

**必要なSecrets**:

| Secret名 | 説明 | 補足 |
|---------|------|------|
| `AWS_ACCESS_KEY_ID` | AWSアクセスキーID | ECRへのアクセスに必要 |
| `AWS_SECRET_ACCESS_KEY` | AWSシークレットアクセスキー | ECRへのアクセスに必要 |
| `EC2_HOST` | EC2のIPアドレス | `3.24.16.82` |
| `EC2_SSH_PRIVATE_KEY` | SSH秘密鍵の内容全体 | `-----BEGIN...` から `-----END...` まで |
| `EC2_USER` | SSHユーザー名 | `ubuntu` |
| `SUPABASE_URL` | Supabase プロジェクトURL | 例: `https://xxx.supabase.co` |
| `SUPABASE_KEY` | Supabase サービスロールキー | 例: `eyJhbGci...` |
| `S3_BUCKET_NAME` | S3バケット名 | 例: `watchme-vault` |

**確認方法**:
- GitHubリポジトリのSettings画面を開く
- 左メニューから「Secrets and variables」→「Actions」を選択
- 上記8つのSecretsが全て設定されているか確認

**⚠️ 注意**:
- `EC2_SSH_PRIVATE_KEY` は秘密鍵ファイルの**内容全体**をコピーしてください
- 他のプロジェクトで既に設定されている場合は、そのまま使用できます

---

### 2️⃣ GitHubへコミット＆プッシュ

新しく作成したCI/CD設定ファイルをGitHubにプッシュします。

```bash
cd /Users/kaya.matsumoto/projects/watchme/api/vault

# Git statusで変更を確認
git status

# 新規ファイルをステージング
git add .github/workflows/deploy-to-ecr.yml
git add run-prod.sh
git add CICD_SETUP.md
git add DEPLOY_INSTRUCTIONS.md

# コミット
git commit -m "feat: Add CI/CD configuration for automated deployment

- Add GitHub Actions workflow for ECR and EC2 deployment
- Add run-prod.sh deployment script
- Add setup documentation"

# プッシュ（CI/CDが自動的に開始されます）
git push origin main
```

**⚠️ 重要**:
- `git push` を実行すると、GitHub Actionsが自動的に起動します
- 初回デプロイは10〜15分程度かかります

---

### 3️⃣ GitHub Actionsの実行確認

GitHubのActions画面でCI/CDの実行状況を確認します。

**確認手順**:

1. GitHubリポジトリを開く
2. 「Actions」タブをクリック
3. 最新のワークフロー実行を確認

**URL例**:
```
https://github.com/{organization}/vault/actions
```

**成功した場合**:
- ✅ `Build and Push to ECR` ジョブが緑色のチェックマーク
- ✅ `Deploy to EC2` ジョブが緑色のチェックマーク
- ✅ ログに「Health check passed」と表示

**失敗した場合**:
- ❌ 赤いバツマークが表示される
- ログを確認してエラーメッセージを特定
- [トラブルシューティング](#トラブルシューティング)セクションを参照

---

### 4️⃣ 動作確認

デプロイが成功したら、以下のコマンドで動作を確認します。

#### EC2での確認

```bash
# EC2にSSH接続
ssh -i ~/watchme-key.pem ubuntu@3.24.16.82

# コンテナが起動しているか確認
docker ps | grep watchme-vault-api

# ヘルスチェック
curl http://localhost:8000/health | python3 -m json.tool

# ログ確認
docker logs watchme-vault-api --tail 50

# ログアウト
exit
```

#### 本番環境での確認

```bash
# ローカルマシンから本番URLにアクセス
curl https://api.hey-watch.me/vault/health | python3 -m json.tool
```

**期待される出力**:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-25T12:34:56.789Z",
  "s3_configured": true,
  "supabase_configured": true
}
```

---

## 🎉 完了後の状態

CI/CDセットアップが完了すると、以下の自動化が実現されます：

1. **自動ビルド**: `git push origin main` すると、自動的にDockerイメージがビルドされます
2. **自動デプロイ**: ビルドされたイメージが自動的にEC2にデプロイされます
3. **自動ヘルスチェック**: デプロイ後に自動的にヘルスチェックが実行されます
4. **ゼロダウンタイム**: 古いコンテナを停止してから新しいコンテナを起動します

---

## 📝 2回目以降のデプロイ

初回セットアップが完了した後は、以下のコマンドだけでデプロイできます。

```bash
# コードを修正
vim app.py

# コミット＆プッシュ（これだけでCI/CDが自動実行されます）
git add .
git commit -m "Update: 修正内容"
git push origin main
```

GitHub Actionsが自動的に：
1. Dockerイメージをビルド
2. ECRにプッシュ
3. EC2にデプロイ
4. ヘルスチェック実行

---

## 🔍 トラブルシューティング

### GitHub Actionsが失敗する

**症状**: Actionsタブで赤いバツマークが表示される

**確認手順**:
1. 失敗したジョブをクリック
2. ログを読んでエラーメッセージを特定
3. 以下のよくあるエラーを確認

**よくあるエラー**:

| エラーメッセージ | 原因 | 解決方法 |
|---------------|------|---------|
| `Permission denied (publickey)` | SSH鍵が正しくない | `EC2_SSH_PRIVATE_KEY` の設定を確認 |
| `repository does not exist` | ECRリポジトリがない | ECRリポジトリを作成 |
| `No such file or directory` | EC2のディレクトリがない | EC2でディレクトリを作成 |
| `Error response from daemon: pull access denied` | ECRログインエラー | AWS認証情報を確認 |

---

### コンテナが起動しない

**症状**: `docker ps` でコンテナが表示されない

**診断手順**:
```bash
# EC2にSSH接続
ssh -i ~/watchme-key.pem ubuntu@3.24.16.82

# ログ確認
docker logs watchme-vault-api --tail 100

# 環境変数ファイル確認
cat /home/ubuntu/watchme-vault-api/.env

# コンテナの全状態確認
docker ps -a | grep watchme-vault-api
```

**よくある原因**:
- `.env`ファイルに必須環境変数が不足している
- S3バケット名が間違っている
- Supabaseの認証情報が間違っている
- ポート8000が既に使用されている

---

### ヘルスチェックが失敗する

**症状**: `curl http://localhost:8000/health` が失敗する

**診断手順**:
```bash
# EC2にSSH接続
ssh -i ~/watchme-key.pem ubuntu@3.24.16.82

# ログ確認
docker logs watchme-vault-api --tail 100

# ローカルでヘルスチェック実行
curl -v http://localhost:8000/health
```

**よくある原因**:
- アプリケーションがまだ起動中（待機時間を延ばす）
- 環境変数が正しく設定されていない
- S3またはSupabaseへの接続エラー

---

## 📚 参考資料

- [CI/CD詳細セットアップ手順](./CICD_SETUP.md)
- [CI/CD標準仕様書](/Users/kaya.matsumoto/projects/watchme/server-configs/docs/CICD_STANDARD_SPECIFICATION.md)
- [参考実装: behavior-analysis/aggregator](../behavior-analysis/aggregator/.github/workflows/deploy-to-ecr.yml)

---

## ❓ 質問・サポート

問題が解決しない場合は、以下の情報を含めて相談してください：

1. GitHub Actionsのログ（スクリーンショット）
2. EC2のコンテナログ（`docker logs watchme-vault-api --tail 100`）
3. エラーメッセージの全文
4. 実行したコマンドとその結果
