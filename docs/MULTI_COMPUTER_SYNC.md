# 멀티 컴퓨터 동기화 가이드

이 가이드는 집 컴퓨터와 회사 컴퓨터를 번갈아가며 사용할 때 일관성을 유지하는 방법을 설명합니다.

## 🎯 목표

- 두 컴퓨터 간 데이터 일관성 유지
- 중복 업로드 방지
- 작업 상태 추적

## 📋 동기화되는 항목

### 1. 코드 및 설정
- ✅ **Git을 통한 자동 동기화**: 코드 변경사항은 Git으로 자동 동기화됩니다.
- ✅ **.env 파일**: 환경 변수는 각 컴퓨터에서 동일하게 설정해야 합니다.
  - `.env` 파일은 Git에 포함되지 않으므로, 각 컴퓨터에서 수동으로 설정하거나 안전한 방법으로 공유해야 합니다.

### 2. 데이터 파일
- ✅ **동기화 상태 파일** (`data/sync_state.json`): Git에 포함되어 두 컴퓨터 간 동기화됩니다.
  - 마지막 업로드 정보
  - 업로드 히스토리 (최근 10개)
  - 컴퓨터별 작업 기록

- ⚠️ **데이터베이스** (`data/videos.db`): Git에 포함되지 않습니다.
  - 각 컴퓨터에서 독립적으로 관리됩니다.
  - 필요시 수동으로 동기화할 수 있습니다.

- ⚠️ **수익화 데이터** (`data/monetization_data.json`): Git에 포함되지 않습니다.
  - 각 컴퓨터에서 독립적으로 관리됩니다.

### 3. 생성된 파일
- ❌ **생성된 영상** (`output/videos/`): Git에 포함되지 않습니다.
  - 각 컴퓨터에서 독립적으로 생성됩니다.
  - 필요시 수동으로 공유할 수 있습니다.

## 🔄 동기화 프로세스

### 매일 작업 전 (필수)

1. **Git Pull**: 최신 코드와 동기화 상태 가져오기
   ```bash
   git pull
   ```

2. **동기화 상태 확인**
   ```bash
   python main.py sync-status
   ```
   또는 코드에서:
   ```python
   from src.pipeline.sync_manager import SyncManager
   sync = SyncManager()
   sync.print_sync_status()
   ```

3. **오늘 업로드 여부 확인**
   - 로컬 상태 파일 확인
   - YouTube API로 실제 업로드 확인
   - 이미 업로드했다면 업로드를 건너뜁니다.

### 매일 작업 후 (권장)

1. **Git Commit & Push**: 변경사항 저장
   ```bash
   git add data/sync_state.json
   git commit -m "업로드 완료: [영상 제목]"
   git push
   ```

2. **동기화 상태 확인**
   - `data/sync_state.json` 파일이 Git에 포함되어 있는지 확인

## 🛡️ 중복 업로드 방지

시스템은 다음 방법으로 중복 업로드를 방지합니다:

### 1. 로컬 상태 파일 확인
- `data/sync_state.json` 파일에서 오늘 업로드 여부 확인
- 오늘 이미 업로드했다면 경고 메시지 표시

### 2. YouTube API 확인
- YouTube API를 통해 실제로 오늘 업로드된 영상 확인
- 이미 업로드된 영상이 있으면 자동으로 업로드 건너뜀

### 3. 수동 확인
- 로컬 상태 파일에 오늘 업로드 기록이 있지만, YouTube API 확인이 실패한 경우
- 사용자에게 확인 메시지 표시

## 📝 사용 예시

### 시나리오 1: 집에서 업로드 후 회사에서 확인

**집 컴퓨터에서:**
```bash
# 1. 영상 업로드
python main.py upload

# 2. Git에 동기화 상태 저장
git add data/sync_state.json
git commit -m "업로드 완료"
git push
```

**회사 컴퓨터에서:**
```bash
# 1. 최신 코드 및 동기화 상태 가져오기
git pull

# 2. 업로드 시도 (자동으로 오늘 업로드 확인)
python main.py upload
# → "오늘 이미 업로드했습니다" 메시지 표시 후 건너뜀
```

### 시나리오 2: 회사에서 업로드 후 집에서 확인

**회사 컴퓨터에서:**
```bash
# 1. 영상 업로드
python main.py upload

# 2. Git에 동기화 상태 저장
git add data/sync_state.json
git commit -m "업로드 완료"
git push
```

**집 컴퓨터에서:**
```bash
# 1. 최신 코드 및 동기화 상태 가져오기
git pull

# 2. 동기화 상태 확인
python main.py sync-status
# → 마지막 업로드 정보 표시
```

## ⚙️ 설정

### .env 파일 동기화

`.env` 파일은 Git에 포함되지 않으므로, 각 컴퓨터에서 동일하게 설정해야 합니다.

**방법 1: 수동 설정 (권장)**
- 각 컴퓨터에서 `.env` 파일을 동일하게 설정
- API 키는 안전하게 관리

**방법 2: 안전한 공유**
- 암호화된 방식으로 `.env` 파일 공유
- 또는 환경 변수 관리 도구 사용

### 데이터베이스 동기화 (선택사항)

필요한 경우 `data/videos.db` 파일을 수동으로 동기화할 수 있습니다:

```bash
# 한 컴퓨터에서
git add data/videos.db
git commit -m "데이터베이스 동기화"
git push

# 다른 컴퓨터에서
git pull
```

⚠️ **주의**: 데이터베이스 파일이 크면 Git 저장소가 커질 수 있습니다.

## 🔍 문제 해결

### 문제 1: 동기화 상태가 업데이트되지 않음

**증상**: 한 컴퓨터에서 업로드했지만 다른 컴퓨터에서 인식하지 못함

**해결**:
1. Git pull 확인
2. `data/sync_state.json` 파일이 Git에 포함되어 있는지 확인
3. 수동으로 Git push 확인

### 문제 2: 중복 업로드 발생

**증상**: 두 컴퓨터에서 같은 날 업로드됨

**해결**:
1. YouTube API 확인이 실패했을 수 있음
2. 수동으로 YouTube 채널 확인
3. 필요시 한 영상 삭제

### 문제 3: 동기화 상태 파일 충돌

**증상**: Git merge conflict 발생

**해결**:
1. 두 컴퓨터에서 업로드한 경우, 최신 업로드 정보를 유지
2. 수동으로 `data/sync_state.json` 파일 편집
3. Git commit & push

## 📊 동기화 상태 파일 구조

`data/sync_state.json` 파일 구조:

```json
{
  "last_upload": {
    "video_id": "abc123",
    "title": "영상 제목",
    "topic": "주제",
    "computer_id": "computer-name",
    "upload_time": "2025-11-17T09:00:00",
    "date": "2025-11-17"
  },
  "upload_history": [
    {
      "video_id": "abc123",
      "title": "영상 제목",
      "topic": "주제",
      "computer_id": "computer-name",
      "upload_time": "2025-11-17T09:00:00",
      "date": "2025-11-17"
    }
  ]
}
```

## 💡 모범 사례

1. **매일 작업 전 Git Pull**: 최신 상태 확인
2. **매일 작업 후 Git Push**: 변경사항 저장
3. **동기화 상태 확인**: `python main.py sync-status` 실행
4. **오늘 업로드 확인**: 업로드 전에 항상 확인
5. **일관된 작업 시간**: 가능하면 같은 시간에 작업

## 🚀 자동화

스케줄러를 사용하는 경우, 자동으로 중복 업로드를 방지합니다:

```bash
python main.py schedule
```

스케줄러는:
1. 동기화 상태 확인
2. 오늘 업로드 여부 확인
3. 이미 업로드했다면 자동으로 건너뜀
4. 업로드 후 동기화 상태 자동 업데이트

---

**마지막 업데이트**: 2025-11-17

