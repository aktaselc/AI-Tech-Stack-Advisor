"""
BulWise Flask Backend - WITH 166 TOOLS INTEGRATION 
==================================================

This version properly integrates your 166-tool database with Claude API.
Claude will now use YOUR tools and provide alternatives for each recommendation.

CRITICAL: Replace your current flask_backend_with_protection.py with this file.
"""

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import anthropic
import os
import json
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
CORS(app)

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per hour"],
    storage_uri="memory://"
)

# Cost tracking
MONTHLY_BUDGET_CAP = 50.00
COST_PER_1K_INPUT_TOKENS = 0.003
COST_PER_1K_OUTPUT_TOKENS = 0.015
COST_TRACKING_FILE = "cost_tracking.json"

# Input validation
MAX_QUERY_LENGTH = 2000
MAX_CONTEXT_LENGTH = 500

# ==============================================================================
# TOOLS DATABASE INTEGRATION
# ==============================================================================

def load_tools_database():
    """
    Load all 250 AI tools from JSON file.
    
    The tools are in complete_250_tools.json in the same directory.
    """
    try:
        import os
        script_dir = os.path.dirname(os.path.abspath(__file__))
        tools_file = os.path.join(script_dir, 'complete_250_tools.json')
        
        with open(tools_file, 'r') as f:
            data = json.load(f)
            tools = data.get('tools', [])
        
        print(f"✅ Loaded {len(tools)} tools from database")
        return tools
        
    except FileNotFoundError:
        print("❌ complete_250_tools.json not found! Make sure it's in the same directory as this script.")
        return []
    except Exception as e:
        print(f"❌ Error loading tools: {e}")
        return []

def format_tools_for_claude(tools):
    """Format tools database for Claude's system prompt"""
    if not tools:
        return "NO TOOLS DATABASE AVAILABLE - Using general knowledge instead."
    
    formatted = []
    for tool in tools:
        # Handle both formats: tool_name/name
        name = tool.get("tool_name") or tool.get("name")
        
        # Build strengths list from available data
        strengths = tool.get("strengths", [])
        if not strengths:
            # Derive from use_cases or best_for
            use_cases = tool.get("use_cases", [])
            best_for = tool.get("best_for", "")
            if use_cases:
                strengths = [f"Supports {case}" for case in use_cases[:3]]
            elif best_for:
                strengths = [best_for]
        
        formatted.append({
            "name": name,
            "category": tool.get("category"),
            "description": tool.get("description"),
            "strengths": strengths if isinstance(strengths, list) else [strengths],
            "best_for": tool.get("best_for", "General AI tasks"),
            "integrations": tool.get("integration_options") or tool.get("integrations", ["Web"]),
            "trade_offs": tool.get("trade_offs", "Standard limitations apply")
        })
    
    return json.dumps(formatted, indent=2)

# ==============================================================================
# COST TRACKING (Same as before)
# ==============================================================================

def get_current_month():
    return datetime.now().strftime("%Y-%m")

def load_cost_data():
    if not Path(COST_TRACKING_FILE).exists():
        return {"month": get_current_month(), "total_cost": 0.0, "requests": []}
    
    with open(COST_TRACKING_FILE, 'r') as f:
        data = json.load(f)
    
    if data.get("month") != get_current_month():
        return {"month": get_current_month(), "total_cost": 0.0, "requests": []}
    
    return data

def save_cost_data(data):
    with open(COST_TRACKING_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def calculate_cost(input_tokens, output_tokens):
    input_cost = (input_tokens / 1000) * COST_PER_1K_INPUT_TOKENS
    output_cost = (output_tokens / 1000) * COST_PER_1K_OUTPUT_TOKENS
    return input_cost + output_cost

def check_budget():
    data = load_cost_data()
    return data["total_cost"] < MONTHLY_BUDGET_CAP

def log_request(input_tokens, output_tokens, cost):
    data = load_cost_data()
    
    request_log = {
        "timestamp": datetime.now().isoformat(),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost": cost
    }
    
    data["requests"].append(request_log)
    data["total_cost"] += cost
    
    save_cost_data(data)
    
    print(f"💰 Cost: ${cost:.4f} | Month total: ${data['total_cost']:.2f}/{MONTHLY_BUDGET_CAP}")
    
    return data["total_cost"]

# ==============================================================================
# INPUT VALIDATION (Same as before)
# ==============================================================================

def validate_input(data):
    query = data.get('query', '')
    context = data.get('context', {})
    
    if len(query) > MAX_QUERY_LENGTH:
        return False, f"Query too long. Maximum {MAX_QUERY_LENGTH} characters allowed."
    
    for key, value in context.items():
        if isinstance(value, str) and len(value) > MAX_CONTEXT_LENGTH:
            return False, f"Context field '{key}' too long. Maximum {MAX_CONTEXT_LENGTH} characters allowed."
    
    if not query.strip():
        return False, "Query cannot be empty."
    
    return True, None

# ==============================================================================
# MAIN API ENDPOINT WITH TOOLS INTEGRATION
# ==============================================================================

@app.route('/api/generate', methods=['POST'])
@limiter.limit("3 per day")
def generate_report():
    """Generate AI Stack Advisory Report WITH TOOLS DATABASE"""
    
    try:
        data = request.json
        
        # Validate input
        is_valid, error_message = validate_input(data)
        if not is_valid:
            return jsonify({"error": error_message}), 400
        
        # Check monthly budget
        if not check_budget():
            cost_data = load_cost_data()
            return jsonify({
                "error": f"Monthly budget cap of ${MONTHLY_BUDGET_CAP} has been reached. "
                         f"Current month total: ${cost_data['total_cost']:.2f}. "
                         f"Please contact support at hello@bulwise.io"
            }), 503
        
        # CRITICAL: Load your 166 tools
        all_tools = load_tools_database()
        tools_context = format_tools_for_claude(all_tools)
        
        # Log warning if no tools loaded
        if not all_tools:
            print("⚠️  WARNING: No tools loaded from database! Claude will use general knowledge.")
        else:
            print(f"✅ Loaded {len(all_tools)} tools from database")
        
        # Initialize Anthropic client
        client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
        
        # Prepare the prompt
        query = data.get('query')
        context = data.get('context', {})
        
        # UPDATED SYSTEM PROMPT WITH TOOLS DATABASE
        system_prompt = f"""You are BulWise, an AI Stack Advisory expert.

CRITICAL: You have access to a curated database of {len(all_tools)} AI tools.
You MUST ONLY recommend tools from this database.

TOOLS DATABASE:
{tools_context}

TASK: Generate a comprehensive AI implementation report.

IMPORTANT REQUIREMENTS:
1. SELECT tools from the database above that match the user's specific needs
2. PROVIDE exactly 2 alternatives for each recommended tool
3. VARY recommendations based on:
   - User's budget
   - User's technical level
   - Specific use case requirements
4. DO NOT recommend the same tools for every use case
5. EXPLAIN why you chose each tool over its alternatives

⚠️  CRITICAL FORMAT REQUIREMENT ⚠️
You MUST follow this EXACT format for the Recommended Stack section.
DO NOT use tables, lists, or any other format.
This format is MANDATORY for the frontend to work correctly.

FORMAT YOUR REPORT EXACTLY LIKE THIS:

## Executive Summary
[Brief overview of the solution - 2-3 sentences]

## Recommended Stack

### Research & Data Gathering

**PRIMARY TOOL: Perplexity Pro**

Strengths:
• Real-time web search with citations
• Best-in-class accuracy for research
• API available for automation

Best for: Competitive intelligence, market research, fact-checking

Integration: Web interface, API, Zapier, mobile app

**ALTERNATIVE 1: ChatGPT Plus**

Strengths:
• Excellent for creative ideation
• Large plugin ecosystem
• DALL-E image generation

Best for: Brainstorming, content creation

Integration: Web, API, plugins, mobile

Trade-off: No source citations, less accurate for real-time research

**ALTERNATIVE 2: Gemini Advanced**

Strengths:
• Deep Google Workspace integration
• Strong multimodal capabilities
• Real-time Google Search access

Best for: Google ecosystem users

Integration: Google Workspace, Gmail, Google Docs

Trade-off: Weaker third-party integrations

---

### Content Creation

**PRIMARY TOOL: Jasper**

Strengths:
• Marketing-focused templates
• Brand voice customization
• SEO integration

Best for: Marketing teams, blog posts, ad copy

Integration: Surfer SEO, Chrome extension, API

**ALTERNATIVE 1: Copy.ai**

Strengths:
• Lower cost than Jasper
• Sales copy focus
• Email campaigns

Best for: Sales teams, email marketing

Integration: Web, API, Chrome extension

Trade-off: Less sophisticated than Jasper

**ALTERNATIVE 2: Claude Pro**

Strengths:
• Superior analytical writing
• Long-form content
• Code generation

Best for: Technical content, analysis

Integration: Web, API, Projects

Trade-off: Not marketing-optimized

---

[Continue this EXACT format for 3-5 categories total]

CRITICAL FORMATTING RULES:
1. Category header: ### [Category Name] (use triple ###)
2. Primary tool: **PRIMARY TOOL: [Exact Tool Name]**
3. Alternatives: **ALTERNATIVE 1:** and **ALTERNATIVE 2:**
4. Separator between categories: --- (three dashes on their own line)
5. Each tool section must include: Strengths (bullets), Best for, Integration
6. Alternatives must include: Trade-off line
7. DO NOT use tables, bullet lists for tools, or any other format

⚠️ CRITICAL: NEWLINES AND FORMATTING ⚠️
YOU MUST follow these formatting rules EXACTLY:

1. **Phased Implementation Roadmap**: Each phase MUST be on separate lines with blank lines between them
   - Put **Phase 1: Foundation (Week 1-2)** on its own line
   - Add a blank line
   - Then list the steps (with bullet points, each on new line)
   - Add a blank line
   - Then **Phase 2: Integration (Week 3-4)** on its own line
   - And so on

2. **Success Metrics**: Each subsection MUST have bullets on SEPARATE LINES
   - Put ### heading on its own line
   - Then EACH bullet (• **What it is**:, • **How to measure**:, etc.) on ITS OWN LINE
   - Add blank line between subsections
   
3. **Related Opportunities**: Same as Success Metrics - each bullet on its OWN LINE

DO NOT COMBINE multiple bullets into one paragraph!
DO NOT COMBINE multiple phases into one paragraph!
ALWAYS use proper line breaks and blank lines!

Example of CORRECT formatting:
```
**Phase 1: Foundation (Week 1-2)**
• Set up Perplexity Pro account
• Configure Claude Sonnet 4 API
• Establish data storage

**Phase 2: Integration (Week 3-4)**
• Build automated workflows
• Set up templates
```

Example of WRONG formatting:
```
**Phase 1: Foundation (Week 1-2)** • Set up Perplexity Pro • Configure Claude **Phase 2: Integration** • Build workflows
```

⚠️ REMEMBER: Each bullet MUST be on its own line! Each phase MUST be separated!

## Architecture Diagram

```mermaid
graph TD
    A[User Input] --> B[Tool 1]
    B --> C[Tool 2]
    C --> D[Final Output]
```

## Phased Implementation Roadmap

**Phase 1: Foundation (Week 1-2)**
[Setup steps]

**Phase 2: Integration (Week 3-4)**
[Integration steps]

**Phase 3: Optimization (Month 2+)**
[Optimization steps]

## Success Metrics

1. **Time Reduction**: 80% reduction in manual competitive research time
2. **Coverage Increase**: 3x more competitors monitored regularly
3. **Report Frequency**: Weekly automated reports vs. monthly manual reports
4. **Insight Quality**: 90% of strategic insights validated by business stakeholders

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| [Risk 1] | Medium | High | [Strategy] |
| [Risk 2] | Low | Medium | [Strategy] |

## Related Opportunities

1. **Patient Sentiment Analysis**: Extend competitor monitoring to include patient reviews and social media sentiment
2. **Clinical Trial Intelligence**: Monitor competitor clinical trial activities and regulatory filings
3. **Partnership Mapping**: Track competitor partnerships, acquisitions, and strategic alliances
4. **Technology Stack Analysis**: Monitor competitor technology adoptions and digital transformation initiatives

⚠️  REMINDER: The Recommended Stack section MUST use the exact format shown above.
Frontend parsing depends on this specific structure. DO NOT deviate from it.

Remember:
- Use ONLY tools from the database
- Provide exactly 2 alternatives per tool
- Focus on strengths, best use cases, integrations
- Explain trade-offs clearly
- NO PRICING information
- FOLLOW THE FORMAT EXACTLY
"""
        
        user_prompt = f"""
Problem/Goal: {query}

Context:
- Report Purpose: {context.get('report_purpose', 'Not specified')}
- Primary Audience: {context.get('primary_audience', 'Not specified')}
- Budget: {context.get('budget', 'Not specified')}
- Existing Tools: {context.get('existing_tools', 'None specified')}

Generate a comprehensive AI Stack Advisory Report following the format specified in the system prompt.
"""
        
        # Call Claude API
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            temperature=0.7,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        
        # Extract response
        report_content = message.content[0].text
        
        # Calculate and log cost
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens
        cost = calculate_cost(input_tokens, output_tokens)
        total_cost = log_request(input_tokens, output_tokens, cost)
        
        # Return response - with success flag for frontend compatibility
        return jsonify({
            "success": True,
            "report": report_content,
            "metadata": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": f"${cost:.4f}",
                "month_total": f"${total_cost:.2f}/{MONTHLY_BUDGET_CAP}",
                "tools_loaded": len(all_tools)
            }
        })
    
    except anthropic.RateLimitError:
        return jsonify({"error": "API rate limit exceeded. Please try again later."}), 429
    
    except anthropic.APIError as e:
        print(f"Anthropic API Error: {e}")
        return jsonify({"error": f"AI service error: {str(e)}"}), 500
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500

# ==============================================================================
# HEALTH CHECK & MONITORING
# ==============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    cost_data = load_cost_data()
    all_tools = load_tools_database()
    
    return jsonify({
        "status": "healthy",
        "month": cost_data["month"],
        "total_cost": f"${cost_data['total_cost']:.2f}",
        "budget_cap": f"${MONTHLY_BUDGET_CAP}",
        "budget_remaining": f"${MONTHLY_BUDGET_CAP - cost_data['total_cost']:.2f}",
        "requests_this_month": len(cost_data["requests"]),
        "tools_in_database": len(all_tools)
    })

@app.route('/api/costs', methods=['GET'])
def get_costs():
    cost_data = load_cost_data()
    return jsonify(cost_data)

@app.route('/api/generate-pdf', methods=['POST'])
def generate_pdf():
    """
    Generate PDF from HTML content using WeasyPrint
    """
    try:
        from weasyprint import HTML
        from io import BytesIO
        
        data = request.get_json()
        html_content = data.get('html', '')
        
        if not html_content:
            return jsonify({"error": "No HTML content provided"}), 400
        
        # Generate PDF - HTML already contains all necessary CSS for page breaks
        pdf_buffer = BytesIO()
        HTML(string=html_content).write_pdf(pdf_buffer)
        pdf_buffer.seek(0)
        
        # Create response
        response = make_response(pdf_buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'attachment; filename=BulWise-AI-Stack-Report.pdf'
        
        return response
        
    except ImportError as e:
        print(f"❌ WeasyPrint Import Error: {str(e)}")
        return jsonify({"error": "WeasyPrint not installed"}), 500
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ PDF Generation Error: {str(e)}")
        print(f"Full traceback:\n{error_trace}")
        return jsonify({"error": f"PDF generation failed: {str(e)}"}), 500

# ==============================================================================
# ERROR HANDLERS
# ==============================================================================

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        "error": "Rate limit exceeded. You can generate up to 3 reports per day. "
                 "Please try again tomorrow or contact hello@bulwise.io for more access."
    }), 429

# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == '__main__':
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  WARNING: ANTHROPIC_API_KEY not set!")
    
    print("=" * 60)
    print("BulWise Flask API - WITH TOOLS DATABASE INTEGRATION")
    print("=" * 60)
    print(f"✅ Rate Limiting: 3 requests per day per IP")
    print(f"✅ Monthly Budget Cap: ${MONTHLY_BUDGET_CAP}")
    print(f"✅ Input Validation: Max {MAX_QUERY_LENGTH} chars")
    print(f"✅ Cost Tracking: {COST_TRACKING_FILE}")
    
    # Check if tools database is accessible
    tools = load_tools_database()
    if tools:
        print(f"✅ Tools Database: {len(tools)} tools loaded")
    else:
        print(f"⚠️  WARNING: Tools database is EMPTY!")
        print(f"⚠️  You MUST implement load_tools_database() function!")
    
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
