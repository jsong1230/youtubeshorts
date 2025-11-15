# 콘텐츠 최적화 가이드

이 프로젝트는 **수익화 최적화된 콘텐츠 형태**를 지원합니다.

## 🎯 지원하는 콘텐츠 타입

### 1. Hook (영어/한국어 한 문장 학습)
- **특징**: 짧고 강한 Hook으로 시작
- **길이**: 15-30초 (기본: 20초)
- **구조**: Hook 문장 → 설명 → 반복/강조
- **예시 주제**:
  - 영어 한 문장으로 배우는 실생활 표현
  - 한국어 속담 한 줄로 배우기
  - 영어 회화 필수 한 문장

### 2. Quote (AI·비즈니스·명언·지식 한 줄)
- **특징**: 강력한 명언이나 인사이트로 시작
- **길이**: 15-30초 (기본: 20초)
- **구조**: 명언 → 설명 → 실생활 적용법
- **예시 주제**:
  - AI가 바꿀 미래 한 줄
  - 부자들의 생각 한 줄
  - 비즈니스 인사이트 한 줄

### 3. Story (스토리텔링)
- **특징**: 심리/역사/부자습관 등 스토리로 교훈 전달
- **길이**: 25-45초 (기본: 30초)
- **구조**: Hook → 전개 → 교훈 → 마무리
- **예시 주제**:
  - 역사 속 숨겨진 이야기
  - 심리학으로 보는 인간관계
  - 부자들의 습관 이야기

### 4. Fact (숏폼 팩트 기반)
- **특징**: 놀라운 팩트로 Hook 생성
- **길이**: 15-30초 (기본: 20초)
- **구조**: 팩트 → 설명 → 왜 놀라운지 강조
- **예시 주제**:
  - 놀라운 과학 팩트
  - 인간 뇌의 놀라운 사실
  - 우주에 대한 놀라운 사실

### 5. Short Story (AI 이미지 기반 짧은 스토리)
- **특징**: 인생 교훈, 영감, 성공 스토리
- **길이**: 20-35초 (기본: 25초)
- **구조**: Hook → 사건 → 교훈 → 마무리
- **예시 주제**:
  - 짧은 인생 교훈 이야기
  - 영감을 주는 짧은 이야기
  - 성공 스토리 한 편

## ⚙️ 설정 방법

### 환경 변수 (.env)

```bash
# 콘텐츠 타입 설정
CONTENT_TYPE=auto  # 'hook', 'quote', 'story', 'fact', 'short_story', 'auto'

# 짧은 영상 선호 (기본: true)
PREFER_SHORT_VIDEOS=true  # true: 15-30초, false: 30-55초
```

### 콘텐츠 타입별 설정

#### Hook 영상
```bash
CONTENT_TYPE=hook
PREFER_SHORT_VIDEOS=true
```

#### 명언/지식 영상
```bash
CONTENT_TYPE=quote
PREFER_SHORT_VIDEOS=true
```

#### 스토리텔링 영상
```bash
CONTENT_TYPE=story
PREFER_SHORT_VIDEOS=true
```

#### 팩트 기반 영상
```bash
CONTENT_TYPE=fact
PREFER_SHORT_VIDEOS=true
```

#### 짧은 스토리 영상
```bash
CONTENT_TYPE=short_story
PREFER_SHORT_VIDEOS=true
```

#### 자동 선택 (랜덤)
```bash
CONTENT_TYPE=auto
PREFER_SHORT_VIDEOS=true
```

## 📊 수익화 최적화 이유

이런 콘텐츠 형태가 수익화에 유리한 이유:

1. **저작권 위험 없음**
   - 모든 콘텐츠가 AI 생성 또는 CC0 라이선스
   - 게임 영상, 저작권 있는 콘텐츠 사용 안 함

2. **짧아서 Click-Through Rate 좋음**
   - 15-30초 영상은 시청 완료율이 높음
   - YouTube 알고리즘이 짧은 영상을 선호

3. **조회수 폭발 확률 높음**
   - 강력한 Hook으로 첫 3초 안에 관심 유도
   - 명언, 팩트, 스토리 등 공유하기 좋은 콘텐츠
   - 알고리즘 추천에 유리한 구조

4. **재사용 가능**
   - 같은 주제를 다른 각도로 재생성 가능
   - 다양한 콘텐츠 타입으로 다양성 확보

## 🎬 실행 예시

### Hook 영상 생성
```bash
python main.py upload
# 또는
CONTENT_TYPE=hook python main.py upload
```

### 명언 영상 생성
```bash
CONTENT_TYPE=quote python main.py upload
```

### 스토리텔링 영상 생성
```bash
CONTENT_TYPE=story python main.py upload
```

### 팩트 기반 영상 생성
```bash
CONTENT_TYPE=fact python main.py upload
```

### 짧은 스토리 영상 생성
```bash
CONTENT_TYPE=short_story python main.py upload
```

## 💡 최적화 팁

1. **Hook 강화**: 첫 3초가 가장 중요합니다
2. **짧게 유지**: 15-30초가 가장 효과적입니다
3. **다양성**: 여러 콘텐츠 타입을 번갈아 사용하세요
4. **성과 분석**: 데이터베이스에서 성과 좋은 타입 확인
5. **자동 선택**: `CONTENT_TYPE=auto`로 다양성 확보

## 📈 성과 추적

데이터베이스에서 다음 정보를 확인할 수 있습니다:
- 콘텐츠 타입별 평균 조회수
- 콘텐츠 타입별 참여율
- 성과 좋은 콘텐츠 타입

성과 기반 프롬프트가 자동으로 적용되어 점점 더 좋은 콘텐츠를 생성합니다.

