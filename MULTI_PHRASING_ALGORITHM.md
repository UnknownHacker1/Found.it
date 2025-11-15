# Multi-Phrasing Search Algorithm

## Overview

The new search algorithm uses **multi-phrasing with weighted ranking** and **chain-of-thought reasoning** to find the most relevant files with much higher accuracy.

## How It Works

### Step 1: Generate 4 Different Phrasings

When you search for "find my resume", the AI generates 4 different ways to express the same intent:

**Example:**
```
Original: "find my resume"

Phrasing 1: "resume professional experience"
Phrasing 2: "CV curriculum vitae"
Phrasing 3: "employment history work background"
Phrasing 4: "career profile job application document"
```

Each phrasing:
- Uses **different synonyms**
- Captures **different aspects** of what you want
- Gets **enhanced with hardcoded synonym fallbacks**

### Step 2: Multi-Phrasing Vector Search

The system searches **4 times** (once per phrasing) and aggregates results:

```
Phrasing 1 search → Top 30 results
Phrasing 2 search → Top 30 results
Phrasing 3 search → Top 30 results
Phrasing 4 search → Top 30 results
```

### Step 3: Weighted Scoring

Files are ranked using a **combined score** based on:

#### A. Frequency Score (3x weight)
How many phrasings found this file:
- Found in 4/4 phrasings = 1.0 score
- Found in 3/4 phrasings = 0.75 score
- Found in 2/4 phrasings = 0.5 score
- Found in 1/4 phrasings = 0.25 score

**Why this matters:** If your CV appears in searches for "resume", "CV", "employment history", AND "career profile", it's definitely what you want!

#### B. Position Score (2x weight)
Average rank position across all appearances:
- Position 1 = 1.0
- Position 2 = 0.5
- Position 3 = 0.33
- Position 10 = 0.1

**Why this matters:** A file consistently ranked #1 is better than one ranked #15.

#### C. Similarity Score (1x weight)
Average vector similarity from all searches.

**Formula:**
```python
combined_score = (frequency * 3.0) + (position * 2.0) + (similarity * 1.0)
```

### Step 4: Chain-of-Thought Reasoning

The AI analyzes the top 15 candidates and **talks through its reasoning for EVERY file**:

```
ANALYSIS:
File 1: Professional_CV.pdf - Resume/CV document. Match: YES.
        Contains professional experience, education, skills.
        File name explicitly says "CV". This is clearly a resume.

File 2: budget_2024.xlsx - Financial spreadsheet. Match: NO.
        This is a budget document, not employment-related.
        Contains financial data, not work history.

File 3: Resume_John_Doe.docx - Resume document. Match: YES.
        File name says "Resume". Contains work experience and education.
        Exactly what the user is looking for.

... (continues for all 15 files)

SELECTED: 1, 3
EXPLANATION: Selected Professional_CV.pdf and Resume_John_Doe.docx
             because they are clearly resume/CV documents with work
             experience and education information.
```

**Why this works:** By forcing the AI to explain its reasoning for each file, it makes more accurate decisions (this is called "chain of thought" prompting).

## Example: "Find my resume"

### Without Multi-Phrasing
```
Single search: "resume CV curriculum vitae..."
→ Top result might be: Meeting_Notes_Resume_Project.docx
   (has "resume" in filename but is NOT a resume)
```

### With Multi-Phrasing
```
Search 1: "resume professional experience" → CV.pdf (rank 2)
Search 2: "CV curriculum vitae" → CV.pdf (rank 1)
Search 3: "employment history" → CV.pdf (rank 1)
Search 4: "career profile" → CV.pdf (rank 3)

CV.pdf appears in 4/4 phrasings at ranks 1,1,2,3
→ Combined score: Very high!

Meeting_Notes_Resume_Project.docx appears in 1/4 phrasings at rank 15
→ Combined score: Very low
```

**Result:** CV.pdf is correctly ranked #1

## Performance

### Speed
- **4 LLM calls** (1 for phrasings + 1 for reasoning + 2 internal)
- **4 vector searches** (one per phrasing)
- **Total time:** ~5-10 seconds (depending on API speed)

### Accuracy Improvements
- Files appearing in **multiple phrasings** ranked much higher
- **Synonym mismatches** solved (resume vs CV)
- **Chain-of-thought** prevents false positives
- **Position weighting** favors consistently high-ranked files

## Logging

Check the backend logs to see the full reasoning:

```bash
cd d:\Foundit\backend
python app.py
```

You'll see:
```
Generated phrasings:
  Phrasing 1: resume professional experience CV...
  Phrasing 2: curriculum vitae employment history...
  ...

Multi-phrasing ranking:
  1. CV.pdf - Score: 4.850 (appears in 4/4 phrasings, best position: 1)
  2. Resume.docx - Score: 3.200 (appears in 3/4 phrasings, best position: 2)
  ...

================================================================================
CHAIN-OF-THOUGHT REASONING:
File 1: CV.pdf - Resume document. Match: YES. Contains professional...
File 2: budget.xlsx - Financial document. Match: NO. This is not a resume...
...
================================================================================
```

## Reverting to Simple Chain-of-Thought

If multi-phrasing is too slow or not working well, we can easily revert to:
- **Single query** (no multi-phrasing)
- **Chain-of-thought reasoning only**
- Faster but potentially less accurate

Just let me know if you want to switch!

## Configuration

Current settings in [rag_engine.py](d:\Foundit\backend\rag_engine.py):

```python
# Number of phrasings: 4
phrasings = self._generate_query_phrasings(user_message)

# Results per phrasing: 30
results = self.search_engine.search(phrasing, top_k=30)

# Candidates shown to LLM: 15
for i, candidate in enumerate(candidates[:15]):

# Score weights
frequency_score * 3.0  # Appearance frequency
avg_position_score * 2.0  # Rank position
avg_similarity * 1.0  # Vector similarity
```

You can adjust these if needed!
