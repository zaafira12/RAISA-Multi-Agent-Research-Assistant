import pandas as pd
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
from datetime import datetime
from collections import Counter

sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
kw_model = KeyBERT(model=sentence_model)

def extract_keywords(text):
    if not text or len(text) < 50:
        return ["N/A"]
    
    # Speed optimization: Only use the first 500 chars for keyword detection
    # Academic papers usually have the main topics at the start
    keywords = kw_model.extract_keywords(
        text[:500], 
        keyphrase_ngram_range=(1, 2), 
        stop_words='english', 
        top_n=5
    )
    return [kw[0] for kw in keywords]

def calculate_research_trends(results_list):
    """Uses Pandas to analyze publication growth and citation impact over time."""
    if not results_list:
        return {}

    df = pd.DataFrame(results_list)
    
    # Filter out invalid years if any
    df = df[df['year'] != "N/A"]
    
    # 1. Publication Growth: Count papers per year
    yearly_counts = df.groupby('year').size().sort_index().to_dict()
    
    # 2. Citation Impact: Average citations per year
    yearly_impact = df.groupby('year')['citations'].mean().sort_index().to_dict()
    
    # 3. Detect the 'Peak' year (most papers)
    if not df.empty:
        peak_year = int(df['year'].value_counts().idxmax())
    else:
        peak_year = "N/A"

    return {
        "yearly_counts": yearly_counts,
        "yearly_impact": yearly_impact,
        "peak_year": peak_year
    }

from collections import Counter

def calculate_research_gaps(results_list, topic):
    """
    Identifies a specific 'Unexplored Area' or 'Literature Limitation' 
    by analyzing the rarity of sub-topics within the search results.
    """
    topic_clean = topic.lower().strip()
    all_keywords = []
    
    # 1. Keyword Extraction & Normalization
    for paper in results_list:
     for kw in paper.get('keywords', []):
        clean_kw = kw.lower().strip()
        
        if clean_kw.endswith('s') and len(clean_kw) > 4:
            clean_kw = clean_kw[:-1]
        
        if clean_kw not in ["n/a", "none", ""]:
            all_keywords.append(clean_kw)  # ✅ CRITICAL FIX
    if not all_keywords:
        return None

    counts = Counter(all_keywords)
    ordered_kws = [item[0] for item in counts.most_common()]
    
    # 2. Define the 'Mainstream' and 'Unexplored Area'
    mainstream = ordered_kws[0] if ordered_kws else "General Theory"
    niche_list = [k for k in ordered_kws if counts[k] <= 2]
    unexplored_area = niche_list[0] if niche_list else ordered_kws[-1]

    thesis = (
        f"While existing literature in {topic.title()} heavily emphasizes {mainstream}, "
        f"there remains a critical gap in understanding the role of {unexplored_area}. "
        f"This study addresses this limitation by developing a framework that integrates "
        f"{unexplored_area} into current {topic} workflows to improve overall efficiency."
    )

    # 4. 📊 RESEARCH POTENTIAL METER LOGIC
    total_papers = len(results_list)
    if total_papers > 0:
        avg_mainstream_citations = sum(p.get('citations', 0) for p in results_list) / total_papers
    else:
        avg_mainstream_citations = 0
    
    if avg_mainstream_citations > 100:
        strength = 95
        label = " High Research Potential (Gold Mine)"
        color = "#e74c3c"  # Red
    elif avg_mainstream_citations > 30:
        strength = 75
        label = " Strong Opportunity"
        color = "#f39c12"  # Orange
    else:
        strength = 50
        label = " Emerging Niche"
        color = "#27ae60"  # Green

    # 5. Generate the Final Insight Dictionary
    return {
        "title": f"The '{unexplored_area}' Limitation in {topic.title()}",
        "unexplored_area": unexplored_area,
        "limitation": f"Current literature is heavily saturated with <b>{mainstream}</b>, creating a theoretical 'blind spot' regarding <b>{unexplored_area}</b>.",
        "thesis_statement": thesis, 
        "strength_score": strength, 
        "strength_label": label,    
        "strength_color": color,    
        "roadmap": [
            f"<b>Primary Research Question:</b> How does {unexplored_area} influence {topic} in ways that {mainstream} cannot explain?",
            f"<b>Literature Gap:</b> Most high-citation papers assume {mainstream} is universal; your study can challenge this by testing {unexplored_area} as a primary variable.",
            f"<b>Project Goal:</b> Develop a specialized framework for {unexplored_area} integration."
        ]
    }