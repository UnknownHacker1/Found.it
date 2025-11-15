# Foundit Chat Features

Your AI file search assistant now has enhanced chatbot capabilities!

## 🎯 What Can It Do?

### 1. **Smart File Search** (Keyword-Based)
The AI now extracts keywords from your natural language queries before searching.

**Examples:**
- **You:** "find my resume"
  - **AI extracts:** "resume CV curriculum vitae professional experience work history"
  - **Then searches** with all these keywords to find your CV even if it doesn't say "resume"

- **You:** "show me travel documents from 2023"
  - **AI extracts:** "travel documents passport visa i94 immigration 2023"
  - **Finds:** Passports, visas, I-94 forms, boarding passes, etc.

- **You:** "where are my tax files"
  - **AI extracts:** "tax taxes income revenue IRS W2 1040 financial"
  - **Finds:** All tax-related documents

### 2. **File Summarization**
Ask the AI to summarize or explain files from your search results.

**Examples:**
- **You:** "find my resume"
- **AI:** Shows your CV file
- **You:** "summarize that"
- **AI:** Reads the CV and provides a summary of your experience, education, skills

Or:
- **You:** "find my budget spreadsheet"
- **AI:** Shows budget.xlsx
- **You:** "what's in it?"
- **AI:** Reads and explains the contents

### 3. **General Conversation**
Ask questions, get help, or chat naturally.

**Examples:**
- **You:** "what can you do?"
- **AI:** Explains its capabilities

- **You:** "how do I use this?"
- **AI:** Provides guidance

- **You:** "thank you!"
- **AI:** Responds naturally

## 🔍 How It Works

### Intent Classification
The AI automatically detects what you want:

- **File Search** (keywords: find, search, show, get, locate, where is)
  - Extracts keywords using AI
  - Adds synonym fallbacks
  - Searches with enhanced keywords
  - Returns best matches

- **General Chat** (keywords: summarize, explain, what's in, help)
  - Maintains conversation context
  - Can read files from previous searches
  - Responds naturally

### Keyword Extraction Process
1. **User query:** "find my resume"
2. **AI extracts keywords:** "resume CV curriculum vitae professional experience work history employment"
3. **Adds synonyms:** + "career profile professional summary qualifications education skills"
4. **Vector search:** Finds 50 candidates using all these terms
5. **AI reasoning:** Analyzes top 20 to pick best matches
6. **Returns:** Your CV, resume, professional profile, etc.

## 💬 Usage Examples

### Scenario 1: Finding and Analyzing a Resume
```
You: find my resume
AI: I found 2 relevant files:
    1. Professional_CV.pdf
    2. Resume_2024.docx

You: summarize the first one
AI: [Reads Professional_CV.pdf]
    This is a professional CV for [Name]. Key highlights:
    - Education: MIT, Computer Science
    - Experience: Google (2020-2023), Microsoft (2018-2020)
    - Skills: Python, JavaScript, Machine Learning
    [... full summary ...]
```

### Scenario 2: Travel Documents
```
You: show me my passport and visa
AI: I found 3 relevant files:
    1. Passport_USA.pdf
    2. H1B_Visa.pdf
    3. I94_2024.pdf

You: what's in the visa document?
AI: [Reads H1B_Visa.pdf]
    This is your H1B work visa issued on [date].
    Valid from: [start date]
    Valid until: [end date]
    Employer: [company name]
    [... details ...]
```

### Scenario 3: General Help
```
You: help
AI: I'm Foundit, your AI file search assistant!

    I can help you:
    - Find files by their content (not just filename)
    - Understand what you're looking for using AI
    - Summarize and analyze documents
    - Answer questions about your files

    Try asking:
    - "find my resume"
    - "show travel documents"
    - "where are my tax files from 2023"
    - "summarize that file"
```

## 🚀 Tips for Best Results

1. **Be natural** - Just ask like you're talking to a person
   - ✅ "find my resume"
   - ✅ "where's my passport"
   - ✅ "show me budget files"

2. **Use reference words** for follow-ups
   - ✅ "summarize that"
   - ✅ "what's in the first one"
   - ✅ "explain it to me"

3. **The AI understands synonyms**
   - "resume" = "CV" = "curriculum vitae"
   - "passport" = "travel document"
   - "budget" = "financial report"

4. **You can be specific or vague**
   - ✅ "find my resume from 2024"
   - ✅ "show me files about travel"
   - ✅ "where are important documents"

## 🎨 Current Capabilities

- ✅ Semantic file search (finds by meaning, not just keywords)
- ✅ AI keyword extraction from natural language
- ✅ Synonym expansion (resume → CV, etc.)
- ✅ File content analysis and summarization
- ✅ Conversational chat with context
- ✅ Multi-format support (PDF, DOCX, PPTX, TXT)
- ✅ Vector embeddings for similarity matching
- ✅ LLM reasoning for best results

## 🔧 Technical Details

**Search Pipeline:**
1. User query → Intent classification
2. If file search:
   - Extract keywords with AI
   - Add synonym fallbacks
   - Vector search (50 candidates)
   - LLM ranks top 20
   - Return top 5
3. If general chat:
   - Check for file references
   - Read file contents if needed
   - Respond with conversation context

**Supported File Types:**
- PDF documents
- Word documents (.docx)
- PowerPoint (.pptx)
- Text files (.txt, .md, .py, .js, etc.)

**AI Models:**
- OpenRouter (free Llama 3.1 model)
- Sentence transformers for embeddings
- FAISS for vector search
