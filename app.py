"""
BulWise Flask Backend with Cost Protection
===========================================

This is your Flask API backend with rate limiting and budget protection.
Replace your current Flask API code with this protected version.

Requirements:
pip install flask flask-cors flask-limiter anthropic python-dotenv --break-system-packages
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import anthropic
import os
from datetime import datetime
import json
from pathlib import Path

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# ============================================================================
# RATE LIMITING CONFIGURATION
# ============================================================================

# Initialize rate limiter with memory storage
limiter = Limiter(
    app=app,
    key_func=get_remote_address,  # Track by IP address
    default_limits=["100 per hour"],  # Fallback limit
    storage_uri="memory://"  # Use in-memory storage (for production, use Redis)
)

# ============================================================================
# COST TRACKING CONFIGURATION
# ============================================================================

MONTHLY_BUDGET_CAP = 50.00  # $50 per month
COST_PER_1K_INPUT_TOKENS = 0.003  # Claude Sonnet 4 pricing
COST_PER_1K_OUTPUT_TOKENS = 0.015  # Claude Sonnet 4 pricing
COST_TRACKING_FILE = "cost_tracking.json"

def get_current_month():
    """Returns current month in YYYY-MM format"""
    return datetime.now().strftime("%Y-%m")

def load_cost_data():
    """Load cost tracking data from file"""
    if not Path(COST_TRACKING_FILE).exists():
        return {"month": get_current_month(), "total_cost": 0.0, "requests": []}
    
    with open(COST_TRACKING_FILE, 'r') as f:
        data = json.load(f)
        
    # Reset if new month
    if data.get("month") != get_current_month():
        return {"month": get_current_month(), "total_cost": 0.0, "requests": []}
    
    return data

def save_cost_data(data):
    """Save cost tracking data to file"""
    with open(COST_TRACKING_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def calculate_cost(input_tokens, output_tokens):
    """Calculate cost based on token usage"""
    input_cost = (input_tokens / 1000) * COST_PER_1K_INPUT_TOKENS
    output_cost = (output_tokens / 1000) * COST_PER_1K_OUTPUT_TOKENS
    return input_cost + output_cost

def check_budget():
    """Check if monthly budget has been exceeded"""
    data = load_cost_data()
    return data["total_cost"] < MONTHLY_BUDGET_CAP

def log_request(input_tokens, output_tokens, cost):
    """Log request and update total cost"""
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
    
    # Print cost summary
    print(f"💰 Cost: ${cost:.4f} | Month total: ${data['total_cost']:.2f}/{MONTHLY_BUDGET_CAP}")
    
    return data["total_cost"]

# ============================================================================
# INPUT VALIDATION
# ============================================================================

MAX_QUERY_LENGTH = 2000  # characters
MAX_CONTEXT_LENGTH = 500  # characters per context field

def validate_input(data):
    """Validate input lengths to prevent abuse"""
    query = data.get('query', '')
    context = data.get('context', {})
    
    # Validate query length
    if len(query) > MAX_QUERY_LENGTH:
        return False, f"Query too long. Maximum {MAX_QUERY_LENGTH} characters allowed."
    
    # Validate context fields
    for key, value in context.items():
        if isinstance(value, str) and len(value) > MAX_CONTEXT_LENGTH:
            return False, f"Context field '{key}' too long. Maximum {MAX_CONTEXT_LENGTH} characters allowed."
    
    # Check for empty input
    if not query.strip():
        return False, "Query cannot be empty."
    
    return True, None

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/generate', methods=['POST'])
@limiter.limit("3 per day")  # CRITICAL: 3 requests per day per IP
def generate_report():
    """Generate AI Stack Advisory Report"""
    
    try:
        # Get request data
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
        
        # Initialize Anthropic client
        client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
        
        # Prepare the prompt
        query = data.get('query')
        context = data.get('context', {})
        
        system_prompt = """You are an AI Stack Advisory expert. Generate detailed, actionable AI implementation reports."""
        
        user_prompt = f"""
Problem/Goal: {query}

Context:
- Report Purpose: {context.get('report_purpose', 'Not specified')}
- Primary Audience: {context.get('primary_audience', 'Not specified')}
- Budget: {context.get('budget', 'Not specified')}
- Existing Tools: {context.get('existing_tools', 'None specified')}

Generate a comprehensive AI Stack Advisory Report with:
1. Executive Summary
2. Recommended AI Tools (specific products with pricing)
3. Implementation Timeline (week-by-week)
4. Architecture Diagram (Mermaid format)
5. Success Metrics
6. Risk Assessment
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
        
        # Return response
        return jsonify({
            "report": report_content,
            "metadata": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": f"${cost:.4f}",
                "month_total": f"${total_cost:.2f}/{MONTHLY_BUDGET_CAP}"
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

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    cost_data = load_cost_data()
    
    return jsonify({
        "status": "healthy",
        "month": cost_data["month"],
        "total_cost": f"${cost_data['total_cost']:.2f}",
        "budget_cap": f"${MONTHLY_BUDGET_CAP}",
        "budget_remaining": f"${MONTHLY_BUDGET_CAP - cost_data['total_cost']:.2f}",
        "requests_this_month": len(cost_data["requests"])
    })

@app.route('/api/costs', methods=['GET'])
def get_costs():
    """Get cost tracking data (admin endpoint - secure this in production!)"""
    cost_data = load_cost_data()
    return jsonify(cost_data)

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded"""
    return jsonify({
        "error": "Rate limit exceeded. You can generate up to 3 reports per day. "
                 "Please try again tomorrow or contact hello@bulwise.io for more access."
    }), 429

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  WARNING: ANTHROPIC_API_KEY not set!")
        print("Set it in your environment or .env file")
    
    # Print configuration
    print("=" * 60)
    print("BulWise Flask API - Protected Version")
    print("=" * 60)
    print(f"✅ Rate Limiting: 3 requests per day per IP")
    print(f"✅ Monthly Budget Cap: ${MONTHLY_BUDGET_CAP}")
    print(f"✅ Input Validation: Max {MAX_QUERY_LENGTH} chars (query), {MAX_CONTEXT_LENGTH} chars (context)")
    print(f"✅ Cost Tracking: {COST_TRACKING_FILE}")
    print("=" * 60)
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)
