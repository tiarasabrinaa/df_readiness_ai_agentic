from typing import List, Dict

class CalculateScore:
    """
    Calculator for contribution-based scoring
    Formula: (contribution_max / answer) * sum_contribution_max
    """
    
    @staticmethod
    def calculate_single_score(contribution_max: int, answer: int, sum_contribution_max: int) -> float:
        """
        Calculate score for single answer
        
        Args:
            contribution_max: Maximum contribution for this question
            answer: User's answer (1-4)
            sum_contribution_max: Sum of all contribution_max values
            
        Returns:
            Calculated score
        """
        if answer == 0:
            return 0.0
        
        score = (contribution_max / answer) * sum_contribution_max
        return round(score, 2)
    
    @staticmethod
    def calculate_enabler_score(answers: List[int], test_questions: List[Dict], sum_contribution_max: int) -> Dict:
        """
        Calculate total score for each enabler
        
        Args:
            answers: List of user's answers
            test_questions: List of test questions with enabler info
            sum_contribution_max: Sum of all contribution_max values
            
        Returns:
            Dictionary with scores per enabler
        """
        enabler_scores = {}
        
        for i, answer in enumerate(answers):
            question = test_questions[i]
            contribution_max = question.get("contribution_max", 0)
            enabler = question.get("enabler", "unknown")
            
            # Calculate score for the current question
            score = CalculateScore.calculate_single_score(contribution_max, answer, sum_contribution_max)
            
            # Aggregate score by enabler
            if enabler not in enabler_scores:
                enabler_scores[enabler] = 0.0
            enabler_scores[enabler] += score
        
        return enabler_scores
