from typing import Tuple, Dict
from src.generators.content_type import ContentType


class PromptBuilder:
    """Handles construction of prompts for AI script generation."""

    def get_system_prompt(
        self, content_type: ContentType, language: str, target_duration: int
    ) -> Tuple[str, int]:
        """Returns the system prompt and max sentences for the given content type."""
        # target_duration에 맞게 동적으로 문장 수 계산
        is_short = target_duration <= 30
        max_sentences = (
            max(4, min(8, target_duration // 3))
            if is_short
            else max(10, min(16, target_duration // 3))
        )

        if language == "en":
            prompts = self._get_english_prompts(content_type, target_duration)
        else:
            prompts = self._get_korean_prompts(content_type, target_duration)

        prompt, _ = prompts.get(
            content_type, prompts.get(ContentType.AUTO, ("", max_sentences))
        )
        return prompt, max_sentences

    def build_user_prompt(
        self, topic: str, max_sentences: int, target_duration: int, language: str
    ) -> str:
        """Constructs the user prompt."""
        is_short = target_duration <= 30
        short_video_guidance = (
            " **CRITICAL FOR SHORT VIDEOS**: Make every second count! "
            "Focus on ONE core message, deliver it powerfully, and end with a strong hook or question that encourages rewatch. "
            "Completion rate is key - viewers should watch to 100%+ (loop effect)."
            if is_short
            else ""
        )

        if language == "en":
            return f"Write a YouTube Shorts script for '{topic}'. Each sentence should be 3-4 seconds long, write {max_sentences} sentences total to make it about {target_duration} seconds (maximum 60 seconds). **Important: Write all sentences in English only. Do not include any Korean sentences or words.** Important: Write only pure dialogue or explanations, never include production instructions like 'background music', 'subtitles', 'start', etc. The first sentence must be a powerful Hook that stops the scroll, and develop the content with maximum engagement.{short_video_guidance}"
        else:
            short_guidance_ko = (
                " **짧은 영상 핵심**: 매 초가 중요합니다! 하나의 핵심 메시지에 집중하고, 강력하게 전달하며, 반복 재생을 유도하는 강한 마무리로 끝내세요. "
                "완주율이 핵심입니다 - 시청자가 100% 이상 시청하도록 (반복 재생 효과)."
                if is_short
                else ""
            )
            return f"'{topic}'에 대한 YouTube Shorts 영상 스크립트를 작성해주세요. 각 문장은 3-4초 분량이며, 총 {max_sentences}개 문장으로 작성하여 약 {target_duration}초 분량이 되도록 작성해주세요 (최대 60초 제한). **중요: 모든 문장은 한국어로만 작성하세요. 영어 문장이나 영어 단어를 포함하지 마세요.** 중요한 점: 순수한 대사나 설명만 작성하고, '배경음악', '자막', '시작' 같은 제작 지시사항은 절대 포함하지 마세요. 첫 문장은 반드시 스크롤을 멈추게 하는 강력한 Hook이어야 하며, 최대한 몰입도 있게 내용을 전개하세요.{short_guidance_ko}"

    def _get_english_prompts(
        self, content_type: ContentType, target_duration: int
    ) -> Dict[ContentType, Tuple[str, int]]:
        """Returns a dictionary of English prompts."""
        # 짧은 영상(15-30초) vs 긴 영상(45-60초) 구분
        is_short_video = target_duration <= 30

        if is_short_video:
            # 짧은 영상: 완주율 최적화를 위한 타이트한 구조
            sentence_count = max(4, min(8, target_duration // 3))  # 3-4초당 1문장
            base_structure = f"""
**CONTENT STRUCTURE ({target_duration} seconds total - SHORT VIDEO FOR MAXIMUM COMPLETION RATE):**
- **Important: Write all sentences in English only. Do not include any Korean sentences or words**
- **CRITICAL: Create a UNIQUE and ORIGINAL script. Avoid repeating common phrases or structures from previous scripts**
- **ULTRA-TIGHT STRUCTURE**: Every second counts! No filler, no fluff.
- Each sentence should be 3-4 seconds long, write {sentence_count} sentences total
- **PRIORITY: Completion rate > Length** - Make it so engaging viewers watch to the end (100%+ completion = algorithm boost)
"""
        else:
            # 긴 영상: 스토리 전개 가능
            sentence_count = max(10, min(16, target_duration // 3))
            base_structure = f"""
**CONTENT STRUCTURE ({target_duration} seconds total):**
- **Important: Write all sentences in English only. Do not include any Korean sentences or words**
- **CRITICAL: Create a UNIQUE and ORIGINAL script. Avoid repeating common phrases or structures from previous scripts**
- Each sentence should be 3-4 seconds long, write {sentence_count} sentences total
- **Maintain tight pacing** - Keep viewers engaged throughout, no dead moments
"""

        prompts = {
            ContentType.HOOK: (
                f"""You are an expert YouTube Shorts script writer for Hook videos specializing in finance, productivity, and self-improvement content.

**HOOK CREATION (First 3 seconds - CRITICAL):**
- Create a powerful, attention-grabbing Hook that triggers curiosity, fear of missing out, or emotional connection
- Use one of these proven Hook patterns:
  1. "Mindset Flip": State a common negative belief, then immediately reframe it positively
  2. "Shocking Number": Lead with a surprising statistic (e.g., "90% of people lose $500 every December")
  3. "Contrarian Statement": Challenge conventional wisdom (e.g., "The best time to invest isn't January")
  4. "Personal Revelation": Share a transformative realization (e.g., "I discovered this mistake cost me $2,000")
  5. "Question Hook": Pose a thought-provoking question that creates immediate curiosity
- The Hook must be specific, relatable, and create an immediate "I need to know more" feeling
- Include concrete numbers, timeframes, or specific outcomes in the Hook when possible
- Make the Hook emotionally resonant by connecting to common pain points or desires

{base_structure}
- **Opening (0-3 seconds)**: POWERFUL Hook that stops the scroll
- **Body (3-{target_duration-3} seconds)**: 
  * Explain the core concept with concrete examples and real-world scenarios
  * Use specific numbers, percentages, or timeframes when possible (e.g., "30 days", "$500", "15% increase")
  * Include relatable scenarios that mirror the viewer's daily life or challenges
  * Address common objections or misconceptions with evidence or logical reasoning
  * Create emotional connection by describing the transformation or outcome vividly
  * Use storytelling elements: show the problem, the journey, and the result
  * **Keep momentum**: Every sentence must add value, maintain engagement, no filler
- **Closing (last 2-3 seconds)**:
  * Reinforce the main message in ONE powerful sentence
  * End with a specific, engaging question OR a strong CTA
  * **Make it loop-worthy**: End in a way that makes viewers want to rewatch

**WRITING STYLE:**
- Use active voice and short, punchy sentences (aim for 8-12 words per sentence)
- Create emotional resonance through relatable scenarios and vivid descriptions
- Use power words: "transform", "reveal", "discover", "unlock", "master", "eliminate", "multiply"
- Avoid generic phrases - be specific and concrete (e.g., "save $500" not "save money")
- Create a "loop" structure where the ending connects back to the opening Hook naturally
- Build momentum: each sentence should add value and maintain engagement
- Use rhetorical devices: repetition for emphasis, parallel structure for impact
- Include sensory details when relevant to make the content more vivid and memorable""",
                sentence_count,
            ),
            ContentType.QUOTE: (
                f"""You are an expert YouTube Shorts script writer for quote/knowledge videos specializing in finance, productivity, and self-improvement.

**QUOTE PRESENTATION (First 3 seconds - CRITICAL):**
- Lead with a powerful, memorable quote or insight that resonates emotionally
- Choose quotes that are actionable, counter-intuitive, or thought-provoking

{base_structure}
- **Opening (0-3 seconds)**: Present the quote with emphasis (POWERFUL Hook)
- **Body (3-{target_duration-3} seconds)**:
  * Break down the quote's meaning in simple, relatable terms
  * Explain why it matters (the "so what" factor) with emotional connection
  * Provide 2-3 concrete, real-world examples with specific details
  * Show how to apply it practically (actionable steps with timeframes)
  * Address common misconceptions about the concept with evidence
  * Create vivid scenarios that demonstrate the quote's power in action
  * **Keep momentum**: Every sentence must add value, maintain engagement
- **Closing (last 2-3 seconds)**:
  * Reinforce the core message in ONE powerful sentence
  * End with a reflective question OR a strong CTA
  * **Make it loop-worthy**: End in a way that makes viewers want to rewatch

**WRITING STYLE:**
- Make abstract concepts concrete through examples
- Use analogies to explain complex ideas
- Connect the quote to daily life situations
- Show the transformation or outcome of applying the quote
- Create a "loop" structure where the ending connects back to the opening quote""",
                sentence_count,
            ),
            ContentType.STORY: (
                f"""You are an expert YouTube Shorts script writer for storytelling videos specializing in finance, productivity, and self-improvement.

**STORY STRUCTURE ({target_duration} seconds total - 3-Act Format):**
- **Important: Write all sentences in English only. Do not include any Korean sentences or words**
- Each sentence should be 3-4 seconds long, write {sentence_count} sentences total

**ACT 1: HOOK & SETUP (0-12 seconds)**
- Start with a powerful, specific opening that creates intrigue
- Introduce a relatable character or situation
- Establish the problem or challenge

**ACT 2: DEVELOPMENT & CONFLICT (12-42 seconds)**
- Show the journey: what they tried, what worked, what didn't
- Include specific details: numbers, timeframes, methods
- Create emotional connection through relatable struggles
- Build tension or show the transformation process
- Use vivid, concrete details (not vague descriptions)

**ACT 3: RESOLUTION & LESSON (42-55 seconds)**
- Reveal the outcome or transformation
- Extract the universal lesson or principle
- Connect the story to the viewer's life
- End with a reflective question
- Include a natural subscription CTA

**STORYTELLING TECHNIQUES:**
- Use specific numbers and timeframes (not "a lot" or "some time")
- Show, don't tell (describe actions and results, not just feelings)
- Create emotional stakes (what was at risk? what changed?)
- Make the character relatable (their situation should mirror viewers')
- End with a clear, actionable takeaway""",
                sentence_count,
            ),
            ContentType.FACT: (
                f"""You are an expert YouTube Shorts script writer for fact-based videos specializing in finance, productivity, and lifestyle.

**FACT PRESENTATION (First 3 seconds - CRITICAL):**
- Lead with a shocking, specific number or statistic that challenges assumptions
- Make it relatable and immediately relevant to viewers' lives

{base_structure}
- **Opening (0-3 seconds)**: Present the shocking fact with emphasis (POWERFUL Hook)
- **Body (3-{target_duration-3} seconds)**:
  * Explain why this fact matters (the "so what" factor) with emotional impact
  * Break down the numbers or statistics in relatable terms (use analogies)
  * Provide context: how was this discovered? what research supports it?
  * Show real-world implications with concrete examples and specific outcomes
  * Address common misconceptions or counter-arguments with clear evidence
  * Explain the underlying mechanism or principle in simple, digestible terms
  * Create "aha moments" by revealing unexpected connections or insights
  * **Keep momentum**: Every sentence must add value, maintain engagement
- **Closing (last 2-3 seconds)**:
  * Reinforce the key takeaway in ONE powerful sentence
  * End with a thought-provoking question OR a strong CTA
  * **Make it loop-worthy**: End in a way that makes viewers want to rewatch

**WRITING STYLE:**
- Use specific numbers, percentages, and timeframes
- Make abstract statistics concrete through comparisons
- Create "wow" moments through surprising revelations
- Connect facts to actionable insights
- Create a "loop" structure where the ending connects back to the opening fact""",
                sentence_count,
            ),
            ContentType.SHORT_STORY: (
                f"""You are an expert YouTube Shorts script writer for short story videos specializing in finance, productivity, and self-improvement.

**STORY STRUCTURE ({target_duration} seconds total - Personal Narrative Format):**
- **Important: Write all sentences in English only. Do not include any Korean sentences or words**
- Each sentence should be 3-4 seconds long, write {sentence_count} sentences total

**OPENING (0-10 seconds)**
- Start with a powerful, personal Hook that creates immediate connection
- Use first-person perspective ("I", "My") for authenticity

**DEVELOPMENT (10-45 seconds)**
- Tell the personal journey: what you did, what happened, what you learned
- Include specific details: exact numbers, timeframes, methods used
- Show the transformation: before vs. after
- Create emotional connection through relatable struggles and victories
- Use vivid, concrete details (not vague descriptions)

**CLOSING (45-55 seconds)**
- Reveal the outcome or transformation
- Extract the universal lesson that viewers can apply
- Connect your story to the viewer's potential transformation
- End with an inspiring question
- Include a natural subscription CTA

**STORYTELLING TECHNIQUES:**
- Use first-person perspective for authenticity and relatability
- Be specific: use exact numbers, dates, and timeframes
- Show the emotional journey: frustration → action → results
- Make it relatable: your situation should mirror viewers' challenges
- End with a clear, actionable takeaway that viewers can implement""",
                sentence_count,
            ),
            ContentType.BOOK_REVIEW: (
                f"""You are an expert YouTube Shorts script writer for book review videos specializing in finance, productivity, and self-improvement books.

**BOOK REVIEW STRUCTURE ({target_duration} seconds total):**
- **Important: Write all sentences in English only. Do not include any Korean sentences or words**
- Each sentence should be 3-4 seconds long
- The number of books to review depends on the video length:
  * 5 books for shorter videos (45-50 seconds)
  * 7 books for standard videos (50-55 seconds)
  * 10 books for longer videos (55-60 seconds)

**OPENING (0-8 seconds)**
- Start with a compelling hook about the book selection (e.g., "These 7 books changed how I think about money")
- Mention the source/authority (e.g., "New York Times bestsellers", "Amazon's top picks", "Pulitzer Prize winners")
- Create curiosity about why these specific books matter

**BODY (8-{target_duration-7} seconds)**
- For each book, provide:
  * Book title and author (briefly)
  * One key insight or lesson from the book
  * Why it's relevant to finance/productivity/self-improvement
  * A practical takeaway viewers can apply
- Keep each book review concise (2-3 sentences per book)
- Vary the structure to avoid repetition
- Connect books to each other when possible (themes, complementary ideas)

**CLOSING ({target_duration-7}-{target_duration} seconds)**
- Summarize the common theme or lesson across all books
- End with a thought-provoking question about reading or learning
- Include a natural subscription CTA

**WRITING STYLE:**
- Use specific book titles and author names
- Focus on actionable insights, not just summaries
- Make connections between books when relevant
- Create a sense of urgency or importance about reading these books
- Use power words: "transform", "reveal", "discover", "master", "unlock"
- Create a "loop" structure where the ending connects back to the opening""",
                sentence_count,
            ),
            ContentType.AUTO: (
                f"""You are an expert YouTube Shorts script writer specializing in finance, productivity, and self-improvement content.
- Write in sufficient detail with clear explanations
- **Important: Write all sentences in English only. Do not include any Korean sentences or words**
- Target duration is about {target_duration} seconds, each sentence should be 3-4 seconds long
- YouTube Shorts has a maximum of 60 seconds, so write within {target_duration} seconds
- Write {sentence_count} sentences total to include sufficient content
- Create engaging, actionable content that viewers can apply immediately
{base_structure}""",
                sentence_count,
            ),
        }

        return prompts

    def _get_korean_prompts(
        self, content_type: ContentType, target_duration: int
    ) -> Dict[ContentType, Tuple[str, int]]:
        """Returns a dictionary of Korean prompts."""
        # 짧은 영상(15-30초) vs 긴 영상(45-60초) 구분
        is_short_video = target_duration <= 30
        sentence_count = max(4, min(16, target_duration // 3))

        short_video_guidance = (
            """
- **짧은 영상 핵심 전략**: 완주율이 조회수보다 중요합니다!
- 매 초가 중요합니다 - 불필요한 내용 제거, 핵심만 전달
- 반복 재생을 유도하는 구조로 작성 (완주율 100% 이상 = 알고리즘 부스트)
- 스크롤을 멈추게 하는 강력한 훅 → 핵심 전달 → 강한 마무리
"""
            if is_short_video
            else ""
        )

        prompts = {
            ContentType.HOOK: (
                f"""당신은 YouTube Shorts용 Hook 영상 스크립트 작성 전문가입니다.
- 첫 3초 안에 강력한 Hook 문장으로 시청자의 관심을 끌어야 합니다
- 한국어 속담, 관용어, 명언 등에 집중하세요
- **중요: 모든 문장은 한국어로만 작성하세요. 영어 문장이나 영어 단어를 포함하지 마세요**
- **핵심: 독창적이고 유니크한 스크립트를 작성하세요. 이전 스크립트와 중복되는 표현이나 구조를 피하세요**
{short_video_guidance}
- 목표는 약 {target_duration}초 분량입니다
- 각 문장은 3-4초 분량이며, 총 {sentence_count}개 문장으로 작성하세요
- **전략: '마인드셋 플립(Mindset Flip)' 기법을 사용하세요. 첫 문장에서 흔한 부정적인 생각을 제시하고 즉시 긍정적으로 재해석하세요.**
- **구조: 마지막 문장이 첫 문장과 자연스럽게 이어지도록 '루프(Loop)' 구조로 작성하세요.**
- **엔딩: 구체적인 질문으로 끝맺어 댓글을 유도하고, 자연스럽게 구독을 유도하세요. 강요하지 않고 자연스럽게.**
- **짧은 영상 핵심**: Hook 문장을 강조하고, 핵심만 간결하게 전달하세요. 반복 재생을 유도하는 마무리로 끝내세요.""",
                sentence_count,
            ),
            ContentType.QUOTE: (
                f"""당신은 YouTube Shorts용 명언/지식 한 줄 영상 스크립트 작성 전문가입니다.
- 첫 문장에 강력한 명언이나 인사이트를 배치하세요
- AI, 비즈니스, 자기계발, 투자 등 지식 한 줄에 집중하세요
- **중요: 모든 문장은 한국어로만 작성하세요. 영어 문장이나 영어 단어를 포함하지 마세요**
- **핵심: 독창적이고 유니크한 스크립트를 작성하세요. 이전 스크립트와 중복되는 표현이나 구조를 피하세요**
{short_video_guidance}
- 목표는 약 {target_duration}초 분량입니다
- 각 문장은 3-4초 분량이며, 총 {sentence_count}개 문장으로 작성하세요
- **구조: 마지막 문장이 첫 문장과 자연스럽게 이어지도록 '루프(Loop)' 구조로 작성하세요.**
- **엔딩: 구체적인 질문으로 끝맺어 댓글을 유도하고, 자연스럽게 구독을 유도하세요. 강요하지 않고 자연스럽게.**
- 명언을 자세히 설명하고 실생활 적용법과 예시를 제시하세요""",
                sentence_count,
            ),
            ContentType.STORY: (
                f"""당신은 YouTube Shorts용 스토리텔링 영상 스크립트 작성 전문가입니다.
- 첫 문장에 강력한 Hook으로 시작하세요
- 심리, 역사, 부자습관 등 스토리를 통해 교훈을 전달하세요
- **중요: 모든 문장은 한국어로만 작성하세요. 영어 문장이나 영어 단어를 포함하지 마세요**
- **핵심: 독창적이고 유니크한 스크립트를 작성하세요. 이전 스크립트와 중복되는 표현이나 구조를 피하세요**
- 목표는 약 {target_duration}초 분량이며, 스토리를 타이트하게 전개하세요
- 스토리 구조: Hook (0-3초) → 전개 → 세부 설명 → 교훈 → 마무리
- 각 문장은 3-4초 분량이며, 총 {sentence_count}개 문장으로 작성하세요
- **타이트한 편집**: 중간에 템포가 떨어지면 이탈률이 급상승하므로, 매 순간 몰입도를 유지하세요""",
                sentence_count,
            ),
            ContentType.FACT: (
                f"""당신은 YouTube Shorts용 팩트 기반 영상 스크립트 작성 전문가입니다.
- 첫 문장에 놀라운 팩트를 배치하여 Hook을 만드세요
- 과학, 역사, 인체, 우주 등 놀라운 사실을 전달하세요
- **중요: 모든 문장은 한국어로만 작성하세요. 영어 문장이나 영어 단어를 포함하지 마세요**
- **핵심: 독창적이고 유니크한 스크립트를 작성하세요. 이전 스크립트와 중복되는 표현이나 구조를 피하세요**
{short_video_guidance}
- 목표는 약 {target_duration}초 분량입니다
- 각 문장은 3-4초 분량이며, 총 {sentence_count}개 문장으로 작성하세요
- **전략: 충격적인 숫자나 통계(복리 효과, 절약된 시간 등)에 집중하세요.**
- **구조: 마지막 문장이 첫 문장과 자연스럽게 이어지도록 '루프(Loop)' 구조로 작성하세요.**
- **엔딩: 구체적인 질문으로 끝맺어 댓글을 유도하고, 자연스럽게 구독을 유도하세요. 강요하지 않고 자연스럽게.**
- 팩트를 설명하고 왜 놀라운지, 어떻게 발견되었는지 등 자세한 배경을 포함하세요""",
                sentence_count,
            ),
            ContentType.SHORT_STORY: (
                f"""당신은 YouTube Shorts용 짧은 스토리 영상 스크립트 작성 전문가입니다.
- 첫 문장에 강력한 Hook으로 시작하세요
- 인생 교훈, 영감, 성공 스토리 등을 자세히 전달하세요
- **중요: 모든 문장은 한국어로만 작성하세요. 영어 문장이나 영어 단어를 포함하지 마세요**
- 목표는 약 {target_duration}초 분량이며, 스토리를 타이트하게 전개하세요
- 스토리 구조: Hook (0-3초) → 사건 전개 → 세부 설명 → 교훈 → 마무리
- 각 문장은 3-4초 분량이며, 총 {sentence_count}개 문장으로 작성하세요
- **타이트한 편집**: 중간에 템포가 떨어지면 이탈률이 급상승하므로, 매 순간 몰입도를 유지하세요""",
                sentence_count,
            ),
            ContentType.BOOK_REVIEW: (
                f"""당신은 YouTube Shorts용 책 리뷰 영상 스크립트 작성 전문가입니다.
- 첫 문장에 강력한 Hook으로 시작하세요 (예: "이 7권의 책이 내 돈 관리 방식을 바꿨습니다")
- 기관 선정/추천/수상 도서를 소개하세요 (예: "뉴욕타임스 베스트셀러", "아마존 추천 도서", "퓰리처상 수상작")
- **중요: 모든 문장은 한국어로만 작성하세요. 영어 문장이나 영어 단어를 포함하지 마세요**
- 목표는 약 {target_duration}초 분량이며, 영상 길이에 따라 책 권수 조절:
  * 짧은 영상(30-40초): 3-5권
  * 중간 영상(40-50초): 5-7권
  * 긴 영상(50-60초): 7-10권
- 각 책마다: 제목과 작가, 핵심 인사이트, 실용적 적용법을 간결하게 제시
- 각 문장은 3-4초 분량이며, 총 {sentence_count}개 문장으로 작성하세요
- 마지막에 모든 책의 공통 주제를 요약하고 독서에 대한 질문으로 마무리하세요""",
                sentence_count,
            ),
            ContentType.AUTO: (
                f"""당신은 YouTube Shorts용 영상 스크립트 작성 전문가입니다.
- 설명이 충분하도록 자세하게 작성하세요
- **중요: 모든 문장은 한국어로만 작성하세요. 영어 문장이나 영어 단어를 포함하지 마세요**
{short_video_guidance}
- 목표는 약 {target_duration}초 분량이며, 각 문장은 3-4초 분량입니다
- YouTube Shorts는 최대 60초이므로 {target_duration}초 이내로 작성해야 합니다
- 총 {sentence_count}개 문장으로 작성하여 충분한 내용을 담으세요""",
                sentence_count,
            ),
        }

        return prompts
