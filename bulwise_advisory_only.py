import streamlit as st
import anthropic
import json
from datetime import datetime, timedelta
import hashlib
import sqlite3
import re
import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
import io

# Page configuration
st.set_page_config(
    page_title="Bulwise - Strategic AI Stack Advisory",
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
    
    c.execute('''CREATE TABLE IF NOT EXISTS feedback
                 (feedback_id TEXT PRIMARY KEY,
                  timestamp TEXT,
                  user_query TEXT,
                  sentiment TEXT,
                  feedback_text TEXT,
                  user_session_id TEXT)''')
    
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

def log_feedback(user_query, sentiment, feedback_text):
    """Log user feedback to analytics database."""
    try:
        feedback_id = hashlib.md5(f"{user_query}{datetime.now().timestamp()}".encode()).hexdigest()
        timestamp = datetime.now().isoformat()
        browser_id = get_browser_id()
        
        conn = sqlite3.connect('bulwise_analytics.db')
        c = conn.cursor()
        
        c.execute("""INSERT INTO feedback VALUES (?, ?, ?, ?, ?, ?)""",
                  (feedback_id, timestamp, user_query, sentiment, feedback_text, browser_id))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        st.error(f"Feedback logging error: {str(e)}")

# ============================================================================
# POWERPOINT GENERATION
# ============================================================================

def generate_professional_pptx(report_text, user_query):
    """Generate a professional PowerPoint presentation from the report."""
    
    # Create presentation
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)
    
    # Define color scheme - Professional green/gray
    BRAND_GREEN = RGBColor(46, 125, 50)  # #2E7D32
    DARK_GRAY = RGBColor(51, 51, 51)
    LIGHT_GRAY = RGBColor(245, 245, 245)
    
    # Parse sections from report
    sections = {}
    current_section = None
    current_content = []
    
    for line in report_text.split('\n'):
        if line.startswith('## '):
            if current_section:
                sections[current_section] = '\n'.join(current_content)
            current_section = line.replace('## ', '').strip()
            current_content = []
        else:
            current_content.append(line)
    
    if current_section:
        sections[current_section] = '\n'.join(current_content)
    
    # Slide 1: Title Slide
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout
    
    # Add background color
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = LIGHT_GRAY
    
    # Title
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(2.5), Inches(9), Inches(1))
    title_frame = title_box.text_frame
    title_frame.text = "Strategic AI Implementation Advisory"
    title_p = title_frame.paragraphs[0]
    title_p.font.size = Pt(44)
    title_p.font.bold = True
    title_p.font.color.rgb = BRAND_GREEN
    title_p.alignment = PP_ALIGN.CENTER
    
    # Subtitle with query
    subtitle_box = slide.shapes.add_textbox(Inches(1), Inches(3.8), Inches(8), Inches(1.5))
    subtitle_frame = subtitle_box.text_frame
    subtitle_frame.word_wrap = True
    subtitle_frame.text = f'"{user_query[:150]}..."' if len(user_query) > 150 else f'"{user_query}"'
    subtitle_p = subtitle_frame.paragraphs[0]
    subtitle_p.font.size = Pt(18)
    subtitle_p.font.color.rgb = DARK_GRAY
    subtitle_p.alignment = PP_ALIGN.CENTER
    
    # Date and branding
    date_box = slide.shapes.add_textbox(Inches(0.5), Inches(6.5), Inches(9), Inches(0.5))
    date_frame = date_box.text_frame
    date_frame.text = f"Bulwise Advisory Report | {datetime.now().strftime('%B %d, %Y')}"
    date_p = date_frame.paragraphs[0]
    date_p.font.size = Pt(14)
    date_p.font.color.rgb = DARK_GRAY
    date_p.alignment = PP_ALIGN.CENTER
    
    # Slide 2: Executive Summary
    if 'EXECUTIVE SUMMARY' in sections:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        
        # Header bar
        header = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(10), Inches(0.8))
        header.fill.solid()
        header.fill.fore_color.rgb = BRAND_GREEN
        header.line.color.rgb = BRAND_GREEN
        
        # Title in header
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.15), Inches(9), Inches(0.5))
        tf = title_box.text_frame
        tf.text = "Executive Summary"
        p = tf.paragraphs[0]
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255, 255, 255)
        
        # Content
        content_text = sections['EXECUTIVE SUMMARY'].strip()
        content_box = slide.shapes.add_textbox(Inches(0.75), Inches(1.5), Inches(8.5), Inches(5))
        tf = content_box.text_frame
        tf.word_wrap = True
        tf.text = content_text[:1500]  # Increased from 500 to 1500
        for paragraph in tf.paragraphs:
            paragraph.font.size = Pt(14)  # Reduced from 16 to fit more
            paragraph.font.color.rgb = DARK_GRAY
            paragraph.space_before = Pt(8)  # Reduced from 12
    
    # Slide 2.5: Methodology & Analysis (NEW)
    if 'METHODOLOGY & ANALYSIS' in sections or 'METHODOLOGY AND ANALYSIS' in sections:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        
        header = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(10), Inches(0.8))
        header.fill.solid()
        header.fill.fore_color.rgb = BRAND_GREEN
        header.line.color.rgb = BRAND_GREEN
        
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.15), Inches(9), Inches(0.5))
        tf = title_box.text_frame
        tf.text = "Methodology & Analysis"
        p = tf.paragraphs[0]
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255, 255, 255)
        
        method_key = 'METHODOLOGY & ANALYSIS' if 'METHODOLOGY & ANALYSIS' in sections else 'METHODOLOGY AND ANALYSIS'
        method_text = sections[method_key]
        content_box = slide.shapes.add_textbox(Inches(0.75), Inches(1.5), Inches(8.5), Inches(5))
        tf = content_box.text_frame
        tf.word_wrap = True
        
        for line in method_text.split('\n')[:30]:
            if line.strip() and not line.startswith('#'):
                p = tf.add_paragraph()
                p.text = line.strip('- ').strip()
                p.font.size = Pt(12)
                p.font.color.rgb = DARK_GRAY
                p.space_before = Pt(5)
    
    # Slide 3: Recommended Tools
    if 'STRATEGIC RECOMMENDATIONS' in sections:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        
        # Header
        header = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(10), Inches(0.8))
        header.fill.solid()
        header.fill.fore_color.rgb = BRAND_GREEN
        header.line.color.rgb = BRAND_GREEN
        
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.15), Inches(9), Inches(0.5))
        tf = title_box.text_frame
        tf.text = "Recommended Technology Stack"
        p = tf.paragraphs[0]
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255, 255, 255)
        
        # Extract tool names (look for **Tool Name** patterns)
        tools_section = sections['STRATEGIC RECOMMENDATIONS']
        tool_lines = [line for line in tools_section.split('\n') if line.strip().startswith('- **') or line.strip().startswith('**')]
        
        # Create table for tools
        if tool_lines:
            rows = min(len(tool_lines) + 1, 6)  # Max 5 tools + header
            cols = 2
            
            left = Inches(0.75)
            top = Inches(1.5)
            width = Inches(8.5)
            height = Inches(4.5)
            
            table = slide.shapes.add_table(rows, cols, left, top, width, height).table
            
            # Header row
            table.cell(0, 0).text = "Tool"
            table.cell(0, 1).text = "Purpose"
            
            for i in range(cols):
                cell = table.cell(0, i)
                cell.fill.solid()
                cell.fill.fore_color.rgb = BRAND_GREEN
                paragraph = cell.text_frame.paragraphs[0]
                paragraph.font.size = Pt(14)
                paragraph.font.bold = True
                paragraph.font.color.rgb = RGBColor(255, 255, 255)
            
            # Tool rows
            for idx, tool_line in enumerate(tool_lines[:5], 1):
                # Extract tool name
                tool_name = tool_line.split('**')[1] if '**' in tool_line else tool_line.strip('- ')
                purpose = tool_line.split('(')[1].split(')')[0] if '(' in tool_line else "AI Tool"
                
                table.cell(idx, 0).text = tool_name
                table.cell(idx, 1).text = purpose
                
                for i in range(cols):
                    cell = table.cell(idx, i)
                    paragraph = cell.text_frame.paragraphs[0]
                    paragraph.font.size = Pt(12)
                    paragraph.font.color.rgb = DARK_GRAY
    
    # Slide 4: Implementation Roadmap
    if 'IMPLEMENTATION ROADMAP' in sections:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        
        # Header
        header = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(10), Inches(0.8))
        header.fill.solid()
        header.fill.fore_color.rgb = BRAND_GREEN
        header.line.color.rgb = BRAND_GREEN
        
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.15), Inches(9), Inches(0.5))
        tf = title_box.text_frame
        tf.text = "Implementation Roadmap"
        p = tf.paragraphs[0]
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255, 255, 255)
        
        # Parse phases
        roadmap_text = sections['IMPLEMENTATION ROADMAP']
        phases = []
        for line in roadmap_text.split('\n'):
            if 'Phase' in line and ':' in line:
                phases.append(line.strip('# ').strip())
        
        # Create boxes for each phase
        if phases:
            box_width = Inches(2.5)
            box_height = Inches(1.2)
            spacing = Inches(0.3)
            start_y = Inches(1.8)
            start_x = Inches(0.75)
            
            for idx, phase in enumerate(phases[:3]):  # Max 3 phases
                y_pos = start_y + (idx * (box_height + spacing))
                
                # Phase box
                shape = slide.shapes.add_shape(1, start_x, y_pos, box_width, box_height)
                shape.fill.solid()
                shape.fill.fore_color.rgb = BRAND_GREEN if idx == 0 else LIGHT_GRAY
                shape.line.color.rgb = BRAND_GREEN
                shape.line.width = Pt(2)
                
                # Phase text
                tf = shape.text_frame
                tf.text = phase
                tf.word_wrap = True
                p = tf.paragraphs[0]
                p.font.size = Pt(14)
                p.font.bold = True
                p.font.color.rgb = RGBColor(255, 255, 255) if idx == 0 else DARK_GRAY
                p.alignment = PP_ALIGN.CENTER
                
                # Arrow to next phase
                if idx < len(phases) - 1 and idx < 2:
                    arrow_start_y = y_pos + box_height + Inches(0.05)
                    arrow_end_y = arrow_start_y + Inches(0.2)
                    arrow = slide.shapes.add_connector(1, start_x + box_width/2, arrow_start_y, start_x + box_width/2, arrow_end_y)
                    arrow.line.color.rgb = BRAND_GREEN
                    arrow.line.width = Pt(3)
        
        # Add Implementation Details slide (NEW - shows full roadmap text)
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        
        header = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(10), Inches(0.8))
        header.fill.solid()
        header.fill.fore_color.rgb = BRAND_GREEN
        header.line.color.rgb = BRAND_GREEN
        
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.15), Inches(9), Inches(0.5))
        tf = title_box.text_frame
        tf.text = "Implementation Details"
        p = tf.paragraphs[0]
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255, 255, 255)
        
        content_box = slide.shapes.add_textbox(Inches(0.75), Inches(1.5), Inches(8.5), Inches(5))
        tf = content_box.text_frame
        tf.word_wrap = True
        
        for line in roadmap_text.split('\n')[:30]:
            if line.strip() and not line.startswith('#'):
                p = tf.add_paragraph()
                p.text = line.strip('- ').strip()
                p.font.size = Pt(11)
                p.font.color.rgb = DARK_GRAY
                p.space_before = Pt(4)
    
    # Slide 5: Financial Analysis
    if 'FINANCIAL ANALYSIS' in sections:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        
        # Header
        header = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(10), Inches(0.8))
        header.fill.solid()
        header.fill.fore_color.rgb = BRAND_GREEN
        header.line.color.rgb = BRAND_GREEN
        
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.15), Inches(9), Inches(0.5))
        tf = title_box.text_frame
        tf.text = "Financial Analysis"
        p = tf.paragraphs[0]
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255, 255, 255)
        
        # Content
        finance_text = sections['FINANCIAL ANALYSIS']
        content_box = slide.shapes.add_textbox(Inches(0.75), Inches(1.5), Inches(8.5), Inches(5))
        tf = content_box.text_frame
        tf.word_wrap = True
        
        # Extract key financial points - increased from 10 to 25 lines
        for line in finance_text.split('\n')[:25]:
            if line.strip() and not line.startswith('#'):
                p = tf.add_paragraph()
                p.text = line.strip('- ').strip()
                p.font.size = Pt(12)  # Reduced from 14 to fit more
                p.font.color.rgb = DARK_GRAY
                p.space_before = Pt(6)  # Reduced from 8
                p.level = 1 if line.startswith('**') else 0
    
    # Slide 6: Risk Assessment
    if 'RISK ASSESSMENT' in sections or 'RISK ASSESSMENT & MITIGATION' in sections:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        
        # Header
        header = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(10), Inches(0.8))
        header.fill.solid()
        header.fill.fore_color.rgb = BRAND_GREEN
        header.line.color.rgb = BRAND_GREEN
        
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.15), Inches(9), Inches(0.5))
        tf = title_box.text_frame
        tf.text = "Risk Assessment & Mitigation"
        p = tf.paragraphs[0]
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255, 255, 255)
        
        # Content
        risk_key = 'RISK ASSESSMENT & MITIGATION' if 'RISK ASSESSMENT & MITIGATION' in sections else 'RISK ASSESSMENT'
        risk_text = sections[risk_key]
        content_box = slide.shapes.add_textbox(Inches(0.75), Inches(1.5), Inches(8.5), Inches(5))
        tf = content_box.text_frame
        tf.word_wrap = True
        
        for line in risk_text.split('\n')[:25]:  # Increased from 12 to 25
            if line.strip() and not line.startswith('#'):
                p = tf.add_paragraph()
                p.text = line.strip('- ').strip()
                p.font.size = Pt(12)  # Reduced from 13 to fit more
                p.font.color.rgb = DARK_GRAY
                p.space_before = Pt(5)  # Reduced from 6
    
    # Slide 7: Alternative Scenarios (NEW)
    if 'ALTERNATIVE SCENARIOS' in sections:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        
        header = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(10), Inches(0.8))
        header.fill.solid()
        header.fill.fore_color.rgb = BRAND_GREEN
        header.line.color.rgb = BRAND_GREEN
        
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.15), Inches(9), Inches(0.5))
        tf = title_box.text_frame
        tf.text = "Alternative Scenarios"
        p = tf.paragraphs[0]
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255, 255, 255)
        
        scenarios_text = sections['ALTERNATIVE SCENARIOS']
        content_box = slide.shapes.add_textbox(Inches(0.75), Inches(1.5), Inches(8.5), Inches(5))
        tf = content_box.text_frame
        tf.word_wrap = True
        
        for line in scenarios_text.split('\n')[:30]:
            if line.strip() and not line.startswith('#'):
                p = tf.add_paragraph()
                p.text = line.strip('- ').strip()
                p.font.size = Pt(11)
                p.font.color.rgb = DARK_GRAY
                p.space_before = Pt(4)
    
    # Final Slide: Next Steps
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    
    # Background
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = BRAND_GREEN
    
    # Title
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(2.5), Inches(9), Inches(1))
    tf = title_box.text_frame
    tf.text = "Ready to Implement?"
    p = tf.paragraphs[0]
    p.font.size = Pt(40)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.alignment = PP_ALIGN.CENTER
    
    # Contact
    contact_box = slide.shapes.add_textbox(Inches(0.5), Inches(4), Inches(9), Inches(2))
    tf = contact_box.text_frame
    tf.text = "Get personalized implementation support\n\nhello@bulwise.io\nbulwise.io"
    for paragraph in tf.paragraphs:
        paragraph.font.size = Pt(20)
        paragraph.font.color.rgb = RGBColor(255, 255, 255)
        paragraph.alignment = PP_ALIGN.CENTER
        paragraph.space_before = Pt(10)
    
    # Save to BytesIO
    pptx_io = io.BytesIO()
    prs.save(pptx_io)
    pptx_io.seek(0)
    
    return pptx_io

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
        /* Enable copy/paste */
        user-select: text !important;
        -webkit-user-select: text !important;
        -moz-user-select: text !important;
        -ms-user-select: text !important;
    }
    
    .whitepaper-section * {
        user-select: text !important;
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

# ============================================================================
# HIDDEN ADMIN SECTION (Password Protected)
# ============================================================================

# Add small password input in sidebar (only visible if sidebar expanded)
with st.sidebar:
    admin_password = st.text_input("🔒", type="password", key="admin_pass", help="Admin access")
    
    if admin_password == "bulwise2024":  # Change this password!
        st.success("✅ Admin access granted")
        
        # Show admin panel
        st.markdown("---")
        st.markdown("### 📊 Admin Panel")
        
        # Download database button
        if st.button("💾 Download Analytics Database"):
            try:
                with open('bulwise_analytics.db', 'rb') as f:
                    st.download_button(
                        label="⬇️ Click to Download",
                        data=f,
                        file_name='bulwise_analytics.db',
                        mime='application/octet-stream'
                    )
            except FileNotFoundError:
                st.warning("No database file found yet")
        
        # Show quick stats
        try:
            conn = sqlite3.connect('bulwise_analytics.db')
            c = conn.cursor()
            
            # Total queries
            c.execute("SELECT COUNT(*) FROM queries")
            total = c.fetchone()[0]
            st.metric("Total Queries", total)
            
            # Recent queries
            c.execute("SELECT user_query, timestamp FROM queries ORDER BY timestamp DESC LIMIT 5")
            recent = c.fetchall()
            
            if recent:
                st.markdown("**Recent Queries:**")
                for query, timestamp in recent:
                    st.text(f"{timestamp[:10]}: {query[:50]}...")
            
            conn.close()
        except Exception as e:
            st.info("No analytics data yet")

# Header
st.markdown("# 🎯 Strategic AI Stack Advisory")
st.markdown("### Get professional recommendations tailored to your needs")
st.markdown("---")

st.markdown("<br>", unsafe_allow_html=True)

# Initialize step tracking
if 'workflow_step' not in st.session_state:
    st.session_state.workflow_step = 1
if 'initial_query' not in st.session_state:
    st.session_state.initial_query = ''
if 'clarifying_answers' not in st.session_state:
    st.session_state.clarifying_answers = {}

# STEP 1: Initial Query
if st.session_state.workflow_step == 1:
    # ChatGPT Differentiator
    st.markdown("""
    <div style='background: #f0f7ff; padding: 1.2rem; border-radius: 8px; border-left: 4px solid #2E7D32; margin-bottom: 1.5rem;'>
        <strong>🎯 Why Bulwise?</strong> Turn your AI question into a boardroom-ready strategic advisory report with implementation details, not just suggestions.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style='background: #f8f9fa; padding: 1.5rem; border-radius: 8px; border-left: 4px solid #2E7D32; margin-bottom: 1.5rem;'>
        <h4 style='margin-top: 0; color: #2E7D32;'>💡 For Best Results, Include:</h4>
        <ul style='margin-bottom: 0;'>
            <li>What you're trying to accomplish</li>
            <li>Team size and budget (if relevant)</li>
            <li>Current blockers or constraints</li>
            <li>Timeline or urgency</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # Quick start examples - MOVED BEFORE TEXT AREA
    st.markdown("**Quick Start Examples:**")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📹 Video\nProduction", use_container_width=True, key="ex_video"):
            st.session_state.initial_query = "I run a digital agency and need to produce 10-15 professional video content pieces monthly for enterprise clients. Need AI tools for script writing, video generation, voiceovers, and editing. Budget: $200-300/month. Team of 3 people with mixed technical skills."
            st.rerun()
    
    with col2:
        if st.button("✍️ Content\nMarketing", use_container_width=True, key="ex_content"):
            st.session_state.initial_query = "E-commerce business needing to scale content creation: product descriptions, blog posts, email campaigns, and social media. Team of 2 marketers. Budget: $75-100/month."
            st.rerun()
    
    with col3:
        if st.button("💻 Software\nDevelopment", use_container_width=True, key="ex_dev"):
            st.session_state.initial_query = "Software development team of 5 engineers working on full-stack web applications. Need AI assistants for code generation, debugging, documentation, and code review. Budget: $100-150/month total."
            st.rerun()
    
    with col4:
        if st.button("🎙️ Podcast\nProduction", use_container_width=True, key="ex_podcast"):
            st.session_state.initial_query = "Starting a weekly B2B podcast. Need tools for recording, editing, transcription, show notes generation, and distribution. Solo operation with limited technical background. Budget: $50-75/month."
            st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Text area - now AFTER examples
    user_query = st.text_area(
        "**📝 Describe Your Situation:**",
        value=st.session_state.initial_query,
        height=180,
        placeholder="Example: I'm a marketing consultant working with 5-10 small business clients simultaneously. I need to create weekly content (blog posts, social media, email campaigns) efficiently. Budget is $100-150/month. I have intermediate technical skills and need tools that integrate well together. Timeline: implement within 2 weeks.",
        key="initial_query_input",
        help="Click 'Continue →' button below when ready to proceed"
    )
    
    # Update session state from user input
    st.session_state.initial_query = user_query
    
    st.markdown("---")
    
    # Continue button for Step 1
    col1, col2 = st.columns([3, 1])
    with col2:
        continue_button = st.button(
            "Continue →",
            type="primary",
            use_container_width=True,
            disabled=not st.session_state.initial_query.strip()
        )
        
        if continue_button:
            st.session_state.workflow_step = 2
            st.rerun()

# STEP 2: Clarifying Questions
elif st.session_state.workflow_step == 2:
    st.markdown("### 🔍 Quick Clarifying Questions")
    st.markdown("*Help us refine your recommendations (optional)*")
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Show what they entered
    with st.expander("📝 Your Initial Request", expanded=False):
        st.write(st.session_state.initial_query)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Clarifying questions
    col1, col2 = st.columns(2)
    
    with col1:
        team_size = st.selectbox(
            "**Team Size:**",
            ["Not specified", "Individual (just me)", "Small team (2-10)", "Medium team (11-50)", "Large team (50+)"],
            index=0,
            key="team_size_select"
        )
        
        timeline = st.selectbox(
            "**Implementation Timeline:**",
            ["Not specified", "Urgent (need now)", "Within 2 weeks", "Within 1 month", "Within 3 months", "Flexible timeline"],
            index=0,
            key="timeline_select"
        )
    
    with col2:
        budget = st.selectbox(
            "**Monthly Budget Range:**",
            ["Not specified", "Under $50/month", "$50-$200/month", "$200-$500/month", "$500-$1,000/month", "$1,000+/month"],
            index=0,
            key="budget_select"
        )
        
        experience = st.selectbox(
            "**Technical Experience:**",
            ["Not specified", "Beginner (need easy tools)", "Intermediate (comfortable with tech)", "Advanced (can handle complexity)"],
            index=0,
            key="experience_select"
        )
    
    # Save answers
    st.session_state.clarifying_answers = {
        'team_size': team_size if team_size != "Not specified" else None,
        'budget': budget if budget != "Not specified" else None,
        'timeline': timeline if timeline != "Not specified" else None,
        'experience': experience if experience != "Not specified" else None
    }
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Navigation buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("← Back", use_container_width=True):
            st.session_state.workflow_step = 1
            st.rerun()
    
    with col2:
        if st.button("Skip Questions →", use_container_width=True):
            st.session_state.clarifying_answers = {}
            st.session_state.workflow_step = 3
            st.rerun()
    
    with col3:
        if st.button("Continue →", type="primary", use_container_width=True):
            st.session_state.workflow_step = 3
            st.rerun()

# STEP 3: Generate Report
elif st.session_state.workflow_step == 3:
    # Build complete query with clarifying answers
    user_query = st.session_state.initial_query
    
    if any(st.session_state.clarifying_answers.values()):
        clarifications = []
        if st.session_state.clarifying_answers.get('team_size'):
            clarifications.append(f"Team size: {st.session_state.clarifying_answers['team_size']}")
        if st.session_state.clarifying_answers.get('budget'):
            clarifications.append(f"Budget: {st.session_state.clarifying_answers['budget']}")
        if st.session_state.clarifying_answers.get('timeline'):
            clarifications.append(f"Timeline: {st.session_state.clarifying_answers['timeline']}")
        if st.session_state.clarifying_answers.get('experience'):
            clarifications.append(f"Technical experience: {st.session_state.clarifying_answers['experience']}")
        
        user_query += "\n\nAdditional context: " + "; ".join(clarifications)
    
    # Show summary
    st.markdown("### 📋 Review Your Request")
    with st.expander("View full request", expanded=True):
        st.write(user_query)
    
    # Back button
    if st.button("← Edit Request"):
        st.session_state.workflow_step = 1
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
                
                # System prompt - UPDATED with user validation, data sources upfront, no emojis, visualizations, enhanced costs
                system_prompt = f"""You are Bulwise, a strategic AI implementation advisory service. Generate professional, data-driven reports for clients seeking AI tool recommendations.

You have access to:
1. A comprehensive database of {len(database['ai_tools'])} AI tools with detailed specifications
2. Web search capability to find current market research and trends

CRITICAL: Format your response as a professional whitepaper-style advisory report with the following structure (IN THIS EXACT ORDER):

---

## ANALYST NOTE
[Brief professional note (2-3 sentences) welcoming the client, emphasizing the data-driven strategic nature of this recommendation, and expressing willingness to answer follow-up questions. Keep warm and professional. NO EMOJIS.]

---

## REQUIREMENTS VALIDATION
[NEW - #4: Before proceeding with analysis, confirm your understanding of the client's needs]

Based on your request, I understand you are seeking to:
- **Primary Goal:** [State what you understand they want to accomplish]
- **Team Context:** [Solo, small team, enterprise - based on their input]
- **Budget Range:** [If mentioned, confirm. If not mentioned, note "Budget not specified - recommendations will span multiple price points"]
- **Timeline:** [If mentioned, confirm. If not, note "Timeline not specified"]
- **Key Constraints:** [Any blockers or limitations they mentioned]

If any of these assumptions are incorrect, please let me know. Proceeding with analysis based on these parameters.

---

## EXECUTIVE SUMMARY
[2-3 sentences providing high-level overview of the recommendation and expected outcomes]

**Data Foundation:** [NEW - #5: Move data sources upfront]
This analysis draws from {len(database['ai_tools'])} AI tools across 15+ categories in our proprietary database, supplemented by current market research from Gartner, Forrester, IDC, and industry-specific sources. All statistics and benchmarks are cited with sources.

---

## METHODOLOGY & ANALYSIS

**Requirements Analysis:**
[Summarize the client's stated needs, constraints, and objectives]

**Evaluation Criteria:**
[List the key factors considered in tool selection: budget alignment, technical requirements, workflow integration, scalability, etc.]

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
- **Official Website:** [Include the tool's website URL]

### Technology Stack Visualization
[NEW - #14: ASCII diagram showing how tools connect]

```
Data Flow Architecture:

[Input Source] → [Primary Tool] → [Enhancement Tool] → [Output/Storage]
                      ↓
                [Supporting Tool]
                      ↓
                [Quality Control]

Example:
User Content → ChatGPT (Generation) → Grammarly (Polish) → Notion (Storage)
                      ↓
                  Midjourney (Visuals)
                      ↓
                  Canva (Assembly)
```

### Tool Integration Workflow
[Provide step-by-step explanation of how these tools work together in practice, including data flow and handoffs between systems]

---

## IMPLEMENTATION ROADMAP

### Visual Timeline
[NEW - #15: Mermaid diagram]

```mermaid
graph LR
    A[Week 1-2: Foundation] --> B[Week 3-4: Integration]
    B --> C[Month 2: Optimization]
    C --> D[Month 3+: Scaling]
    
    A --> A1[Tool Setup]
    A --> A2[Team Training]
    B --> B1[Workflow Integration]
    B --> B2[Testing]
    C --> C1[Process Refinement]
    C --> C2[Advanced Features]
```

### Phase 1: Foundation (Week 1-2)
[Initial setup steps and quick wins]

### Phase 2: Integration (Week 3-4)
[Connecting tools and establishing workflows]

### Phase 3: Optimization (Month 2+)
[Refinement and advanced feature adoption]

---

## FINANCIAL ANALYSIS

### Detailed Cost Breakdown
[NEW - #16: Enhanced with per-tool details]

**Monthly Costs by Tool:**

| Tool | Recommended Tier | Monthly Cost | Annual Cost | Notes |
|------|-----------------|--------------|-------------|-------|
| [Tool 1] | [Tier name] | $XX | $XXX | [Why this tier] |
| [Tool 2] | [Tier name] | $XX | $XXX | [Why this tier] |
| [Tool 3] | [Tier name] | $XX | $XXX | [Why this tier] |

**Cost Summary:**
- **Total Monthly Investment:** $[X]
- **Annual Projection:** $[Y]
- **Cost Per User (if team):** $[Z]

**Payment Options:**
- Monthly billing: $[X]/month
- Annual billing: $[Y]/year (save $[Z] vs monthly)

### Expected ROI
[Quantify time savings, efficiency gains, or revenue impact where possible, using industry benchmarks from market research WITH SOURCES. Be realistic and conservative.]

**ROI Calculation:**
- Time saved per week: [X] hours
- Value per hour: $[Y]
- Monthly value: $[Z]
- Break-even point: [X] months

### Cost Optimization Strategies
[Suggest ways to reduce costs or maximize value]
- Annual payment discounts
- Team vs individual plans
- Free tier alternatives for testing
- Bundled vs a la carte pricing

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

**Modified Stack (Reduced Budget):**
- Total monthly cost: $[X]
- Key tradeoffs: [What you lose]
- Still achieves: [Core objectives maintained]

### Premium Alternative
[If budget allows 50-100% more investment, what enhanced capabilities could be added?]

**Enhanced Stack (Increased Budget):**
- Total monthly cost: $[X]
- Additional capabilities: [What you gain]
- Recommended for: [When premium makes sense]

### Different Scale Scenario
[How would recommendations change for 2x team size or 2x content volume?]

---

## SUPPORTING DATA

### Tool Comparison Matrix
[Create a simple text-based comparison of recommended tools vs alternatives on key criteria]

| Criteria | [Recommended Tool 1] | [Alternative] | Winner |
|----------|---------------------|---------------|--------|
| Price | $XX/month | $XX/month | [Tool] |
| Features | [Key features] | [Key features] | [Tool] |
| Ease of Use | [Rating] | [Rating] | [Tool] |
| Integration | [Rating] | [Rating] | [Tool] |

### Industry Benchmarks
[Include relevant statistics from market research about typical costs, implementation times, adoption rates - WITH SOURCES]

### Reference Documentation
[List official documentation, case studies, or resources for each recommended tool]

**Tool Resources:**
- **[Tool 1]:** [Official docs URL], [Getting started guide URL]
- **[Tool 2]:** [Official docs URL], [Getting started guide URL]

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
- **NO EMOJIS** - Maintain professional consulting-firm tone throughout [NEW - #7]
- Use formal section headers without decorative elements
- Focus on substance over style

DATABASE:
{json.dumps(database['ai_tools'], indent=2)}"""
                
                status_text.text("📊 Researching market data... (30%)")
                progress_bar.progress(30)

                status_text.text("🤖 Generating strategic recommendations... (50%)")
                progress_bar.progress(50)
                
                # Retry logic for API overload errors
                max_retries = 3
                retry_count = 0
                message = None
                
                while retry_count < max_retries:
                    try:
                        if retry_count > 0:
                            status_text.text(f"⏳ API busy, retrying ({retry_count}/{max_retries})... (50%)")
                        
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
                        break  # Success! Exit retry loop
                        
                    except anthropic.APIError as e:
                        if "overloaded" in str(e).lower() and retry_count < max_retries - 1:
                            retry_count += 1
                            wait_time = 5 * retry_count  # 5s, 10s, 15s
                            status_text.text(f"⏳ API overloaded, waiting {wait_time}s before retry {retry_count}/{max_retries}...")
                            import time
                            time.sleep(wait_time)
                        else:
                            # Not an overload error, or out of retries
                            raise
                
                if message is None:
                    raise Exception("Failed to generate report after multiple retries")
                
                status_text.text("✨ Finalizing report... (80%)")
                progress_bar.progress(80)
                
                # Extract text from response (handling tool use blocks)
                response_text = ""
                for block in message.content:
                    if hasattr(block, 'text'):
                        response_text += block.text
                
                # Clean response text - remove artifacts and fix formatting
                # Remove common debug/artifact patterns
                response_text = re.sub(r'```[\w]*\n.*?```', '', response_text, flags=re.DOTALL)  # Remove code blocks that might contain paths
                response_text = re.sub(r'/[^\s]+\.py', '', response_text)  # Remove file paths
                response_text = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL)  # Remove thinking tags
                
                # Fix currency markdown - ensure $ symbols display correctly
                # Streamlit markdown handles $ fine, but double-check escaping if needed
                response_text = response_text.replace('\\$', '$')  # Remove any over-escaping
                
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
                
                # Feedback section
                st.markdown("---")
                
                # Export options
                col1, col2 = st.columns(2)
                
                with col1:
                    # PowerPoint export
                    try:
                        pptx_file = generate_professional_pptx(response_text, user_query)
                        st.download_button(
                            label="📊 Export as Presentation (.pptx)",
                            data=pptx_file,
                            file_name=f"bulwise_advisory_{datetime.now().strftime('%Y%m%d')}.pptx",
                            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"PowerPoint export error: {str(e)}")
                
                with col2:
                    # PDF export placeholder for future
                    st.button("📄 Export as PDF (Coming Soon)", disabled=True, use_container_width=True)
                
                st.markdown("---")
                st.markdown("### 💬 Quick Feedback")
                
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.markdown("**Was this report helpful?**")
                
                with col2:
                    if st.button("👍 Yes, helpful", key="feedback_yes", use_container_width=True):
                        log_feedback(user_query, "positive", None)
                        st.success("Thank you for your feedback!")
                        st.session_state.feedback_given = True
                
                with col3:
                    if st.button("👎 Not helpful", key="feedback_no", use_container_width=True):
                        st.session_state.show_feedback_form = True
                
                # If they clicked "Not helpful", show form for details
                if st.session_state.get('show_feedback_form', False) and not st.session_state.get('feedback_given', False):
                    feedback_text = st.text_area(
                        "What could we improve?",
                        placeholder="Tell us what was missing or could be better...",
                        key="feedback_details"
                    )
                    
                    if st.button("Submit Feedback", type="primary"):
                        log_feedback(user_query, "negative", feedback_text)
                        st.success("Thank you for your feedback! We'll use this to improve.")
                        st.session_state.feedback_given = True
                        st.session_state.show_feedback_form = False
                
                # Reset workflow for new query
                if st.button("📝 Generate Another Report", type="primary"):
                    st.session_state.workflow_step = 1
                    st.session_state.initial_query = ''
                    st.session_state.clarifying_answers = {}
                    if 'feedback_given' in st.session_state:
                        del st.session_state.feedback_given
                    if 'show_feedback_form' in st.session_state:
                        del st.session_state.show_feedback_form
                    st.rerun()
                
                # Consultancy CTA
                st.markdown("---")
                st.markdown("""
                <div style='background: linear-gradient(135deg, #2E7D32 0%, #1B5E20 100%); padding: 2rem; border-radius: 12px; text-align: center; margin: 2rem 0;'>
                    <h3 style='color: white; margin-top: 0;'>Need Implementation Support?</h3>
                    <p style='color: #E8F5E9; font-size: 1.1rem; margin-bottom: 1.5rem;'>
                        Get personalized 1:1 consultation to help you implement these recommendations
                    </p>
                    <a href='mailto:hello@bulwise.io?subject=Implementation%20Consultation%20Request' 
                       style='background: white; color: #2E7D32; padding: 0.75rem 2rem; border-radius: 8px; 
                              text-decoration: none; font-weight: 600; display: inline-block;'>
                        📞 Book a Consultation
                    </a>
                </div>
                """, unsafe_allow_html=True)
                
            except anthropic.APIError as e:
                if "overloaded" in str(e).lower():
                    st.error("⚠️ Anthropic API is experiencing high traffic")
                    st.info("💡 The API is temporarily overloaded. Please try again in 1-2 minutes. Your query has been saved.")
                    st.markdown(f"**Your query:** {user_query[:200]}...")
                elif "credit balance" in str(e).lower():
                    st.error(f"API Error: {str(e)}")
                    st.info("Please add credits to your Anthropic account at console.anthropic.com")
                else:
                    st.error(f"API Error: {str(e)}")
                    st.info("💡 Please try again in a moment.")
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
