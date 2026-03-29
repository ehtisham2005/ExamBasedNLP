import re
import logging
from typing import List, Set
from loader import load_text_file

# Configure logging for production monitoring
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ExamParser:
    """
    Universal subject-agnostic parser for extracting structured data from 
    unstructured Syllabus and Previous Year Question (PYQ) text files.
    """

    def __init__(self, syllabus_path: str = "data/syllabus.txt", pyqs_path: str = "data/pyqs.txt"):
        self.syllabus_path = syllabus_path
        self.pyqs_path = pyqs_path
        
        # Generalized Regex: Detects structural headers across subjects
        # Matches: "Module 1", "Unit I", "Chapter 5", "Part A", "Section 2"
        self.header_pattern = re.compile(
            r'^\s*(Module|Unit|Chapter|Section|Part|Block)\s+([0-9]+|[IVXLC]+|[:\-A-Z])[:\-]?.*', 
            re.IGNORECASE
        )
        
        # Flexible Question Detection: Handles diverse exam formatting
        # Matches: "1.", "1)", "Q1:", "Question 1.", "22. ", "a) "
        self.question_start_pattern = re.compile(
            r'^\s*(Question\s+)?\d+[\.\)\:]\s+|^\s*Q\d+[\.\)\:]\s+', 
            re.IGNORECASE
        )

    def clean_topic(self, text: str) -> str:
        """
        The 'De-Noiser': Removes academic fluff so the AI focuses on core concepts.
        Refined to be more aggressive for subject-agnostic compatibility.
        """
        # 1. Remove parenthetical context (e.g., "Cost (Human Resources)" -> "Cost")
        text = re.sub(r'\(.*?\)', '', text)
        
        # 2. Remove syllabus artifacts/bullets (e.g., "1.1 Topic", "a) Topic")
        text = re.sub(r'^\s*([0-9]+(\.[0-9]+)*|[a-z])[\.\)\-]\s*', '', text, flags=re.IGNORECASE)
        
        # 3. Strip leading/trailing punctuation and common syllabus junk
        text = text.strip(" :.-–—()[]")
        
        # 4. Filter out generic academic stop-words that don't represent unique topics
        academic_fluff = {"introduction", "overview", "basics", "summary", "conclusion", "references", "preface"}
        if text.lower() in academic_fluff:
            return ""

        return text

    def parse_syllabus(self) -> List[str]:
        """
        Extracts individual topics. Splits multi-topic lines and cleans them.
        Filters headers like "Unit 1: Overview".
        """
        raw_lines = load_text_file(self.syllabus_path, "Syllabus")
        if not raw_lines:
            logger.warning(f"Syllabus file at {self.syllabus_path} is empty or missing.")
            return []

        extracted_topics: Set[str] = set()
        
        for line in raw_lines:
            line_str = line.strip()
            
            # Skip empty lines or structural headers
            if not line_str or self.header_pattern.match(line_str):
                continue
            
            # Split by common delimiters (comma, semicolon, bullet points)
            # This ensures "Cohesion, Coupling" becomes two distinct nodes
            parts = re.split(r'[,;•\t]', line_str)
            
            for part in parts:
                topic = self.clean_topic(part)
                
                # Filter: Must be long enough to be a concept and not just a number/artifact
                if len(topic) > 3 and not topic.replace('.', '').isdigit():
                    extracted_topics.add(topic)
        
        final_list = sorted(list(extracted_topics))
        logger.info(f"Successfully parsed {len(final_list)} unique topics from syllabus.")
        return final_list

    def parse_pyqs(self) -> List[str]:
        """
        Extracts individual questions from the PYQs file. 
        Normalizes multi-line questions into single semantic blocks for SBERT.
        """
        # Load as full content to handle complex multi-line breaks correctly
        try:
            with open(self.pyqs_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error reading PYQs: {e}")
            return []

        # Split content into distinct questions using the numbering pattern
        # We use re.split to handle questions that don't start at the beginning of a line
        raw_splits = self.question_start_pattern.split(content)
        
        valid_questions: List[str] = []
        for q in raw_splits:
            if not q:
                continue
            
            # Normalize whitespace: convert multiple spaces/newlines into one space
            # This is critical for reliable SBERT embedding matches
            normalized_q = " ".join(q.split()).strip()
            
            # Ensure the question has enough context to be analyzable
            if len(normalized_q) > 15:
                valid_questions.append(normalized_q)

        logger.info(f"Successfully parsed {len(valid_questions)} individual questions from PYQs.")
        return valid_questions

if __name__ == "__main__":
    # Test Block for Manual Verification
    parser = ExamParser()
    topics = parser.parse_syllabus()
    questions = parser.parse_pyqs()
    
    print(f"\n--- UNIVERSAL PARSER TEST ---")
    print(f"Total Topics: {len(topics)}")
    print(f"Total Questions: {len(questions)}")
    if topics: 
        print(f"Top 5 Cleaned Topics: {topics[:5]}")
    if questions:
        print(f"First Question Block: {questions[0][:100]}...")