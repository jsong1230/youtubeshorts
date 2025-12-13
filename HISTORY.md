## Recent Updates

- **2025-12-13 - 영상 업로드**
  - **영상 2개 비공개 업로드**:
    - 한국어: "매일 반복되는 일상에 지쳤다면? 새로운 라이프스타일을 위한 작은 변화로 활력을 찾는 법을 공유합니다." (51.63초)
      - Video ID: `aIc0yW_re1k`
      - URL: <https://www.youtube.com/watch?v=aIc0yW_re1k>
    - 영어: "Why Financial Independence is very important" (55.04초)
      - Video ID: `2MKUgLg4uY4`
      - URL: <https://www.youtube.com/watch?v=2MKUgLg4uY4>

- **2025-12-13 - 주제 생성 로직 개선 및 규칙 간소화**
  - **AI 주제 생성 프롬프트 개선**: 한국 문화 및 정서에 특화된 주제를 생성하도록 `trend_collector.py`의 시스템 프롬프트 수정. 일반적이거나 번역된 느낌의 주제를 피하고, '연말 모임', '김장'과 같이 한국의 특정 문화를 다루도록 예시 추가.
  - **`.cursorrules` 간소화**: 복잡하고 반복적인 내용을 제거하고 프로젝트 목표, 필수 확인 문서, Shorts 성공 공식, 핵심 규칙 (사용자 확인, Git 작업) 중심으로 재구성.

- **2025-12-12 - Google Cloud TTS SSML 수정 및 영상 업로드**
  - **Google Cloud TTS SSML 수정**: 한글 텍스트의 영어 단어가 영어로 읽히는 문제 해결
    - `GoogleCloudEngine.generate()` 메서드에 SSML 언어 강제 지정 추가
    - 한글(`lang == "ko"`)인 경우 `<lang xml:lang="ko-KR">` 태그로 언어 강제 지정
    - 한글 텍스트 내 영어 단어(예: "스타일링", "쇼핑")가 한글 발음으로 읽히도록 개선
  - **테스트 영상 생성 및 비공개 업로드**:
    - 한국어 영상: "겨울철 스테이셔너리로 만드는 감성적인 일기 쓰기!" (51.66초)
      - Video ID: `aim9-jfcA9o`
      - URL: <https://www.youtube.com/watch?v=aim9-jfcA9o>
      - 파일: `output/videos/shorts_20251212_231932.mp4`
      - 비공개 업로드 완료
    - 영어 영상: "Worried about your finances? See setbacks as stepping stones to smarter money management!" (54.53초)
      - Video ID: `ohRVuqqPYX8`
      - URL: <https://www.youtube.com/watch?v=ohRVuqqPYX8>
      - 파일: `output/videos/shorts_20251212_230825.mp4`
      - 비공개 업로드 완료
