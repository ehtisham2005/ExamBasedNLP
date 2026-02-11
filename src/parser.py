import re
import logging
from typing import List, Set
from loader import load_text_file

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ExamParser:
    """
    Advanced parser for extracting structured data from unstructured 
    Syllabus and Previous Year Question (PYQ) text files.
    """

    def __init__(self, syllabus_path: str = "data/syllabus.txt", pyqs_path: str = "data/pyqs.txt"):
        self.syllabus_path = syllabus_path
        self.pyqs_path = pyqs_path
        
        # Regex to detect Structural Headers (e.g. "Module 1", "Unit 2")
        self.header_pattern = re.compile(r'^(Module|Unit|Chapter)\s+\d+[:\-]?.*', re.IGNORECASE)
        
        # Regex to detect Question Starts (e.g. "1.", "2)", "Q1")
        self.question_start_pattern = re.compile(r'^\s*(Q)?\d+[\.\)]\s+')

    def clean_topic(self, text: str) -> str:
        """
        The 'De-Noiser':
        Removes academic fluff so the AI focuses on the Core Concept.
        Example: "Cost (Human Resources)" -> "Cost"
        Example: "Time-scale)" -> "Time-scale"
        """
        # 1. Remove text inside parentheses (often context, not the topic)
        # We replace it with nothing to isolate the main noun.
        text = re.sub(r'\([^)]*\)', '', text)
        
        # 2. Remove syllabus artifacts like "1.1", "a)", etc.
        text = re.sub(r'^\s*\d+[\.\)]\s*', '', text)
        text = re.sub(r'^\s*[a-z][\.\)]\s*', '', text)

        # 3. Remove trailing punctuation/junk
        text = re.sub(r'[):.-]+$', '', text)
        
        # 4. Remove generic words if they appear alone (optional but helps)
        if text.lower() in ["introduction", "overview", "basics"]:
            return ""

        return text.strip()

    def parse_syllabus(self) -> List[str]:
        """
        Extracts individual topics from the syllabus. 
        Splits multi-topic lines and cleans them.
        """
        raw_lines = load_text_file(self.syllabus_path, "Syllabus")
        if not raw_lines:
            logger.warning(f"Syllabus file at {self.syllabus_path} is empty or missing.")
            return []

        extracted_topics: Set[str] = set()
        
        for line in raw_lines:
            line = line.strip()
            
            # Skip empty lines or Headers
            if not line or self.header_pattern.match(line):
                continue
            
            # Split by common delimiters (comma, semicolon)
            parts = re.split(r'[,;]', line)
            
            for part in parts:
                # Apply the Intelligent Cleaning
                topic = self.clean_topic(part)
                
                # Filter: Topic must be meaningful (more than 2 chars)
                # and not just a number
                if len(topic) > 2 and not topic.isdigit():
                    extracted_topics.add(topic)
        
        # Sort alphabetically for consistent processing
        final_list = sorted(list(extracted_topics))
        logger.info(f"Successfully parsed {len(final_list)} unique topics from syllabus.")
        return final_list

    def parse_pyqs(self) -> List[str]:
        """
        Extracts individual questions from the PYQs file. 
        Handles multi-line questions.
        """
        raw_lines = load_text_file(self.pyqs_path, "PYQs")
        if not raw_lines:
            logger.warning(f"PYQs file at {self.pyqs_path} is empty or missing.")
            return []

        questions: List[str] = []
        current_question = ""
        
        for line in raw_lines:
            # If line starts with "1." or "Q1", it's a new question
            if self.question_start_pattern.match(line):
                if current_question:
                    questions.append(current_question.strip())
                # Start new question (remove the number for cleaner NLP matching)
                # e.g. "1. Define Agile" -> "Define Agile"
                current_question = re.sub(r'^\s*(Q)?\d+[\.\)]\s+', '', line).strip()
            else:
                # Append to previous question (continuation line)
                current_question += " " + line.strip()
        
        # Append the very last question
        if current_question:
            questions.append(current_question.strip())
        
        # Filter out short/empty questions
        valid_questions = [q for q in questions if len(q) > 10]

        logger.info(f"Successfully parsed {len(valid_questions)} questions from PYQs.")
        return valid_questions

if __name__ == "__main__":
    # Test Block
    parser = ExamParser()
    topics = parser.parse_syllabus()
    questions = parser.parse_pyqs()
    
    print(f"\n--- PARSER TEST ---")
    print(f"Total Topics: {len(topics)}")
    if topics: 
        print(f"Sample Cleaned Topics: {topics[:5]}")
        # Verify specific tricky topics
        print("Checking for 'Cost'...", [t for t in topics if "Cost" in t])