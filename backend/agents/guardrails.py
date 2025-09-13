"""
Guardrails Agent - Safety net to keep conversations professional and on-track
"""

from typing import Dict, Any, List
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
import re
import os
from dotenv import load_dotenv

load_dotenv()

class GuardrailsAgent:
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.1-8b-instant",  # Use most reliable model
            temperature=0.2,
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
        
        # Only block clearly inappropriate content - be very permissive for technical interview
        self.inappropriate_topics = [
            "fuck", "shit", "damn you", "stupid interviewer", "this sucks"
        ]
        
        self.redirect_messages = [
            "Let's keep our focus on technical topics relevant to the interview.",
            "I'd prefer to discuss your technical skills and experience.",
            "Let's redirect our conversation back to the interview questions.",
            "That's outside the scope of this technical interview. Let's continue with coding topics."
        ]
        
        self.conversation_resets = 0
        self.max_resets = 3
    
    def check_response(self, message: str, context: str = "") -> Dict[str, Any]:
        """Check if a response is appropriate for the interview context"""
        
        # Quick pattern checks
        pattern_check = self._check_inappropriate_patterns(message)
        
        # Length and coherence check
        coherence_check = self._check_coherence(message)
        
        # LLM-based appropriateness check
        appropriateness_check = self._llm_appropriateness_check(message, context)
        
        # Prioritize LLM analysis - if LLM says appropriate, trust it unless there are severe pattern violations
        if appropriateness_check["appropriate"]:
            # LLM approved - only block if severe pattern violations (score > 3)
            pattern_score = pattern_check.get("score", 0)
            is_appropriate = pattern_score <= 3 and coherence_check["appropriate"]
            print(f"DEBUG: LLM approved, pattern_score={pattern_score}, coherence={coherence_check['appropriate']}, final={is_appropriate}")
        else:
            # LLM rejected - block regardless
            is_appropriate = False
            print(f"DEBUG: LLM rejected: {appropriateness_check.get('reason', 'No reason')}")
        
        return {
            "appropriate": is_appropriate,
            "needs_redirect": not is_appropriate,
            "reason": self._get_primary_reason(pattern_check, coherence_check, appropriateness_check),
            "suggested_redirect": self._get_redirect_message(),
            "confidence": min(
                pattern_check["confidence"],
                coherence_check["confidence"], 
                appropriateness_check["confidence"]
            )
        }
    
    def _check_inappropriate_patterns(self, message: str) -> Dict[str, Any]:
        """Check for obviously inappropriate content patterns"""
        
        message_lower = message.lower()
        
        # Check for inappropriate topics
        inappropriate_score = 0
        detected_topics = []
        
        for topic in self.inappropriate_topics:
            if topic in message_lower:
                inappropriate_score += 1
                detected_topics.append(topic)
        
        # Check for profanity or inappropriate language
        profanity_patterns = [
            r'\b(damn|hell|shit|fuck|bitch|ass)\b',
            r'(stupid|dumb|idiot|moron)',
            r'(hate|suck|terrible)'
        ]
        
        for pattern in profanity_patterns:
            if re.search(pattern, message_lower):
                inappropriate_score += 2
        
        # Check for personal attacks or negative behavior
        negative_patterns = [
            r'you (are|re) (bad|terrible|stupid|wrong)',
            r'this is (stupid|dumb|ridiculous)',
            r'i (hate|dislike|can\'t stand)'
        ]
        
        for pattern in negative_patterns:
            if re.search(pattern, message_lower):
                inappropriate_score += 2
        
        is_appropriate = inappropriate_score == 0
        
        return {
            "appropriate": is_appropriate,
            "confidence": 0.9 if inappropriate_score > 2 else 0.7,
            "detected_topics": detected_topics,
            "score": inappropriate_score
        }
    
    def _check_coherence(self, message: str) -> Dict[str, Any]:
        """Check if message is coherent and relevant to interview context"""
        
        # Check message length - be very permissive for interview responses
        word_count = len(message.split())
        
        if word_count < 1:  # Only block completely empty
            return {"appropriate": False, "confidence": 0.8, "reason": "Message empty"}
        
        if word_count > 1000:  # Much higher limit
            return {"appropriate": False, "confidence": 0.7, "reason": "Message too long"}
        
        # For technical interview, almost everything should be considered coherent
        # Only block obvious gibberish or spam
        
        # Check if message is just special characters
        if len(message.strip()) > 0 and message.strip().replace(" ", "").isalpha():
            return {"appropriate": True, "confidence": 0.9, "reason": "Valid text message"}
        
        # Check for obvious spam (same character repeated many times)  
        if len(set(message.replace(" ", ""))) <= 2 and len(message) > 10:
            return {"appropriate": False, "confidence": 0.9, "reason": "Appears to be spam"}
        
        # Otherwise assume coherent for interview context
        return {"appropriate": True, "confidence": 0.8, "reason": "Message appears coherent"}
    
    def _llm_appropriateness_check(self, message: str, context: str) -> Dict[str, Any]:
        """Use LLM to check if response is appropriate for interview context"""
        
        system_prompt = """You are a content moderator for a professional technical interview system.
        
        Evaluate if the given message is appropriate for a technical interview context.
        
        CONTEXT: This is a technical interview where candidates discuss:
        - Their programming experience and skills
        - Coding platforms they use (LeetCode, HackerRank, etc.)
        - Technical interests and problem-solving approaches
        - Algorithms, data structures, and programming concepts
        
        Consider:
        1. Professional tone and language
        2. Relevance to technical/interview topics  
        3. Respectful and constructive communication
        4. No inappropriate personal topics
        
        IMPORTANT: Be VERY PERMISSIVE with technical content. Almost all programming-related responses should be APPROPRIATE.
        Only flag as INAPPROPRIATE if there are clear violations of professional conduct (profanity, attacks, etc.).
        
        Examples of APPROPRIATE content:
        - Technical responses about coding solutions
        - Questions about the interview process
        - Sharing professional experience
        - Asking for clarification or hints
        - Mentioning coding platforms (LeetCode, HackerRank, Codeforces)
        - Discussing programming languages and technologies
        - Talking about problem-solving interests
        - Brief responses about coding preferences
        
        Examples of INAPPROPRIATE content:
        - Profanity or offensive language
        - Personal attacks
        - Completely off-topic discussions
        - Inappropriate personal topics
        
        Respond with:
        APPROPRIATE|reason OR INAPPROPRIATE|reason
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Context: {context}\nMessage to evaluate: {message}")
        ]
        
        try:
            response = self.llm.invoke(messages)
            content = response.content.strip()
            
            parts = content.split('|')
            decision = parts[0].strip().upper()
            reason = parts[1].strip() if len(parts) > 1 else "No reason provided"
            
            is_appropriate = decision == "APPROPRIATE"
            
            return {
                "appropriate": is_appropriate,
                "confidence": 0.8,
                "reason": reason
            }
            
        except Exception as e:
            # Fail safe - if LLM fails, assume appropriate for normal interview responses
            print(f"DEBUG: Guardrails LLM failed: {str(e)}")
            return {
                "appropriate": True,
                "confidence": 0.3,
                "reason": f"LLM check failed, assuming appropriate: {str(e)}"
            }
    
    def _get_primary_reason(self, *checks) -> str:
        """Get the primary reason for inappropriateness"""
        
        for check in checks:
            if not check["appropriate"]:
                return check["reason"]
        
        return "Content appears appropriate"
    
    def _get_redirect_message(self) -> str:
        """Get a redirect message to steer conversation back on track"""
        
        import random
        return random.choice(self.redirect_messages)
    
    def handle_inappropriate_response(self, message: str, reason: str) -> Dict[str, Any]:
        """Handle an inappropriate response with gentle redirection"""
        
        self.conversation_resets += 1
        
        if self.conversation_resets >= self.max_resets:
            return {
                "action": "end_interview",
                "message": "I'm sorry, but we need to end this interview session. Please reach out to schedule a new interview if you'd like to continue.",
                "reason": "Too many inappropriate responses"
            }
        
        redirect_message = self._get_redirect_message()
        
        return {
            "action": "redirect",
            "message": redirect_message,
            "reason": reason,
            "attempts_remaining": self.max_resets - self.conversation_resets
        }
    
    def emergency_reset(self) -> Dict[str, Any]:
        """Emergency conversation reset"""
        
        self.conversation_resets += 1
        
        reset_message = """Let's start fresh! I'm here to help you succeed in this technical interview. 
        
        Would you like to try a different question, or shall we continue with where we left off?"""
        
        return {
            "action": "reset",
            "message": reset_message,
            "reset_count": self.conversation_resets
        }
    
    def check_interview_flow(self, conversation_history: List[Dict]) -> Dict[str, Any]:
        """Check overall interview flow and suggest corrections"""
        
        if len(conversation_history) < 2:
            return {"status": "normal", "suggestion": None}
        
        # Check if conversation is stuck in a loop
        recent_messages = [msg["content"][:100] for msg in conversation_history[-4:]]
        if len(set(recent_messages)) <= 2:
            return {
                "status": "stuck", 
                "suggestion": "The conversation seems to be repeating. Let's try a new approach or question."
            }
        
        # Check if interview is taking too long
        if len(conversation_history) > 50:
            return {
                "status": "too_long",
                "suggestion": "This interview has been quite lengthy. Should we start wrapping up?"
            }
        
        # Check if candidate hasn't responded in a while
        last_candidate_msg = None
        for msg in reversed(conversation_history):
            if msg.get("role") == "user":
                last_candidate_msg = msg
                break
        
        if not last_candidate_msg:
            return {
                "status": "no_response",
                "suggestion": "I notice you haven't responded yet. Take your time, and let me know if you need any clarification!"
            }
        
        return {"status": "normal", "suggestion": None}
    
    def get_guardrails_summary(self) -> Dict[str, Any]:
        """Get summary of guardrails activity"""
        
        return {
            "conversation_resets": self.conversation_resets,
            "max_resets": self.max_resets,
            "resets_remaining": self.max_resets - self.conversation_resets,
            "status": "active" if self.conversation_resets < self.max_resets else "limit_reached"
        }