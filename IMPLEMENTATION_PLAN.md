# Script Duplication Issue - Investigation & Fix Plan

## Problem Description
최근 업로드된 4개의 YouTube Shorts에서 동일한 내용이 반복되는 문제 발생. OpenAI API를 사용한 스크립트 생성 로직에 문제가 있는 것으로 추정.

## Root Cause Analysis

### Potential Issues Identified

1. **Temperature Setting (0.7)**
   - 현재 `temperature=0.7`로 설정되어 있음
   - 같은 프롬프트에 대해 유사한 응답을 생성할 가능성 있음
   - 특히 같은 주제가 반복 선택되면 동일한 스크립트 생성 가능

2. **No Seed/Random State**
   - OpenAI API 호출 시 `seed` 파라미터 미사용
   - 동일한 입력에 대해 다양성 보장 안 됨

3. **Topic Selection Issue**
   - 같은 주제가 반복 선택되고 있을 가능성
   - 주제 선택 로직에서 최근 사용 주제 필터링 부재

4. **No Script Deduplication Check**
   - 생성된 스크립트가 이전 스크립트와 중복되는지 확인하지 않음
   - 데이터베이스에 스크립트가 저장되지 않아 비교 불가능

## Proposed Changes

### Script Generator Layer

#### [MODIFY] [script_generator.py](file:///Users/joohansong/dev/youtubeshorts/src/generators/script_generator.py)

**Changes:**
1. **Increase Temperature for Diversity**
   - `temperature` 0.7 → 0.9로 증가
   - 더 다양한 스크립트 생성 유도

2. **Add Randomization Seed**
   - 매 호출마다 다른 `seed` 값 사용
   - `seed=int(time.time() * 1000) % 10000` 추가

3. **Add Script Uniqueness Check**
   - 생성된 스크립트의 첫 3문장을 해시화
   - 최근 10개 스크립트와 비교하여 중복 시 재생성

4. **Enhanced System Prompt**
   - "Create a UNIQUE and ORIGINAL script" 강조
   - "Avoid repeating common phrases or structures" 추가

### Database Layer

#### [MODIFY] [video_database.py](file:///Users/joohansong/dev/youtubeshorts/src/pipeline/video_database.py)

**Changes:**
1. **Ensure Script Storage**
   - `add_video()` 메서드에서 `script` 파라미터가 제대로 저장되는지 확인
   - NULL 체크 및 로깅 추가

2. **Add Script Retrieval Method**
   - `get_recent_scripts(limit=10)` 메서드 추가
   - 최근 스크립트 조회하여 중복 검사에 사용

### Topic Selection Layer

#### [MODIFY] [video_generator.py](file:///Users/joohansong/dev/youtubeshorts/src/generators/video_generator.py)

**Changes:**
1. **Recent Topic Filtering**
   - 최근 5개 영상에 사용된 주제 제외
   - `TopicDatabase`에서 최근 사용 주제 조회 후 필터링

2. **Topic Diversity Enforcement**
   - 같은 카테고리 주제가 연속 3회 이상 선택되지 않도록 제한

## Verification Plan

### Automated Tests
1. **Script Uniqueness Test**
   - 같은 주제로 10번 스크립트 생성
   - 각 스크립트의 유사도 측정 (< 70% 유사도 목표)

2. **Temperature Impact Test**
   - Temperature 0.7 vs 0.9 비교
   - 다양성 지표 측정

### Manual Verification
1. **Delete Duplicate Videos**
   - YouTube에서 중복 영상 4개 삭제
   - Video IDs: rXCDiFxBL2Q, yKQIb6o9_KM, rBkBC0q41eE, NVJHCu01knQ

2. **Generate Test Videos**
   - 수정 후 5개 테스트 영상 생성
   - 스크립트 내용 수동 확인

3. **Monitor Production**
   - 다음 10개 영상 모니터링
   - 중복 발생 여부 추적

## Implementation Timeline
- **Day 1-2**: Apply code changes (script_generator, database, video_generator)
- **Day 3**: Write unit tests and run CI
- **Day 4**: Generate test videos, verify no repetition
- **Day 5**: Deploy to staging, monitor first batch of videos

## Risks & Mitigations
- **Risk**: Increased temperature may produce incoherent text.
  - *Mitigation*: Add post‑processing validation and fallback to lower temperature if quality drops.
- **Risk**: Database schema changes could affect existing data.
  - *Mitigation*: Migration script already added; run on staging first.
- **Risk**: New uniqueness check adds latency.
  - *Mitigation*: Cache recent script hashes for quick lookup.

---
*Prepared by Antigravity, 2025-11-22*
