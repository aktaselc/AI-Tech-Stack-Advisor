"""
BulWise Flask Backend - FROM YOUR WORKING VERSION + Tools Database
===================================================================
"""

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import anthropic
import os
from datetime import datetime
import json
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
# TOOLS DATABASE
# ==============================================================================

def load_tools_database():
    """Load all 250 AI tools from JSON file."""
    try:
        with open('complete_250_tools.json', 'r') as f:
            tools = json.load(f)
        print(f"✅ Loaded {len(tools)} tools from database")
        return tools
    except FileNotFoundError:
        print("❌ complete_250_tools.json not found!")
        return []

all_tools = load_tools_database()

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
# API ENDPOINTS
# ==============================================================================

@app.route('/api/generate', methods=['POST'])
@limiter.limit("3 per day")
def generate_report():
    """Generate AI Stack Advisory Report"""
    
    try:
        data = request.json
        
        is_valid, error_message = validate_input(data)
        if not is_valid:
            return jsonify({"error": error_message}), 400
        
        if not check_budget():
            cost_data = load_cost_data()
            return jsonify({
                "error": f"Monthly budget cap of ${MONTHLY_BUDGET_CAP} has been reached. "
                         f"Current month total: ${cost_data['total_cost']:.2f}. "
                         f"Please contact support at hello@bulwise.io"
            }), 503
        
        client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
        
        query = data.get('query')
        context = data.get('context', {})
        
        # Format tools for the prompt (if available)
        tools_context = ""
        if len(all_tools) > 0:
            tools_context = "\n".join([
                f"- {tool['name']}: {tool.get('description', 'AI tool')}"
                for tool in all_tools[:100]  # First 100 tools
            ])
            tools_available_text = f"You have access to a database of {len(all_tools)} AI tools. Use ONLY these tools in your recommendations.\n\nTools available:\n{tools_context}"
        else:
            tools_available_text = "Select appropriate AI tools for the user's needs."
        
        system_prompt = f"""You are an AI Stack Advisory expert. Generate detailed, actionable AI implementation reports.

{tools_available_text}

CRITICAL: The Recommended Stack section MUST use this EXACT format:

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

[Continue this EXACT format for 3-5 categories total based on the user's needs]

CRITICAL FORMATTING RULES:
1. Category header: ### [Category Name] (use triple ###)
2. Primary tool: **PRIMARY TOOL: [Exact Tool Name]**
3. Alternatives: **ALTERNATIVE 1:** and **ALTERNATIVE 2:**
4. Separator between categories: --- (three dashes on their own line)
5. Each tool section must include: Strengths (bullets), Best for, Integration
6. Alternatives must include: Trade-off line
7. DO NOT use tables or any other format
"""
        
        user_prompt = f"""
Problem/Goal: {query}

Context:
- Report Purpose: {context.get('report_purpose', 'Not specified')}
- Primary Audience: {context.get('primary_audience', 'Not specified')}
- Budget: {context.get('budget', 'Not specified')}
- Existing Tools: {context.get('existing_tools', 'None specified')}

Generate a comprehensive AI Stack Advisory Report with:
1. Executive Summary
2. Recommended AI Tools (specific products) - For each tool, provide 2 alternatives
3. Implementation Timeline (week-by-week)
4. Architecture Diagram (Mermaid format)
5. Success Metrics
6. Risk Assessment
7. Related Opportunities
"""
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            temperature=0.7,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        
        report_content = message.content[0].text
        
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens
        cost = calculate_cost(input_tokens, output_tokens)
        total_cost = log_request(input_tokens, output_tokens, cost)
        
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
        import traceback
        error_trace = traceback.format_exc()
        print(f"Unexpected error: {e}")
        print(f"Full traceback:\n{error_trace}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    cost_data = load_cost_data()
    
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
    """Generate PDF from HTML content using WeasyPrint"""
    try:
        from weasyprint import HTML
        from io import BytesIO
        
        data = request.get_json()
        html_content = data.get('html', '')
        
        if not html_content:
            return jsonify({"error": "No HTML content provided"}), 400
        
        pdf_buffer = BytesIO()
        HTML(string=html_content).write_pdf(pdf_buffer)
        pdf_buffer.seek(0)
        
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

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        "error": "Rate limit exceeded. You can generate up to 3 reports per day. "
                 "Please try again tomorrow or contact hello@bulwise.io for more access."
    }), 429

if __name__ == '__main__':
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  WARNING: ANTHROPIC_API_KEY not set!")
        print("Set it in your environment or .env file")
    
    print("=" * 60)
    print("BulWise Flask API - WITH TOOLS DATABASE")
    print("=" * 60)
    print(f"✅ Rate Limiting: 3 requests per day per IP")
    print(f"✅ Monthly Budget Cap: ${MONTHLY_BUDGET_CAP}")
    print(f"✅ Tools in Database: {len(all_tools)}")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
