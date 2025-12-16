import hashlib
import re
from typing import List, Tuple, Optional
from src.utils.logger import get_logger
from src.generators.video_constants import VideoConstants

logger = get_logger(__name__)


class ScriptValidator:
    """Handles validation of generated scripts."""

    def validate_hook(
        self, first_sentence: str, first_sentence_duration: float
    ) -> Tuple[bool, List[str]]:
        """Hook 검증 (성공 공식: 초반 3초 Hook 강화)
        
        Args:
            first_sentence: 첫 문장
            first_sentence_duration: 첫 문장의 TTS 길이 (초)
            
        Returns:
            (is_valid, issues): 검증 결과와 문제점 리스트
        """
        issues = []
        is_valid = True
        
        # 1. 길이 검증 (3초 이내)
        max_hook_duration = VideoConstants.HOOK_MAX_DURATION
        if first_sentence_duration > max_hook_duration:
            issues.append(
                f"❌ Hook이 너무 깁니다: {first_sentence_duration:.2f}초 (목표: {max_hook_duration}초 이내)"
            )
            is_valid = False
        else:
            logger.info(
                f"✅ Hook 길이 적절: {first_sentence_duration:.2f}초 (목표: {max_hook_duration}초 이내)"
            )
        
        # 2. 강력한 Hook 기법 검증
        hook_techniques = {
            "question": r"^\s*[가-힣a-zA-Z]*\?|^[가-힣a-zA-Z]*\s+[가-힣a-zA-Z]*\?",  # 질문
            "shocking": r"절대|절대로|never|don't|never|absolutely|completely",  # 충격적 진술
            "conclusion_first": r"^[가-힣a-zA-Z]*는|^[가-힣a-zA-Z]*은|^[가-힣a-zA-Z]*이|^[가-힣a-zA-Z]*가|^The|^This|^That",  # 결론 먼저
        }
        
        has_technique = False
        for technique_name, pattern in hook_techniques.items():
            if re.search(pattern, first_sentence, re.IGNORECASE):
                has_technique = True
                logger.info(f"✅ Hook 기법 감지: {technique_name}")
                break
        
        if not has_technique:
            issues.append(
                "⚠️ 강력한 Hook 기법이 감지되지 않음 (질문/충격적 진술/결론 먼저 제시 권장)"
            )
            # 경고만 표시 (실패로 처리하지 않음)
        
        # 3. 금지 사항 검증
        forbidden_patterns = [
            r"안녕|hello|hi|greetings",  # 인사
            r"로고|logo|브랜드|brand",  # 로고
            r"시작|start|beginning",  # 느린 시작
        ]
        
        for pattern in forbidden_patterns:
            if re.search(pattern, first_sentence, re.IGNORECASE):
                issues.append(f"❌ 금지된 패턴 감지: '{pattern}' (인사/로고/느린 시작 금지)")
                is_valid = False
        
        return is_valid, issues

    def is_script_unique(self, script_sentences: List[str]) -> bool:
        """Checks if the script is unique compared to recent scripts."""
        if not script_sentences or len(script_sentences) < 3:
            return True  # Skip check if too short

        try:
            # Import here to avoid circular dependency if possible, or assume it's available
            from src.pipeline.database import VideoDatabase

            db = VideoDatabase()
            recent_scripts = db.get_recent_scripts(limit=10)

            if not recent_scripts:
                return True

            # Hash first 3 sentences of current script
            current_preview = " ".join(script_sentences[:3])
            current_hash = hashlib.md5(current_preview.encode()).hexdigest()

            for recent_script in recent_scripts:
                if not recent_script:
                    continue

                # Hash first 3 sentences of recent script
                recent_sentences = recent_script.split("\n")[:3]
                recent_preview = " ".join(recent_sentences)
                recent_hash = hashlib.md5(recent_preview.encode()).hexdigest()

                # Check for exact match
                if current_hash == recent_hash:
                    logger.warning(
                        f"⚠️ Duplicate script detected: {current_preview[:100]}..."
                    )
                    return False

                # Check for similarity
                similarity = self._calculate_similarity(current_preview, recent_preview)
                if similarity > 0.8:  # 80% similarity threshold
                    logger.warning(
                        f"⚠️ Similar script detected (Similarity: {similarity:.2%})"
                    )
                    return False

            return True
        except Exception as e:
            logger.warning(f"⚠️ Script uniqueness check failed: {e}")
            return True  # Pass on error

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculates simple word-based similarity between two texts."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0
