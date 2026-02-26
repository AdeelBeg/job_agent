"""
Agent 2: Job Scorer
Uses sentence-transformers to embed your resume + job descriptions,
then ranks by cosine similarity. No API calls needed — runs locally for free.
"""

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import os


class JobScorer:
    def __init__(self, resume_text: str, threshold: float = None):
        print("  → Loading embedding model (first time = slow, cached after)...")
        # all-MiniLM-L6-v2: tiny (80MB), fast, good quality — perfect for this
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.resume_embedding = self.model.encode([resume_text])
        self.threshold = threshold or float(os.getenv("MATCH_THRESHOLD", "0.42"))

    def score_job(self, job: dict) -> float:
        """Return cosine similarity between resume and job description."""
        jd_text = f"{job['title']} {job.get('description', '')} {job.get('company', '')}"
        jd_embedding = self.model.encode([jd_text])
        score = cosine_similarity(self.resume_embedding, jd_embedding)[0][0]
        return round(float(score), 4)

    def filter_and_rank(self, jobs: list) -> list:
        """Score all jobs, filter below threshold, sort best first."""
        print(f"  → Scoring {len(jobs)} jobs against your resume...")
        matched = []
        for job in jobs:
            job["match_score"] = self.score_job(job)
            if job["match_score"] >= self.threshold:
                matched.append(job)

        matched.sort(key=lambda x: x["match_score"], reverse=True)
        print(f"  ✅ {len(matched)} jobs passed threshold ({self.threshold})")
        return matched

    def explain_match(self, job: dict) -> str:
        """Generate a simple explanation of why this job matched."""
        score = job.get("match_score", 0)
        if score >= 0.70:
            return "🔥 Excellent match — very aligned with your background"
        elif score >= 0.60:
            return "✅ Strong match — good overlap with your skills"
        elif score >= 0.50:
            return "👍 Decent match — some relevant experience required"
        else:
            return "🤔 Weak match — stretch role, worth considering"
