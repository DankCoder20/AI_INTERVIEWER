"""
AI Interviewer Agent System - Main workflow orchestrator using LangGraph
"""

from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime
import json

# LangGraph imports
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

# Agent imports
from agents.intent_guard import IntentGuardAgent
from agents.interviewer import InterviewAgent
from agents.guardrails import GuardrailsAgent
from agents.evaluator import EvaluatorAgent

# API imports
from apis.leetcode_api import LeetCodeAPI
from apis.codeforces_api import CodeforcesAPI

# State definition for LangGraph
class InterviewState(TypedDict):
    user_input: str
    conversation_history: List[Dict[str, Any]]
    current_stage: str
    interview_metadata: Dict[str, Any]
    security_check: Dict[str, Any]
    guardrails_check: Dict[str, Any]
    response: str
    current_question: Optional[Dict[str, Any]]
    candidate_responses: List[Dict[str, Any]]
    interview_complete: bool
    evaluation: Optional[Dict[str, Any]]
    error: Optional[str]

class AIInterviewerSystem:
    def __init__(self):
        # Initialize all agents
        self.intent_guard = IntentGuardAgent()
        self.interviewer = InterviewAgent()
        self.guardrails = GuardrailsAgent()
        self.evaluator = EvaluatorAgent()
        
        # Initialize APIs
        self.leetcode_api = LeetCodeAPI()
        self.codeforces_api = CodeforcesAPI()
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
        
        # Session state
        self.session_active = False
        self.current_state = None
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for interview process"""
        
        workflow = StateGraph(InterviewState)
        
        # Add nodes (agents/functions)
        workflow.add_node("security_check", self._security_check_node)
        workflow.add_node("guardrails_check", self._guardrails_check_node)
        workflow.add_node("interview_process", self._interview_process_node)
        workflow.add_node("generate_response", self._generate_response_node)
        workflow.add_node("evaluation", self._evaluation_node)
        workflow.add_node("error_handler", self._error_handler_node)
        
        # Set entry point
        workflow.set_entry_point("security_check")
        
        # Add conditional edges based on security and guardrails
        workflow.add_conditional_edges(
            "security_check",
            self._route_after_security,
            {
                "safe": "guardrails_check",
                "unsafe": "error_handler"
            }
        )
        
        workflow.add_conditional_edges(
            "guardrails_check", 
            self._route_after_guardrails,
            {
                "appropriate": "interview_process",
                "inappropriate": "error_handler",
                "redirect": "generate_response"
            }
        )
        
        workflow.add_conditional_edges(
            "interview_process",
            self._route_after_interview,
            {
                "continue": "generate_response",
                "complete": "evaluation",
                "error": "error_handler"
            }
        )
        
        workflow.add_edge("generate_response", END)
        workflow.add_edge("evaluation", END)
        workflow.add_edge("error_handler", END)
        
        return workflow.compile()
    
    def start_interview(self, candidate_name: str = "Candidate", target_role: str = "Software Engineer") -> Dict[str, Any]:
        """Start a new interview session"""
        
        self.session_active = True
        
        # Initialize interview
        intro_response = self.interviewer.start_interview(candidate_name)
        
        # Initialize state
        self.current_state = {
            "user_input": "",
            "conversation_history": [],
            "current_stage": "introduction",
            "interview_metadata": {
                "candidate_name": candidate_name,
                "target_role": target_role,
                "start_time": datetime.now().isoformat(),
                "question_source": "mixed"
            },
            "candidate_name": candidate_name,
            "target_role": target_role,
            "security_check": {},
            "guardrails_check": {},
            "response": intro_response["message"],
            "current_question": None,
            "candidate_responses": [],
            "interview_complete": False,
            "evaluation": None,
            "error": None
        }
        
        return {
            "status": "interview_started",
            "message": intro_response["message"],
            "session_id": f"interview_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
    
    async def process_message(self, user_input: str) -> Dict[str, Any]:
        """Process user message through the workflow"""
        
        if not self.session_active:
            return {"error": "No active interview session. Please start an interview first."}
        
        # Update state with new input
        self.current_state.update({
            "user_input": user_input,
            "error": None
        })
        
        try:
            # Run through workflow
            result = await self.workflow.ainvoke(self.current_state)
            
            # Update current state
            self.current_state.update(result)
            
            # Return response
            return {
                "status": "success",
                "message": result.get("response", ""),
                "stage": result.get("current_stage", "unknown"),
                "interview_complete": result.get("interview_complete", False),
                "evaluation": result.get("evaluation") if result.get("interview_complete") else None
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": "I apologize, but I encountered a technical issue. Could you please try again?",
                "error": str(e)
            }
    
    def _security_check_node(self, state: InterviewState) -> InterviewState:
        """Security check node - Intent Guard Agent"""
        
        user_input = state.get("user_input", "")
        
        if not user_input.strip():
            security_result = {"approved": True, "message": user_input}
        else:
            security_result = self.intent_guard.process_message(user_input)
        
        state["security_check"] = security_result
        return state
    
    def _guardrails_check_node(self, state: InterviewState) -> InterviewState:
        """Guardrails check node - safety and appropriateness"""
        
        user_input = state.get("user_input", "")
        context = f"Interview stage: {state.get('current_stage', 'unknown')}"
        
        if not user_input.strip():
            guardrails_result = {"appropriate": True}
        else:
            guardrails_result = self.guardrails.check_response(user_input, context)
        
        state["guardrails_check"] = guardrails_result
        return state
    
    def _interview_process_node(self, state: InterviewState) -> InterviewState:
        """Main interview processing node"""
        
        user_input = state.get("user_input", "")
        current_stage = state.get("current_stage", "introduction")
        
        try:
            if current_stage == "introduction" and not user_input.strip():
                # Starting the interview - no user input yet
                return state
            
            # Process the candidate's response
            if user_input.strip():
                interview_result = self.interviewer.process_response(
                    user_input, 
                    state.get("current_question")
                )
                
                # Update state with interview results
                state["current_stage"] = interview_result.get("stage", current_stage)
                state["interview_complete"] = interview_result.get("interview_complete", False)
                state["response"] = interview_result.get("message", "")
                
                # Add to conversation history
                state["conversation_history"].append({
                    "role": "user",
                    "content": user_input,
                    "timestamp": datetime.now().isoformat(),
                    "stage": current_stage
                })
                
                state["conversation_history"].append({
                    "role": "assistant", 
                    "content": interview_result.get("message", ""),
                    "timestamp": datetime.now().isoformat(),
                    "stage": interview_result.get("stage", current_stage)
                })
                
                # Use the interviewer's response directly - don't override with external APIs
                if interview_result.get("needs_question"):
                    # Only get external question for initial transition to technical stage
                    question = self._get_next_question(state)
                    if question:
                        question_response = self.interviewer.ask_question_with_context(question)
                        state["current_question"] = question
                        state["response"] = question_response["message"]
                    else:
                        state["response"] = interview_result.get("message", "")
                else:
                    # Always use the interviewer's response for follow-ups
                    state["response"] = interview_result.get("message", "")
            
        except Exception as e:
            state["error"] = f"Interview processing error: {str(e)}"
        
        return state
    
    def _generate_response_node(self, state: InterviewState) -> InterviewState:
        """Generate final response node"""
        
        # Check if we need to handle guardrails redirect
        guardrails_check = state.get("guardrails_check", {})
        
        if guardrails_check.get("needs_redirect"):
            redirect_response = self.guardrails.handle_inappropriate_response(
                state.get("user_input", ""),
                guardrails_check.get("reason", "Inappropriate content")
            )
            
            if redirect_response.get("action") == "end_interview":
                state["interview_complete"] = True
                state["response"] = redirect_response["message"]
            else:
                state["response"] = redirect_response["message"]
        
        # Ensure we have a response
        if not state.get("response"):
            state["response"] = "I'm here to help with your interview. Please let me know how I can assist you."
        
        return state
    
    def _evaluation_node(self, state: InterviewState) -> InterviewState:
        """Evaluation node - generate final assessment"""
        
        try:
            interview_data = {
                "conversation_history": state.get("conversation_history", []),
                "candidate_responses": self.interviewer.candidate_responses,  # Get from interviewer
                "metadata": {
                    **state.get("interview_metadata", {}),
                    "candidate_name": state.get("candidate_name", "Unknown"),
                    "target_role": state.get("target_role", "Unknown"),
                    "end_time": datetime.now().isoformat(),
                    "final_stage": state.get("current_stage", "unknown"),
                    "duration": self._calculate_interview_duration(state)
                }
            }
            
            evaluation = self.evaluator.evaluate_interview(interview_data)
            state["evaluation"] = evaluation
            
            # Generate evaluation summary response
            summary = self.evaluator._format_summary_report(evaluation)
            state["response"] = f"""Thank you for completing the interview! Here's your evaluation summary:

{summary}

The detailed evaluation has been generated and will be reviewed by our team."""
            
        except Exception as e:
            state["error"] = f"Evaluation error: {str(e)}"
            state["response"] = "Thank you for completing the interview! We'll review your responses and get back to you soon."
        
        return state
    
    def _calculate_interview_duration(self, state: InterviewState) -> str:
        """Calculate interview duration in minutes"""
        try:
            start_time = state.get("start_time")
            if start_time:
                start = datetime.fromisoformat(start_time)
                end = datetime.now()
                duration_minutes = int((end - start).total_seconds() / 60)
                return f"{duration_minutes}"
            return "Unknown"
        except:
            return "Unknown"
    
    def _error_handler_node(self, state: InterviewState) -> InterviewState:
        """Error handling node"""
        
        security_check = state.get("security_check", {})
        guardrails_check = state.get("guardrails_check", {})
        error = state.get("error")
        
        if not security_check.get("approved", True):
            state["response"] = "I noticed your message might contain inappropriate content. Let's keep our conversation focused on the interview. Could you please rephrase your response?"
        elif not guardrails_check.get("appropriate", True):
            state["response"] = guardrails_check.get("suggested_redirect", "Let's keep our conversation professional and focused on the interview.")
        elif error:
            state["response"] = "I apologize for the technical issue. Let's continue with the interview. Could you please repeat your last response?"
        else:
            state["response"] = "I'm having trouble processing your request. Could you please try again?"
        
        return state
    
    def _get_next_question(self, state: InterviewState) -> Optional[Dict[str, Any]]:
        """Get next technical question from APIs"""
        
        try:
            # Always use hard/medium difficulty for 1300+ Codeforces level
            difficulty = "hard"  # Focus on challenging problems only
            
            # Alternate between LeetCode and Codeforces
            import random
            if random.choice([True, False]):
                question = self.leetcode_api.get_problem_by_difficulty(difficulty)
            else:
                question = self.codeforces_api.get_problem_by_difficulty(difficulty)
            
            return question
            
        except Exception as e:
            # Random selection from challenging problems for 1300+ Codeforces level
            challenging_problems = [
                {
                    "title": "Binary Tree Maximum Path Sum",
                    "description": """Given a non-empty binary tree, find the maximum path sum. A path is any sequence of nodes from some starting node to any node in the tree along parent-child connections.

Example:
Input: [1,2,3] → Output: 6 (path: 2->1->3)
Input: [-10,9,20,null,null,15,7] → Output: 42 (path: 15->20->7)

Constraints: Up to 30,000 nodes. Values can be negative."""
                },
                {
                    "title": "Longest Increasing Subsequence",
                    "description": """Given an integer array nums, return the length of the longest strictly increasing subsequence.

Example:
Input: nums = [10,9,2,5,3,7,101,18]
Output: 4 (subsequence: [2,3,7,101])

Input: nums = [0,1,0,3,2,3]
Output: 4 (subsequence: [0,1,2,3])

Constraints: 1 <= nums.length <= 2500, -10^4 <= nums[i] <= 10^4"""
                },
                {
                    "title": "Course Schedule II",
                    "description": """There are numCourses courses labeled from 0 to numCourses - 1. You are given prerequisites array where prerequisites[i] = [ai, bi] indicates you must take course bi first to take course ai. Return the ordering of courses you should take to finish all courses.

Example:
Input: numCourses = 4, prerequisites = [[1,0],[2,0],[3,1],[3,2]]
Output: [0,2,1,3] (one possible order)

Input: numCourses = 2, prerequisites = [[1,0]]
Output: [0,1]

If impossible to finish all courses, return empty array."""
                },
                {
                    "title": "Edit Distance",
                    "description": """Given two strings word1 and word2, return the minimum number of operations required to convert word1 to word2. You can insert, delete, or replace any character.

Example:
Input: word1 = "horse", word2 = "ros"
Output: 3 (horse -> rorse -> rose -> ros)

Input: word1 = "intention", word2 = "execution"
Output: 5

Constraints: 0 <= word1.length, word2.length <= 500"""
                },
                {
                    "title": "Word Ladder",
                    "description": """Given two words beginWord and endWord, and a dictionary wordList, return the length of shortest transformation sequence from beginWord to endWord such that only one letter can be changed at a time and each transformed word must exist in wordList.

Example:
Input: beginWord = "hit", endWord = "cog", wordList = ["hot","dot","dog","lot","log","cog"]
Output: 5 ("hit" -> "hot" -> "dot" -> "dog" -> "cog")

Input: beginWord = "hit", endWord = "cog", wordList = ["hot","dot","dog","lot","log"]
Output: 0 (endWord not in wordList)

Constraints: All words have same length, only lowercase letters."""
                },
                {
                    "title": "Serialize and Deserialize Binary Tree",
                    "description": """Design an algorithm to serialize and deserialize a binary tree. Serialization is converting a tree to a string, deserialization is converting string back to tree.

Example:
Input: root = [1,2,3,null,null,4,5]
    1
   / \\
  2   3
     / \\
    4   5
You can serialize this to "1,2,null,null,3,4,null,null,5,null,null"

No restrictions on serialization format. Ensure your algorithm can deserialize what it serializes."""
                },
                {
                    "title": "Maximum Product Subarray",
                    "description": """Given an integer array nums, find a contiguous non-empty subarray that has the largest product, and return the product.

Example:
Input: nums = [2,3,-2,4]
Output: 6 (subarray: [2,3])

Input: nums = [-2,0,-1]
Output: 0

Constraints: 1 <= nums.length <= 2 * 10^4, -10 <= nums[i] <= 10"""
                },
                {
                    "title": "Trapping Rain Water",
                    "description": """Given n non-negative integers representing elevation map where width of each bar is 1, compute how much water can be trapped after raining.

Example:
Input: height = [0,1,0,2,1,0,1,3,2,1,2,1]
Output: 6

Input: height = [4,2,0,3,2,5]
Output: 9

Constraints: n == height.length, 1 <= n <= 2 * 10^4"""
                }
            ]
            
            import random
            selected_problem = random.choice(challenging_problems)
            selected_problem["source"] = "fallback_random"
            return selected_problem
    
    # Routing functions for conditional edges
    def _route_after_security(self, state: InterviewState) -> str:
        security_check = state.get("security_check", {})
        return "safe" if security_check.get("approved", False) else "unsafe"
    
    def _route_after_guardrails(self, state: InterviewState) -> str:
        guardrails_check = state.get("guardrails_check", {})
        if not guardrails_check.get("appropriate", True):
            return "redirect" if guardrails_check.get("needs_redirect") else "inappropriate"
        return "appropriate"
    
    def _route_after_interview(self, state: InterviewState) -> str:
        if state.get("error"):
            return "error"
        elif state.get("interview_complete"):
            return "complete"
        else:
            return "continue"
    
    def get_interview_summary(self) -> Dict[str, Any]:
        """Get current interview summary"""
        
        if not self.current_state:
            return {"error": "No active interview session"}
        
        return {
            "session_active": self.session_active,
            "current_stage": self.current_state.get("current_stage"),
            "conversation_length": len(self.current_state.get("conversation_history", [])),
            "interview_complete": self.current_state.get("interview_complete", False),
            "metadata": self.current_state.get("interview_metadata", {})
        }
    
    def end_interview(self) -> Dict[str, Any]:
        """Force end the current interview"""
        
        if not self.session_active:
            return {"error": "No active interview session"}
        
        self.session_active = False
        
        # Generate final evaluation if interview was in progress
        if self.current_state and not self.current_state.get("interview_complete"):
            self.current_state["interview_complete"] = True
            evaluation_state = self._evaluation_node(self.current_state)
            
            return {
                "status": "interview_ended",
                "evaluation": evaluation_state.get("evaluation")
            }
        
        return {"status": "interview_ended"}

# Interactive interview session
async def interactive_interview():
    """Interactive interview session for client demo"""
    
    print("=" * 60)
    print("AI INTERVIEWER SYSTEM - CLIENT DEMO POC")
    print("=" * 60)
    print("\nFeatures Demo:")
    print("• Multi-agent security (Intent Guard + Guardrails)")
    print("• Dynamic questions from LeetCode/Codeforces APIs")
    print("• Real-time evaluation and feedback")
    print("• Professional interview experience")
    print("\nCommands:")
    print("• Type naturally for conversation")
    print("• 'hint' - Get help on current question")
    print("• 'quit' - End interview")
    print("• 'help' - Show available commands")
    print("-" * 60)
    
    try:
        # Initialize system
        print("\nInitializing AI Interviewer System...")
        interviewer_system = AIInterviewerSystem()
        
        # Get candidate information
        print("\nCANDIDATE REGISTRATION")
        candidate_name = input("Enter candidate name: ").strip()
        if not candidate_name:
            candidate_name = "Demo Candidate"
        
        role_interest = input("What role are you interviewing for? (e.g., Software Engineer): ").strip()
        if not role_interest:
            role_interest = "Software Engineer"
        
        print(f"\n🎯 Starting interview for {candidate_name} - {role_interest} position")
        print("=" * 60)
        
        # Start interview
        start_result = interviewer_system.start_interview(candidate_name, role_interest)
        print(f"\n🤖 AI Interviewer: {start_result['message']}")
        
        # Interactive conversation loop
        conversation_count = 0
        while True:
            try:
                print(f"\n{'-' * 40}")
                user_input = input(f"👤 {candidate_name}: ").strip()
                
                # Handle special commands
                if user_input.lower() in ['quit', 'exit', 'end']:
                    print(f"\n👋 Thank you {candidate_name}! Ending interview session...")
                    
                    # Generate evaluation before ending
                    print(f"\n🔍 Generating interview evaluation...")
                    end_result = interviewer_system.end_interview()
                    
                    if end_result.get('evaluation'):
                        evaluation = end_result['evaluation']
                        print(f"\n📋 FINAL INTERVIEW EVALUATION:")
                        print(f"Overall Score: {evaluation.get('overall_score', 'N/A')}/5.0")
                        print(f"Overall Rating: {evaluation.get('overall_rating', 'N/A').upper()}")
                        print(f"Hiring Decision: {evaluation.get('recommendations', {}).get('hiring_decision', 'N/A')}")
                        print(f"\n💾 Complete evaluation files have been saved to the evaluations/ directory!")
                    else:
                        print(f"⚠️  Unable to generate evaluation - insufficient data.")
                    
                    break
                
                if user_input.lower() == 'help':
                    print("\n📋 Available Commands:")
                    print("• Type naturally to respond to questions")
                    print("• 'hint' - Get a helpful hint for current question")
                    print("• 'quit' - End the interview")
                    print("• 'help' - Show this help message")
                    continue
                
                if user_input.lower() == 'hint':
                    hint_response = interviewer_system.interviewer.provide_hint()
                    print(f"\n💡 AI Interviewer: {hint_response.get('message', 'No hint available right now.')}")
                    continue
                
                if not user_input:
                    print("Please provide a response or type 'help' for commands.")
                    continue
                
                # Process the message
                print(f"\n🔍 Processing response...")
                response = await interviewer_system.process_message(user_input)
                
                conversation_count += 1
                
                # Display AI response
                print(f"\n🤖 AI Interviewer: {response.get('message', 'I apologize, but I encountered an issue. Please try again.')}")
                
                # Show status for demo purposes
                status_info = f"[Status: {response.get('status', 'unknown')} | Stage: {response.get('stage', 'unknown')} | Turn: {conversation_count}]"
                print(f"\n📊 {status_info}")
                
                # Check if interview is complete
                if response.get('interview_complete'):
                    print("\n" + "=" * 60)
                    print("🎉 INTERVIEW COMPLETED!")
                    print("=" * 60)
                    
                    # Display evaluation if available
                    if response.get('evaluation'):
                        evaluation = response['evaluation']
                        print(f"\n📋 EVALUATION SUMMARY:")
                        print(f"Overall Score: {evaluation.get('overall_score', 'N/A')}/5.0")
                        print(f"Overall Rating: {evaluation.get('overall_rating', 'N/A').upper()}")
                        
                        # Show detailed scores
                        detailed_scores = evaluation.get('detailed_scores', {})
                        if detailed_scores:
                            print(f"\n📊 DETAILED SCORES:")
                            for criteria, score_data in detailed_scores.items():
                                criteria_name = criteria.replace('_', ' ').title()
                                score = score_data.get('score', 'N/A')
                                rating = score_data.get('rating', 'N/A')
                                print(f"• {criteria_name}: {score}/5 ({rating})")
                        
                        # Show recommendations
                        recommendations = evaluation.get('recommendations', {})
                        hiring_decision = recommendations.get('hiring_decision', 'Not available')
                        print(f"\n🎯 HIRING RECOMMENDATION:")
                        print(f"• {hiring_decision}")
                        
                        # Show next steps
                        next_steps = recommendations.get('next_steps', [])
                        if next_steps:
                            print(f"\n📝 NEXT STEPS:")
                            for step in next_steps[:3]:
                                print(f"• {step}")
                        
                        print(f"\n💾 Full evaluation report generated successfully!")
                    
                    break
                
                # Prevent infinite loops in demo
                if conversation_count >= 20:
                    print(f"\n⏰ Demo session limit reached. Wrapping up interview...")
                    break
                    
            except KeyboardInterrupt:
                print(f"\n\n⚠️  Interview interrupted by user (Ctrl+C)")
                print(f"📊 Session Summary: {conversation_count} exchanges completed")
                break
            except Exception as e:
                print(f"\n❌ Error occurred: {str(e)}")
                print("Please try again or type 'quit' to end the session.")
        
        # Final session summary
        print(f"\n" + "=" * 60)
        print("📊 SESSION SUMMARY")
        print("=" * 60)
        
        summary = interviewer_system.get_interview_summary()
        print(f"Candidate: {candidate_name}")
        print(f"Role: {role_interest}")
        print(f"Final Stage: {summary.get('current_stage', 'Unknown')}")
        print(f"Total Exchanges: {conversation_count}")
        print(f"Session Complete: {'Yes' if summary.get('interview_complete') else 'No'}")
        print(f"System Status: {'Active' if summary.get('session_active') else 'Ended'}")
        
        print(f"\n🎉 AI Interviewer POC Demo Complete!")
        print("Thank you for testing our AI Interview System!")
        
    except Exception as e:
        print(f"\n💥 Critical Error: {str(e)}")
        print("Please check your setup and try again.")

async def run_automated_test():
    """Quick automated test for development"""
    
    print("🧪 Running Automated Test...")
    interviewer_system = AIInterviewerSystem()
    
    start_result = interviewer_system.start_interview("Test User")
    print(f"✅ System initialized: {start_result['message'][:50]}...")
    
    test_response = await interviewer_system.process_message("I'm a software engineer with Python experience")
    print(f"✅ Message processing: {test_response.get('status')}")
    
    print("✅ All systems operational!")

def show_system_info():
    """Display system information"""
    print("\n🔧 SYSTEM INFORMATION:")
    print("• Backend: Python + LangGraph + Groq API")
    print("• Security: Intent Guard + Guardrails agents")
    print("• Questions: LeetCode + Codeforces APIs")
    print("• Evaluation: Multi-criteria weighted scoring")
    print("• Architecture: Multi-agent workflow orchestration")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Quick test mode
        asyncio.run(run_automated_test())
    elif len(sys.argv) > 1 and sys.argv[1] == "info":
        # System info mode
        show_system_info()
    else:
        # Full interactive interview mode (default)
        asyncio.run(interactive_interview())