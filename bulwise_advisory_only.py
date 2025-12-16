"""
BulWise - AI Stack Advisory Platform
Version 2.2 - UI Refinements

Updates:
- Removed "Strategic Advisory Report" title
- Simplified recommended stack format
- Fixed mermaid diagram height
- Added timeline diagram for implementation phases
- Added % completion to follow-up question generation
"""

import streamlit as st
import anthropic
import json
import os
import time
from datetime import datetime
import pandas as pd

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
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 500;
    }
    
    .stTextArea textarea {
        border-radius: 8px;
    }
    
    .example-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        cursor: pointer;
        border: 2px solid transparent;
    }
    
    .example-card:hover {
        border: 2px solid #4CAF50;
        background-color: #e8f5e9;
    }
    
    .risk-high {
        background-color: #ffebee;
        color: #c62828;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    
    .risk-medium {
        background-color: #fff3e0;
        color: #ef6c00;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    
    .risk-low {
        background-color: #e8f5e9;
        color: #2e7d32;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# ANALYTICS TRACKING
# ============================================================================

def init_analytics():
    """Initialize analytics storage"""
    if 'analytics' not in st.session_state:
        st.session_state.analytics = {
            'sessions': [],
            'queries': [],
            'reports_generated': 0
        }

def track_session():
    """Track new session"""
    init_analytics()
    session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    st.session_state.analytics['sessions'].append({
        'session_id': session_id,
        'timestamp': datetime.now().isoformat(),
        'user_agent': 'web'
    })
    return session_id

def track_query(query, context):
    """Track user query"""
    init_analytics()
    st.session_state.analytics['queries'].append({
        'timestamp': datetime.now().isoformat(),
        'query': query,
        'context': context,
        'report_purpose': context.get('report_purpose', 'Not specified'),
        'primary_audience': context.get('primary_audience', 'Not specified'),
        'budget': context.get('budget', 'Not specified')
    })
    st.session_state.analytics['reports_generated'] += 1

def export_analytics():
    """Export analytics as CSV"""
    init_analytics()
    df = pd.DataFrame(st.session_state.analytics['queries'])
    return df.to_csv(index=False)

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

if 'session_id' not in st.session_state:
    st.session_state.session_id = track_session()

# Initialize analytics
init_analytics()

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
# SYSTEM PROMPT WITH UPDATED STRUCTURE
# ============================================================================

SYSTEM_PROMPT = """You are an expert AI strategy consultant helping users select and implement the right AI tools for their specific use cases.

Your role is to provide a comprehensive, actionable advisory report that is:
- SPECIFIC (exact tool names, not categories)
- ACTIONABLE (step-by-step implementation plans)
- PROFESSIONAL (ready to present to stakeholders)
- BEGINNER-FRIENDLY (assumes no technical expertise)

## REPORT STRUCTURE - FOLLOW THIS EXACTLY

### 1. Executive Summary
[2-3 paragraphs: problem, solution, expected impact]

### 2. Recommended Stack
[REQUIRED - Ultra-simple format with ONLY tool names and categories]

Format as:
```
**Recommended AI Stack:**

• Perplexity Pro (Search)
• Claude Pro (LLM)
• Beautiful.ai (Presentation)
• Zapier Professional (Automation)

**Total Monthly Cost:** $72
**Total Annual Cost:** $864
```

CRITICAL: Only show tool name and (category). Nothing else. No prices next to tools, no descriptions. Just clean list.

### 3. Implementation Timeline
[REQUIRED - Visual timeline showing phases and milestones]

Create a Mermaid Gantt chart showing the implementation timeline:

```mermaid
gantt
    title Implementation Timeline
    dateFormat  YYYY-MM-DD
    
    section Phase 1: Setup
    Account Setup           :p1, 2024-01-01, 7d
    Tool Configuration      :p2, after p1, 7d
    
    section Phase 2: Integration
    Connect Tools          :p3, after p2, 7d
    Test Workflows         :p4, after p3, 7d
    
    section Phase 3: Optimization
    Refine Processes       :p5, after p4, 14d
    Team Training          :p6, after p5, 7d
    
    section Phase 4: Production
    Go Live               :p7, after p6, 7d
    Monitor & Improve     :p8, after p7, 30d
```

Then provide a text breakdown:

**Implementation Phases:**

**Phase 1: Setup (Weeks 1-2)**
What you'll achieve:
- All accounts created and configured
- Team members have access
- Basic understanding of each tool

Key milestone: ✓ Ready to start connecting tools

**Phase 2: Integration (Weeks 3-4)**
What you'll achieve:
- Tools connected and data flowing
- First successful end-to-end test
- Documented workflow process

Key milestone: ✓ Complete workflow working

**Phase 3: Optimization (Weeks 5-6)**
What you'll achieve:
- Processes refined based on testing
- Team trained and comfortable
- Automated processes running smoothly

Key milestone: ✓ Team independently using system

**Phase 4: Production (Weeks 7+)**
What you'll achieve:
- Fully operational system
- Regular output generation
- Continuous improvement process

Key milestone: ✓ Measurable business impact

### 4. AI Architecture Flow (Mermaid Diagram)
[REQUIRED - Create a Mermaid flowchart showing the complete workflow]

Use Mermaid syntax to create a visual flowchart. IMPORTANT: Keep it readable with 6-8 nodes maximum:

```mermaid
graph TB
    A[User Input:<br/>Describe query] --> B[Perplexity Pro:<br/>Search & collect data]
    B --> C[Claude Pro:<br/>Analyze & structure]
    C --> D[Beautiful.ai:<br/>Create presentation]
    D --> E[Final Output:<br/>Professional report]
    
    style A fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style E fill:#c8e6c9,stroke:#388e3c,stroke-width:2px
    style B fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style C fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style D fill:#fff3e0,stroke:#f57c00,stroke-width:2px
```

Requirements:
- Use actual tool names (not generic "LLM")
- Maximum 6-8 nodes for readability
- Use colors: start (#e3f2fd), process (#fff3e0), end (#c8e6c9)
- Include brief description in each node using <br/> for line breaks
- Show linear or simple branching flow only

### 5. Detailed Architecture Breakdown
[REQUIRED - Text-based detailed breakdown]

Format:
```
**Data Flow Architecture:**

INPUT LAYER
What enters: [Specific description]
Format: [Text/JSON/CSV]
Example: "Healthcare AI startup names and funding data"

↓

ORCHESTRATION LAYER
Tool: [Specific tool name - e.g., Zapier Professional]
Role: [What it orchestrates]
Setup: [1-2 sentences on configuration]

↓

PROCESSING LAYER 1: Data Collection
Tool: [Specific tool - e.g., Perplexity Pro]
Input: [What it receives]
Process: [What it does]
Output: [Format and content]

↓

PROCESSING LAYER 2: Analysis
Tool: [Specific tool - e.g., Claude Pro]  
Input: [What it receives from previous layer]
Process: [What analysis it performs]
Output: [Format and content]

↓

OUTPUT LAYER
Tool: [Specific tool - e.g., Beautiful.ai]
Input: [What it receives]
Process: [How it creates final output]
Output: [Final deliverable format]
```

### 6. Detailed Tool Analysis
For each recommended tool:
- Tool name and category
- Why it's recommended (specific to use case)
- Key features relevant to this use case
- Pricing breakdown (monthly/annual)
- Integration requirements
- Setup complexity (beginner/intermediate/advanced)
- Alternative options at different price points

### 7. Implementation Roadmap
[Detailed day-by-day plan]

Format for each task:
```
**WEEK X, DAY Y: [Specific Task Name]**
───────────────────────────────────────

**What you'll accomplish:**
[One-sentence goal]

**Step-by-step instructions:**
1. [Exact action - e.g., "Go to perplexity.ai"]
2. [Specific button - e.g., "Click 'Sign Up' (blue button, top right)"]
3. [Exact field - e.g., "Enter your email in 'Email Address' field"]
4. [Expected result - e.g., "You'll receive verification code"]
5. [Verification - e.g., "Check for 'Pro' badge next to your name"]

**Time required:** [X minutes/hours]

**Prerequisites:**
- [What you need - e.g., "Credit card for $20/month payment"]
- [Access requirements]

**Expected output:**
- Format: [JSON/CSV/Text/etc]
- Contents: [What data you'll have]
- Where to save: [Location/folder]

**✓ CHECKPOINT:**
You should now have [specific outcome]

**Troubleshooting:**
- If [problem], then [solution]
- Common issue: [issue] → [fix]

**Connecting to next step:**
You'll use this [output] in [next task] on [Week X, Day Y]
───────────────────────────────────────
```

### 8. Risk Assessment & Mitigation

[REQUIRED - Present as a structured table with color-coded risk levels]

| Risk | Likelihood | Impact | Mitigation Strategy |
|------|-----------|--------|---------------------|
| [Specific risk] | 🔴 High / 🟡 Medium / 🟢 Low | 🔴 High / 🟡 Medium / 🟢 Low | [Specific mitigation steps] |

Include 4-6 most relevant risks for the use case.

### 9. Success Metrics

[REQUIRED - Provide clear, understandable metrics with explanations]

Format:
```
**How to Measure Success:**

**1. [Metric Name]**
   - **What it is:** [Clear explanation in simple terms]
   - **How to measure:** [Specific measurement method]
   - **Target:** [Specific number/goal]
   - **Why it matters:** [Business impact]
   
   Example: After 3 months, you should see [specific outcome]
```

AVOID vague metrics. ALWAYS explain HOW to measure and WHY it matters.

### 10. Financial Summary

[Simple cost breakdown - NO ROI analysis]

Format:
```
**Investment Summary:**

**Setup Costs (One-time):**
- Account setup & configuration: $X
- Initial training: $X
- Total setup: $XXX

**Monthly Costs:**
- [Tool 1]: $X/month
- [Tool 2]: $Y/month
- [Tool 3]: $Z/month
- Total monthly: $XXX/month

**Annual Costs:**
- Tools & subscriptions: $X,XXX/year
- Estimated total: $X,XXX/year

**Cost Optimization Tips:**
- [Specific tip to reduce costs]
- [Another tip]
```

### 11. Related AI Opportunities

[REQUIRED - Show exactly 2 adjacent use cases]

Format:
```
**Based on your [use case], you might also benefit from:**

**1. [Related Use Case Name]**

**What it is:** [2-3 sentence description]

**How it connects:** [2 sentences explaining the connection]

**Recommended tools:**
• [Tool 1] (Category) - $X/month
• [Tool 2] (Category) - $Y/month

**Setup time:** [X weeks]
**Potential impact:** [Specific business value]

---

**2. [Second Related Use Case Name]**

**What it is:** [2-3 sentence description]

**How it connects:** [2 sentences explaining connection]

**Recommended tools:**
• [Tool 1] (Category) - $X/month
• [Tool 2] (Category) - $Y/month

**Setup time:** [X weeks]
**Potential impact:** [Specific business value]

---

*Want recommendations for additional use cases? Just ask in the follow-up section below!*
```

### 12. Next Steps

[Immediate actionable items]
- [ ] [Specific first action]
- [ ] [Specific second action]
- [ ] [Specific third action]

## CRITICAL REQUIREMENTS

### Mermaid Diagrams
- ALWAYS include TWO Mermaid diagrams:
  1. Timeline (Gantt chart) at the beginning
  2. Architecture flow (flowchart) after timeline
- Use proper Mermaid syntax
- Keep architecture flow to 6-8 nodes maximum for readability
- Use colors for visual appeal
- Architecture should show linear workflow with actual tool names

### Recommended Stack Format
CRITICAL: Only show tool name and (category). Example:
```
• Perplexity Pro (Search)
• Claude Pro (LLM)
```

NOT:
```
• Perplexity Pro (Search) - $20/month - Why this tool
```

Keep it ultra-clean and simple.

### Context-Aware Customization

Adapt based on user context:

**If primary_audience = "Individual (just me)":**
- Conversational, friendly tone
- Assume limited budget
- Focus on self-implementation
- Include free/low-cost alternatives

**If primary_audience = "C-suite executives":**
- Minimize technical jargon
- Focus on business outcomes
- Emphasize competitive advantage

**If primary_audience = "Technical team":**
- Include technical details
- Provide integration specifics
- Use appropriate technical terminology

## OUTPUT REQUIREMENTS

- Use Markdown formatting
- Include TWO Mermaid diagrams (timeline + architecture)
- Present risks in table format with color coding
- Explain all metrics clearly
- Show exactly 2 related opportunities
- Recommended Stack: ONLY tool name (category)
- Be specific with URLs and costs
- NO ROI analysis
- Professional and ready to present
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
    """Generate comprehensive advisory report using Claude API"""
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
    
    # Progress indicators with percentages
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Step 1: 20%
        status_text.text("◆ Analyzing your requirements... (20%)")
        progress_bar.progress(20)
        time.sleep(0.3)
        
        # Step 2: 40%
        status_text.text("◇ Searching tool database... (40%)")
        progress_bar.progress(40)
        time.sleep(0.3)
        
        # Step 3: 60% - Actual API call
        status_text.text("▲ Generating recommendations... (60%)")
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
        
        # Step 4: 80%
        status_text.text("△ Creating diagrams and charts... (80%)")
        progress_bar.progress(80)
        time.sleep(0.2)
        
        # Step 5: 100%
        status_text.text("● Finalizing report... (100%)")
        progress_bar.progress(100)
        time.sleep(0.2)
        
        # Complete
        status_text.text("✓ Your report is ready!")
        time.sleep(0.5)
        
        # Clean up
        progress_bar.empty()
        status_text.empty()
        
        # Track analytics
        track_query(user_query, clarifying_answers)
        
        # Extract report text
        report_text = response.content[0].text
        return report_text
        
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"Error generating report: {str(e)}")
        return None

def generate_followup_answer(original_report, user_question):
    """Generate answer to user's follow-up question with progress indicator"""
    prompt = f"""Based on this AI stack advisory report:

{original_report}

The user has asked: "{user_question}"

Provide a detailed, helpful answer to their question. Match the report's tone and format.
Be specific and actionable. If they ask for more related AI opportunities, provide 2-3 additional ones following the same format as in the original report."""

    # Progress indicator for follow-up
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("◆ Understanding your question... (25%)")
        progress_bar.progress(25)
        time.sleep(0.2)
        
        status_text.text("◇ Generating detailed answer... (50%)")
        progress_bar.progress(50)
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        status_text.text("▲ Formatting response... (75%)")
        progress_bar.progress(75)
        time.sleep(0.2)
        
        status_text.text("✓ Answer ready! (100%)")
        progress_bar.progress(100)
        time.sleep(0.3)
        
        # Clean up
        progress_bar.empty()
        status_text.empty()
        
        return response.content[0].text
        
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
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

def render_example_prompts():
    """Render example use cases for users to click"""
    st.markdown("### 💡 Example Use Cases")
    st.caption("Click any example to get started, or write your own below")
    
    examples = [
        {
            "title": "🔍 Competitor Intelligence",
            "prompt": "I need to build a competitor intelligence system that tracks healthcare AI startups, monitors their funding rounds, analyzes their product launches, and generates weekly summary reports for our executive team."
        },
        {
            "title": "✍️ Content Creation Workflow",
            "prompt": "Help me create an AI-powered content workflow that generates blog posts, optimizes them for SEO, creates social media snippets, and schedules posts across multiple platforms."
        },
        {
            "title": "📊 Data Analysis & Visualization",
            "prompt": "I want to automate our sales data analysis by pulling data from our CRM, analyzing trends, generating insights, and creating interactive dashboards that update daily."
        },
        {
            "title": "💬 Customer Support Automation",
            "prompt": "Build an AI customer support system that handles common inquiries via chat, escalates complex issues to humans, and learns from past conversations to improve responses."
        },
        {
            "title": "📈 Market Research Automation",
            "prompt": "Create a system that monitors industry news, tracks market trends, identifies emerging competitors, and produces monthly market intelligence reports for strategic planning."
        },
        {
            "title": "🎨 Marketing Asset Generation",
            "prompt": "I need AI tools to help my marketing team generate product descriptions, create social media graphics, write email campaigns, and produce video scripts for different audience segments."
        }
    ]
    
    cols = st.columns(2)
    for idx, example in enumerate(examples):
        with cols[idx % 2]:
            if st.button(
                f"{example['title']}",
                key=f"example_{idx}",
                use_container_width=True
            ):
                st.session_state.user_query = example['prompt']
                st.session_state.current_step = 2
                st.rerun()

def render_step_1():
    """Step 1: Initial user query with examples"""
    render_example_prompts()
    
    st.markdown("---")
    st.markdown("### Or Describe Your Own Use Case")
    
    user_query = st.text_area(
        "What AI workflow do you want to build?",
        value=st.session_state.user_query,
        placeholder="Example: I need to automate our weekly competitor analysis by searching for competitors, analyzing their strategies, and creating a presentation for stakeholders...",
        height=150,
        key="query_input"
    )
    
    if st.button("Continue", type="primary", disabled=not user_query):
        st.session_state.user_query = user_query
        st.session_state.current_step = 2
        st.rerun()

def render_step_2():
    """Step 2: Clarifying questions"""
    st.markdown("## Help Us Tailor Your Report")
    st.markdown(f"**Your use case:** {st.session_state.user_query}")
    st.markdown("---")
    
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
    """Step 3: Generate and display report"""
    tools_database = load_tool_database()
    
    # Generate report if not already done
    if not st.session_state.generated_report:
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
    
    # Display report with Mermaid support (REMOVED "Strategic Advisory Report" title)
    
    # Check if report contains mermaid diagrams
    if "```mermaid" in st.session_state.generated_report:
        # Split report by mermaid blocks
        parts = st.session_state.generated_report.split("```mermaid")
        
        # Display first part (before first mermaid)
        st.markdown(parts[0], unsafe_allow_html=True)
        
        # Display each mermaid diagram and subsequent text
        for i in range(1, len(parts)):
            # Extract mermaid code and remaining text
            mermaid_end = parts[i].find("```")
            if mermaid_end != -1:
                mermaid_code = parts[i][:mermaid_end].strip()
                remaining_text = parts[i][mermaid_end + 3:]
                
                # Display mermaid diagram with increased height
                try:
                    import streamlit.components.v1 as components
                    components.html(
                        f"""
                        <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
                        <script>mermaid.initialize({{startOnLoad:true}});</script>
                        <div class="mermaid">
                        {mermaid_code}
                        </div>
                        """,
                        height=600,
                        scrolling=True
                    )
                except:
                    # Fallback: show as code block
                    st.code(mermaid_code, language="mermaid")
                
                # Display remaining text
                st.markdown(remaining_text, unsafe_allow_html=True)
    else:
        # No mermaid diagrams, display normally
        st.markdown(st.session_state.generated_report, unsafe_allow_html=True)
    
    # Download button
    st.download_button(
        label="📥 Download Report (Markdown)",
        data=st.session_state.generated_report,
        file_name=f"bulwise_report_{datetime.now().strftime('%Y%m%d')}.md",
        mime="text/markdown"
    )
    
    st.markdown("---")
    
    # Conversational follow-up section
    st.markdown("### 💬 Want More Detail?")
    st.markdown("""
I can help with:
- **Setup instructions** (step-by-step account creation)
- **Tool connections** (how to connect Tool A → Tool B)
- **More related opportunities** (additional use cases beyond the 2 shown)
- **Implementation guidance** (team training, change management)
- **Specific questions** (pricing, alternatives, technical details)

**Tell me what you'd like to know more about:**
""")
    
    user_followup = st.text_area(
        label="Your question:",
        placeholder="Example: 'Show me 3 more related AI opportunities' or 'I need detailed setup instructions for Perplexity'",
        height=100,
        key="followup_question"
    )
    
    if st.button("Add to Report", type="primary", disabled=not user_followup):
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
# OWNER ANALYTICS SIDEBAR
# ============================================================================

def render_analytics_sidebar():
    """Render analytics for owner (password protected)"""
    with st.sidebar:
        st.markdown("## 📊 Analytics Dashboard")
        st.caption("Owner access only")
        
        # Simple password protection
        password = st.text_input("Enter owner password:", type="password", key="owner_pass")
        
        # Check password (you should change this!)
        if password == "bulwise2024":
            st.success("✓ Access granted")
            
            init_analytics()
            
            st.markdown("### Usage Statistics")
            st.metric("Total Reports Generated", st.session_state.analytics['reports_generated'])
            st.metric("Total Queries", len(st.session_state.analytics['queries']))
            st.metric("Total Sessions", len(st.session_state.analytics['sessions']))
            
            # Show recent queries
            if st.session_state.analytics['queries']:
                st.markdown("### Recent Queries")
                recent = st.session_state.analytics['queries'][-5:][::-1]  # Last 5, reversed
                for q in recent:
                    with st.expander(f"{q['timestamp'][:10]} - {q['primary_audience']}"):
                        st.write(f"**Query:** {q['query'][:100]}...")
                        st.write(f"**Purpose:** {q['report_purpose']}")
                        st.write(f"**Budget:** {q['budget']}")
            
            # Export button
            st.markdown("### Export Data")
            if st.button("📥 Download All Analytics (CSV)"):
                csv = export_analytics()
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"bulwise_analytics_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        elif password:
            st.error("❌ Incorrect password")

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application flow"""
    render_header()
    
    # Show analytics sidebar (password protected)
    render_analytics_sidebar()
    
    if st.session_state.current_step == 1:
        render_step_1()
    elif st.session_state.current_step == 2:
        render_step_2()
    elif st.session_state.current_step == 3:
        render_step_3()

if __name__ == "__main__":
    main()
