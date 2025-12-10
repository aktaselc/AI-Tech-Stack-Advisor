import streamlit as st
import anthropic
import json
from datetime import datetime, timedelta
import hashlib
import sqlite3
import re
import os

# Page configuration
st.set_page_config(
    page_title="Bulwise - Strategic AI Advisory",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================================
# RATE LIMITING - Cookie-Based
# ============================================================================

def get_browser_id():
    """Generate a unique browser ID for rate limiting."""
    if 'browser_id' not in st.session_state:
        import random
        st.session_state.browser_id = hashlib.md5(
            f"{datetime.now().timestamp()}{random.random()}".encode()
        ).hexdigest()
    return st.session_state.browser_id

def get_usage_data():
    """Get usage data from browser storage."""
    browser_id = get_browser_id()
    
    if 'usage_data' not in st.session_state:
        st.session_state.usage_data = {
            'browser_id': browser_id,
            'count': 0,
            'reset_date': datetime.now().isoformat(),
            'first_use': datetime.now().isoformat()
        }
    
    usage = st.session_state.usage_data
    
    # Check if we need to reset (monthly)
    reset_date = datetime.fromisoformat(usage['reset_date'])
    if datetime.now() > reset_date + timedelta(days=30):
        usage['count'] = 0
        usage['reset_date'] = datetime.now().isoformat()
        st.session_state.usage_data = usage
    
    return usage

def increment_usage():
    """Increment usage counter."""
    usage = get_usage_data()
    usage['count'] += 1
    st.session_state.usage_data = usage
    return usage['count']

def check_rate_limit():
    """Check if user has exceeded rate limit. Returns (allowed, count, reset_date)."""
    MAX_QUERIES_PER_MONTH = 3
    usage = get_usage_data()
    reset_date = datetime.fromisoformat(usage['reset_date'])
    next_reset = reset_date + timedelta(days=30)
    
    allowed = usage['count'] < MAX_QUERIES_PER_MONTH
    return allowed, usage['count'], next_reset

# ============================================================================
# ANALYTICS TRACKING
# ============================================================================

def init_analytics_db():
    """Initialize analytics database."""
    conn = sqlite3.connect('bulwise_analytics.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS queries
                 (query_id TEXT PRIMARY KEY,
                  timestamp TEXT,
                  user_query TEXT,
                  query_length INTEGER,
                  detected_category TEXT,
                  budget_mentioned BOOLEAN,
                  team_size TEXT,
                  recommended_tools TEXT,
                  response_time REAL,
                  user_session_id TEXT,
                  rate_limit_hit BOOLEAN,
                  is_return_user BOOLEAN,
                  visit_count INTEGER,
                  days_since_last_visit REAL)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS user_sessions
                 (user_session_id TEXT PRIMARY KEY,
                  first_visit TEXT,
                  last_visit TEXT,
                  total_queries INTEGER,
                  total_visits INTEGER)''')
    
    conn.commit()
    conn.close()

def detect_query_category(query):
    """Detect category from user query."""
    query_lower = query.lower()
    
    categories = {
        'video': ['video', 'youtube', 'tiktok', 'reels', 'editing'],
        'content': ['content', 'blog', 'article', 'writing', 'copy', 'social media'],
        'coding': ['code', 'coding', 'software', 'developer', 'programming', 'engineer'],
        'marketing': ['marketing', 'seo', 'email', 'campaign', 'ads'],
        'data': ['data', 'analytics', 'analysis', 'insights', 'reporting'],
        'design': ['design', 'graphic', 'ui', 'ux', 'creative'],
        'audio': ['audio', 'podcast', 'voice', 'music', 'sound'],
        'automation': ['automation', 'workflow', 'process', 'automate'],
        'customer_service': ['customer', 'support', 'service', 'chat']
    }
    
    for category, keywords in categories.items():
        if any(keyword in query_lower for keyword in keywords):
            return category
    
    return 'general'

def extract_budget(query):
    """Extract budget information from query."""
    budget_patterns = [r'\$\d+', r'\d+\s*dollars?', r'budget.*?\d+', r'cost', r'price', r'afford']
    query_lower = query.lower()
    
    for pattern in budget_patterns:
        if re.search(pattern, query_lower):
            return True
    return False

def extract_team_size(query):
    """Extract team size from query."""
    query_lower = query.lower()
    
    if any(word in query_lower for word in ['solo', 'freelance', 'individual', 'myself', 'i am']):
        return 'solo'
    elif any(word in query_lower for word in ['team of', 'people', 'members', 'employees']):
        numbers = re.findall(r'\d+', query)
        if numbers:
            size = int(numbers[0])
            if size <= 5:
                return 'small_team'
            elif size <= 20:
                return 'medium_team'
            else:
                return 'enterprise'
        return 'small_team'
    
    return 'unspecified'

def get_user_session_info():
    """Get or create user session info."""
    browser_id = get_browser_id()
    
    conn = sqlite3.connect('bulwise_analytics.db')
    c = conn.cursor()
    
    c.execute("SELECT * FROM user_sessions WHERE user_session_id = ?", (browser_id,))
    session = c.fetchone()
    
    if session:
        session_id, first_visit, last_visit, total_queries, total_visits = session
        
        last_visit_dt = datetime.fromisoformat(last_visit)
        days_since = (datetime.now() - last_visit_dt).total_seconds() / 86400
        
        is_return = True
        visit_count = total_visits + 1
        
        conn.close()
        return is_return, visit_count, days_since
    else:
        conn.close()
        return False, 1, 0.0

def update_user_session():
    """Update user session after query."""
    browser_id = get_browser_id()
    
    conn = sqlite3.connect('bulwise_analytics.db')
    c = conn.cursor()
    
    c.execute("SELECT * FROM user_sessions WHERE user_session_id = ?", (browser_id,))
    session = c.fetchone()
    
    if session:
        c.execute("""UPDATE user_sessions 
                     SET last_visit = ?, total_queries = total_queries + 1, total_visits = total_visits + 1
                     WHERE user_session_id = ?""",
                  (datetime.now().isoformat(), browser_id))
    else:
        c.execute("""INSERT INTO user_sessions VALUES (?, ?, ?, ?, ?)""",
                  (browser_id, datetime.now().isoformat(), datetime.now().isoformat(), 1, 1))
    
    conn.commit()
    conn.close()

def log_query(user_query, recommended_tools=None, response_time=None):
    """Log query to analytics database."""
    try:
        init_analytics_db()
        
        query_id = hashlib.md5(f"{user_query}{datetime.now().timestamp()}".encode()).hexdigest()
        timestamp = datetime.now().isoformat()
        query_length = len(user_query)
        category = detect_query_category(user_query)
        budget_mentioned = extract_budget(user_query)
        team_size = extract_team_size(user_query)
        browser_id = get_browser_id()
        
        allowed, count, _ = check_rate_limit()
        rate_limit_hit = not allowed
        
        is_return, visit_count, days_since = get_user_session_info()
        
        conn = sqlite3.connect('bulwise_analytics.db')
        c = conn.cursor()
        
        c.execute("""INSERT INTO queries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (query_id, timestamp, user_query, query_length, category,
                   budget_mentioned, team_size, recommended_tools, response_time,
                   browser_id, rate_limit_hit, is_return, visit_count, days_since))
        
        conn.commit()
        conn.close()
        
        update_user_session()
        
    except Exception as e:
        st.error(f"Analytics logging error: {str(e)}")

# ============================================================================
# LOAD DATABASE
# ============================================================================

@st.cache_data
def load_database():
    """Load AI tools database."""
    try:
        with open('ai_tools_complete.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("Database file not found. Please ensure ai_tools_complete.json is in the app directory.")
        return {'ai_tools': []}

# ============================================================================
# CUSTOM CSS
# ============================================================================

st.markdown("""
    <style>
    /* Clean, minimal styling */
    .main {
        padding-top: 2rem;
    }
    
    /* Progress bar styling */
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
    
    /* Button styling */
    .stButton > button {
        background-color: #2E7D32;
        color: white;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        border: none;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background-color: #1B5E20;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Text input styling */
    .stTextArea textarea {
        border-radius: 8px;
        border: 2px solid #e0e0e0;
        padding: 1rem;
    }
    
    /* Report styling */
    .whitepaper-section {
        background: white;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-top: 2rem;
    }
    
    .whitepaper-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 1.5rem;
        padding-bottom: 1rem;
        border-bottom: 3px solid #2E7D32;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Responsive */
    @media (max-width: 768px) {
        .main {
            padding: 1rem;
        }
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# MAIN APP - ADVISORY ONLY
# ============================================================================

# Initialize analytics
init_analytics_db()

# Load database
database = load_database()

# Get API key from secrets or user input
try:
    api_key = st.secrets.get("ANTHROPIC_API_KEY", None)
except Exception:
    api_key = None

if not api_key:
    st.warning("⚠️ API key required")
    api_key = st.text_input(
        "Enter your Anthropic API Key:",
        type="password",
        help="Get your API key at console.anthropic.com"
    )
    
    if not api_key:
        st.info("💡 **No API key?** Get one at [console.anthropic.com](https://console.anthropic.com)")
        st.stop()

# Header
st.markdown("# 🎯 Strategic AI Advisory")
st.markdown("### Get professional recommendations tailored to your needs")
st.markdown("---")

# Info expander
with st.expander("ℹ️ What you'll receive", expanded=False):
    st.markdown("""
    **Your personalized advisory report includes:**
    
    - 📊 Analyst note with strategic overview
    - 📋 Executive summary and methodology
    - 🛠️ Tool recommendations with detailed rationale
    - 📅 Implementation roadmap with timeline
    - 💰 Cost analysis and ROI projections
    - ⚠️ Risk assessment and success factors
    - 🔄 Alternative scenarios for different budgets
    - 📈 Market research and industry benchmarks
    
    *Report generation takes 30-60 seconds with real-time progress tracking.*
    """)

st.markdown("<br>", unsafe_allow_html=True)

# User input
user_query = st.text_area(
    "**📝 Describe Your Requirements:**",
    value=st.session_state.get('example_query', ''),
    height=180,
    placeholder="Example: I'm a marketing consultant working with 5-10 small business clients simultaneously. I need to create weekly content (blog posts, social media, email campaigns) efficiently. Budget is $100-150/month. I have intermediate technical skills and need tools that integrate well together. Timeline: implement within 2 weeks.",
    help="Be specific about your use case, budget, team size, and timeline for best results."
)

# Quick start examples
st.markdown("**Quick Start Examples:**")
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("📹 Video\nProduction", use_container_width=True):
        st.session_state['example_query'] = "I run a digital agency and need to produce 10-15 professional video content pieces monthly for enterprise clients. Need AI tools for script writing, video generation, voiceovers, and editing. Budget: $200-300/month. Team of 3 people with mixed technical skills."
        st.rerun()

with col2:
    if st.button("✍️ Content\nMarketing", use_container_width=True):
        st.session_state['example_query'] = "E-commerce business needing to scale content creation: product descriptions, blog posts, email campaigns, and social media. Team of 2 marketers. Budget: $75-100/month."
        st.rerun()

with col3:
    if st.button("💻 Software\nDevelopment", use_container_width=True):
        st.session_state['example_query'] = "Software development team of 5 engineers working on full-stack web applications. Need AI assistants for code generation, debugging, documentation, and code review. Budget: $100-150/month total."
        st.rerun()

with col4:
    if st.button("🎙️ Podcast\nProduction", use_container_width=True):
        st.session_state['example_query'] = "Starting a weekly B2B podcast. Need tools for recording, editing, transcription, show notes generation, and distribution. Solo operation with limited technical background. Budget: $50-75/month."
        st.rerun()

st.markdown("---")

# Check rate limit and display status
allowed, query_count, next_reset = check_rate_limit()

# Display usage status
col1, col2 = st.columns([3, 1])
with col1:
    if allowed:
        remaining = 3 - query_count
        if remaining == 3:
            st.info(f"ℹ️ Free tier: {remaining} advisory reports remaining this month")
        elif remaining == 2:
            st.info(f"ℹ️ {remaining} advisory reports remaining this month")
        else:
            st.warning(f"⚠️ Only {remaining} advisory report remaining this month. Resets on {next_reset.strftime('%B %d, %Y')}")
    else:
        st.error(f"🚫 Monthly limit reached (3 free reports). Resets on {next_reset.strftime('%B %d, %Y')}")
        st.info("💡 Want unlimited reports? Contact: hello@bulwise.io")

with col2:
    generate_button = st.button(
        "📊 Generate Advisory",
        type="primary",
        use_container_width=True,
        disabled=not allowed or not user_query.strip()
    )

# Generate advisory report
if generate_button and user_query.strip():
    
    with st.spinner(""):
        try:
            client = anthropic.Anthropic(api_key=api_key)
            
            # Create progress tracking
            progress_container = st.container()
            with progress_container:
                progress_bar = st.progress(0)
                status_text = st.empty()
            
            status_text.text("🔍 Analyzing your requirements... (10%)")
            progress_bar.progress(10)
            
            # System prompt (keeping full prompt from original)
            system_prompt = f"""You are Bulwise, a strategic AI implementation advisory service. Generate professional, data-driven reports for clients seeking AI tool recommendations.

You have access to:
1. A comprehensive database of {len(database['ai_tools'])} AI tools with detailed specifications
2. Web search capability to find current market research and trends

CRITICAL: Format your response as a professional whitepaper-style advisory report with the following structure (IN THIS EXACT ORDER):

---

## ANALYST NOTE
[Brief professional note (2-3 sentences) welcoming the client, emphasizing the data-driven strategic nature of this recommendation, and expressing willingness to answer follow-up questions. Keep warm and professional.]

---

## EXECUTIVE SUMMARY
[2-3 sentences providing high-level overview of the recommendation and expected outcomes]

---

## METHODOLOGY & ANALYSIS
**Requirements Analysis:**
[Summarize the client's stated needs, constraints, and objectives]

**Evaluation Criteria:**
[List the key factors considered in tool selection: budget alignment, technical requirements, workflow integration, scalability, etc.]

**Data Sources:**
[Note that recommendations are based on comprehensive database analysis of {len(database['ai_tools'])} tools across 15+ categories, plus current market research from credible sources]

---

## STRATEGIC RECOMMENDATIONS

### Recommended Tools
[FIRST: List the 3-5 recommended tool NAMES ONLY as a simple bulleted list for quick reference]

Example format:
- **ChatGPT** (Content Generation)
- **Midjourney** (Visual Design)
- **Claude** (Strategic Analysis)

### Detailed Technology Stack Analysis
[NOW: Provide the full detailed analysis for each tool]

For each tool, provide:
- **Tool Name** (Category)
- **Strategic Rationale:** Why this tool fits the client's needs (2-3 sentences with specific data points, referencing market position if available)
- **Key Capabilities:** Bullet list of relevant features
- **Pricing:** Specific tier recommendation with justification

### Tool Integration Workflow
[Provide step-by-step explanation of how these tools work together in practice, including data flow and handoffs between systems]

---

## IMPLEMENTATION ROADMAP

### Phase 1: Foundation (Week 1-2)
[Initial setup steps and quick wins]

### Phase 2: Integration (Week 3-4)
[Connecting tools and establishing workflows]

### Phase 3: Optimization (Month 2+)
[Refinement and advanced feature adoption]

---

## FINANCIAL ANALYSIS

### Cost Breakdown
[Detailed monthly cost projection for each tool, including tier recommendations]

**Total Monthly Investment:** $[X]
**Annual Projection:** $[Y]

### Expected ROI
[Quantify time savings, efficiency gains, or revenue impact where possible, using industry benchmarks from market research WITH SOURCES. Be realistic and conservative.]

### Cost Optimization Strategies
[Suggest ways to reduce costs or maximize value]

---

## RISK ASSESSMENT & MITIGATION

### Potential Challenges
[List 3-5 realistic challenges the client might face, informed by industry best practices and market research]

### Mitigation Strategies
[For each challenge, provide specific actionable mitigation approach]

### Success Factors
[List critical factors for successful implementation]

---

## ALTERNATIVE SCENARIOS

### Budget-Constrained Alternative
[If budget is reduced by 30-50%, what would you recommend?]

### Premium Alternative
[If budget allows 50-100% more investment, what enhanced capabilities could be added?]

### Different Scale Scenario
[How would recommendations change for 2x team size or 2x content volume?]

---

## SUPPORTING DATA

### Tool Comparison Matrix
[Create a simple text-based comparison of recommended tools vs alternatives on key criteria]

### Industry Benchmarks
[Include relevant statistics from market research about typical costs, implementation times, adoption rates - WITH SOURCES]

### Reference Documentation
[List official documentation, case studies, or resources for each recommended tool]

---

## MARKET RESEARCH & CONTEXT

**Industry Overview:**
Use web_search to find current market data related to the user's specific use case. For EVERY statistic or claim, include the source in parentheses.

Example format:
"The AI-powered video production market reached $2.8 billion in 2024 and is projected to grow at 22% CAGR through 2028 (MarketsandMarkets, 2024). According to Gartner's 2024 State of Marketing survey, 67% of marketing teams now use AI video tools, up from 34% in 2023."

Include:
- Market size and growth rate (with source)
- Current adoption trends and statistics (with source)
- Industry ROI benchmarks - be conservative (with source)
- Key challenges organizations typically face (with source)

**Competitive Landscape:**
Brief overview of how AI is currently transforming this specific area and what solutions are gaining traction (cite sources where applicable).

**Sources:**
After the Market Research section, include a "Sources" subsection listing all references:
- Source Name (Year): Brief description or URL if available
- Format as a simple bulleted list

Example:
**Sources:**
- MarketsandMarkets (2024): AI Video Production Market Report
- Gartner (2024): State of Marketing Survey
- Content Marketing Institute (2024): Industry Benchmark Report
- HubSpot Research (2024): Marketing Trends Report
- Forrester (2024): ROI Analysis

---

CRITICAL SOURCE CITATION REQUIREMENTS:
- EVERY statistic in Market Research section MUST include source in parentheses: (Source Name, Year)
- Include a "Sources:" subsection after Market Research with full references
- Use credible sources: Gartner, Forrester, IDC, McKinsey, industry associations, academic research
- If you cannot find a credible source for a claim, do not include the claim
- Industry benchmarks in ROI section should also cite sources when possible
- Prefer recent sources (2023-2024) over older data

TONE GUIDELINES:
- Professional and consultative, not casual or chatty
- Data-driven with specific numbers and CITED sources
- Balanced and objective, acknowledging tradeoffs
- Accessible to both technical and non-technical readers
- Conservative on ROI projections (under-promise, over-deliver)
- Analyst Note should be warm and welcoming while maintaining professionalism

DATABASE:
{json.dumps(database['ai_tools'], indent=2)}"""
            
            status_text.text("📊 Researching market data... (30%)")
            progress_bar.progress(30)

            status_text.text("🤖 Generating strategic recommendations... (50%)")
            progress_bar.progress(50)
            
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                system=[{
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"}
                }],
                messages=[{"role": "user", "content": user_query}]
            )
            
            status_text.text("✨ Finalizing report... (80%)")
            progress_bar.progress(80)
            
            # Extract text from response (handling tool use blocks)
            response_text = ""
            for block in message.content:
                if hasattr(block, 'text'):
                    response_text += block.text
            
            status_text.text("✅ Report complete! (100%)")
            progress_bar.progress(100)
            
            # Clear progress indicators after brief pause
            import time
            time.sleep(0.5)
            progress_bar.empty()
            status_text.empty()
            
            # Display the report
            st.markdown('<div class="whitepaper-section">', unsafe_allow_html=True)
            st.markdown('<div class="whitepaper-header">Strategic Advisory Report</div>', unsafe_allow_html=True)
            st.markdown(response_text)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Log query for analytics
            log_query(
                user_query=user_query,
                recommended_tools=None,
                response_time=None
            )
            
            # Increment usage counter
            new_count = increment_usage()
            
            # Show success message
            remaining = 3 - new_count
            if remaining > 0:
                st.success(f"✅ Report generated successfully! You have {remaining} reports remaining this month.")
            else:
                st.info("✅ Report generated! This was your last free report this month. Resets on " + 
                       next_reset.strftime('%B %d, %Y'))
            
        except anthropic.APIError as e:
            st.error(f"API Error: {str(e)}")
            if "credit balance" in str(e).lower():
                st.info("Please add credits to your Anthropic account at console.anthropic.com")
        except AttributeError as e:
            st.error("Response parsing error - this is usually due to tool use blocks in the API response")
            st.info("💡 The response format was unexpected. Please try again. The issue has been logged.")
        except Exception as e:
            st.error(f"Unexpected error: {str(e)}")
            st.info("💡 Please try again. If the issue persists, contact support.")

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #666; padding: 2rem 0;'>
        <p>Bulwise - AI Implementation Intelligence</p>
        <p>Questions? <a href='mailto:hello@bulwise.io'>hello@bulwise.io</a></p>
    </div>
""", unsafe_allow_html=True)
