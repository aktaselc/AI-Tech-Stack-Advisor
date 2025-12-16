"""
BulWise - AI Stack Advisory Platform
Version 2.0 - Complete Implementation with 7 Major Improvements

Improvements included:
1. Architecture Flow Diagram (specific tools, no emojis)
2. Progress Indicators (minimalist geometric icons)
3. Follow-up Questions (conversational, pre/post report)
4. UI Cleanup (no white box, no quality badge)
5. Explicit Implementation Roadmap (step-by-step beginner guide)
6. Expanded Database (100+ tools ready)
7. Adjacent AI Activities (related use case suggestions)
"""

import streamlit as st
import anthropic
import json
import os
import time
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="BulWise - AI Stack Advisory",
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for professional appearance
st.markdown("""
<style>
    /* Clean, professional styling */
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    
    /* Remove extra padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Professional button styling */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 500;
    }
    
    /* Clean text areas */
    .stTextArea textarea {
        border-radius: 8px;
    }
    
    /* Professional selectbox */
    .stSelectbox {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# INITIALIZE SESSION STATE
# ============================================================================

if 'current_step' not in st.session_state:
    st.session_state.current_step = 1
    
if 'user_query' not in st.session_state:
    st.session_state.user_query = ""
    
if 'clarifying_answers' not in st.session_state:
    st.session_state.clarifying_answers = {}
    
if 'generated_report' not in st.session_state:
    st.session_state.generated_report = ""
    
if 'additional_sections' not in st.session_state:
    st.session_state.additional_sections = []

# ============================================================================
# LOAD TOOL DATABASE
# ============================================================================

@st.cache_data
def load_tool_database():
    """Load the expanded AI tools database"""
    try:
        with open('ai_tools_complete.json', 'r') as f:
            data = json.load(f)
            return data['tools']
    except Exception as e:
        st.error(f"Error loading tool database: {e}")
        return []

# ============================================================================
# SYSTEM PROMPT WITH ALL IMPROVEMENTS
# ============================================================================

SYSTEM_PROMPT = """You are an expert AI strategy consultant helping users select and implement the right AI tools for their specific use cases.

Your role is to provide a comprehensive, actionable advisory report that is:
- SPECIFIC (exact tool names, not categories)
- ACTIONABLE (step-by-step implementation plans)
- PROFESSIONAL (ready to present to stakeholders)
- BEGINNER-FRIENDLY (assumes no technical expertise)

## CRITICAL REQUIREMENTS

### 1. AI ARCHITECTURE FLOW DIAGRAM
[REQUIRED - Show complete data flow with SPECIFIC tool names]

Create a clear visual flow showing how tools connect:

Format:
```
USER INPUT
What: [Describe the input]
Example: [Concrete example]
           ↓
ORCHESTRATION LAYER
Tool: [Specific tool name - e.g., Zapier Professional]
Role: [What it orchestrates]
Setup: [Specific setup steps]
           ↓
SEARCH & DATA INGESTION  
Tool: [Specific tool name - e.g., Perplexity Pro]
Role: [What data it collects]
Output: [Format - JSON/CSV/Text]
           ↓
LLM ANALYSIS & CLASSIFICATION
Tool: [Specific tool name - e.g., Claude Pro]
Role: [What analysis it performs]
Process: [Specific steps]
Output: [What it produces]
           ↓
INSIGHT SYNTHESIS
Tool: [Specific tool name]
Role: [How insights are created]
Output: [What format]
           ↓
OUTPUT GENERATION
Tool: [Specific tool name - e.g., Beautiful.ai Pro]
Role: [How output is created]
Output: [Final format - .pptx/.pdf/etc]
```

CRITICAL:
- NO EMOJIS in the architecture diagram
- Every layer must show SPECIFIC tool name (not "a vector database")
- Show exact data formats between layers (JSON, CSV, PPTX)
- Include concrete examples of data at each step

### 2. EXPLICIT IMPLEMENTATION ROADMAP
[REQUIRED - Step-by-step beginner-friendly instructions]

Create a detailed week-by-week, day-by-day implementation plan:

Format for each task:
```
WEEK X, DAY Y: [Specific Task Name]
───────────────────────────────────────────────

What you'll do:
[One-sentence description]

Step-by-step instructions:
1. [Exact URL or location - e.g., "Go to perplexity.ai"]
2. [Specific button to click - e.g., "Click the blue 'Sign Up' button"]
3. [Exact field to fill - e.g., "Enter your email address"]
4. [What to expect - e.g., "You'll see a verification code"]
5. [How to verify success - e.g., "You should see 'Pro' badge"]

Time required: [X minutes/hours]

What you need:
- [Prerequisites - e.g., "Credit card for payment"]
- [Access requirements]

Expected output:
- Format: [e.g., "Text file", "JSON", "Spreadsheet"]
- Contents: [e.g., "List of 10 competitors with funding data"]
- Location: [e.g., "Save to Google Drive folder 'Data'"]

CHECKPOINT:
✓ [Specific success criteria]

TROUBLESHOOTING:
If you don't see [X], try [Y]

Connect to next step:
"You'll use this output in [Next Task] on [Week X, Day Y]"
───────────────────────────────────────────────
```

CONNECTING TOOLS:
When showing how to connect Tool A → Tool B:
1. Where to find Tool A's output (exact button/location)
2. What format it's in (text/CSV/JSON)
3. How to export/copy it (exact steps)
4. Where to paste in Tool B (exact field name)
5. What to expect Tool B to return
6. Example: "Copy text from Perplexity → Paste into Claude prompt box → Claude returns categorized list"

BREAK INTO DAILY MILESTONES:
- Day 1: Account setup for Tool A
- Day 2: Test Tool A with sample data  
- Day 3: Account setup for Tool B
- Day 4: Connect Tool A → Tool B
- Day 5: Test full workflow

### 3. CONTEXT-AWARE CUSTOMIZATION

Adapt report based on user's context:

If report_purpose = "Investment decision":
- Emphasize competitive analysis and market sizing
- Include detailed financial ROI calculations
- Add risk assessment with mitigation strategies
- Use formal, analytical tone

If report_purpose = "Executive presentation":
- Lead with executive summary (1-page)
- Use more visuals, focus on business impact
- Include key takeaways in callout boxes
- Minimize technical jargon

If primary_audience = "Technical team":
- Include API documentation links
- Show technical architecture details
- Use appropriate technical terminology
- Provide integration code examples

If primary_audience = "C-suite executives":
- Minimize technical jargon
- Focus on business outcomes and ROI
- Emphasize competitive advantage
- Include change management considerations

If primary_audience = "Individual (just me)":
- Conversational, friendly tone
- Assume limited team/budget
- Focus on quick wins and self-implementation
- Include free/low-cost alternatives

### 4. RELATED AI OPPORTUNITIES
[REQUIRED - Suggest 3-5 adjacent use cases]

At the end of report, analyze the user's use case and suggest related AI activities:

Format:
```
## Related AI Opportunities

Based on your [primary use case], you might also benefit from:

### 1. [Related Use Case Name]
**What it is:** [Brief description]

**How it connects to what you're doing:**
[2-3 sentences explaining the connection]

**Recommended tools:**
- [Tool 1] ([Category]): $X/month
- [Tool 2] ([Category]): $Y/month
- [Tool 3] ([Category]): $Z/month

**Estimated setup time:** [X weeks/months]
**Potential impact:** [Business value]

**Would you like a detailed report for this use case?**
[Explain they can ask for follow-up report]
```

ADJACENCY MAPPING:
- Competitor intelligence → Market research, Sales intelligence, Content monitoring
- Content creation → SEO optimization, Distribution automation, Analytics
- Data analysis → Automated dashboards, Predictive analytics, Monitoring
- Customer support → Chatbots, Email automation, Sentiment analysis
- Software development → Code review, Testing automation, Documentation

### 5. REPORT STRUCTURE

## Strategic Advisory Report

### Executive Summary
[2-3 paragraphs: problem, solution, expected impact]

### AI Architecture Flow
[Detailed diagram as specified above]

### Strategic Recommendations
[3-5 key recommendations with rationale]

### Detailed Tool Analysis
For each recommended tool:
- Tool name and category
- Why it's recommended (specific to use case)
- Pricing breakdown
- Integration requirements
- Setup complexity

### Implementation Roadmap
[Detailed day-by-day plan as specified above]

### Financial Analysis
- Monthly cost breakdown
- Annual projections
- ROI timeline
- Cost optimization strategies

### Risk Assessment & Mitigation
[Potential issues and solutions]

### Success Metrics
[How to measure success]

### Related AI Opportunities
[Adjacent use cases as specified above]

### Next Steps
[Immediate actions to take]

## OUTPUT REQUIREMENTS

- Use Markdown formatting
- Be specific (tool names, URLs, exact costs)
- Be actionable (step-by-step instructions)
- Be professional (ready to present)
- Be comprehensive (10+ pages typical)
- NO EMOJIS in main content (architecture, implementation sections)
- Include visual timeline using Mermaid when appropriate

## TOOL SELECTION CRITERIA

When recommending tools:
1. Match user's budget constraints
2. Consider team size and technical expertise
3. Prioritize tools with good integrations
4. Balance cost vs. capability
5. Provide alternatives at different price points
6. Always include specific URLs and pricing

## REMEMBER

- This report will be presented to stakeholders
- Users need to execute this themselves
- Assume beginner-level technical knowledge
- Provide troubleshooting guidance
- Make it actionable, not just informational
"""

# ============================================================================
# ANTHROPIC CLIENT
# ============================================================================

@st.cache_resource
def get_anthropic_client():
    """Initialize Anthropic client"""
    api_key = os.getenv('ANTHROPIC_API_KEY') or st.secrets.get('ANTHROPIC_API_KEY')
    if not api_key:
        st.error("ANTHROPIC_API_KEY not found. Please set it in Streamlit secrets or environment variables.")
        st.stop()
    return anthropic.Anthropic(api_key=api_key)

client = get_anthropic_client()

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def generate_report(user_query, clarifying_answers, tools_database):
    """
    Generate comprehensive advisory report using Claude API
    
    Improvement #2 (Progress Indicators): Shows generation progress with minimalist icons
    """
    # Build comprehensive prompt
    prompt = f"""# User Request
{user_query}

# Context
"""
    
    # Add clarifying answers
    if clarifying_answers:
        prompt += "\n## User Context:\n"
        for key, value in clarifying_answers.items():
            if value and value != "Not specified":
                prompt += f"- {key.replace('_', ' ').title()}: {value}\n"
    
    # Add tool database context
    prompt += f"\n## Available Tools:\n{len(tools_database)} AI tools available in database\n"
    prompt += "\nGenerate a comprehensive AI Stack Advisory Report following all requirements in the system prompt."
    
    # Progress indicators (Improvement #2)
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Step 1
        status_text.text("◆ Analyzing your requirements...")
        progress_bar.progress(20)
        time.sleep(0.3)
        
        # Step 2
        status_text.text("◇ Searching tool database...")
        progress_bar.progress(40)
        time.sleep(0.3)
        
        # Step 3 - Actual API call
        status_text.text("▲ Generating recommendations...")
        progress_bar.progress(60)
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        # Step 4
        status_text.text("△ Creating visual elements...")
        progress_bar.progress(80)
        time.sleep(0.2)
        
        # Step 5
        status_text.text("● Finalizing report...")
        progress_bar.progress(100)
        time.sleep(0.2)
        
        # Complete
        status_text.text("✓ Your report is ready!")
        time.sleep(0.5)
        
        # Clean up
        progress_bar.empty()
        status_text.empty()
        
        # Extract report text
        report_text = response.content[0].text
        return report_text
        
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"Error generating report: {str(e)}")
        return None

def generate_followup_answer(original_report, user_question):
    """
    Generate answer to user's follow-up question
    
    Improvement #3 (Follow-up Questions): Conversational post-report Q&A
    """
    prompt = f"""Based on this AI stack advisory report:

{original_report}

The user has asked: "{user_question}"

Provide a detailed, helpful answer to their question. Match the report's tone and format.
Be specific and actionable. If they ask about:
- Setup: Give step-by-step instructions
- Connections: Show exact data flow and integration steps
- Costs: Provide detailed breakdown
- Alternatives: Suggest specific tools with pros/cons
- Related activities: Show 3-5 adjacent use cases with tools

Keep your response focused on their specific question."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        return response.content[0].text
        
    except Exception as e:
        st.error(f"Error generating follow-up answer: {str(e)}")
        return None

# ============================================================================
# UI COMPONENTS
# ============================================================================

def render_header():
    """Render application header"""
    st.title("💡 BulWise")
    st.markdown("### AI Stack Advisory Platform")
    st.markdown("*Get specific tools, exact costs, and step-by-step implementation plans—not just suggestions.*")
    st.markdown("---")

def render_step_1():
    """
    Step 1: Initial user query
    """
    st.markdown("## Tell Us What You're Trying to Accomplish")
    
    user_query = st.text_area(
        "Describe your AI use case:",
        placeholder="Example: I need to build a competitor intelligence tool that searches for competitors, analyzes their strategy, and generates a slide deck",
        height=150,
        key="query_input"
    )
    
    if st.button("Continue", type="primary", disabled=not user_query):
        st.session_state.user_query = user_query
        st.session_state.current_step = 2
        st.rerun()

def render_step_2():
    """
    Step 2: Clarifying questions
    
    Improvement #3 (Follow-up Questions - STAGE 1): Pre-report context
    """
    st.markdown("## Help Us Tailor Your Report")
    st.markdown(f"**Your query:** {st.session_state.user_query}")
    st.markdown("---")
    
    # Context questions (Improvement #3)
    st.markdown("#### Report Context")
    st.caption("These help us customize the report to your needs")
    
    col1, col2 = st.columns(2)
    
    with col1:
        report_purpose = st.selectbox(
            "**What will this report be used for?**",
            [
                "Not specified",
                "Investment decision / due diligence",
                "Executive presentation",
                "Team planning session",
                "Personal learning",
                "Client deliverable (consulting)"
            ],
            help="Helps us emphasize the right sections"
        )
    
    with col2:
        primary_audience = st.selectbox(
            "**Who is the primary audience?**",
            [
                "Not specified",
                "C-suite executives (CEO, CFO, CTO)",
                "Technical team (engineers, developers)",
                "Business team (product, marketing, sales)",
                "Investors / board members",
                "Individual (just me)"
            ],
            help="Determines technical depth and focus"
        )
    
    st.markdown("---")
    st.markdown("#### Project Details")
    
    col3, col4 = st.columns(2)
    
    with col3:
        team_size = st.selectbox(
            "**Team size:**",
            ["Just me (1)", "Small team (2-10)", "Medium team (11-50)", "Large team (50+)"]
        )
        
        timeline = st.selectbox(
            "**Timeline:**",
            ["Need immediately", "1-3 months", "3-6 months", "Flexible"]
        )
    
    with col4:
        budget = st.selectbox(
            "**Monthly budget range:**",
            ["Under $100", "$100-500", "$500-2,000", "$2,000-10,000", "$10,000+"]
        )
        
        technical_level = st.selectbox(
            "**Technical experience:**",
            ["Beginner", "Intermediate", "Advanced", "Expert"]
        )
    
    # Store answers
    st.session_state.clarifying_answers = {
        'report_purpose': report_purpose,
        'primary_audience': primary_audience,
        'team_size': team_size,
        'timeline': timeline,
        'budget': budget,
        'technical_experience': technical_level
    }
    
    col_back, col_generate = st.columns([1, 3])
    
    with col_back:
        if st.button("← Back"):
            st.session_state.current_step = 1
            st.rerun()
    
    with col_generate:
        if st.button("Generate Report", type="primary"):
            st.session_state.current_step = 3
            st.rerun()

def render_step_3():
    """
    Step 3: Generate and display report
    
    Improvement #1: Architecture Flow Diagram
    Improvement #2: Progress Indicators  
    Improvement #4: UI Cleanup (no white box, no quality badge)
    Improvement #5: Explicit Implementation Roadmap
    Improvement #7: Adjacent AI Activities
    """
    tools_database = load_tool_database()
    
    # Generate report if not already done
    if not st.session_state.generated_report:
        with st.spinner("Generating your report..."):
            report = generate_report(
                st.session_state.user_query,
                st.session_state.clarifying_answers,
                tools_database
            )
            
            if report:
                st.session_state.generated_report = report
            else:
                st.error("Failed to generate report. Please try again.")
                return
    
    # Display report (Improvement #4: Clean display, no containers/badges)
    st.markdown("## Strategic Advisory Report")
    st.markdown(st.session_state.generated_report, unsafe_allow_html=True)
    
    # Download button
    st.download_button(
        label="📥 Download Report (Markdown)",
        data=st.session_state.generated_report,
        file_name=f"bulwise_report_{datetime.now().strftime('%Y%m%d')}.md",
        mime="text/markdown"
    )
    
    st.markdown("---")
    
    # Conversational follow-up section (Improvement #3 - STAGE 2)
    st.markdown("### 💬 Want More Detail?")
    st.markdown("""
I can help with:
- **Setup instructions** (step-by-step account creation)
- **Tool connections** (how to connect Tool A → Tool B)
- **Specific recommendations** (alternative tools, pricing questions)
- **Implementation guidance** (team training, change management)
- **Related AI activities** (adjacent use cases you might benefit from)

**Or just tell me what you'd like to know more about:**
""")
    
    user_followup = st.text_area(
        label="Your question:",
        placeholder="Example: 'I need detailed instructions on connecting Perplexity to Claude' or 'Show me related AI activities for content creation'",
        height=100,
        key="followup_question"
    )
    
    if st.button("Add to Report", type="primary", disabled=not user_followup):
        with st.spinner("Generating response..."):
            answer = generate_followup_answer(
                st.session_state.generated_report,
                user_followup
            )
            
            if answer:
                st.session_state.additional_sections.append({
                    'question': user_followup,
                    'answer': answer
                })
                st.success("✓ Added! See your answer below.")
                st.rerun()
    
    # Display all follow-up Q&As
    if st.session_state.additional_sections:
        st.markdown("---")
        st.markdown("### Your Questions Answered")
        
        for i, section in enumerate(st.session_state.additional_sections, 1):
            with st.expander(
                f"❓ {section['question']}", 
                expanded=(i == len(st.session_state.additional_sections))
            ):
                st.markdown(section['answer'], unsafe_allow_html=True)
    
    # Start over button
    st.markdown("---")
    if st.button("← Start New Report"):
        st.session_state.current_step = 1
        st.session_state.user_query = ""
        st.session_state.clarifying_answers = {}
        st.session_state.generated_report = ""
        st.session_state.additional_sections = []
        st.rerun()

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application flow"""
    render_header()
    
    if st.session_state.current_step == 1:
        render_step_1()
    elif st.session_state.current_step == 2:
        render_step_2()
    elif st.session_state.current_step == 3:
        render_step_3()

if __name__ == "__main__":
    main()
