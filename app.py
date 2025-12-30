"""
BulWise Flask Backend - Hybrid Approach (Markdown + Structured JSON)
====================================================================
"""

from flask import Flask, request, jsonify, make_response, Response, stream_with_context
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
        
        system_prompt = """You are BulWise, an AI Stack Advisory expert.

CRITICAL: You must respond with ONLY valid JSON. No markdown, no code blocks, no preamble - ONLY the JSON object.

Return a JSON object with this structure:

{
  "detailed_architecture": [
    {"from": "Tool A", "to": "Tool B", "description": "How they connect"}
  ],
  "phased_implementation": [
    {"phase": "Phase 1: Foundation (Week 1-2)", "description": "What to do in this phase"}
  ],
  "success_metrics": [
    {
      "name": "Metric Name",
      "what_it_is": "Description",
      "how_to_measure": "Measurement method",
      "target": "Target value",
      "why_it_matters": "Business impact",
      "example": "Concrete example"
    }
  ],
  "related_opportunities": [
    {
      "name": "Opportunity Name",
      "what_it_is": "Description",
      "how_it_connects": "How it builds on implementation",
      "recommended_tools": "Tool names",
      "setup_time": "Time estimate",
      "potential_impact": "Expected impact"
    }
  ],
  "check_alternative_tools": [
    {
      "category": "Category Name",
      "primary_tool": {
        "name": "Tool Name",
        "strengths": ["Strength 1", "Strength 2", "Strength 3"],
        "best_for": "Use cases description",
        "integration": "Integration options"
      },
      "alternatives": [
        {
          "name": "Alternative Tool Name",
          "strengths": ["Strength 1", "Strength 2"],
          "best_for": "Use cases description",
          "integration": "Integration options",
          "trade_off": "What you give up vs primary"
        }
      ]
    }
  ],
  "markdown_report": "Full markdown report with Executive Summary, Architecture Diagram (Mermaid), and Risk Assessment"
}

The markdown_report should contain ONLY:
1. Executive Summary (with Recommended Stack table with clickable links - DO NOT include pricing/cost columns, only Tool | Category | Purpose)
2. Architecture Diagram (Mermaid format)
3. Risk Assessment (table with Risk | Category | Likelihood | Impact | Mitigation, use only "Low", "Medium", "High" - no emojis)

CRITICAL RULE - NO PRICING ANYWHERE:
- DO NOT include pricing, cost, fees, or monthly charges in ANY section
- DO NOT mention "$" amounts or pricing tiers
- Focus only on tool capabilities, features, and use cases
- If budget context is provided, acknowledge it but don't estimate costs

In the Executive Summary Recommended Stack table:
- Columns: Tool | Category | Purpose
- NO pricing columns

The other sections (detailed_architecture, phased_implementation, success_metrics, related_opportunities, check_alternative_tools) are in structured JSON format.

For check_alternative_tools, include 3-5 tool categories, each with 1 primary tool and exactly 2 alternatives.
"""
        
        user_prompt = f"""
Problem/Goal: {query}

Context:
- Report Purpose: {context.get('report_purpose', 'Not specified')}
- Primary Audience: {context.get('primary_audience', 'Not specified')}
- Budget: {context.get('budget', 'Not specified')}
- Existing Tools: {context.get('existing_tools', 'None specified')}

Generate a comprehensive AI Stack Advisory Report with structured data for the 4 sections and full markdown for remaining sections.
"""
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            temperature=0.7,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        response_text = message.content[0].text
        
        # Try to parse JSON, handle potential markdown wrapper
        try:
            # Remove potential markdown code blocks
            if response_text.strip().startswith('```'):
                response_text = response_text.strip()
                lines = response_text.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines[-1].strip() == '```':
                    lines = lines[:-1]
                response_text = '\n'.join(lines)
            
            report_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"JSON Parse Error: {e}")
            print(f"Response preview: {response_text[:500]}")
            return jsonify({"error": "Failed to parse AI response as JSON"}), 500
        
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens
        cost = calculate_cost(input_tokens, output_tokens)
        total_cost = log_request(input_tokens, output_tokens, cost)
        
        return jsonify({
            "success": True,
            "report": report_data,
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

@app.route('/api/generate-stream', methods=['POST'])
@limiter.limit("3 per day")
def generate_report_stream():
    """Streaming version of generate_report using Server-Sent Events"""
    def generate():
        try:
            data = request.json
            
            is_valid, error_message = validate_input(data)
            if not is_valid:
                yield f"data: {json.dumps({'error': error_message})}\n\n"
                return
            
            if not check_budget():
                yield f"data: {json.dumps({'error': 'Monthly budget cap reached. Contact hello@bulwise.io'})}\n\n"
                return
            
            client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            
            query = data.get('query')
            context = data.get('context', {})
            
            system_prompt = """You are BulWise, an AI Stack Advisory expert.

CRITICAL: You must respond with ONLY valid JSON. No markdown, no code blocks, no preamble - ONLY the JSON object.

Return a JSON object with this structure:

{
  "detailed_architecture": [
    {"from": "Tool A", "to": "Tool B", "description": "How they connect"}
  ],
  "phased_implementation": [
    {"phase": "Phase 1: Foundation (Week 1-2)", "description": "What to do in this phase"}
  ],
  "success_metrics": [
    {
      "name": "Metric Name",
      "what_it_is": "Description",
      "how_to_measure": "Measurement method",
      "target": "Target value",
      "why_it_matters": "Business impact",
      "example": "Concrete example"
    }
  ],
  "related_opportunities": [
    {
      "name": "Opportunity Name",
      "what_it_is": "Description",
      "how_it_connects": "How it builds on implementation",
      "recommended_tools": "Tool names",
      "setup_time": "Time estimate",
      "potential_impact": "Expected impact"
    }
  ],
  "check_alternative_tools": [
    {
      "category": "Category Name",
      "primary_tool": {
        "name": "Tool Name",
        "strengths": ["Strength 1", "Strength 2", "Strength 3"],
        "best_for": "Use cases description",
        "integration": "Integration options"
      },
      "alternatives": [
        {
          "name": "Alternative Tool Name",
          "strengths": ["Strength 1", "Strength 2"],
          "best_for": "Use cases description",
          "integration": "Integration options",
          "trade_off": "What you give up vs primary"
        }
      ]
    }
  ],
  "markdown_report": "Full markdown report with Executive Summary, Architecture Diagram (Mermaid), and Risk Assessment"
}

The markdown_report should contain ONLY:
1. Executive Summary (with Recommended Stack table with clickable links - DO NOT include pricing/cost columns, only Tool | Category | Purpose)
2. Architecture Diagram (Mermaid format)
3. Risk Assessment (table with Risk | Category | Likelihood | Impact | Mitigation, use only "Low", "Medium", "High" - no emojis)

CRITICAL RULE - NO PRICING ANYWHERE:
- DO NOT include pricing, cost, fees, or monthly charges in ANY section
- DO NOT mention "$" amounts or pricing tiers
- Focus only on tool capabilities, features, and use cases
- If budget context is provided, acknowledge it but don't estimate costs

In the Executive Summary Recommended Stack table:
- Columns: Tool | Category | Purpose
- NO pricing columns

The other sections (detailed_architecture, phased_implementation, success_metrics, related_opportunities, check_alternative_tools) are in structured JSON format.

For check_alternative_tools, include 3-5 tool categories, each with 1 primary tool and exactly 2 alternatives.
"""
            
            user_prompt = f"""
Problem/Goal: {query}

Context:
- Report Purpose: {context.get('report_purpose', 'Not specified')}
- Primary Audience: {context.get('primary_audience', 'Not specified')}
- Budget: {context.get('budget', 'Not specified')}
- Existing Tools: {context.get('existing_tools', 'None specified')}

Generate a comprehensive AI Stack Advisory Report with structured data for the 4 sections and full markdown for remaining sections.
"""
            
            # Send initial status
            yield f"data: {json.dumps({'status': 'generating', 'progress': 10})}\n\n"
            
            # Use streaming API
            full_response = ""
            with client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=8000,
                temperature=0.7,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            ) as stream:
                for text in stream.text_stream:
                    full_response += text
                    # Send chunks as they arrive
                    yield f"data: {json.dumps({'chunk': text, 'progress': min(90, 10 + len(full_response) // 100)})}\n\n"
            
            # Parse the complete response
            response_text = full_response
            
            # Remove potential markdown code blocks
            if response_text.strip().startswith('```'):
                response_text = response_text.strip()
                lines = response_text.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines[-1].strip() == '```':
                    lines = lines[:-1]
                response_text = '\n'.join(lines)
            
            try:
                report_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                yield f"data: {json.dumps({'error': 'Failed to parse AI response as JSON'})}\n\n"
                return
            
            # Get usage stats
            message = stream.get_final_message()
            input_tokens = message.usage.input_tokens
            output_tokens = message.usage.output_tokens
            cost = calculate_cost(input_tokens, output_tokens)
            total_cost = log_request(input_tokens, output_tokens, cost)
            
            # Send complete report
            yield f"data: {json.dumps({'status': 'complete', 'report': report_data, 'progress': 100, 'metadata': {'input_tokens': input_tokens, 'output_tokens': output_tokens, 'cost': f'${cost:.4f}'}})}\n\n"
            
        except Exception as e:
            import traceback
            print(f"Streaming Error: {e}")
            print(traceback.format_exc())
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no'
    })

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
    print("BulWise API - Hybrid Approach (Markdown + Structured JSON)")
    print(f"Tools: {len(all_tools)}")
    app.run(debug=True, host='0.0.0.0', port=5000)
