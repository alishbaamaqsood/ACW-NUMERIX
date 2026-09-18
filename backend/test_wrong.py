import os 
from dotenv import load_dotenv 
import google.generativeai as genai 
load_dotenv() 
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY")) 
judge = genai.GenerativeModel("gemini-3.6-flash") 
QUESTION = "What is the Bisection method?" 
GOOD = "The Bisection method is a root-finding algorithm that bisects an interval where f(a)*f(b) less than 0." 
BAD = "The Bisection method is a sorting algorithm that swaps adjacent elements to sort numbers." 
prompt = "Score 1-5 on correctness,relevance,completeness,faithfulness. JSON only: {\"correctness\":X,\"relevance\":X,\"completeness\":X,\"faithfulness\":X} QUESTION: " + QUESTION 
for label, ans in [("GOOD", GOOD), ("BAD", BAD)]: 
    r = judge.generate_content(prompt + " ANSWER: " + ans) 
    print(label, r.text) 
