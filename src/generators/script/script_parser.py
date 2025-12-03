import re
from typing import List
from src.utils.logger import get_logger

logger = get_logger(__name__)

class ScriptParser:
    """Handles parsing of raw AI response into structured script."""

    def parse_script_text(self, script_text: str, max_sentences: int) -> List[str]:
        """Parses script text into a list of sentences."""
        sentences = []
        # Split by newlines
        for line in script_text.split('\n'):
            line = line.strip()
            if not line:
                continue
            # Split by punctuation (splitting long sentences)
            for sent in re.split(r'[.!?。！？]\s+', line):
                sent = sent.strip()
                if sent:
                    sentences.append(sent)
        
        # Filter unnecessary text
        filter_keywords = [
            '배경음악', '음악', 'BGM', 'bgm', '배경', '시작', '종료',
            '자막', '타이틀', '제목', '인트로', '아웃트로',
            '참고', '주의', '설명', '참고사항'
        ]
        
        filtered_sentences = []
        for s in sentences:
            # Remove numbering or bullet points
            if s.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.',
                           '11.', '12.', '13.', '14.', '15.', '16.', '-', '*', '•')):
                s = re.sub(r'^\d+\.\s*', '', s).strip()
            # Remove too short sentences (min 10 chars)
            if len(s) < 10:
                continue
            # Remove sentences with filter keywords
            if any(keyword in s for keyword in filter_keywords):
                continue
            # Remove script meta-instructions
            lower_s = s.lower()
            if "youtube shorts script" in lower_s or (
                "script" in lower_s and ("youtube" in lower_s or "shorts" in lower_s)
            ):
                continue
            # Remove parenthetical explanations
            s = re.sub(r'\([^)]*\)', '', s).strip()
            s = re.sub(r'\[[^\]]*\]', '', s).strip()
            if s and len(s) >= 10:
                filtered_sentences.append(s)
        
        # Check minimum sentence count
        if len(filtered_sentences) < 12:
            logger.warning(f"⚠️ Insufficient sentences generated ({len(filtered_sentences)}). Re-checking original script.")
            # Try to extract more sentences from original text
            all_sentences = re.split(r'[.!?。！？]\s+', script_text)
            for sent in all_sentences:
                sent = sent.strip()
                if len(sent) >= 10 and sent not in filtered_sentences:
                    if not any(keyword in sent for keyword in filter_keywords):
                        filtered_sentences.append(sent)
                        if len(filtered_sentences) >= max_sentences:
                            break
        
        return filtered_sentences

    def remove_repetitive_phrases(self, sentences: List[str]) -> List[str]:
        """Removes repetitive phrases at the end of sentences."""
        if len(sentences) < 3:
            return sentences
        
        # Extract last 5 words of each sentence
        ending_phrases = []
        for sent in sentences:
            words = sent.split()
            if len(words) >= 5:
                ending_phrase = " ".join(words[-5:]).lower()
                ending_phrases.append(ending_phrase)
            else:
                ending_phrases.append("")
        
        # Find repetitive phrases (appearing 3+ times)
        from collections import Counter
        phrase_counts = Counter(ending_phrases)
        repetitive_phrases = {phrase for phrase, count in phrase_counts.items() 
                             if count >= 3 and phrase}
        
        if repetitive_phrases:
            logger.debug(f"⚠️ Repetitive phrases detected: {list(repetitive_phrases)[:2]}")
            
            cleaned_sentences = []
            for sent, ending in zip(sentences, ending_phrases):
                if ending in repetitive_phrases:
                    # Remove last 5 words
                    words = sent.split()
                    if len(words) > 5:
                        cleaned_sent = " ".join(words[:-5]).strip()
                        if cleaned_sent and len(cleaned_sent) > 20:  # Check min length
                            cleaned_sentences.append(cleaned_sent)
                        else:
                            cleaned_sentences.append(sent)  # Keep original if too short
                    else:
                        cleaned_sentences.append(sent)
                else:
                    cleaned_sentences.append(sent)
            
            logger.info(f"✅ Repetitive phrases removed: {len(repetitive_phrases)} patterns")
            return cleaned_sentences
        
        return sentences
