"""
Agent 3: Resume & Cover Letter Tailor
Uses Groq (free tier) with Llama 3.1 8B to generate tailored documents.

Why Groq?
- 100% free tier: 6000 requests/day, 500K tokens/day
- Fastest inference in the world (up to 800 tokens/sec)
- Runs Llama 3.1 (Meta's open source model)
- No credit card needed to start

Get your key at: https://console.groq.com
"""

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


class ResumeTailor:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        # Best free model options on Groq:
        # llama-3.1-8b-instant  → super fast, good quality
        # llama-3.1-70b-versatile → slower but better, still free
        # mixtral-8x7b-32768    → great for long context
        self.model = "llama-3.1-8b-instant"

    def _call_llm(self, prompt: str, max_tokens: int = 800) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"  [LLM Error] {e}")
            return ""

    def generate_cover_letter(self, resume: str, job: dict) -> str:
        """Generate a targeted, human-sounding cover letter."""
        prompt = f"""
You are an expert career coach who writes compelling cover letters.

CANDIDATE RESUME:
{resume[:2000]}

JOB TITLE: {job['title']}
COMPANY: {job['company']}
JOB DESCRIPTION:
{job.get('description', '')[:1500]}

Write a 3-paragraph cover letter following these STRICT rules:
1. First paragraph: Hook — reference something SPECIFIC about the company or role
2. Second paragraph: Match — connect 2-3 of their exact requirements to your experience
3. Third paragraph: Call to action — confident, not desperate

FORBIDDEN phrases: "I am passionate", "I am a fast learner", "I would love to", "excited opportunity"
TONE: Confident, direct, specific. Sound like a human, not a template.
MAX LENGTH: 220 words

Output ONLY the cover letter body, no subject line, no "Dear Hiring Manager" header.
"""
        return self._call_llm(prompt, max_tokens=600)

    def tailor_resume_summary(self, resume: str, job: dict) -> str:
        """Rewrite the professional summary to match the JD keywords."""
        prompt = f"""
Rewrite ONLY the professional summary/about section of this resume to better match the job.

CURRENT RESUME:
{resume[:800]}

TARGET JOB: {job['title']} at {job['company']}
KEY REQUIREMENTS FROM JD: {job.get('description', '')[:600]}

Rules:
- Keep it 3-4 sentences max
- Mirror the exact keywords/technologies from the JD naturally
- Do not add skills the candidate doesn't have
- Sound confident and specific

Output ONLY the rewritten summary, nothing else.
"""
        return self._call_llm(prompt, max_tokens=200)

    def extract_key_skills_from_jd(self, job: dict) -> list:
        """Extract top required skills from the job description."""
        prompt = f"""
Extract the top 8 technical skills/technologies required from this job description.
Return as a comma-separated list, nothing else.

JD: {job.get('description', '')[:1000]}
"""
        result = self._call_llm(prompt, max_tokens=100)
        return [s.strip() for s in result.split(",") if s.strip()]

    def generate_linkedin_message(self, resume: str, job: dict) -> str:
        """Generate a short LinkedIn cold message to the hiring manager."""
        prompt = f"""
Write a 3-sentence LinkedIn connection request message from a candidate to a hiring manager.

CANDIDATE BACKGROUND: {resume[:500]}
JOB: {job['title']} at {job['company']}

Rules:
- Max 3 sentences, max 80 words total
- Reference something specific about the company
- End with a low-pressure ask
- Do NOT say "I hope this message finds you well"

Output only the message.
"""
        return self._call_llm(prompt, max_tokens=150)
