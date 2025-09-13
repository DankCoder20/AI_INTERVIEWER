"""
Evaluator Agent - AI summary and evaluation of interview performance
"""

from typing import Dict, Any, List, Optional
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
import json
import os
from datetime import datetime
from dotenv import load_dotenv
import pathlib

load_dotenv()

class EvaluatorAgent:
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.1-8b-instant",  # Use same working model as other agents
            temperature=0.3,
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
        
        self.evaluation_criteria = {
            "technical_skills": {
                "weight": 0.4,
                "aspects": ["problem_solving", "coding_ability", "algorithm_knowledge", "data_structures"]
            },
            "communication": {
                "weight": 0.25,
                "aspects": ["clarity", "explanation_ability", "questions_asked", "active_listening"]
            },
            "problem_approach": {
                "weight": 0.2,
                "aspects": ["systematic_thinking", "edge_case_consideration", "optimization_awareness"]
            },
            "collaboration": {
                "weight": 0.15,
                "aspects": ["receptiveness_to_hints", "adaptability", "professional_demeanor"]
            }
        }
        
        self.scoring_rubric = {
            "excellent": {"score": 5, "description": "Exceptional performance, exceeds expectations"},
            "good": {"score": 4, "description": "Strong performance, meets expectations well"},
            "satisfactory": {"score": 3, "description": "Adequate performance, meets basic expectations"},
            "needs_improvement": {"score": 2, "description": "Below expectations, areas for development"},
            "inadequate": {"score": 1, "description": "Significantly below expectations"}
        }
    
    def evaluate_interview(self, interview_data: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive evaluation of the interview performance"""
        
        conversation_history = interview_data.get("conversation_history", [])
        candidate_responses = interview_data.get("candidate_responses", [])
        interview_metadata = interview_data.get("metadata", {})
        
        # Generate detailed analysis
        detailed_analysis = self._analyze_performance(conversation_history, candidate_responses)
        
        # Calculate scores for each criteria
        scores = self._calculate_scores(detailed_analysis)
        
        # Generate overall assessment
        overall_assessment = self._generate_overall_assessment(scores, detailed_analysis)
        
        # Create recommendations
        recommendations = self._generate_recommendations(scores, detailed_analysis)
        
        # Compile final evaluation
        evaluation = {
            "evaluation_id": f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "candidate_name": interview_metadata.get("candidate_name", "Unknown"),
            "target_role": interview_metadata.get("target_role", "Unknown"),
            "timestamp": datetime.now().isoformat(),
            "overall_score": self._calculate_overall_score(scores),
            "overall_rating": self._get_rating_from_score(self._calculate_overall_score(scores)),
            "detailed_scores": scores,
            "analysis": detailed_analysis,
            "assessment": overall_assessment,
            "recommendations": recommendations,
            "interview_metadata": {
                "duration_minutes": interview_metadata.get("duration", "unknown"),
                "questions_completed": len(candidate_responses),
                "interview_stage_reached": interview_metadata.get("final_stage", "unknown"),
                "total_conversation_exchanges": len(conversation_history),
                "candidate_responses": candidate_responses
            }
        }
        
        # Automatically save evaluation to files
        self._save_evaluation_files(evaluation)
        
        return evaluation
    
    def _analyze_performance(self, conversation_history: List[Dict], candidate_responses: List[Dict]) -> Dict[str, Any]:
        """Detailed analysis of candidate performance"""
        
        # Prepare conversation context for LLM analysis
        context = self._prepare_conversation_context(conversation_history, candidate_responses)
        
        system_prompt = """You are an expert technical interviewer and evaluator. 
        Analyze this interview conversation and provide detailed insights on the candidate's performance.
        
        Focus on:
        1. Technical Skills: Problem-solving approach, coding ability, technical knowledge
        2. Communication: Clarity of explanation, asking clarifying questions, articulation
        3. Problem Approach: Systematic thinking, consideration of edge cases, optimization
        4. Collaboration: Response to hints, adaptability, professional behavior
        
        Provide specific examples from the conversation to support your analysis.
        
        Format your response as JSON with these sections:
        {
            "technical_skills": {"strengths": [], "areas_for_improvement": [], "examples": []},
            "communication": {"strengths": [], "areas_for_improvement": [], "examples": []},
            "problem_approach": {"strengths": [], "areas_for_improvement": [], "examples": []},
            "collaboration": {"strengths": [], "areas_for_improvement": [], "examples": []},
            "notable_moments": [],
            "red_flags": [],
            "positive_highlights": []
        }"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Interview conversation to analyze:\n\n{context}")
        ]
        
        try:
            response = self.llm.invoke(messages)
            analysis_text = response.content.strip()
            
            # Try to parse as JSON, fallback to structured text
            try:
                analysis = json.loads(analysis_text)
            except json.JSONDecodeError:
                analysis = self._parse_text_analysis(analysis_text)
            
            return analysis
            
        except Exception as e:
            return self._fallback_analysis(str(e))
    
    def _calculate_scores(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate numerical scores for each evaluation criteria"""
        
        scores = {}
        
        for criteria, config in self.evaluation_criteria.items():
            criteria_analysis = analysis.get(criteria, {})
            
            # Calculate score based on strengths vs areas for improvement
            strengths = len(criteria_analysis.get("strengths", []))
            improvements = len(criteria_analysis.get("areas_for_improvement", []))
            
            # Simple scoring algorithm
            if strengths >= 3 and improvements <= 1:
                score = 5  # Excellent
            elif strengths >= 2 and improvements <= 2:
                score = 4  # Good
            elif strengths >= 1 and improvements <= 3:
                score = 3  # Satisfactory
            elif strengths >= 1 or improvements <= 4:
                score = 2  # Needs improvement
            else:
                score = 1  # Inadequate
            
            scores[criteria] = {
                "score": score,
                "rating": self._get_rating_from_score(score),
                "weight": config["weight"],
                "weighted_score": score * config["weight"]
            }
        
        return scores
    
    def _calculate_overall_score(self, scores: Dict[str, Any]) -> float:
        """Calculate weighted overall score"""
        
        total_weighted_score = sum(criteria["weighted_score"] for criteria in scores.values())
        total_weight = sum(criteria["weight"] for criteria in scores.values())
        
        return round(total_weighted_score / total_weight, 2) if total_weight > 0 else 0
    
    def _get_rating_from_score(self, score: float) -> str:
        """Convert numerical score to rating"""
        
        if score >= 4.5:
            return "excellent"
        elif score >= 3.5:
            return "good"
        elif score >= 2.5:
            return "satisfactory"
        elif score >= 1.5:
            return "needs_improvement"
        else:
            return "inadequate"
    
    def _generate_overall_assessment(self, scores: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Generate human-readable overall assessment"""
        
        overall_score = self._calculate_overall_score(scores)
        overall_rating = self._get_rating_from_score(overall_score)
        
        # Get top strengths and improvement areas
        all_strengths = []
        all_improvements = []
        
        for criteria, criteria_analysis in analysis.items():
            if isinstance(criteria_analysis, dict):
                all_strengths.extend(criteria_analysis.get("strengths", []))
                all_improvements.extend(criteria_analysis.get("areas_for_improvement", []))
        
        assessment_templates = {
            "excellent": f"""The candidate demonstrated exceptional performance throughout the interview with an overall score of {overall_score}/5. 
            They showed strong capabilities across all evaluation areas and would be an excellent addition to the team.""",
            
            "good": f"""The candidate performed well in the interview with an overall score of {overall_score}/5. 
            They demonstrated solid technical skills and good communication, with minor areas for development.""",
            
            "satisfactory": f"""The candidate showed adequate performance with an overall score of {overall_score}/5. 
            While they met basic expectations, there are several areas where continued development would be beneficial.""",
            
            "needs_improvement": f"""The candidate's performance was below expectations with an overall score of {overall_score}/5. 
            Significant improvement would be needed in key areas before they would be ready for this role.""",
            
            "inadequate": f"""The candidate's performance was significantly below expectations with an overall score of {overall_score}/5. 
            They would need substantial development before being considered for a technical role."""
        }
        
        base_assessment = assessment_templates.get(overall_rating, "Assessment unavailable.")
        
        # Add specific highlights
        if all_strengths:
            base_assessment += f"\n\nKey strengths observed: {', '.join(all_strengths[:3])}"
        
        if all_improvements:
            base_assessment += f"\n\nAreas for development: {', '.join(all_improvements[:3])}"
        
        return base_assessment
    
    def _generate_recommendations(self, scores: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate actionable recommendations"""
        
        recommendations = {
            "hiring_decision": "",
            "next_steps": [],
            "development_areas": [],
            "follow_up_questions": []
        }
        
        overall_score = self._calculate_overall_score(scores)
        
        # Hiring decision based on overall score
        if overall_score >= 4.0:
            recommendations["hiring_decision"] = "Strong hire - Recommend proceeding to next round"
        elif overall_score >= 3.0:
            recommendations["hiring_decision"] = "Hire - Candidate meets requirements with some development potential"
        elif overall_score >= 2.0:
            recommendations["hiring_decision"] = "Borderline - Consider additional interviews or specific role fit"
        else:
            recommendations["hiring_decision"] = "No hire - Candidate needs significant development"
        
        # Next steps based on performance
        if overall_score >= 3.5:
            recommendations["next_steps"] = [
                "Schedule technical deep-dive interview",
                "Discuss team fit and role expectations",
                "Check references"
            ]
        elif overall_score >= 2.5:
            recommendations["next_steps"] = [
                "Consider take-home technical assessment",
                "Schedule behavioral interview",
                "Evaluate for junior or alternative roles"
            ]
        else:
            recommendations["next_steps"] = [
                "Provide constructive feedback",
                "Suggest areas for skill development",
                "Keep candidate in pipeline for future opportunities"
            ]
        
        # Development areas from analysis
        for criteria, criteria_analysis in analysis.items():
            if isinstance(criteria_analysis, dict):
                improvements = criteria_analysis.get("areas_for_improvement", [])
                recommendations["development_areas"].extend(improvements[:2])
        
        return recommendations
    
    def _prepare_conversation_context(self, conversation_history: List[Dict], candidate_responses: List[Dict]) -> str:
        """Prepare conversation context for LLM analysis"""
        
        context_parts = ["=== INTERVIEW CONVERSATION ===\n"]
        
        for entry in conversation_history[-20:]:  # Last 20 exchanges
            role = entry.get("role", "unknown")
            content = entry.get("content", "")
            stage = entry.get("stage", "")
            
            context_parts.append(f"[{role.upper()} - {stage}]: {content[:500]}\n")
        
        if candidate_responses:
            context_parts.append("\n=== KEY CANDIDATE RESPONSES ===\n")
            for i, response in enumerate(candidate_responses):
                question = response.get("question", "Unknown question")
                answer = response.get("response", "")
                context_parts.append(f"Q{i+1}: {question}\nA{i+1}: {answer[:300]}\n")
        
        return "\n".join(context_parts)
    
    def _parse_text_analysis(self, analysis_text: str) -> Dict[str, Any]:
        """Parse text-based analysis when JSON parsing fails"""
        
        # Simple text parsing - in a real implementation, this would be more sophisticated
        return {
            "technical_skills": {"strengths": ["Analysis available in text format"], "areas_for_improvement": [], "examples": []},
            "communication": {"strengths": [], "areas_for_improvement": [], "examples": []},
            "problem_approach": {"strengths": [], "areas_for_improvement": [], "examples": []},
            "collaboration": {"strengths": [], "areas_for_improvement": [], "examples": []},
            "raw_analysis": analysis_text
        }
    
    def _fallback_analysis(self, error_msg: str) -> Dict[str, Any]:
        """Fallback analysis when LLM fails"""
        
        return {
            "technical_skills": {"strengths": [], "areas_for_improvement": ["Unable to analyze due to technical issue"], "examples": []},
            "communication": {"strengths": [], "areas_for_improvement": [], "examples": []},
            "problem_approach": {"strengths": [], "areas_for_improvement": [], "examples": []},
            "collaboration": {"strengths": [], "areas_for_improvement": [], "examples": []},
            "error": error_msg
        }
    
    def export_evaluation(self, evaluation: Dict[str, Any], format: str = "json") -> str:
        """Export evaluation in specified format"""
        
        if format == "json":
            return json.dumps(evaluation, indent=2)
        
        elif format == "summary":
            return self._format_summary_report(evaluation)
        
        else:
            return json.dumps(evaluation, indent=2)
    
    def _format_summary_report(self, evaluation: Dict[str, Any]) -> str:
        """Format evaluation as human-readable summary report"""
        
        report_parts = [
            f"=== INTERVIEW EVALUATION REPORT ===",
            f"Evaluation ID: {evaluation['evaluation_id']}",
            f"Date: {evaluation['timestamp']}",
            f"Overall Score: {evaluation['overall_score']}/5.0 ({evaluation['overall_rating'].upper()})",
            "",
            "=== DETAILED SCORES ===",
        ]
        
        for criteria, score_data in evaluation["detailed_scores"].items():
            report_parts.append(f"{criteria.replace('_', ' ').title()}: {score_data['score']}/5 ({score_data['rating']})")
        
        report_parts.extend([
            "",
            "=== OVERALL ASSESSMENT ===",
            evaluation["assessment"],
            "",
            "=== RECOMMENDATIONS ===",
            f"Hiring Decision: {evaluation['recommendations']['hiring_decision']}",
        ])
        
        if evaluation["recommendations"]["next_steps"]:
            report_parts.append("Next Steps:")
            for step in evaluation["recommendations"]["next_steps"]:
                report_parts.append(f"  • {step}")
        
        return "\n".join(report_parts)
    
    def _save_evaluation_files(self, evaluation: Dict[str, Any]) -> Dict[str, str]:
        """Save evaluation to multiple file formats"""
        
        # Create evaluations directory if it doesn't exist
        eval_dir = pathlib.Path("evaluations")
        eval_dir.mkdir(exist_ok=True)
        
        # Generate base filename
        candidate_name = evaluation.get("candidate_name", "Unknown").replace(" ", "_")
        eval_id = evaluation["evaluation_id"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{candidate_name}_{timestamp}_{eval_id}"
        
        saved_files = {}
        
        try:
            # 1. Save detailed JSON file
            json_path = eval_dir / f"{base_filename}_detailed.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(evaluation, f, indent=2, ensure_ascii=False)
            saved_files["json_detailed"] = str(json_path)
            
            # 2. Save summary report (human-readable)
            summary_path = eval_dir / f"{base_filename}_summary.txt"
            summary_report = self._format_comprehensive_summary_report(evaluation)
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(summary_report)
            saved_files["summary"] = str(summary_path)
            
            # 3. Save CSV metrics file for data analysis
            csv_path = eval_dir / f"{base_filename}_metrics.csv"
            csv_content = self._format_csv_metrics(evaluation)
            with open(csv_path, 'w', encoding='utf-8') as f:
                f.write(csv_content)
            saved_files["csv_metrics"] = str(csv_path)
            
            # 4. Save conversation transcript
            transcript_path = eval_dir / f"{base_filename}_transcript.txt"
            transcript_content = self._format_conversation_transcript(evaluation)
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(transcript_content)
            saved_files["transcript"] = str(transcript_path)
            
            print(f"\\nEVALUATION SAVED TO FILES:")
            print(f"Detailed JSON: {json_path}")
            print(f"Summary Report: {summary_path}")
            print(f"CSV Metrics: {csv_path}")
            print(f"Transcript: {transcript_path}")
            
        except Exception as e:
            print(f"Warning: Failed to save evaluation files: {str(e)}")
            saved_files["error"] = str(e)
        
        return saved_files
    
    def _format_comprehensive_summary_report(self, evaluation: Dict[str, Any]) -> str:
        """Format a comprehensive human-readable summary report"""
        
        report_parts = [
            "=" * 80,
            "INTERVIEW EVALUATION REPORT",
            "=" * 80,
            "",
            f"CANDIDATE: {evaluation.get('candidate_name', 'Unknown')}",
            f"TARGET ROLE: {evaluation.get('target_role', 'Unknown')}",
            f"DATE: {evaluation['timestamp'][:19].replace('T', ' ')}",
            f"EVALUATION ID: {evaluation['evaluation_id']}",
            "",
            "=" * 80,
            "OVERALL PERFORMANCE",
            "=" * 80,
            "",
            f"OVERALL SCORE: {evaluation['overall_score']}/5.0",
            f"OVERALL RATING: {evaluation['overall_rating'].upper()}",
            "",
            f"HIRING RECOMMENDATION: {evaluation['recommendations']['hiring_decision']}",
            "",
            "=" * 80,
            "DETAILED BREAKDOWN",
            "=" * 80,
            ""
        ]
        
        # Add detailed scores
        for criteria, score_data in evaluation["detailed_scores"].items():
            criteria_name = criteria.replace('_', ' ').title()
            score = score_data['score']
            rating = score_data['rating'].upper()
            weight = score_data['weight']
            weighted = score_data['weighted_score']
            
            report_parts.extend([
                f"{criteria_name}:",
                f"   Score: {score}/5 ({rating})",
                f"   Weight: {weight*100:.0f}%",
                f"   Weighted: {weighted:.2f}",
                ""
            ])
        
        # Add analysis if available
        if "analysis" in evaluation and evaluation["analysis"]:
            report_parts.extend([
                "=" * 80,
                "DETAILED ANALYSIS",
                "=" * 80,
                ""
            ])
            
            for criteria, analysis in evaluation["analysis"].items():
                if isinstance(analysis, dict) and criteria != "error":
                    report_parts.append(f"{criteria.replace('_', ' ').title()}:")
                    
                    if analysis.get("strengths"):
                        report_parts.append("   STRENGTHS:")
                        for strength in analysis["strengths"]:
                            report_parts.append(f"      - {strength}")
                    
                    if analysis.get("areas_for_improvement"):
                        report_parts.append("   AREAS FOR IMPROVEMENT:")
                        for area in analysis["areas_for_improvement"]:
                            report_parts.append(f"      - {area}")
                    
                    report_parts.append("")
        
        # Add overall assessment
        report_parts.extend([
            "=" * 80,
            "OVERALL ASSESSMENT",
            "=" * 80,
            "",
            evaluation.get("assessment", "No assessment available."),
            ""
        ])
        
        # Add recommendations
        if evaluation["recommendations"]["next_steps"]:
            report_parts.extend([
                "=" * 80,
                "RECOMMENDED NEXT STEPS",
                "=" * 80,
                ""
            ])
            for i, step in enumerate(evaluation["recommendations"]["next_steps"], 1):
                report_parts.append(f"{i}. {step}")
            report_parts.append("")
        
        # Add interview metadata
        metadata = evaluation["interview_metadata"]
        report_parts.extend([
            "=" * 80,
            "INTERVIEW STATISTICS",
            "=" * 80,
            "",
            f"Duration: {metadata.get('duration_minutes', 'Unknown')} minutes",
            f"Questions Completed: {metadata.get('questions_completed', 0)}",
            f"Final Stage: {metadata.get('interview_stage_reached', 'Unknown')}",
            f"Total Exchanges: {metadata.get('total_conversation_exchanges', 0)}",
            "",
            "=" * 80
        ])
        
        return "\\n".join(report_parts)
    
    def _format_csv_metrics(self, evaluation: Dict[str, Any]) -> str:
        """Format evaluation metrics as CSV for data analysis"""
        
        csv_lines = [
            "Candidate,Role,Date,EvaluationID,OverallScore,OverallRating,HiringDecision,Duration,QuestionsCompleted,TechnicalScore,CommunicationScore,ProblemApproachScore,CollaborationScore"
        ]
        
        # Extract values
        candidate = evaluation.get("candidate_name", "Unknown")
        role = evaluation.get("target_role", "Unknown") 
        date = evaluation["timestamp"][:10]
        eval_id = evaluation["evaluation_id"]
        overall_score = evaluation["overall_score"]
        overall_rating = evaluation["overall_rating"]
        hiring_decision = evaluation["recommendations"]["hiring_decision"]
        duration = evaluation["interview_metadata"].get("duration_minutes", "Unknown")
        questions = evaluation["interview_metadata"].get("questions_completed", 0)
        
        scores = evaluation["detailed_scores"]
        tech_score = scores.get("technical_skills", {}).get("score", 0)
        comm_score = scores.get("communication", {}).get("score", 0)
        approach_score = scores.get("problem_approach", {}).get("score", 0)
        collab_score = scores.get("collaboration", {}).get("score", 0)
        
        csv_lines.append(f'"{candidate}","{role}","{date}","{eval_id}",{overall_score},"{overall_rating}","{hiring_decision}","{duration}",{questions},{tech_score},{comm_score},{approach_score},{collab_score}')
        
        return "\\n".join(csv_lines)
    
    def _format_conversation_transcript(self, evaluation: Dict[str, Any]) -> str:
        """Format conversation transcript"""
        
        transcript_parts = [
            "=" * 80,
            f"INTERVIEW TRANSCRIPT - {evaluation.get('candidate_name', 'Unknown')}",
            "=" * 80,
            "",
            f"Date: {evaluation['timestamp'][:19].replace('T', ' ')}",
            f"Role: {evaluation.get('target_role', 'Unknown')}",
            "",
            "=" * 80,
            ""
        ]
        
        # Add candidate responses if available
        if "candidate_responses" in evaluation["interview_metadata"]:
            responses = evaluation["interview_metadata"]["candidate_responses"]
            
            for i, response_data in enumerate(responses, 1):
                question = response_data.get("question", "Unknown question")
                answer = response_data.get("response", "No response")
                stage = response_data.get("stage", "unknown")
                
                transcript_parts.extend([
                    f"[{stage.upper()}] QUESTION {i}:",
                    f"{question}",
                    "",
                    f"CANDIDATE RESPONSE:",
                    f"{answer}",
                    "",
                    "-" * 60,
                    ""
                ])
        
        return "\\n".join(transcript_parts)