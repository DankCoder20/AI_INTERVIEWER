# AI Interviewer Agent POC - 4 Hour Build

## Core Requirements (MVP)

### Agents (Python LangGraph)
1. *Intent Guard Agent* - Detects prompt injection/hacks
2. *Interview Agent* - Conducts interview, gives hints, stays friendly  
3. *Guardrails Agent* - Keeps conversation on track
4. *Evaluator Agent* - AI summary and evaluation of interview performance

### Features
- Text-based interview chat
- Dynamic question generation from LeetCode/Codeforces APIs
- Friendly hints when candidate struggles
- Basic security against prompt injection
- Simple conversation flow
- AI-powered interview summary and candidate evaluation

## Technical Stack
- *Backend*: Python + LangGraph + Groq API
- *Frontend*: Next.js simple chat UI (optional)
- *Communication*: REST API or WebSocket

## Agent Specs

### 1. Intent Guard
python
# Check every input for:
- System prompts injection attempts
- Attempts to change agent behavior  
- Off-topic manipulation
- Pass clean inputs to Interview Agent


### 2. Interview Agent
python
# Main conductor:
- Ask relevant interview questions
- Provide encouraging hints
- Give positive feedback
- Maintain friendly tone
- Progress through interview stages


### 3. Guardrails
python
# Safety net:
- Block inappropriate responses
- Redirect off-topic conversations
- Maintain professional boundaries
- Emergency conversation reset


### 4. Evaluator Agent
python
# Assessment and summary:
- Track candidate responses throughout interview
- Generate final interview summary
- Provide candidate evaluation and scoring
- Highlight strengths and improvement areas
- Export summary in structured format


## External APIs
- *LeetCode API*: Fetch coding problems for technical interviews
- *Codeforces API*: Alternative source for competitive programming questions
- *Question Selection*: Auto-select appropriate difficulty based on role/level

## 4-Hour Implementation Plan

### Hour 1: Setup & Basic Agents
- Setup LangGraph project
- Create 3 basic agents with simple prompts
- Test agent communication

### Hour 2: Core Logic & APIs
- Implement intent detection patterns
- Add interview question flow
- Basic guardrails implementation
- Integrate LeetCode/Codeforces API calls

### Hour 3: Integration & Evaluation
- Connect agents in workflow
- Implement evaluator agent
- Test prompt injection scenarios
- Add interview summary generation

### Hour 4: Simple UI (Optional)
- Basic Next.js chat interface
- Connect to Python backend
- Final testing

## Success Criteria
- ✅ Detects basic prompt injection attempts
- ✅ Conducts coherent interview conversation
- ✅ Provides helpful hints to candidates
- ✅ Maintains friendly, professional tone
- ✅ Stays on interview topics
- ✅ Fetches questions from LeetCode/Codeforces APIs
- ✅ Generates comprehensive interview summary and evaluation

## File Structure

ai-interviewer/
├── backend/
│   ├── agents/
│   │   ├── intent_guard.py
│   │   ├── interviewer.py
│   │   ├── guardrails.py
│   │   └── evaluator.py
│   ├── apis/
│   │   ├── leetcode_api.py
│   │   └── codeforces_api.py
│   ├── main.py
│   └── requirements.txt
└── frontend/ (optional)
    ├── pages/
    ├── components/
    └── package.json
