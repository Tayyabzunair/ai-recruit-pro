"""
Skill matching service - semantic + keyword based.
For Phase 2: smart keyword matching with synonyms.
For Phase 3: will add sentence-transformers for full semantic match.
"""
import re
from loguru import logger


class SkillMatcher:
    """Smart skill matching between candidate and job."""
    
    # Common skill synonyms / variations
    SYNONYMS = {
        'js': 'javascript',
        'ts': 'typescript',
        'py': 'python',
        'reactjs': 'react',
        'react.js': 'react',
        'nodejs': 'node',
        'node.js': 'node',
        'nextjs': 'next',
        'next.js': 'next',
        'ml': 'machine learning',
        'ai': 'artificial intelligence',
        'dl': 'deep learning',
        'nlp': 'natural language processing',
        'db': 'database',
        'postgres': 'postgresql',
        'mongo': 'mongodb',
        'k8s': 'kubernetes',
        'gcp': 'google cloud',
        'aws cloud': 'aws',
        'rest api': 'rest',
        'restful': 'rest',
        'css3': 'css',
        'html5': 'html',
    }
    
    @classmethod
    def normalize_skill(cls, skill):
        """Normalize a single skill - lowercase, strip, expand synonyms."""
        skill = skill.lower().strip()
        skill = re.sub(r'[^\w\s+#.]', '', skill)  # Keep alphanumeric, +, #, .
        skill = ' '.join(skill.split())  # Normalize whitespace
        return cls.SYNONYMS.get(skill, skill)
    
    @classmethod
    def parse_skills(cls, skills_str):
        """Parse comma/semicolon-separated skills into normalized set."""
        if not skills_str:
            return set()
        
        # Split on common separators
        raw_skills = re.split(r'[,;|\n/]', str(skills_str))
        normalized = set()
        for s in raw_skills:
            s = cls.normalize_skill(s)
            if s and len(s) > 1:
                normalized.add(s)
        return normalized
    
    @classmethod
    def calculate_match(cls, candidate_skills, job_skills, experience_years=0, required_experience=0):
        """
        Calculate match score between 0-100.
        
        Algorithm:
        - 70% weight: skill overlap
        - 20% weight: experience match
        - 10% weight: bonus for extra relevant skills
        """
        c_skills = cls.parse_skills(candidate_skills)
        j_skills = cls.parse_skills(job_skills)
        
        if not j_skills:
            return 0.0
        
        # 1. Skill match (70%)
        matched = c_skills.intersection(j_skills)
        
        # Also check partial matches (e.g., "python" matches "python3")
        partial_matches = set()
        for j_skill in j_skills:
            if j_skill in matched:
                continue
            for c_skill in c_skills:
                if j_skill in c_skill or c_skill in j_skill:
                    if len(j_skill) >= 3 and len(c_skill) >= 3:
                        partial_matches.add(j_skill)
                        break
        
        total_matched = len(matched) + (len(partial_matches) * 0.5)
        skill_score = (total_matched / len(j_skills)) * 70
        
        # 2. Experience match (20%)
        exp_score = 0
        if required_experience > 0:
            if experience_years >= required_experience:
                exp_score = 20
            else:
                exp_score = (experience_years / required_experience) * 20
        else:
            exp_score = 20  # No requirement = full marks
        
        # 3. Bonus for having extra skills (10%)
        extra_skills = len(c_skills - j_skills)
        bonus = min(10, extra_skills * 2)
        
        total = skill_score + exp_score + bonus
        total = min(100, round(total, 1))
        
        logger.info(f'Match: {total}% (skills: {len(matched)}/{len(j_skills)}, extras: {extra_skills})')
        return total
    
    @classmethod
    def get_matched_skills(cls, candidate_skills, job_skills):
        """Return list of matched and missing skills."""
        c_skills = cls.parse_skills(candidate_skills)
        j_skills = cls.parse_skills(job_skills)
        
        matched = list(c_skills.intersection(j_skills))
        missing = list(j_skills - c_skills)
        extra = list(c_skills - j_skills)
        
        return {
            'matched': matched,
            'missing': missing,
            'extra': extra[:10],  # Limit to 10
        }
