"""
LeetCode API Integration - Fetch coding problems for technical interviews
"""

import requests
import json
import random
from typing import Dict, Any, List, Optional

class LeetCodeAPI:
    def __init__(self):
        self.base_url = "https://leetcode.com/graphql"
        self.problems_cache = {}
        
        # Curated list of good interview problems by difficulty
        self.curated_problems = {
            "easy": [
                {"id": 1, "title": "Two Sum", "slug": "two-sum"},
                {"id": 26, "title": "Remove Duplicates from Sorted Array", "slug": "remove-duplicates-from-sorted-array"},
                {"id": 121, "title": "Best Time to Buy and Sell Stock", "slug": "best-time-to-buy-and-sell-stock"},
                {"id": 125, "title": "Valid Palindrome", "slug": "valid-palindrome"},
                {"id": 136, "title": "Single Number", "slug": "single-number"},
                {"id": 169, "title": "Majority Element", "slug": "majority-element"},
                {"id": 217, "title": "Contains Duplicate", "slug": "contains-duplicate"},
                {"id": 242, "title": "Valid Anagram", "slug": "valid-anagram"},
                {"id": 268, "title": "Missing Number", "slug": "missing-number"},
                {"id": 283, "title": "Move Zeroes", "slug": "move-zeroes"}
            ],
            "medium": [
                {"id": 3, "title": "Longest Substring Without Repeating Characters", "slug": "longest-substring-without-repeating-characters"},
                {"id": 15, "title": "3Sum", "slug": "3sum"},
                {"id": 33, "title": "Search in Rotated Sorted Array", "slug": "search-in-rotated-sorted-array"},
                {"id": 49, "title": "Group Anagrams", "slug": "group-anagrams"},
                {"id": 56, "title": "Merge Intervals", "slug": "merge-intervals"},
                {"id": 75, "title": "Sort Colors", "slug": "sort-colors"},
                {"id": 102, "title": "Binary Tree Level Order Traversal", "slug": "binary-tree-level-order-traversal"},
                {"id": 139, "title": "Word Break", "slug": "word-break"},
                {"id": 200, "title": "Number of Islands", "slug": "number-of-islands"},
                {"id": 238, "title": "Product of Array Except Self", "slug": "product-of-array-except-self"}
            ],
            "hard": [
                {"id": 4, "title": "Median of Two Sorted Arrays", "slug": "median-of-two-sorted-arrays"},
                {"id": 23, "title": "Merge k Sorted Lists", "slug": "merge-k-sorted-lists"},
                {"id": 25, "title": "Reverse Nodes in k-Group", "slug": "reverse-nodes-in-k-group"},
                {"id": 42, "title": "Trapping Rain Water", "slug": "trapping-rain-water"},
                {"id": 76, "title": "Minimum Window Substring", "slug": "minimum-window-substring"},
                {"id": 84, "title": "Largest Rectangle in Histogram", "slug": "largest-rectangle-in-histogram"},
                {"id": 124, "title": "Binary Tree Maximum Path Sum", "slug": "binary-tree-maximum-path-sum"},
                {"id": 295, "title": "Find Median from Data Stream", "slug": "find-median-from-data-stream"}
            ]
        }
    
    def get_problem_by_difficulty(self, difficulty: str = "easy") -> Dict[str, Any]:
        """Get a random problem by difficulty level"""
        
        if difficulty.lower() not in self.curated_problems:
            difficulty = "easy"
        
        problems = self.curated_problems[difficulty.lower()]
        selected_problem = random.choice(problems)
        
        # Try to fetch full problem details
        problem_details = self.fetch_problem_details(selected_problem["slug"])
        
        if problem_details:
            return problem_details
        else:
            # Fallback to basic problem info
            return self._get_fallback_problem(selected_problem, difficulty)
    
    def fetch_problem_details(self, problem_slug: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed problem information from LeetCode"""
        
        # Check cache first
        if problem_slug in self.problems_cache:
            return self.problems_cache[problem_slug]
        
        query = """
        query getQuestionDetail($titleSlug: String!) {
            question(titleSlug: $titleSlug) {
                questionId
                questionFrontendId
                title
                titleSlug
                content
                difficulty
                likes
                dislikes
                exampleTestcases
                topicTags {
                    name
                    slug
                }
                hints
                similarQuestions
                sampleTestCase
            }
        }
        """
        
        variables = {"titleSlug": problem_slug}
        
        try:
            response = requests.post(
                self.base_url,
                json={"query": query, "variables": variables},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                question_data = data.get("data", {}).get("question")
                
                if question_data:
                    problem_details = self._format_problem_details(question_data)
                    self.problems_cache[problem_slug] = problem_details
                    return problem_details
            
        except Exception as e:
            print(f"Error fetching problem details: {str(e)}")
        
        return None
    
    def _format_problem_details(self, question_data: Dict) -> Dict[str, Any]:
        """Format raw LeetCode data into structured problem details"""
        
        # Clean up HTML content
        content = question_data.get("content", "")
        content = self._clean_html_content(content)
        
        return {
            "id": question_data.get("questionFrontendId"),
            "title": question_data.get("title"),
            "slug": question_data.get("titleSlug"),
            "difficulty": question_data.get("difficulty", "").lower(),
            "description": content,
            "hints": question_data.get("hints", []),
            "topics": [tag["name"] for tag in question_data.get("topicTags", [])],
            "examples": self._parse_examples(question_data.get("exampleTestcases", "")),
            "source": "leetcode"
        }
    
    def _clean_html_content(self, html_content: str) -> str:
        """Clean HTML tags from problem content"""
        
        import re
        
        # Remove HTML tags
        clean_text = re.sub(r'<[^>]+>', '', html_content)
        
        # Clean up extra whitespace
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        # Basic formatting
        clean_text = clean_text.replace('&nbsp;', ' ')
        clean_text = clean_text.replace('&lt;', '<')
        clean_text = clean_text.replace('&gt;', '>')
        clean_text = clean_text.replace('&amp;', '&')
        
        return clean_text
    
    def _parse_examples(self, example_testcases: str) -> List[Dict[str, str]]:
        """Parse example test cases into structured format"""
        
        if not example_testcases:
            return []
        
        examples = []
        try:
            # Split by newlines and group inputs/outputs
            lines = example_testcases.strip().split('\n')
            for i in range(0, len(lines), 2):
                if i + 1 < len(lines):
                    examples.append({
                        "input": lines[i],
                        "output": lines[i + 1]
                    })
        except:
            pass
        
        return examples
    
    def _get_fallback_problem(self, problem_info: Dict, difficulty: str) -> Dict[str, Any]:
        """Get fallback problem when API fails"""
        
        fallback_problems = {
            "two-sum": {
                "description": """Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.
                
You may assume that each input would have exactly one solution, and you may not use the same element twice.

Example:
Input: nums = [2,7,11,15], target = 9
Output: [0,1]
Explanation: Because nums[0] + nums[1] == 9, we return [0, 1].""",
                "hints": [
                    "Try using a hash map to store numbers you've seen",
                    "For each number, check if target - number exists in your hash map"
                ]
            },
            "valid-palindrome": {
                "description": """A phrase is a palindrome if, after converting all uppercase letters into lowercase letters and removing all non-alphanumeric characters, it reads the same forward and backward.

Given a string s, return true if it is a palindrome, or false otherwise.

Example:
Input: s = "A man, a plan, a canal: Panama"
Output: true
Explanation: "amanaplanacanalpanama" is a palindrome.""",
                "hints": [
                    "Use two pointers, one from start and one from end",
                    "Skip non-alphanumeric characters and compare lowercase versions"
                ]
            }
        }
        
        slug = problem_info["slug"]
        fallback_data = fallback_problems.get(slug, {
            "description": f"This is a {difficulty} level coding problem. Please solve it step by step.",
            "hints": ["Think about the problem systematically", "Consider edge cases"]
        })
        
        return {
            "id": problem_info["id"],
            "title": problem_info["title"],
            "slug": slug,
            "difficulty": difficulty,
            "description": fallback_data["description"],
            "hints": fallback_data["hints"],
            "topics": [],
            "examples": [],
            "source": "leetcode_fallback"
        }
    
    def get_problems_by_topic(self, topic: str, difficulty: str = "medium", count: int = 1) -> List[Dict[str, Any]]:
        """Get problems filtered by topic and difficulty"""
        
        # For MVP, return from curated list
        problems = self.curated_problems.get(difficulty.lower(), self.curated_problems["easy"])
        
        # Simple topic filtering (in real implementation, would use API)
        topic_keywords = {
            "array": ["two-sum", "remove-duplicates", "merge-intervals"],
            "string": ["valid-palindrome", "valid-anagram", "group-anagrams"],
            "tree": ["binary-tree-level-order-traversal", "binary-tree-maximum-path-sum"],
            "dynamic-programming": ["word-break", "best-time-to-buy-and-sell-stock"]
        }
        
        relevant_slugs = topic_keywords.get(topic.lower(), [])
        filtered_problems = [p for p in problems if p["slug"] in relevant_slugs]
        
        if not filtered_problems:
            filtered_problems = problems
        
        selected_problems = random.sample(filtered_problems, min(count, len(filtered_problems)))
        
        return [self.get_problem_by_difficulty(difficulty) for _ in selected_problems]
    
    def search_problems(self, query: str, difficulty: str = None) -> List[Dict[str, Any]]:
        """Search problems by title or keywords"""
        
        all_problems = []
        difficulties = [difficulty] if difficulty else ["easy", "medium", "hard"]
        
        for diff in difficulties:
            problems = self.curated_problems.get(diff, [])
            for problem in problems:
                if query.lower() in problem["title"].lower():
                    problem_details = self.fetch_problem_details(problem["slug"])
                    if problem_details:
                        all_problems.append(problem_details)
        
        return all_problems[:5]  # Return top 5 matches
    
    def get_random_problem(self) -> Dict[str, Any]:
        """Get a completely random problem"""
        
        difficulty = random.choice(["easy", "medium"])
        return self.get_problem_by_difficulty(difficulty)
    
    def get_interview_problem_set(self, candidate_level: str = "mid") -> List[Dict[str, Any]]:
        """Get a curated set of problems for a complete interview"""
        
        problem_sets = {
            "junior": ["easy", "easy", "medium"],
            "mid": ["easy", "medium", "medium"],
            "senior": ["medium", "medium", "hard"],
            "staff": ["medium", "hard", "hard"]
        }
        
        difficulties = problem_sets.get(candidate_level, problem_sets["mid"])
        problems = []
        
        for difficulty in difficulties:
            problem = self.get_problem_by_difficulty(difficulty)
            problems.append(problem)
        
        return problems