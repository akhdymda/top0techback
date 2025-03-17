# Githubリポジトリの初期化→プッシュまで

## 1. カレントディレクトリをGitリポジトリとして初期化
git init

## 2. ファイルをステージングエリアに追加
git add .

## 3. 初期コミットを作成
git commit -m "Initial commit"

## 4. リモートリポジトリのURLを追加（URLは実際のものに置き換えてください）
git remote add origin your-repository-url

## 5. ローカルのmainブランチをリモートにプッシュ
git push -u origin main


## 環境変数備忘
SCM_DO_BUILD_DURING_DEPLOYMENT:1
