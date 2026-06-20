#!/bin/bash
cd "$(dirname "$0")"

echo "=========================================="
echo "  サロン LINE Bot を起動しています..."
echo "=========================================="

source venv/bin/activate

# 既存プロセスを停止
pkill -f "python3 app.py" 2>/dev/null
sleep 1

# Flaskサーバーをバックグラウンドで起動
python3 app.py &
SERVER_PID=$!
echo "✅ サーバー起動完了"
sleep 2

echo ""
echo "🌐 外部URLを取得中（10秒ほど待ってください）..."
echo ""

# localhost.run でトンネル開通（サインアップ不要）
# 実際のトンネルURLは「xxxxx.localhost.run」の形式
ssh -o StrictHostKeyChecking=no \
    -o LogLevel=ERROR \
    -R 80:localhost:8080 \
    nokey@localhost.run 2>&1 | tee /tmp/tunnel_output.txt | while IFS= read -r line; do
    echo "$line"
    # サブドメイン付きのURLだけを取得（docs URLは除外）
    TUNNEL=$(echo "$line" | grep -oE 'https://[a-zA-Z0-9_-]+\.localhost\.run' | head -1)
    if [ -n "$TUNNEL" ]; then
        echo ""
        echo "=========================================="
        echo "  ✅ 起動完了！"
        echo ""
        echo "  📋 LINEに登録するWebhook URL："
        echo "  ${TUNNEL}/webhook"
        echo ""
        echo "  ⚠️ このURLをコピーして"
        echo "     LINE DevelopersのWebhook URLに"
        echo "     貼り付けてください"
        echo "=========================================="
    fi
done

wait $SERVER_PID
