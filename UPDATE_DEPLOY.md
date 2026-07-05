# SourceTreeを使った修正反映手順

この手順書は、ローカルPCで修正した内容をSourceTreeで管理し、
GitHubの`main`ブランチを経由して、さくらのVPSへ反映するためのものです。

本番環境は次の流れで更新します。

```text
ローカル develop
  → GitHub origin/develop
  → SourceTreeでmainへマージ
  → GitHub origin/main
  → VPSのmainへpull
```

`develop`は開発用、`main`は公開用です。VPSは必ず`main`から更新します。
`.env`、`db.sqlite3`、`media`はGit管理外なので、通常の`git pull`では
本番の秘密鍵、問い合わせ、お知らせ、投稿画像を上書きしません。

## 本番DB・投稿データの扱い

初回公開後は、VPS上の`/srv/nishimuraya/app/db.sqlite3`を正として運用します。
スタッフ画面で追加・編集したお知らせ、受信した問い合わせ、管理ユーザーは
すべてこの本番DBへ保存されます。

次の通常更新処理では、本番DBの内容は消えません。

```text
SourceTreeでのコミット・プッシュ
git fetch
git pull
pip install
collectstatic
Gunicornの再起動
```

これらはコード、ライブラリ、静的ファイル、実行プロセスを更新する処理であり、
Git管理外の`db.sqlite3`や`media`を置き換えないためです。

`migrate`は既存データを残したまま、必要なテーブルや列を追加・変更します。
ただし、モデル削除、列削除、独自データ移行を含むマイグレーションには
データ変更の可能性があります。そのため、VPS更新前には必ず
`nishimuraya-backup.service`を成功させてから`migrate`を実行します。

初回公開時に行ったローカルPCからVPSへの`db.sqlite3`転送は、今後は行いません。
再転送すると、公開後に追加された問い合わせやお知らせを古いローカルDBで
上書きするためです。

VPSを再構築する場合は、ローカルの開発DBではなく、
`/var/backups/nishimuraya`から取得した最新の本番バックアップを復元します。
投稿画像も同じ時刻の`media-日時.tar.gz`から復元します。

更新中に管理画面や問い合わせ送信が行われる可能性を減らすため、
反映作業はアクセスの少ない時間帯に実施します。Gunicorn再起動時には
数秒程度、処理中のリクエストへ影響する可能性があります。

## 1. 修正を始める前の準備

SourceTreeでリポジトリを開き、現在のブランチが`develop`であることを確認します。
`main`になっている場合は、左側の「ブランチ」にある`develop`をダブルクリックして
チェックアウトします。

次に、SourceTree上部の「プル」をクリックし、リモートを`origin`、
対象ブランチを`develop`として最新状態を取得します。

作業前にプルするのは、GitHub側の変更と古いローカルコードが食い違った状態で
修正を始めないためです。

## 2. ローカルで修正・検証

修正後、Windows PowerShellでプロジェクトへ移動します。

```powershell
Set-Location "E:\tonomura-project\nishimuraya"
$python = "C:\Users\Owner\AppData\Local\Programs\Python\Python314\python.exe"
```

以降のコマンドをプロジェクト直下で実行するための準備です。
`$python`には、このPCでPipenvを実行できるPythonの場所を設定しています。

通常の修正では、次の検査とテストを実行します。

```powershell
$env:PYTHONUTF8 = "1"
& $python -m pipenv run python manage.py check
& $python -m pipenv run python manage.py test
```

`check`はDjango設定やモデル定義の問題を検出し、`test`は既存機能が
修正によって壊れていないかを確認します。両方成功してからコミットします。

### モデルを変更した場合

`models`配下を変更した場合は、マイグレーションを生成してから再度テストします。

```powershell
& $python -m pipenv run python manage.py makemigrations
& $python -m pipenv run python manage.py test
```

マイグレーションは、Pythonのモデル変更を本番SQLiteの構造へ反映するための
履歴ファイルです。生成された`migrations`配下のファイルもコミット対象です。

### Tailwind CSSの元ファイルを変更した場合

`static/tailwind/style.src.css`やTailwindクラスを変更した場合は、CSSを再生成します。

```powershell
& $python -m pipenv run python manage.py tailwind build
```

この処理で本番配信用の`static/css/style.css`が更新されます。
生成されたCSSもコミット対象です。

## 3. SourceTreeでdevelopへコミット

SourceTreeの「ファイルステータス」を開き、次の順で操作します。

1. 「作業ツリーのファイル」で差分を1ファイルずつ確認する
2. 今回変更したファイルだけを「ステージ済みファイル」へ移す
3. コミットメッセージに変更目的を日本語で記載する
4. 「コミット」をクリックする
5. 上部の「プッシュ」をクリックする
6. リモート`origin`の`develop`を選択してプッシュする

コミットメッセージは「トップページの営業時間を変更」のように、
何を目的として変更したかが分かる内容にします。

次のファイルやディレクトリは、秘密情報または本番データなのでコミットしません。

```text
.env
db.sqlite3
.db-backups/
media/
staticfiles/
backups/
```

これらは`.gitignore`で除外されています。SourceTreeに表示された場合は
ステージせず、原因を確認してください。

## 4. SourceTreeでdevelopをmainへ統合

`develop`へのプッシュ後、公開用の`main`へ統合します。

1. SourceTreeで`main`をダブルクリックしてチェックアウトする
2. 上部の「プル」で`origin/main`を取得する
3. 左側の`develop`を右クリックする
4. 「現在のブランチにdevelopをマージ」を選択する
5. 競合がないことを確認する
6. PowerShellでテストをもう一度実行する
7. SourceTree上部の「プッシュ」をクリックする
8. リモート`origin`の`main`を選択してプッシュする

マージ後のテストには、次を使います。

```powershell
Set-Location "E:\tonomura-project\nishimuraya"
$python = "C:\Users\Owner\AppData\Local\Programs\Python\Python314\python.exe"
$env:PYTHONUTF8 = "1"
& $python -m pipenv run python manage.py test
```

VPSが取得する最終的な`main`でテストするためです。
テスト成功後に`main`をプッシュしてください。

SourceTreeのプッシュ画面では「強制プッシュ」を使用しません。
プッシュ後は、SourceTreeのログ上で`main`と`origin/main`が同じ最新コミットを
指していることを確認します。

必要に応じて、最後に`develop`へ戻して次回の修正に備えます。

## 5. VPSへ反映

Windows PowerShellからVPSへログインします。

```powershell
ssh ubuntu@133.167.125.134
```

VPSの管理ユーザーとして接続するコマンドです。パスワードや秘密鍵は
チャット、Git、スクリーンショットへ記載しないでください。

ログイン後、VPSで次を実行します。

```bash
cd /srv/nishimuraya/app

git status --short
sudo systemctl start nishimuraya-backup.service

git fetch origin
git pull --ff-only origin main

.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py check --deploy

sudo systemctl restart nishimuraya
sudo systemctl status nishimuraya --no-pager
```

各コマンドの意味は次のとおりです。

- `git status --short`：VPS上に意図しないコード変更がないか確認
- `nishimuraya-backup.service`：更新前のSQLiteと投稿画像を保存
- `git fetch`、`git pull`：GitHubの最新`main`を取得
- `pip install`：追加・更新されたPythonライブラリを反映
- `migrate`：データベース構造を更新
- `collectstatic`：CSS、JavaScript、固定画像を本番配信用領域へ収集
- `check --deploy`：本番向けセキュリティ設定を検査
- `systemctl restart`：新しいコードでGunicornを再起動

最初の`git status --short`で何か表示された場合は、`git pull`を実行せず、
表示内容を確認してください。本番サーバー上の変更を消す操作は行いません。

`check --deploy`では、HSTSの全サブドメイン適用とpreloadを意図的に
無効にしているため、`security.W005`と`security.W021`の2警告は想定内です。

## 6. 公開確認

VPSで次を実行します。

```bash
curl -I https://nishimuraya-soga.com/
sudo journalctl -u nishimuraya -n 50 --no-pager
```

`curl`で`HTTP/1.1 200 OK`が返れば、トップページは正常です。
`journalctl`ではGunicornの起動エラーやDjangoの例外がないか確認します。

ブラウザーでも次を確認します。

- トップページ
- 修正したページ
- お知らせ一覧と画像
- 問い合わせ画面
- スタッフログイン画面
- スマートフォン表示

## 7. 変更内容別の追加作業

| 変更内容 | 通常手順以外に必要な作業 |
| --- | --- |
| HTML・Python・フォーム | なし。通常手順で反映 |
| CSS・JavaScript・固定画像 | `collectstatic`が必要。通常手順に含まれる |
| `requirements.txt` | `pip install`が必要。通常手順に含まれる |
| モデル・マイグレーション | `migrate`が必要。通常手順に含まれる |
| `.env`の設定項目 | VPSの`.env`を手動編集し、Gunicornを再起動 |
| Gunicornのsystemd設定 | serviceファイルを再配置し、systemdを再読み込み |
| バックアップ設定 | service/timerを再配置し、systemdを再読み込み |
| Nginx設定 | Certbot設定を維持しながら手動反映し、構文検査 |

### systemd設定を変更した場合

`deploy/nishimuraya.service`を変更した場合だけ実行します。

```bash
cd /srv/nishimuraya/app
sudo cp deploy/nishimuraya.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart nishimuraya
```

リポジトリのserviceファイルをsystemdへ再登録し、新しい起動条件で
Gunicornを再起動します。

バックアップ設定を変更した場合は、次を実行します。

```bash
cd /srv/nishimuraya/app
sudo cp deploy/nishimuraya-backup.service /etc/systemd/system/
sudo cp deploy/nishimuraya-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart nishimuraya-backup.timer
```

日次バックアップの処理内容や実行時刻をsystemdへ再登録します。

### Nginx設定を変更した場合

初回公開後の`/etc/nginx/sites-available/nishimuraya`には、Certbotが追加した
HTTPS証明書設定が含まれています。

`deploy/nginx.conf.example`をそのままコピーすると、CertbotのHTTPS設定を
上書きしてサイトへ接続できなくなる可能性があります。通常更新ではコピーしません。

Nginx変更が必要な場合は、VPS上の現在の設定へ必要箇所だけを手動反映し、
次を実行します。

```bash
sudo nginx -t
sudo systemctl reload nginx
```

`nginx -t`で構文が正しいことを確認してから再読み込みするため、
設定ミスによるWebサーバー停止を防げます。

## 8. 更新に失敗した場合

まずVPSで状態とログを確認します。

```bash
sudo systemctl status nishimuraya --no-pager
sudo journalctl -u nishimuraya -n 100 --no-pager
sudo nginx -t
sudo tail -n 100 /var/log/nginx/error.log
```

Gunicorn、Django、Nginxのどこで失敗したかを切り分けるコマンドです。
ログを共有するときは、パスワード、秘密鍵、`.env`、問い合わせ内容を伏せます。

コードを元へ戻す場合は、SourceTreeの`main`のログから問題のコミットを選び、
右クリックして「コミットを打ち消す」を使用します。その打ち消しコミットを
`main`へプッシュし、VPSで通常の更新手順をもう一度実行します。

履歴を書き換えるresetや強制プッシュは使用しません。

モデル変更やマイグレーション後にDBを戻す必要がある場合は、コードだけを
打ち消してもDB構造は自動では元に戻りません。更新前バックアップの復元が
必要になる可能性があるため、自己判断でマイグレーションを逆実行せず、
バックアップの時刻とエラー内容を確認してから対応します。

## 9. 更新完了チェックリスト

- SourceTreeで`develop`へコミット・プッシュした
- SourceTreeで`develop`を`main`へマージした
- ローカルテストが成功した
- `origin/main`へプッシュした
- VPS更新前バックアップが成功した
- VPSの`git pull --ff-only origin main`が成功した
- `migrate`と`collectstatic`が成功した
- Gunicornが`active (running)`になった
- 本番URLが`200 OK`になった
- ブラウザーで修正内容を確認した
