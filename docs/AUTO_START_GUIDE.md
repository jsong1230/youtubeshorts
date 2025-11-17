# 자동 업로드 설정 가이드

## 방법 1: 터미널에서 직접 실행 (간단)

```bash
# 백그라운드에서 실행
nohup python main.py schedule > output/bot.log 2>&1 &

# 프로세스 확인
ps aux | grep "main.py schedule"

# 종료하려면
pkill -f "main.py schedule"
```

## 방법 2: macOS LaunchAgent 사용 (권장, 재부팅 후에도 자동 시작)

### 1. LaunchAgent 파일 복사
```bash
cp com.youtubeshorts.bot.plist ~/Library/LaunchAgents/
```

### 2. LaunchAgent 로드
```bash
launchctl load ~/Library/LaunchAgents/com.youtubeshorts.bot.plist
```

### 3. 상태 확인
```bash
launchctl list | grep youtubeshorts
```

### 4. 중지하려면
```bash
launchctl unload ~/Library/LaunchAgents/com.youtubeshorts.bot.plist
```

### 5. 로그 확인
```bash
tail -f output/bot.log
tail -f output/bot_error.log
```

## 방법 3: screen 또는 tmux 사용

```bash
# screen 사용
screen -S youtubeshorts
python main.py schedule
# Ctrl+A, D로 분리

# 다시 접속
screen -r youtubeshorts

# tmux 사용
tmux new -s youtubeshorts
python main.py schedule
# Ctrl+B, D로 분리

# 다시 접속
tmux attach -t youtubeshorts
```

## 업로드 시간 변경

`.env` 파일에서 설정:
```
UPLOAD_SCHEDULE_TIME=09:00  # 기본 시작 시간 (4시간 간격으로 6번 업로드)
UPLOAD_TIMEZONE=Asia/Seoul
```

**참고**: 
- 기본 시작 시간에서 4시간 간격으로 총 6번 자동 업로드됩니다
- 예: `UPLOAD_SCHEDULE_TIME=09:00`이면 → 09:00, 13:00, 17:00, 21:00, 01:00, 05:00에 업로드
- YouTube Shorts는 하루에 최대 6개까지 업로드 가능합니다

변경 후 봇을 재시작하세요.

