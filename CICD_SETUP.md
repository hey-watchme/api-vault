# WatchMe Vault API - CI/CD セットアップ手順書

このドキュメントは、Vault APIのCI/CD環境を初回セットアップするための手順書です。

---

## 📋 目次

1. [前提条件](#前提条件)
2. [必要なGitHub Secrets](#必要なgithub-secrets)
3. [初回セットアップ手順](#初回セットアップ手順)
4. [デプロイ実行](#デプロイ実行)
5. [動作確認](#動作確認)
6. [トラブルシューティング](#トラブルシューティング)

---

## 前提条件

### 環境情報
- **ECRリポジトリ名**: `watchme-api-vault`
- **EC2ディレクトリ**: `/home/ubuntu/watchme-vault-api`
- **ポート番号**: `8000`
- **コンテナ名**: `watchme-vault-api`
- **本番URL**: `https://api.hey-watch.me/vault/`

### 必要なツール
- AWS CLI（ECRリポジトリ作成用）
- SSH鍵（`~/watchme-key.pem`）

---

## 必要なGitHub Secrets

以下のSecretsがGitHubリポジトリに設定されていることを確認してください。

**Settings > Secrets and variables > Actions** で設定：

| Secret名 | 説明 | 例 |
|---------|------|-----|
| `AWS_ACCESS_KEY_ID` | AWSアクセスキーID | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | AWSシークレットアクセスキー | `wJalrXUtn...` |
| `EC2_HOST` | EC2のIPアドレス | `3.24.16.82` |
| `EC2_SSH_PRIVATE_KEY` | SSH秘密鍵の内容全体 | `-----BEGIN...` |
| `EC2_USER` | SSHユーザー名 | `ubuntu` |
| `SUPABASE_URL` | Supabase プロジェクトURL | `https://xxx.supabase.co` |
| `SUPABASE_KEY` | Supabase サービスロールキー | `eyJhbGci...` |
| `S3_BUCKET_NAME` | S3バケット名 | `watchme-vault` |

---

## 初回セットアップ手順

### ステップ1: ECRリポジトリの作成

まず、AWS ECRにDockerイメージ用のリポジトリを作成します。

```bash
# AWS CLIでECRリポジトリを作成
aws ecr create-repository \
  --repository-name watchme-api-vault \
  --region ap-southeast-2 \
  --image-scanning-configuration scanOnPush=true
```

**確認方法**:
```bash
aws ecr describe-repositories \
  --repository-names watchme-api-vault \
  --region ap-southeast-2
```

---

### ステップ2: EC2サーバーの準備

EC2サーバーにSSH接続して、アプリケーション用のディレクトリを作成します。

```bash
# EC2に接続
ssh -i ~/watchme-key.pem ubuntu@3.24.16.82

# アプリケーション用ディレクトリ作成
mkdir -p /home/ubuntu/watchme-vault-api

# Dockerネットワークの確認/作成
docker network create watchme-network 2>/dev/null || true

# ディレクトリが作成されたことを確認
ls -la /home/ubuntu/watchme-vault-api

# ログアウト
exit
```

---

### ステップ3: GitHub Secretsの設定

GitHubリポジトリのSettings画面で、上記の必要なSecretsをすべて設定します。

**設定場所**:
`https://github.com/{organization}/vault/settings/secrets/actions`

**⚠️ 重要**:
- `EC2_SSH_PRIVATE_KEY` は秘密鍵ファイルの**内容全体**をコピー＆ペーストしてください
- `-----BEGIN OPENSSH PRIVATE KEY-----` から `-----END OPENSSH PRIVATE KEY-----` まで全て含める

---

### ステップ4: 初回セットアップ完了チェックリスト

以下をすべて確認してください：

- [ ] ECRリポジトリ `watchme-api-vault` が作成されている
- [ ] EC2上に `/home/ubuntu/watchme-vault-api` ディレクトリが作成されている
- [ ] GitHub Secretsが8つすべて設定されている
- [ ] Dockerネットワーク `watchme-network` が存在する
- [ ] SSH鍵でEC2に接続できる

---

## デプロイ実行

### 初回デプロイ

すべてのセットアップが完了したら、以下のコマンドでCI/CDパイプラインを起動します。

```bash
cd /Users/kaya.matsumoto/projects/watchme/api/vault

# すべてのファイルをコミット＆プッシュ
git add .github/workflows/deploy-to-ecr.yml docker-compose.prod.yml run-prod.sh
git commit -m "Add CI/CD configuration for Vault API"
git push origin main
```

### GitHub Actionsの確認

GitHub Actionsの実行を確認：
```
https://github.com/{organization}/vault/actions
```

**成功した場合**:
- ✅ `Build and Push to ECR` ジョブが成功
- ✅ `Deploy to EC2` ジョブが成功
- ✅ ヘルスチェックが通過

**失敗した場合**:
- ログを確認してエラーメッセージを特定
- [トラブルシューティング](#トラブルシューティング)セクションを参照

---

## 動作確認

### EC2での確認

```bash
# EC2にSSH接続
ssh -i ~/watchme-key.pem ubuntu@3.24.16.82

# コンテナが起動しているか確認
docker ps | grep watchme-vault-api

# ヘルスチェック
curl http://localhost:8000/health | python3 -m json.tool

# ログ確認
docker logs watchme-vault-api --tail 100
```

### 期待される出力

**コンテナステータス**:
```
CONTAINER ID   IMAGE                                                                    STATUS         PORTS
abc123def456   754724220380.dkr.ecr.ap-southeast-2.amazonaws.com/watchme-api-vault:latest   Up 2 minutes   127.0.0.1:8000->8000/tcp
```

**ヘルスチェック**:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-25T12:34:56.789Z",
  "s3_configured": true,
  "supabase_configured": true
}
```

### 本番環境での確認

```bash
# ローカルマシンから本番URLにアクセス
curl https://api.hey-watch.me/vault/health | python3 -m json.tool
```

---

## トラブルシューティング

### 1. ECRログインエラー

**症状**:
```
Error: Cannot perform an interactive login from a non TTY device
```

**解決方法**:
- GitHub SecretsのAWS認証情報が正しいか確認
- IAMユーザーにECR権限があるか確認

---

### 2. コンテナが起動しない

**症状**:
```
⚠️ Container not found
```

**診断手順**:
```bash
# EC2にSSH接続
ssh -i ~/watchme-key.pem ubuntu@3.24.16.82

# ログ確認
docker logs watchme-vault-api --tail 100

# 環境変数ファイル確認
cat /home/ubuntu/watchme-vault-api/.env
```

**よくある原因**:
- `.env`ファイルに必須環境変数が不足
- S3バケット名が間違っている
- Supabaseの認証情報が間違っている

---

### 3. ヘルスチェック失敗

**症状**:
```
❌ Health check failed
```

**診断手順**:
```bash
# EC2にSSH接続
ssh -i ~/watchme-key.pem ubuntu@3.24.16.82

# コンテナログ確認
docker logs watchme-vault-api --tail 100

# ローカルでヘルスチェック実行
curl -v http://localhost:8000/health
```

**よくある原因**:
- コンテナが起動中（待機時間を延ばす）
- ポート8000が別のプロセスに使用されている
- アプリケーションコードにエラーがある

---

### 4. GitHub Actionsが失敗する

**診断手順**:
1. GitHub Actionsのログでどのステップでエラーが出ているか確認
2. エラーメッセージを読む
3. 該当するトラブルシューティングセクションを参照

**よくあるエラー**:
- `Permission denied (publickey)` → `EC2_SSH_PRIVATE_KEY`の設定を確認
- `repository does not exist` → ECRリポジトリが作成されているか確認
- `No such file or directory` → EC2のディレクトリが作成されているか確認

---

## 2回目以降のデプロイ

初回セットアップが完了した後は、以下のコマンドだけで自動デプロイされます。

```bash
# コードを修正
git add .
git commit -m "Update Vault API"
git push origin main

# GitHub Actionsが自動的にデプロイを実行
```

---

## 参考資料

- [CI/CD標準仕様書](/Users/kaya.matsumoto/projects/watchme/server-configs/docs/CICD_STANDARD_SPECIFICATION.md)
- [参考実装: behavior-analysis/aggregator](../behavior-analysis/aggregator/.github/workflows/deploy-to-ecr.yml)
- [GitHub Actions ドキュメント](https://docs.github.com/en/actions)
- [AWS ECR ドキュメント](https://docs.aws.amazon.com/ecr/)

---

## サポート

問題が解決しない場合は、以下を確認してください：

1. CI/CD標準仕様書の該当セクション
2. 参考実装のコード
3. GitHub ActionsとEC2のログ
4. 環境変数とSecrets設定

それでも解決しない場合は、エラーメッセージとログを持ってサポートに連絡してください。
