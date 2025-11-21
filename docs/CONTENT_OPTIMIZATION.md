# 콘텐츠 최적화 가이드 (2025 트렌드 반영)

이 문서는 2025년 글로벌 숏폼 트렌드, 계절 이슈, 알고리즘 변화를 반영한 **최신 콘텐츠 최적화 전략**입니다. 모든 콘텐츠(스크립트, 자막, 썸네일, TTS)는 영어로 생성되며, 하루 1개 고품질 영상 전략을 기준으로 작성되었습니다.

---

## 🎯 지원하는 콘텐츠 타입

### 1. Hook (임팩트 한 문장)
- **특징**: 3초 안에 꽂히는 문장, 강한 명제 + 즉각적 설명
- **목표 길이**: 55초
- **구조**: Hook → 설명 → 강조 → 결론
- **대표 주제**:
  - 💸 Money: “Money vanishes in patterns, not accidents.”
  - 🧠 Self: “Routines decide your life long before you do.”
  - 🏠 Declutter: “A messy closet is a money leak in disguise.”
  - 🚨 Risk: “Insurance is a receipt, not a rescue plan.”
- **추천 Hook 예시**: “Your spending isn’t random, it’s rehearsed.”, “Structure builds wealth faster than effort.”

### 2. Quote (명언·인사이트)
- 명언 한 줄 → 실생활 연결
- 55초 목표 길이
- **예시**: “Tiny routines create massive peace.”, “Money is measurement; direction is wealth.”

### 3. Story (1분 스토리텔링)
- Hook → 사건 → 교훈 → 결론
- 변화 경험, 습관 전환, 생활 리셋 사례에 강함
- **예시**: “He cleared one closet and reset his entire routine.”

### 4. Fact (팩트 기반 숏폼)
- 놀라운 팩트 → 왜 중요한지 → 실천 팁
- **예시**: “Tracking spend for 30 days cuts impulse buys by 15%.”

### 5. Short Story (AI 이미지 기반 초단편)
- 감성 스토리 + 여운 + 명확한 교훈
- **예시**: “Ten minutes of routine completely rerouted her life.”

### 6. Auto
- Hook/Quote/Story/Fact/Short Story 중 랜덤 선택
- `TREND_MODE`가 켜져 있으면 트렌드 가중치가 자동 반영됨

---

## 🌍 2025 글로벌 숏폼 트렌드
1. **심플 라이프 / 디클러터링**: 디지털·생활 정리, 주의력 회복
2. **AI 활용 생활 자동화**: AI 툴, 자동화 루틴, 시간 절약
3. **금융 한 줄 핵심 콘텐츠**: “돈이 모이지 않는 이유” 류의 직설적 메시지
4. **심리·뇌과학 기반 팩트**: 짧고 충격적인 팩트 선호
5. **1인 변화 스토리**: 감성 스토리 + 교훈 조합이 강력

> 트렌드 키워드는 `TREND_MODE=true` 설정 시 자동 가중치(글로벌 40%)로 적용됩니다.

---

## 🍂 계절 기반 주제 선택 (25% 확률)

| 계절 | 주요 키워드 |
| --- | --- |
| 봄 (3~5월) | 새출발, 옷장 리셋, 미니멀 루틴, 지출 패턴 재정비 |
| 여름 (6~8월) | 전기요금 절약, 습기·곰팡이 케어, 휴가 예산 |
| 가을 (9~11월) | 하반기 점검, 목표 재정비, 옷장 교체 |
| 겨울 (12~2월) | 난방비 절약, 자동차·배터리 관리, 연말 소비 점검 |

현재 날짜(11~12월) 기준: **겨울 주제 우선 적용**.

---

## 🔥 트렌드 가중치 시스템 (`TREND_MODE=true`)

트렌드를 적극 반영하고 다양성을 유지하기 위한 가중치는 아래와 같습니다.

| 분류 | 비율 | 설명 |
| --- | --- | --- |
| **글로벌 트렌드** | 40% | 2025 핵심 테마 반영 (디클러터링, AI 자동화, 금융 한 줄 등) |
| **계절 기반 선택** | 25% | `_get_season()` 결과에 맞는 주제 우선 |
| **채널 성과 기반** | 20% | 반복 노출 시 성과가 높았던 주제·톤 재사용 |
| **랜덤성 유지** | 15% | 알고리즘 탐색을 위한 신선한 주제 |

코드에서는 `config.TREND_MODE`가 `true`일 때 위 가중치에 따라 주제 풀이 자동 선택됩니다.

---

## 📚 2025 확장 주제팩 (요약)

### 💸 돈/재테크
- Why money refuses to stay in your account
- The habit separating savers from investors
- Winter heating cost reset routine

### 🧠 자기계발
- Why weak execution keeps winning the day
- How routines quietly rewire ambition

### 🏠 집·정리
- Only 20% of your closet actually leaves the house
- Decluttered desks raise focus by 25%

### 🚨 리스크
- Emergency expenses always attack unprotected categories
- Insurance without structure still equals bankruptcy

### 🧬 심리/팩트
- Tracking spend for 30 days rewires impulse buying
- Brain fatigue mirrors clutter in your environment

### 📈 AI/기술
- Automate 30 minutes a day with AI micro-routines
- ChatGPT + Claude dual workflow for faster planning

필요 시 전체 100개 풀을 기반 코드에서 순차적으로 재활용합니다.

---

## ⚙️ 시스템 설정

### `.env` 예시
```bash
CONTENT_TYPE=auto
TREND_MODE=true
PREFER_SHORT_VIDEOS=true  # 55초 목표 유지
```

### 프로바이더 우선순위 (자동 폴백)
1. Claude  
   - `claude-3-opus-20240229` → `claude-3-sonnet-20240229` → `claude-3-5-sonnet-20241022`
2. OpenAI GPT (GPT-4o-mini 권장)
3. 무료/오픈소스 모델

### 언어 정책
- 모든 스크립트·자막·썸네일 텍스트·TTS 문구는 **영어 고정**
- 한국어 입력 시 내부 번역 프롬프트로 자동 변환
- TTS 호출 시 `lang='en'` 강제

### 안전 필터링 & 폴백
- “Here’s the script…” 같은 메타 문장은 자동 제거
- 모든 모델 호출 실패 시에도 55초 분량을 채우는 기본 스크립트로 폴백

---

## 🎬 실행 예시
```bash
# Hook 영상
CONTENT_TYPE=hook python main.py upload

# Fact 영상
CONTENT_TYPE=fact python main.py upload

# 트렌드 기반 자동 선택
CONTENT_TYPE=auto TREND_MODE=true python main.py upload
```

---

## 📈 수익화 최적화 이유
1. **저작권 안전**: 스크립트, 음성, 배경 모두 자체 제작 또는 CC0
2. **55초 완주율 최적화**: Shorts 알고리즘이 가장 선호하는 구간
3. **계절 + 트렌드 결합**: 시의성 + 실용성으로 CTR·완주율 상승
4. **AI Hook 강화**: 첫 3초 집중도로 초기 이탈 최소화
5. **하루 1개 고품질 전략**: 알고리즘 신뢰도와 수익화 속도 동시 확보

---

## 💡 팁
- Hook은 명제 → 이유 → 선택지 구조를 유지 (3문장 이내)
- Story는 “사실 → 감정 → 교훈” 순서를 유지
- Fact는 “수치 → 원인 → 실천법”으로 마무리
- Short Story는 “이미지 프롬프트 + 마지막 문장”에 감성을 집중
- 트렌드/계절/성과 중 어느 쪽이 선택됐는지 로그를 확인해 다음 영상을 튜닝하세요.

---

필요 시 GitHub·Cursor·Notion용 버전을 분리해 제공할 수 있습니다. 추가 확장팩이나 세부 프롬프트가 필요하면 요청해주세요.
