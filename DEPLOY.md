# さくらのVPSへの公開手順

この手順は、契約済みのさくらのVPS「大阪第3・1GB」と標準OS
「Ubuntu 24.04 amd64」、ログインユーザー`ubuntu`、
配置先 `/srv/nishimuraya/app` を前提とします。

構成は「お名前.comのDNS → Nginx → Gunicorn → Django → SQLite」です。
NginxがHTTPS、静的ファイル、投稿画像を担当し、GunicornがDjangoを実行します。

## 0. 事前に控える情報

- ドメイン名：`nishimuraya-soga.com`
- VPSのIPv4アドレス
- VPSの`ubuntu`ユーザーのパスワードまたはSSH秘密鍵
- 公開するGitブランチ（現在の最新版は`develop`）

以降の`VPS_IP_ADDRESS`だけは、さくらのVPSコントロールパネルに表示される
実際のIPv4アドレスへ置き換えてください。

## 1. VPSのネットワーク設定

さくらのVPSコントロールパネルのパケットフィルターで、TCPの22、80、443を
許可します。22番は、可能なら管理に使う接続元IPだけに制限してください。

それぞれSSH、HTTP、HTTPSに必要なポートです。それ以外を閉じることで、
公開サーバーへの不要な接続を減らします。

## 2. VPSへログインして基本ソフトを導入

Windows PowerShellから接続します。

```powershell
ssh ubuntu@VPS_IP_ADDRESS
```

このコマンドは、VPSの標準管理ユーザー`ubuntu`としてSSH接続します。

VPS上で次を実行します。

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git nginx python3-venv snapd
sudo timedatectl set-timezone Asia/Tokyo
```

OSを更新し、Git、Nginx、Python仮想環境、Certbotの導入に使うSnapを
インストールします。タイムゾーンはバックアップ時刻とログを日本時間に揃えるためです。

## 3. アプリケーションを配置

```bash
sudo install -d -o ubuntu -g www-data -m 0750 /srv/nishimuraya
git clone -b develop \
  https://github.com/norikkun/nishimuraya_soga.git \
  /srv/nishimuraya/app
cd /srv/nishimuraya/app
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

`/srv/nishimuraya/app`へ最新版の`develop`ブランチを配置し、アプリ専用の
Python環境へ依存パッケージを導入します。本番ブランチを`main`へ統合した後は、
`-b develop`を`-b main`へ変更してください。

## 4. 本番環境変数を設定

まず秘密鍵を生成します。

```bash
.venv/bin/python -c "from secrets import token_urlsafe; print(token_urlsafe(64))"
```

表示されたランダム文字列は、Djangoの署名処理に使う秘密鍵です。
Gitやチャットへ貼らず、次の`.env`だけへ保存します。

```bash
cp deploy/.env.production.example .env
nano .env
chmod 0600 .env
```

テンプレートをコピーし、`DJANGO_SECRET_KEY`を生成した値へ変更します。
ドメイン名はすでに`nishimuraya-soga.com`へ設定済みです。
`chmod 0600`は`.env`を所有者以外から読めないようにします。

HTTPS設定が完了するまでIPアドレスで動作確認したい場合は、一時的に
`DJANGO_SECURE_SSL_REDIRECT=False`へ変更します。公開前に必ず`True`へ戻します。

## 5. 既存データを移す

現在のローカルSQLiteを引き継ぐ場合は、開発サーバーを停止してから
Windows PowerShellで実行します。

```powershell
scp E:\tonomura-project\nishimuraya\db.sqlite3 ubuntu@VPS_IP_ADDRESS:/tmp/nishimuraya-db.sqlite3
```

SQLiteファイルにはお知らせ、問い合わせ、管理ユーザーが入っているため、
GitではなくSSHで直接転送します。

VPS上で次を実行します。

```bash
cd /srv/nishimuraya/app
mv /tmp/nishimuraya-db.sqlite3 db.sqlite3
chmod 0600 db.sqlite3
mkdir -p media
cp -a static/img/news media/
```

データベースをアプリへ配置し、既存のお知らせ画像を新しい`media/news`へ
コピーします。`media`は投稿データ専用で、今後のGit更新や`collectstatic`から
分離されます。

既存データを使わず新規作成する場合、この転送とコピーは省略できます。

## 6. Djangoの初期処理

```bash
cd /srv/nishimuraya/app
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py check --deploy
```

データベースを最新構造へ更新し、Nginxが配信する静的ファイルを
`staticfiles`へ集約し、本番向けセキュリティ設定を検査します。
初期公開では、HSTSの全サブドメイン適用とブラウザーへのプリロード登録を
意図的に無効にしているため、`security.W005`と`security.W021`の2警告は残ります。
これは未使用のサブドメインまで後戻りできないHTTPS制約をかけないためです。

新しいデータベースを作った場合だけ、管理ユーザーを作成します。

```bash
.venv/bin/python manage.py createsuperuser
```

このユーザーはお知らせと問い合わせの管理画面へログインするために使います。
推測されにくい固有パスワードを設定してください。

## 7. Gunicornを常時起動

```bash
sudo cp deploy/nishimuraya.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now nishimuraya
sudo systemctl status nishimuraya --no-pager
```

systemdへDjangoの実行サービスを登録します。OS再起動後も自動起動し、
異常終了した場合は再起動します。

## 8. Nginxを設定

```bash
sudo cp deploy/nginx.conf.example /etc/nginx/sites-available/nishimuraya
sudo nano /etc/nginx/sites-available/nishimuraya
sudo ln -s /etc/nginx/sites-available/nishimuraya /etc/nginx/sites-enabled/nishimuraya
sudo nginx -t
sudo systemctl reload nginx
```

設定例には`nishimuraya-soga.com`と`www.nishimuraya-soga.com`を設定済みです。
`nginx -t`が成功した場合だけ再読み込みすることで、設定ミスによる停止を防ぎます。

## 9. お名前.comのDNSを設定

2026年7月5日時点では、次のDNS設定になっています。

- ネームサーバー：`ns-rs1.gmoserver.jp`、`ns-rs2.gmoserver.jp`
- Web用Aレコード：`nishimuraya-soga.com`と`www`の両方が`157.120.209.58`
- MXレコード：`mail1036.onamae.ne.jp`
- TXTレコード：`v=spf1 include:_spf.onamae.ne.jp ~all`

このネームサーバー構成では、お名前.comのレンタルサーバー
コントロールパネルからDNSレコードを編集します。ネームサーバー自体は変更せず、
次のAレコード2件の値だけをVPSのIPv4アドレスへ変更してください。

| ホスト名 | TYPE | VALUE |
| --- | --- | --- |
| 空欄 | A | VPSのIPv4アドレス |
| www | A | VPSのIPv4アドレス |

AレコードはドメインをVPSのIPv4アドレスへ向ける設定です。メールを利用している
場合、既存のMX・TXTレコードはメール配送と送信元認証に必要なので、
値を変更したり削除したりしないでください。
IPv6をVPS側で設定していない場合、AAAAレコードは追加しません。

## 10. HTTPS証明書を取得

DNSがVPSを指すようになってから実行します。

```bash
sudo snap install --classic certbot
sudo certbot --nginx -d nishimuraya-soga.com -d www.nishimuraya-soga.com
sudo certbot renew --dry-run
```

Let's Encryptの証明書を取得し、NginxへHTTPS設定を追加します。
最後のコマンドは自動更新が正常に動くかを試験します。

`.env`の`DJANGO_SECURE_SSL_REDIRECT=True`、
`DJANGO_SECURE_HSTS_SECONDS=3600`を確認してGunicornを再起動します。

```bash
sudo systemctl restart nishimuraya
```

DjangoにもHTTPSを認識させ、HTTPアクセス、セッションCookie、CSRF Cookieを
安全なHTTPS通信へ限定します。

## 11. 毎日バックアップ

```bash
sudo install -d -o ubuntu -g www-data -m 0750 /var/backups/nishimuraya
sudo cp deploy/nishimuraya-backup.service /etc/systemd/system/
sudo cp deploy/nishimuraya-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now nishimuraya-backup.timer
sudo systemctl start nishimuraya-backup.service
sudo systemctl status nishimuraya-backup.service --no-pager
```

SQLiteと`media`を毎日3時30分頃に保存し、14日を超えたバックアップを削除します。
初回は手動実行して、バックアップが実際に作られることを確認します。

```bash
sudo ls -lh /var/backups/nishimuraya
```

この一覧に`db-日時.sqlite3`、`media-日時.tar.gz`、
`SHA256SUMS-日時`があれば、データ、画像、破損検査用ハッシュが作成されています。
VPS自体の障害に備え、このディレクトリは定期的に別のPCやストレージへもコピーしてください。

## 12. 更新時の手順

```bash
cd /srv/nishimuraya/app
sudo systemctl start nishimuraya-backup.service
git pull --ff-only origin develop
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py check --deploy
sudo systemctl restart nishimuraya
sudo systemctl reload nginx
```

更新前にバックアップし、コード、依存パッケージ、DB構造、静的ファイルを
順番に更新します。`--ff-only`はVPS上で意図しないマージコミットが作られるのを防ぎます。

## 13. 問題が起きたときの確認

```bash
sudo systemctl status nishimuraya --no-pager
sudo journalctl -u nishimuraya -n 100 --no-pager
sudo nginx -t
sudo tail -n 100 /var/log/nginx/error.log
```

Gunicornの状態とログ、Nginx設定、Nginxのエラーログを確認します。
VPSのパスワード、`.env`、秘密鍵、問い合わせ内容はログ共有時に伏せてください。
