import json
import re
import sys
import os
import asyncio
import logging
import time

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, project_root)

from services.llm_service import LLMService
from lib.generating_question import generate_question_v2_prompt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

llm_service = LLMService()

enabler_list = [
    "1. Enabler 1: Principles, Policies, and Frameworks (jumlah indikator: 10)",
    "2. Enabler 2: Processes (jumlah indikator: 7)",
    "3. Enabler 3: Organizational Structures (jumlah indikator: 8)",
    "4. Enabler 4: Information (jumlah indikator: 11)",
    "5. Enabler 5: Culture, Ethics, and Behavior (jumlah indikator: 10)",
    "6. Enabler 6: People, Skills, and Competences (jumlah indikator: 5)",
    "7. Enabler 7: Services, Infrastructure, and Applications (jumlah indikator: 11)"
]


def parse_questions_to_json(raw_response, enabler_name="Unknown"):
    """Enhanced parser that can extract from various formats"""
    questions = []
    
    # Try to find structured format first
    # Pattern: numbered with Indicator/Question
    pattern1 = r'(\d+)\.\s+\*\*Indicator\*\*:\s*(.+?)\n\s+\*\*Question\*\*:\s*["\"]?(.+?)["\"]?(?=\n\n|\n\d+\.|\Z)'
    matches = re.findall(pattern1, raw_response, re.DOTALL | re.MULTILINE)
    
    if matches:
        logger.info(f"✓ Structured format found for {enabler_name}: {len(matches)} questions")
        for num, indicator, question in matches:
            questions.append({
                "indicator": indicator.strip(),
                "question": question.strip().strip('"\'')
            })
        return questions
    
    # Fallback: Extract questions and try to infer indicators
    logger.warning(f"⚠ Using fallback extraction for {enabler_name}")
    
    # Split by numbered items
    items = re.split(r'\n(?=\d+\.)', raw_response)
    
    for item in items:
        # Try to find question (ends with ?)
        question_match = re.search(r'["\"]?([^"]+\?)["\"]?', item)
        if question_match:
            question = question_match.group(1).strip()
            
            # Try to extract indicator from the item
            # Look for keywords that might indicate the indicator
            indicator = "Extracted from context"
            
            # Try to find text before the question
            text_before = item.split(question)[0] if question in item else ""
            if text_before:
                # Clean and take meaningful part
                indicator_candidate = text_before.strip()
                # Remove numbering and common words
                indicator_candidate = re.sub(r'^\d+\.\s*', '', indicator_candidate)
                if len(indicator_candidate) > 10 and len(indicator_candidate) < 200:
                    indicator = indicator_candidate
            
            questions.append({
                "indicator": indicator,
                "question": question
            })
    
    logger.info(f"Fallback extracted {len(questions)} questions for {enabler_name}")
    return questions


async def create_question_from_text():
    """Generate questions using LLMService"""
    results = []
    
    for idx, enabler in enumerate(enabler_list, 1):
        enabler_name = enabler.split(':')[1].split('(')[0].strip()
        logger.info(f"Processing Enabler {idx}/7: {enabler_name}")
        
        messages = [
            {
                "role": "user",
                "content": f"enabler yang difokuskan saat ini: {enabler}\n\n{generate_question_v2_prompt}\n\nenabler yang difokuskan saat ini: {enabler}"
            }
        ]

        response = await llm_service.call_llm(
            messages=messages,
            max_tokens=4000,
            temperature=0.7
        )

        result = {
            "enabler": enabler,
            "response": response
        }
    
        results.append(result)
        logger.info(f"Completed Enabler {idx}/7")
        
        await asyncio.sleep(1)
    
    return results


def structure_all_enablers(raw_data):
    """Convert raw LLM responses into well-structured JSON"""
    structured_data = {
        "metadata": {
            "model": "DFR Capability Maturity Model",
            "version": "2.0",
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_enablers": 7,
            "total_indicators": 62,
            "scale": {
                "1": {"level": "Initial", "description": "Tidak ada struktur atau proses yang diterapkan"},
                "2": {"level": "Managed", "description": "Beberapa proses mulai dilakukan"},
                "3": {"level": "Defined", "description": "Proses telah terdokumentasi"},
                "4": {"level": "Quantitatively Managed", "description": "Proses terkelola dengan evaluasi berbasis data"},
                "5": {"level": "Optimized", "description": "Proses dioptimalkan dan terintegrasi"}
            }
        },
        "enablers": []
    }
    
    for item in raw_data:
        enabler_info = item["enabler"]
        response = item["response"]
        
        enabler_match = re.match(
            r'(\d+)\.\s+Enabler\s+\d+:\s+(.*?)\s+\(jumlah indikator:\s+(\d+)\)', 
            enabler_info
        )
        
        if enabler_match:
            enabler_num = int(enabler_match.group(1))
            enabler_name = enabler_match.group(2)
            indicator_count = int(enabler_match.group(3))
            
            # Parse with enabler name for better logging
            questions = parse_questions_to_json(response, enabler_name)
            
            enabler_obj = {
                "enabler_id": enabler_num,
                "enabler_name": enabler_name,
                "total_indicators": indicator_count,
                "questions_parsed": len(questions),
                "questions": questions
            }
            
            structured_data["enablers"].append(enabler_obj)
            
            status = "✓" if len(questions) > 0 else "✗"
            logger.info(f"{status} Enabler {enabler_num}: Parsed {len(questions)}/{indicator_count} questions")
            
            # Log sample if parsed successfully
            if questions:
                sample = questions[0]
                logger.info(f"  Sample Q: {sample['question'][:60]}...")
    
    return structured_data


def debug_failed_parsing(raw_data):
    """Debug function to check raw responses for failed enablers"""
    logger.info("\n" + "="*60)
    logger.info("DEBUGGING FAILED PARSING")
    logger.info("="*60)
    
    for item in raw_data:
        enabler_info = item["enabler"]
        response = item["response"]
        
        enabler_match = re.match(r'(\d+)\.\s+Enabler\s+\d+:\s+(.*?)\s+\(', enabler_info)
        if enabler_match:
            enabler_num = int(enabler_match.group(1))
            enabler_name = enabler_match.group(2)
            
            # Parse
            questions = parse_questions_to_json(response, enabler_name)
            
            if len(questions) == 0:
                logger.warning(f"\n⚠ Enabler {enabler_num} ({enabler_name}) - NO QUESTIONS PARSED")
                logger.warning("First 500 chars of response:")
                logger.warning(response[:500])
                logger.warning("Last 200 chars of response:")
                logger.warning(response[-200:])


async def main():
    """Main async function"""
    try:
        start_time = time.time()
        logger.info("Starting question generation...")
        
        raw_questions = await create_question_from_text()
        
        # Debug first
        debug_failed_parsing(raw_questions)
        
        structured_json = structure_all_enablers(raw_questions)
        
        # Save files
        raw_output = "/Users/tiarasabrina/Documents/PROJECT/AI/df_readiness/database/generated_questions_raw.json"
        with open(raw_output, 'w', encoding='utf-8') as f:
            json.dump(raw_questions, f, indent=2, ensure_ascii=False)
        logger.info(f"Raw responses saved to {raw_output}")
        
        structured_output = "/Users/tiarasabrina/Documents/PROJECT/AI/df_readiness/database/generated_questions_structured.json"
        with open(structured_output, 'w', encoding='utf-8') as f:
            json.dump(structured_json, f, indent=2, ensure_ascii=False)
        logger.info(f"Structured JSON saved to {structured_output}")
        
        # Summary
        calc_time = time.time() - start_time
        logger.info(f"\n{'='*60}")
        logger.info(f"Generation Complete!")
        logger.info(f"{'='*60}")
        logger.info(f"Time taken: {calc_time:.2f} seconds")
        logger.info(f"Total Enablers: {len(structured_json['enablers'])}")
        
        total_questions = sum(e['questions_parsed'] for e in structured_json['enablers'])
        logger.info(f"Total Questions Parsed: {total_questions}")
        
        logger.info(f"\nBreakdown per Enabler:")
        for enabler in structured_json['enablers']:
            status = "✓" if enabler['questions_parsed'] > 0 else "✗"
            logger.info(
                f"  {status} {enabler['enabler_id']}. {enabler['enabler_name']}: "
                f"{enabler['questions_parsed']}/{enabler['total_indicators']} questions"
            )
        logger.info(f"{'='*60}\n")
            
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())