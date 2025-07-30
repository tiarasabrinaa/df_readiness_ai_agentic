# utils/helpers.py
import re
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd

def clean_text(text: str) -> str:
    """Clean and normalize text input"""
    if not text:
        return ""
    
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove special characters that might interfere with processing
    text = re.sub(r'[^\w\s\-.,!?():]', '', text)
    
    return text

def extract_keywords(text: str) -> List[str]:
    """Extract keywords from text for categorization"""
    if not text:
        return []
    
    # Common technical keywords for categorization
    keywords = {
        'security': ['security', 'keamanan', 'cyber', 'attack', 'threat', 'vulnerability'],
        'forensics': ['forensic', 'investigation', 'evidence', 'analysis', 'incident'],
        'network': ['network', 'jaringan', 'traffic', 'monitoring', 'firewall'],
        'data': ['data', 'backup', 'recovery', 'storage', 'database'],
        'compliance': ['compliance', 'audit', 'policy', 'governance', 'regulation'],
        'tools': ['tool', 'software', 'application', 'system', 'platform']
    }
    
    text_lower = text.lower()
    found_categories = []
    
    for category, terms in keywords.items():
        if any(term in text_lower for term in terms):
            found_categories.append(category)
    
    return found_categories

def generate_session_id() -> str:
    """Generate unique session ID"""
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    random_part = hashlib.md5(str(datetime.utcnow().microsecond).encode()).hexdigest()[:8]
    return f"df_session_{timestamp}_{random_part}"

def calculate_assessment_duration(start_time: datetime, end_time: datetime) -> Dict[str, Any]:
    """Calculate assessment duration and provide formatted output"""
    if not end_time:
        end_time = datetime.utcnow()
    
    duration = end_time - start_time
    
    total_seconds = int(duration.total_seconds())
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    
    return {
        'total_seconds': total_seconds,
        'minutes': minutes,
        'seconds': seconds,
        'formatted': f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
    }

def validate_user_input(user_input: str, min_length: int = 5, max_length: int = 1000) -> Dict[str, Any]:
    """Validate user input for assessment"""
    if not user_input or not user_input.strip():
        return {
            'valid': False,
            'error': 'Input cannot be empty'
        }
    
    cleaned_input = clean_text(user_input)
    
    if len(cleaned_input) < min_length:
        return {
            'valid': False,
            'error': f'Input too short. Minimum {min_length} characters required.'
        }
    
    if len(cleaned_input) > max_length:
        return {
            'valid': False,
            'error': f'Input too long. Maximum {max_length} characters allowed.'
        }
    
    return {
        'valid': True,
        'cleaned_input': cleaned_input
    }

def categorize_industry(industry_text: str) -> str:
    """Categorize industry from text input"""
    if not industry_text:
        return "Unknown"
    
    industry_lower = industry_text.lower()
    
    categories = {
        'Financial Services': ['bank', 'finance', 'fintech', 'insurance', 'investment'],
        'Healthcare': ['hospital', 'healthcare', 'medical', 'clinic', 'pharmaceutical'],
        'Government': ['government', 'pemerintah', 'public sector', 'municipal', 'federal'],
        'Education': ['university', 'school', 'education', 'academic', 'campus'],
        'Technology': ['tech', 'software', 'IT', 'startup', 'developer'],
        'Manufacturing': ['manufacturing', 'factory', 'production', 'industrial'],
        'Retail': ['retail', 'ecommerce', 'shop', 'store', 'merchant'],
        'Telecommunications': ['telco', 'telecommunications', 'ISP', 'network provider'],
        'Energy': ['energy', 'oil', 'gas', 'power', 'utility'],
        'Transportation': ['transport', 'logistics', 'shipping', 'airline']
    }
    
    for category, keywords in categories.items():
        if any(keyword in industry_lower for keyword in keywords):
            return category
    
    return "Other"

def format_assessment_report(assessment_result: Dict[str, Any], user_profile: Dict[str, Any]) -> str:
    """Format assessment result into readable report"""
    report = f"""
# Digital Forensics Readiness Assessment Report

## User Profile
- **Industry**: {user_profile.get('industry', 'N/A')}
- **Role**: {user_profile.get('role', 'N/A')}
- **Experience Level**: {user_profile.get('experience_level', 'N/A')}
- **Company Size**: {user_profile.get('company_size', 'N/A')}

## Assessment Results
- **Overall Level**: {assessment_result.get('overall_level', 'N/A')}
- **Overall Score**: {assessment_result.get('overall_score', 0)}/100

### Strengths
"""
    
    strengths = assessment_result.get('strengths', [])
    for strength in strengths:
        report += f"- {strength}\n"
    
    report += "\n### Areas for Improvement\n"
    
    weaknesses = assessment_result.get('weaknesses', [])
    for weakness in weaknesses:
        report += f"- {weakness}\n"
    
    report += "\n### Recommendations\n"
    
    recommendations = assessment_result.get('recommendations', [])
    for rec in recommendations:
        report += f"- {rec}\n"
    
    report += f"\n### Detailed Analysis\n{assessment_result.get('detailed_analysis', 'No detailed analysis available.')}"
    
    return report

def parse_csv_questions(csv_path: str) -> List[Dict[str, Any]]:
    """Parse CSV file and return structured questions data"""
    try:
        df = pd.read_csv(csv_path)
        
        # Validate required columns
        required_columns = ['level', 'question', 'why_matter']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        questions = []
        for index, row in df.iterrows():
            # Clean and validate data
            level = str(row['level']).strip().lower()
            question = clean_text(str(row['question']))
            why_matter = clean_text(str(row['why_matter']))
            
            if not all([level, question, why_matter]):
                print(f"Warning: Skipping row {index} due to missing data")
                continue
            
            # Validate level
            if level not in ['basic', 'intermediate', 'advanced']:
                print(f"Warning: Invalid level '{level}' in row {index}, defaulting to 'basic'")
                level = 'basic'
            
            questions.append({
                'level': level,
                'question': question,
                'why_matter': why_matter,
                'keywords': extract_keywords(question)
            })
        
        return questions
        
    except Exception as e:
        print(f"Error parsing CSV: {str(e)}")
        return []

def log_assessment_event(event_type: str, user_id: str, session_id: str, data: Dict[str, Any] = None):
    """Log assessment events for monitoring and analytics"""
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'event_type': event_type,
        'user_id': user_id,
        'session_id': session_id,
        'data': data or {}
    }
    
    # In production, this would write to a proper logging system
    print(f"[ASSESSMENT_LOG] {json.dumps(log_entry)}")

def estimate_assessment_difficulty(user_profile: Dict[str, Any]) -> str:
    """Estimate appropriate starting difficulty based on user profile"""
    experience = user_profile.get('experience_level', '').lower()
    role = user_profile.get('role', '').lower()
    awareness = user_profile.get('current_security_awareness', '').lower()
    
    # Score based on different factors
    score = 0
    
    # Experience scoring
    if 'senior' in experience or '5+' in experience or 'expert' in experience:
        score += 3
    elif 'intermediate' in experience or '2-5' in experience:
        score += 2
    else:
        score += 1
    
    # Role scoring
    security_roles = ['security', 'ciso', 'analyst', 'forensic', 'incident', 'soc']
    if any(role_keyword in role for role_keyword in security_roles):
        score += 2
    elif any(tech_role in role for tech_role in ['admin', 'engineer', 'developer']):
        score += 1
    
    # Awareness scoring
    if 'advanced' in awareness or 'expert' in awareness:
        score += 2
    elif 'intermediate' in awareness or 'familiar' in awareness:
        score += 1
    
    # Determine difficulty
    if score >= 6:
        return 'advanced'
    elif score >= 4:
        return 'intermediate'
    else:
        return 'basic'

class AssessmentAnalyzer:
    """Helper class for analyzing assessment patterns and providing insights"""
    
    @staticmethod
    def analyze_response_pattern(answers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user response patterns across the assessment"""
        if not answers:
            return {'pattern': 'insufficient_data'}
        
        # Analyze response lengths
        response_lengths = [len(answer.get('user_answer', '')) for answer in answers]
        avg_length = sum(response_lengths) / len(response_lengths)
        
        # Analyze response consistency
        level_performance = {}
        for answer in answers:
            level = answer.get('question_level', 'unknown')
            if level not in level_performance:
                level_performance[level] = []
            
            # This would normally include scoring from LLM analysis
            level_performance[level].append(len(answer.get('user_answer', '')))
        
        return {
            'avg_response_length': avg_length,
            'total_responses': len(answers),
            'level_distribution': {level: len(responses) for level, responses in level_performance.items()},
            'engagement_level': 'high' if avg_length > 100 else 'medium' if avg_length > 50 else 'low'
        }
    
    @staticmethod
    def generate_improvement_plan(assessment_result: Dict[str, Any], user_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate step-by-step improvement plan based on assessment results"""
        overall_level = assessment_result.get('overall_level', 'basic').lower()
        weaknesses = assessment_result.get('weaknesses', [])
        
        improvement_plan = []
        
        # Basic improvements
        if overall_level == 'basic':
            improvement_plan.extend([
                {
                    'priority': 'high',
                    'timeframe': '1-2 weeks',
                    'action': 'Establish formal incident response policy',
                    'description': 'Create and document basic incident response procedures'
                },
                {
                    'priority': 'high', 
                    'timeframe': '2-4 weeks',
                    'action': 'Implement comprehensive backup strategy',
                    'description': 'Set up regular, tested backup procedures with offsite storage'
                }
            ])
        
        # Intermediate improvements
        elif overall_level == 'intermediate':
            improvement_plan.extend([
                {
                    'priority': 'medium',
                    'timeframe': '4-6 weeks',
                    'action': 'Deploy forensic tools and training',
                    'description': 'Acquire basic forensic tools and provide team training'
                },
                {
                    'priority': 'medium',
                    'timeframe': '2-3 months',
                    'action': 'Enhance log management capabilities',
                    'description': 'Implement centralized logging and retention policies'
                }
            ])
        
        # Advanced improvements
        else:
            improvement_plan.extend([
                {
                    'priority': 'low',
                    'timeframe': '3-6 months',
                    'action': 'Implement advanced threat hunting',
                    'description': 'Deploy proactive threat hunting capabilities'
                }
            ])
        
        return improvement_plan
    
import logging

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    return logging.getLogger("df_readiness")