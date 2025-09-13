"""
Codeforces API Integration - Alternative source for competitive programming questions
"""

import requests
import json
import random
from typing import Dict, Any, List, Optional

class CodeforcesAPI:
    def __init__(self):
        self.base_url = "https://codeforces.com/api"
        self.problems_cache = {}
        
        # Curated competitive programming problems good for interviews
        self.curated_problems = {
            "easy": [
                {"contestId": 4, "index": "A", "name": "Watermelon", "rating": 800},
                {"contestId": 71, "index": "A", "name": "Way Too Long Words", "rating": 800},
                {"contestId": 231, "index": "A", "name": "Team", "rating": 800},
                {"contestId": 282, "index": "A", "name": "Bit++", "rating": 800},
                {"contestId": 339, "index": "A", "name": "Helpful Maths", "rating": 800},
                {"contestId": 266, "index": "A", "name": "Stones on the Table", "rating": 800},
                {"contestId": 112, "index": "A", "name": "Petya and Strings", "rating": 800},
                {"contestId": 158, "index": "A", "name": "Next Round", "rating": 800},
                {"contestId": 236, "index": "A", "name": "Boy or Girl", "rating": 800},
                {"contestId": 263, "index": "A", "name": "Beautiful Matrix", "rating": 800}
            ],
            "medium": [
                {"contestId": 1, "index": "A", "name": "Theatre Square", "rating": 1000},
                {"contestId": 50, "index": "A", "name": "Domino piling", "rating": 800},
                {"contestId": 118, "index": "A", "name": "String Task", "rating": 1000},
                {"contestId": 122, "index": "A", "name": "Lucky Division", "rating": 1000},
                {"contestId": 160, "index": "A", "name": "Twins", "rating": 900},
                {"contestId": 148, "index": "A", "name": "Insomnia cure", "rating": 900},
                {"contestId": 116, "index": "A", "name": "Tram", "rating": 800},
                {"contestId": 69, "index": "A", "name": "Young Physicist", "rating": 1000},
                {"contestId": 144, "index": "A", "name": "Arrival of the General", "rating": 800},
                {"contestId": 467, "index": "A", "name": "George and Accommodation", "rating": 800}
            ],
            "hard": [
                {"contestId": 580, "index": "C", "name": "Kefa and Park", "rating": 1500},
                {"contestId": 492, "index": "B", "name": "Vanya and Lanterns", "rating": 1200},
                {"contestId": 279, "index": "B", "name": "Books", "rating": 1400},
                {"contestId": 276, "index": "C", "name": "Little Girl and Maximum Sum", "rating": 1400},
                {"contestId": 368, "index": "B", "name": "Sereja and Suffixes", "rating": 1100},
                {"contestId": 433, "index": "B", "name": "Kuriyama Mirai's Stones", "rating": 1200},
                {"contestId": 472, "index": "A", "name": "Design Tutorial: Learn from Math", "rating": 1000},
                {"contestId": 451, "index": "B", "name": "Sort the Array", "rating": 1300}
            ]
        }
    
    def get_problem_by_difficulty(self, difficulty: str = "easy") -> Dict[str, Any]:
        """Get a random problem by difficulty level"""
        
        if difficulty.lower() not in self.curated_problems:
            difficulty = "easy"
        
        problems = self.curated_problems[difficulty.lower()]
        selected_problem = random.choice(problems)
        
        # Try to fetch full problem details
        problem_details = self.fetch_problem_details(
            selected_problem["contestId"], 
            selected_problem["index"]
        )
        
        if problem_details:
            return problem_details
        else:
            # Fallback to basic problem info
            return self._get_fallback_problem(selected_problem, difficulty)
    
    def fetch_problem_details(self, contest_id: int, index: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed problem information from Codeforces"""
        
        cache_key = f"{contest_id}_{index}"
        
        # Check cache first
        if cache_key in self.problems_cache:
            return self.problems_cache[cache_key]
        
        try:
            # Fetch contest problems
            url = f"{self.base_url}/contest.standings"
            params = {
                "contestId": contest_id,
                "from": 1,
                "count": 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("status") == "OK":
                    problems = data.get("result", {}).get("problems", [])
                    
                    for problem in problems:
                        if problem.get("index") == index:
                            problem_details = self._format_codeforces_problem(problem, contest_id)
                            self.problems_cache[cache_key] = problem_details
                            return problem_details
            
            # Alternative: Try problemset.problems API
            return self._fetch_from_problemset(contest_id, index)
            
        except Exception as e:
            print(f"Error fetching Codeforces problem: {str(e)}")
        
        return None
    
    def _fetch_from_problemset(self, contest_id: int, index: str) -> Optional[Dict[str, Any]]:
        """Fallback method to fetch from problemset API"""
        
        try:
            url = f"{self.base_url}/problemset.problems"
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("status") == "OK":
                    problems = data.get("result", {}).get("problems", [])
                    
                    for problem in problems:
                        if (problem.get("contestId") == contest_id and 
                            problem.get("index") == index):
                            return self._format_codeforces_problem(problem, contest_id)
        
        except Exception as e:
            print(f"Error in problemset fetch: {str(e)}")
        
        return None
    
    def _format_codeforces_problem(self, problem_data: Dict, contest_id: int) -> Dict[str, Any]:
        """Format Codeforces problem data into structured format"""
        
        return {
            "id": f"{contest_id}{problem_data.get('index', '')}",
            "title": problem_data.get("name", "Unknown Problem"),
            "contest_id": contest_id,
            "index": problem_data.get("index"),
            "difficulty": self._map_rating_to_difficulty(problem_data.get("rating", 800)),
            "rating": problem_data.get("rating", 800),
            "description": self._get_problem_description(problem_data),
            "tags": problem_data.get("tags", []),
            "time_limit": f"{problem_data.get('timeLimit', 1000)}ms",
            "memory_limit": f"{problem_data.get('memoryLimit', 256)}MB",
            "source": "codeforces",
            "url": f"https://codeforces.com/contest/{contest_id}/problem/{problem_data.get('index', '')}"
        }
    
    def _map_rating_to_difficulty(self, rating: int) -> str:
        """Map Codeforces rating to difficulty level"""
        
        if rating <= 900:
            return "easy"
        elif rating <= 1400:
            return "medium"
        else:
            return "hard"
    
    def _get_problem_description(self, problem_data: Dict) -> str:
        """Generate problem description (Codeforces API doesn't provide full statements)"""
        
        name = problem_data.get("name", "Problem")
        tags = problem_data.get("tags", [])
        rating = problem_data.get("rating", 800)
        
        description = f"""Problem: {name}
        
This is a competitive programming problem from Codeforces with a difficulty rating of {rating}.

Problem tags: {', '.join(tags) if tags else 'General problem solving'}

Since this is a competitive programming problem, focus on:
1. Understanding the problem constraints
2. Designing an efficient algorithm
3. Implementing a clean solution
4. Considering edge cases

Think about the time and space complexity of your solution."""
        
        return description
    
    def _get_fallback_problem(self, problem_info: Dict, difficulty: str) -> Dict[str, Any]:
        """Get fallback problem when API fails"""
        
        fallback_descriptions = {
            "Watermelon": """Given an integer representing the weight of a watermelon in kilograms, determine if it's possible to divide it into two parts such that each part weighs an even number of kilograms.

Example:
Input: 8
Output: YES (can be divided into 2 and 6, both even)

Input: 3  
Output: NO (impossible to divide odd number into two even parts)""",
            
            "Way Too Long Words": """Sometimes words can be very long. If a word has strictly more than 10 characters, replace it with a special abbreviation: write the first character, then the number of characters between first and last, then the last character.

Example:
Input: "localization"
Output: "l10n" (l + 10 characters in between + n)""",
            
            "Theatre Square": """A theatre square in the capital city has a rectangular shape with dimensions n × m meters. It needs to be paved with square stones, each stone is a × a meters. Find the minimum number of stones needed to cover the entire square.

You can use partial stones (cut them if needed)."""
        }
        
        name = problem_info["name"]
        description = fallback_descriptions.get(name, f"""This is a {difficulty} competitive programming problem: {name}

Since we cannot fetch the full problem statement, please work with this general guidance:
- Focus on algorithmic thinking
- Consider time and space complexity  
- Think about edge cases
- Implement a clean, efficient solution""")
        
        return {
            "id": f"{problem_info['contestId']}{problem_info['index']}",
            "title": name,
            "contest_id": problem_info["contestId"],
            "index": problem_info["index"], 
            "difficulty": difficulty,
            "rating": problem_info.get("rating", 800),
            "description": description,
            "tags": [],
            "source": "codeforces_fallback",
            "url": f"https://codeforces.com/contest/{problem_info['contestId']}/problem/{problem_info['index']}"
        }
    
    def get_problems_by_rating_range(self, min_rating: int = 800, max_rating: int = 1200, count: int = 1) -> List[Dict[str, Any]]:
        """Get problems within a specific rating range"""
        
        all_problems = []
        for difficulty, problems in self.curated_problems.items():
            filtered = [p for p in problems if min_rating <= p.get("rating", 800) <= max_rating]
            all_problems.extend(filtered)
        
        if not all_problems:
            all_problems = self.curated_problems["easy"]
        
        selected = random.sample(all_problems, min(count, len(all_problems)))
        
        results = []
        for problem in selected:
            details = self.fetch_problem_details(problem["contestId"], problem["index"])
            if details:
                results.append(details)
            else:
                difficulty = self._map_rating_to_difficulty(problem.get("rating", 800))
                results.append(self._get_fallback_problem(problem, difficulty))
        
        return results
    
    def get_problems_by_tags(self, tags: List[str], difficulty: str = "medium", count: int = 1) -> List[Dict[str, Any]]:
        """Get problems filtered by algorithmic tags"""
        
        # For MVP, return problems from appropriate difficulty level
        # In full implementation, would filter by actual tags from API
        
        difficulty_problems = self.curated_problems.get(difficulty.lower(), self.curated_problems["easy"])
        selected = random.sample(difficulty_problems, min(count, len(difficulty_problems)))
        
        results = []
        for problem in selected:
            details = self.fetch_problem_details(problem["contestId"], problem["index"])
            if details:
                results.append(details)
        
        return results
    
    def search_problems(self, query: str) -> List[Dict[str, Any]]:
        """Search problems by name"""
        
        all_problems = []
        for difficulty, problems in self.curated_problems.items():
            for problem in problems:
                if query.lower() in problem["name"].lower():
                    details = self.fetch_problem_details(problem["contestId"], problem["index"])
                    if details:
                        all_problems.append(details)
        
        return all_problems[:5]  # Top 5 matches
    
    def get_random_problem(self) -> Dict[str, Any]:
        """Get a completely random problem"""
        
        difficulty = random.choice(["easy", "medium"])
        return self.get_problem_by_difficulty(difficulty)
    
    def get_contest_problems(self, contest_id: int) -> List[Dict[str, Any]]:
        """Get all problems from a specific contest"""
        
        try:
            url = f"{self.base_url}/contest.standings"
            params = {
                "contestId": contest_id,
                "from": 1,
                "count": 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("status") == "OK":
                    problems = data.get("result", {}).get("problems", [])
                    
                    results = []
                    for problem in problems:
                        formatted = self._format_codeforces_problem(problem, contest_id)
                        results.append(formatted)
                    
                    return results
        
        except Exception as e:
            print(f"Error fetching contest problems: {str(e)}")
        
        return []
    
    def get_competitive_programming_set(self, level: str = "beginner") -> List[Dict[str, Any]]:
        """Get a set of problems suitable for competitive programming interview"""
        
        problem_sets = {
            "beginner": ["easy", "easy", "medium"],
            "intermediate": ["easy", "medium", "medium"], 
            "advanced": ["medium", "medium", "hard"],
            "expert": ["medium", "hard", "hard"]
        }
        
        difficulties = problem_sets.get(level, problem_sets["beginner"])
        problems = []
        
        for difficulty in difficulties:
            problem = self.get_problem_by_difficulty(difficulty)
            problems.append(problem)
        
        return problems