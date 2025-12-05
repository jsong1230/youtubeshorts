import hashlib
from typing import List
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ScriptValidator:
    """Handles validation of generated scripts."""

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
