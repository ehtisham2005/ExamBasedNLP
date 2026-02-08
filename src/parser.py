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
        
        self.header_pattern = re.compile(r'^(Module|Unit|Chapter)\s+\d+[:\-]?.*', re.IGNORECASE)
        
        self.question_start_pattern = re.compile(r'^\s*\d+[\.\)]\s+')

    def parse_syllabus(self) -> List[str]:
        """
        Extracts individual topics from the syllabus. 
        Filters out structural headers and splits multi-topic lines.
        """
        raw_lines = load_text_file(self.syllabus_path, "Syllabus")
        if not raw_lines:
            logger.warning(f"Syllabus file at {self.syllabus_path} is empty or missing.")
            return []

        extracted_topics: Set[str] = set()
        
        for line in raw_lines:
            clean_line = line.strip()
            
            if not clean_line or self.header_pattern.match(clean_line):
                continue
            
            parts = re.split(r'[,;]', clean_line)
            for part in parts:
                topic = part.strip()
                if len(topic) > 3:
                    extracted_topics.add(topic)
        
        logger.info(f"Successfully parsed {len(extracted_topics)} unique topics from syllabus.")
        return sorted(list(extracted_topics))

    def parse_pyqs(self) -> List[str]:
        """
        Extracts individual questions from the PYQs file. 
        Uses regex to identify question starts and handles multi-line questions.
        """
        raw_lines = load_text_file(self.pyqs_path, "PYQs")
        if not raw_lines:
            logger.warning(f"PYQs file at {self.pyqs_path} is empty or missing.")
            return []

        questions: List[str] = []
        current_question = ""
        
        for line in raw_lines:
            if self.question_start_pattern.match(line):
                if current_question:
                    questions.append(current_question.strip())
                current_question = line.strip()
            else:
                current_question += " " + line.strip()
        
        if current_question:
            questions.append(current_question.strip())
        
        logger.info(f"Successfully parsed {len(questions)} questions from PYQs.")
        return questions

 

if __name__ == "__main__":
    parser = ExamParser()
    topics = parser.parse_syllabus()
    questions = parser.parse_pyqs()
    
    print(f"\n--- PARSER TEST ---")
    print(f"Total Topics Found: {len(topics)}")
    print(f"Total Questions Found: {len(questions)}")
    if topics: print(f"Sample Topic: {topics[15] }")
    for i in range(50):
        print(f"Topic {i+1}: {topics[i]}")
    if questions: print(f"Sample Question: {questions[0][:75]}...")