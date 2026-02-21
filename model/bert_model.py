"""
BERT Model for Semantic Answer Similarity
Uses sentence-transformers (all-MiniLM-L6-v2) to calculate semantic similarity between answers
"""

from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


class BERTModel:
    """
    A class to handle BERT-based semantic similarity calculations
    """
    
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        """
        Initialize the BERT model
        """
        print(f"Loading sentence-transformers model: {model_name}")
        self.model = SentenceTransformer(model_name)
        print("Model loaded successfully!")
    
    def calculate_similarity(self, correct_answer, student_answer):
        """
        Calculate semantic similarity between two answers
        
        Args:
            correct_answer (str): The correct/model answer
            student_answer (str): The student's submitted answer
            
        Returns:
            float: Similarity score between 0 and 1
        """
        if not correct_answer or not student_answer:
            return 0.0
        
        # Encode both answers
        embeddings = self.model.encode([correct_answer, student_answer])
        
        # Calculate cosine similarity
        similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
        
        return float(similarity)
    
    def calculate_marks(self, similarity_score, max_marks=100):
        """
        Calculate marks based on similarity score
        
        Args:
            similarity_score (float): Similarity score between 0 and 1
            max_marks (int): Maximum marks for the answer
            
        Returns:
            float: Calculated marks
        """
        # Marks are directly proportional to similarity score
        marks = similarity_score * max_marks
        return round(marks, 2)
    
    def evaluate_answer(self, correct_answer, student_answer, max_marks=100):
        """
        Complete evaluation of a student's answer
        
        Args:
            correct_answer (str): The correct/model answer
            student_answer (str): The student's submitted answer
            max_marks (int): Maximum marks for the answer
            
        Returns:
            dict: Dictionary containing similarity score and marks
        """
        similarity = self.calculate_similarity(correct_answer, student_answer)
        marks = self.calculate_marks(similarity, max_marks)
        
        return {
            'similarity_score': round(similarity * 100, 2),  # Convert to percentage
            'marks': marks,
            'max_marks': max_marks,
            'correct_answer': correct_answer,
            'student_answer': student_answer
        }


# Global model instance
bert_model = None


def get_bert_model():
    """
    Get or initialize the global BERT model instance
    
    Returns:
        BERTModel: The initialized BERT model
    """
    global bert_model
    if bert_model is None:
        bert_model = BERTModel()
    return bert_model


def evaluate_answer(correct_answer, student_answer, max_marks=100):
    """
    Convenience function to evaluate an answer
    
    Args:
        correct_answer (str): The correct/model answer
        student_answer (str): The student's submitted answer
        max_marks (int): Maximum marks for the answer
        
    Returns:
        dict: Dictionary containing similarity score and marks
    """
    model = get_bert_model()
    return model.evaluate_answer(correct_answer, student_answer, max_marks)


if __name__ == "__main__":
    # Test the model
    model = BERTModel()
    
    # Test cases
    test_cases = [
        ("The capital of France is Paris.", "Paris is the capital of France."),
        ("Water boils at 100 degrees Celsius.", "At 100°C water starts to boil."),
        ("Python is a programming language.", "Python is a snake."),
    ]
    
    print("\n" + "="*60)
    print("BERT Model Test Results")
    print("="*60)
    
    for correct, student in test_cases:
        result = model.evaluate_answer(correct, student)
        print(f"\nCorrect Answer: {correct}")
        print(f"Student Answer: {student}")
        print(f"Similarity Score: {result['similarity_score']}%")
        print(f"Marks: {result['marks']}/{result['max_marks']}")
        print("-"*60)
