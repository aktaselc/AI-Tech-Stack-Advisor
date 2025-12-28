"""
BulWise Flask Backend - Simple Version Like Original
====================================================
"""

from flask import Flask, request, jsonify, make_response
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

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per hour"],
    storage_uri="memory://"
)

MONTHLY_BUDGET_CAP = 50.00
COST_PER_1K_INPUT_TOKENS = 0.003
COST_PER_1K_OUTPUT_TOKENS = 0.015
COST_TRACKING_FILE = "cost_tracking.json"
MAX_QUERY_LENGTH = 2000
MAX_CONTEXT_LENGTH = 500

def load_tools_database():
    try:
        with open('complete_250_tools.json', 'r') as f:
            data = json.load(f)
        if isinstance(data, dict) and 'tools' in data:
            tools = data['tools']
        elif isinstance(data, list):
            tools = data
        else:
            return []
        print(f"✅ Loaded {len(tools)} tools from database")
        return tools
    except:
        print("❌ Tools file not found")
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
            return False, f"Context field '{key}' too long."
    if not query.strip():
        return False, "Query cannot be empty."
    return True, None

@app.route('/api/generate', methods=['POST'])
@limiter.limit("3 per day")
def generate_report():
    try:
        data = request.json
        
        is_valid, error_message = validate_input(data)
        if not is_valid:
            return jsonify({"error": error_message}), 400
        
        if not check_budget():
            cost_data = load_cost_data()
            return jsonify({
                "error": f"Monthly budget cap reached. Contact hello@bulwise.io"
            }), 503
        
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        
        query = data.get('query')
        context = data.get('context', {})
        
        # Simple prompt like original working version
        system_prompt = """You are BulWise, an AI Stack Advisory expert. Generate detailed, actionable AI implementation reports.

For the "Check Alternative AI Tools and Customize Your Stack" section, use this exact format for EACH category:

### Category Name

**PRIMARY TOOL: Tool Name**

**Strengths:**
Real-time web search with citations
Best-in-class accuracy for research
API available for automation

**Best for:** Use cases

**Integration:** Integration options

**ALTERNATIVE 1: Tool Name**

**Strengths:**
Excellent for creative ideation
Large plugin ecosystem
DALL-E image generation

**Best for:** Use cases

**Integration:** Integration options

**Trade-off:** What you give up compared to primary tool

**ALTERNATIVE 2: Tool Name**

**Strengths:**
Deep Google Workspace integration
Strong multimodal capabilities

**Best for:** Use cases

**Integration:** Integration options

**Trade-off:** What you give up compared to primary tool

---

For "Detailed Architecture Breakdown", write each connection as a separate paragraph starting with the tools:

**Zapier → Perplexity Pro:** Weekly scheduled trigger initiates automated searches for each competitor using predefined search queries and monitoring parameters

**Perplexity Pro → Claude Pro:** Raw search results, news articles, and competitor data are processed and sent to Claude for strategic analysis via Zapier webhook integration

**Claude Pro → Notion AI:** Analyzed competitor insights, market categorizations, and strategic summaries are automatically stored in structured Notion database with AI-enhanced tagging

For "Success Metrics", use this format for EACH metric:

### Metric Name

**What it is:** Description here

**How to measure:** Description here

**Target:** Description here

**Why it matters:** Description here

**Example:** Description here

For "Related Opportunities", use this format for EACH opportunity:

### Opportunity Name

**What it is:** Description here

**How it connects:** Description here

**Recommended tools:** Tool list here

**Setup time:** Time estimate here

**Potential impact:** Impact description here

For "Risk Assessment", create a markdown table with columns: Risk | Category | Likelihood | Impact | Mitigation
Use ONLY the words "Low", "Medium", or "High" for Likelihood and Impact (no emojis).
"""
        
        user_prompt = f"""
Problem/Goal: {query}

Context:
- Report Purpose: {context.get('report_purpose', 'Not specified')}
- Primary Audience: {context.get('primary_audience', 'Not specified')}
- Budget: {context.get('budget', 'Not specified')}
- Existing Tools: {context.get('existing_tools', 'None specified')}

Generate a comprehensive AI Stack Advisory Report with these sections:

1. Executive Summary (include a table called "Recommended Stack" with columns: Tool | Category | Purpose)
2. Check Alternative AI Tools and Customize Your Stack (with PRIMARY TOOL, ALTERNATIVE 1, ALTERNATIVE 2 for each category)
3. Detailed Architecture Breakdown (bullet points showing how tools connect)
4. Phased Implementation Roadmap (3 phases with flowing text, no bullets)
5. Architecture Diagram (Mermaid format)
6. Success Metrics (3-4 metrics, each with What it is, How to measure, Target, Why it matters, Example)
7. Risk Assessment (table format)
8. Related Opportunities (3 opportunities, each with the 5 fields listed above)
"""
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            temperature=0.7,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
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
    
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    cost_data = load_cost_data()
    return jsonify({
        "status": "healthy",
        "tools_in_database": len(all_tools)
    })

@app.route('/api/generate-pdf', methods=['POST'])
def generate_pdf():
    try:
        from weasyprint import HTML
        from io import BytesIO
        
        data = request.get_json()
        html_content = data.get('html', '')
        
        if not html_content:
            return jsonify({"error": "No HTML"}), 400
        
        pdf_buffer = BytesIO()
        HTML(string=html_content).write_pdf(pdf_buffer)
        pdf_buffer.seek(0)
        
        response = make_response(pdf_buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'attachment; filename=BulWise-AI-Stack-Report.pdf'
        
        return response
    except Exception as e:
        print(f"PDF Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": "Rate limit exceeded"}), 429

if __name__ == '__main__':
    print("BulWise API - Simple Version")
    print(f"Tools: {len(all_tools)}")
    app.run(debug=True, host='0.0.0.0', port=5000)
