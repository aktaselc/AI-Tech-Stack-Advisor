"""
BulWise Flask Backend - COMPLETE WITH ALL SECTIONS
===================================================
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
            data = json.load(f)
        
        # Extract tools array from JSON object
        if isinstance(data, dict) and 'tools' in data:
            tools = data['tools']
        elif isinstance(data, list):
            tools = data
        else:
            print("❌ Unexpected tools file format!")
            return []
        
        print(f"✅ Loaded {len(tools)} tools from database")
        return tools
    except FileNotFoundError:
        print("❌ complete_250_tools.json not found!")
        return []
    except Exception as e:
        print(f"❌ Error loading tools: {e}")
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
                f"- {tool.get('tool_name', 'Unknown')}: {tool.get('description', 'AI tool')}"
                for tool in all_tools[:100]  # First 100 tools
            ])
            tools_info = f"You have access to {len(all_tools)} AI tools. Tools: {tools_context}"
        else:
            tools_info = ""
        
        system_prompt = f"""You are BulWise, an AI Stack Advisory expert. {tools_info}

Generate a comprehensive, detailed AI Stack Advisory Report using this EXACT structure:

## Executive Summary

[2-3 paragraphs explaining the solution]

### Recommended Stack

| Tool | Category | Purpose |
|------|----------|---------|
| [Perplexity Pro](https://perplexity.ai) | Search & Research | Real-time competitive intelligence gathering |
| [Claude Pro](https://claude.ai) | LLM | Strategic analysis and insight generation |
| [Zapier](https://zapier.com) | Automation | Workflow orchestration between tools |
| [Beautiful.ai](https://beautiful.ai) | Presentation | Automated slide creation |
| [Notion AI](https://notion.so) | Productivity | Database management and documentation |

## Check Alternative AI Tools and Customize Your Stack

### Research & Data Gathering

**PRIMARY TOOL: Perplexity Pro**

**Strengths:**
• Real-time web search with citations
• Healthcare-specific news monitoring
• API available for automation workflows

**Best for:** Competitive intelligence, market research, regulatory tracking

**Integration:** Web interface, API, Zapier workflows, mobile app

**ALTERNATIVE 1: ChatGPT Plus**

**Strengths:**
• Excellent for creative analysis
• Large plugin ecosystem
• DALL-E for visual content

**Best for:** Brainstorming sessions, content ideation

**Integration:** Web, API, plugins, mobile

**Trade-off:** No source citations, less accurate for real-time news

**ALTERNATIVE 2: Gemini Advanced**

**Strengths:**
• Deep Google Workspace integration
• Strong multimodal capabilities
• Real-time Google Search access

**Best for:** Google ecosystem users

**Integration:** Google Workspace, Gmail, Docs

**Trade-off:** Weaker third-party integrations

---

[Continue with 3-5 categories based on user needs. Each must follow this EXACT format with PRIMARY TOOL, ALTERNATIVE 1, ALTERNATIVE 2, and ---]

## Detailed Architecture Breakdown

• **Zapier → Perplexity Pro**: Weekly scheduled trigger initiates automated searches for each competitor using predefined search queries and monitoring parameters

• **Perplexity Pro → Claude Pro**: Raw search results, news articles, and competitor data are processed and sent to Claude for strategic analysis via Zapier webhook integration

• **Claude Pro → Notion AI**: Analyzed competitor insights, market categorizations, and strategic summaries are automatically stored in structured Notion database with AI-enhanced tagging

• **Notion AI → Beautiful.ai**: Database triggers Beautiful.ai template population using Zapier integration, automatically formatting competitive intelligence into presentation slides

• **Beautiful.ai → HubSpot**: Completed slide decks are automatically uploaded to HubSpot deal records and distributed to relevant stakeholders via email automation

• **HubSpot Integration**: Existing CRM data enriches competitor analysis by matching prospects to competitive landscape and deal intelligence

## Phased Implementation Roadmap

**Phase 1: Foundation (Week 1-2)**

Set up Perplexity Pro account and API access. Configure Claude Sonnet 4 API integration. Create Notion workspace with competitor database structure. Establish Beautiful.ai account with healthcare templates. Define initial competitor list and search parameters

**Phase 2: Integration (Week 3-4)**

Build Zapier workflows connecting Perplexity to Claude. Set up automated data flow from Claude to Notion. Configure Beautiful.ai template population. Test end-to-end automation with sample competitors. Create categorization framework in Claude

**Phase 3: Optimization (Month 2+)**

Refine search queries and analysis prompts. Optimize slide templates for consistent branding. Implement error handling and monitoring. Add manual review checkpoints for quality control. Scale to full competitor list monitoring

## Architecture Diagram

```mermaid
graph TD
    A[Scheduled Trigger] --> B[Perplexity Pro]
    B --> C[Competitor Search]
    C --> D[Claude Sonnet 4]
    D --> E[Analysis & Categorization]
    E --> F[Notion Database]
    F --> G[Beautiful.ai]
    G --> H[Slide Generation]
    H --> I[HubSpot]
    I --> J[Email Distribution]
    J --> K[Event Delivery]
```

## Success Metrics

### Time Savings on Competitive Analysis

• **What it is**: Reduction in hours spent on manual competitive research and report preparation
• **How to measure**: Track weekly hours before vs. after implementation across business analyst team  
• **Target**: 75% reduction in manual research time (from 8 hours to 2 hours per week)
• **Why it matters**: Frees up analytical capacity for higher-value strategic work and faster decision-making
• **Example**: Business analyst previously spent full day gathering competitor news; now reviews AI-generated insights in 30 minutes

### Coverage Expansion and Monitoring Depth

• **What it is**: Number of competitors actively monitored and depth of intelligence gathered per competitor
• **How to measure**: Count monitored competitors and average data points captured per competitor monthly
• **Target**: 3x increase in monitored competitors (from 10 to 30) with 5+ intelligence categories per competitor
• **Why it matters**: Broader market visibility prevents blind spots and captures emerging competitive threats early
• **Example**: Expand from tracking 10 major competitors quarterly to monitoring 30 companies across categories weekly

### Insight Delivery Speed and Frequency  

• **What it is**: Time from competitive event to stakeholder notification and reporting cadence
• **How to measure**: Track average hours from event occurrence to HubSpot notification and weekly report cycles
• **Target**: Real-time alerts within 24 hours and weekly comprehensive reports vs. previous monthly manual reports
• **Why it matters**: Faster insights enable quicker strategic responses to market changes and competitive moves
• **Example**: Leadership receives competitive intelligence updates every Monday morning instead of quarterly summaries

## Risk Assessment

| Risk | Category | Likelihood | Impact | Mitigation |
|------|----------|------------|--------|------------|
| Data accuracy and reliability concerns from automated web scraping | Technical | Medium | High | Implement multiple source verification, citation tracking, and manual review processes for critical insights |
| API rate limits and service disruptions affecting automation reliability | Technical | Medium | Medium | Configure backup data sources, implement retry logic, and establish service level monitoring with alerting systems |
| Competitive intelligence sharing compliance and confidentiality risks | Business | Low | High | Establish clear data governance policies, implement access controls, and ensure compliance with healthcare industry regulations |
| Over-reliance on AI analysis leading to strategic blind spots | Business | Medium | Medium | Maintain human oversight processes, regular analysis validation, and diverse analytical perspectives in decision-making |

## Related Opportunities

### Market Trend Prediction and Early Warning System

• **What it is**: Advanced AI system that analyzes competitive patterns to predict market shifts and emerging opportunities before they become obvious
• **How it connects**: Builds on competitive intelligence foundation to identify strategic patterns and market timing opportunities
• **Recommended tools**: Claude Pro for trend analysis, Perplexity Pro for market research, Notion AI for historical pattern tracking
• **Setup time**: 4-6 weeks after core system implementation
• **Potential impact**: 6-month competitive advantage through early identification of market opportunities and threats

### Customer Sentiment Correlation Analysis  

• **What it is**: Link competitive intelligence with customer feedback analysis to understand how competitor actions impact customer perceptions and preferences
• **How it connects**: Combines competitor monitoring with voice-of-customer data for strategic positioning insights
• **Recommended tools**: MonkeyLearn for sentiment analysis, existing customer feedback systems, Notion for correlation tracking
• **Setup time**: 3-4 weeks parallel implementation
• **Potential impact**: 25% improvement in competitive positioning decisions through customer-validated intelligence

### Automated Strategic Playbook Generation

• **What it is**: AI system that automatically generates response strategies and playbooks based on competitor moves and historical successful responses
• **How it connects**: Leverages competitive intelligence and historical decision outcomes to recommend strategic responses
• **Recommended tools**: Claude Pro for strategy generation, Notion for playbook storage, Beautiful.ai for presentation formatting
• **Setup time**: 6-8 weeks with strategy template development
• **Potential impact**: 40% faster strategic response time and improved consistency in competitive countermoves

CRITICAL FORMATTING RULES:
1. Executive Summary must include the Recommended Stack table with clickable links
2. "Check Alternative AI Tools" section MUST use PRIMARY TOOL, ALTERNATIVE 1, ALTERNATIVE 2 format
3. Use --- separators between categories in Check Alternative AI Tools section
4. Each field (Strengths, Best for, Integration, Trade-off) MUST be on its own line with proper line breaks
5. Detailed Architecture Breakdown: Each bullet (•) MUST start on a NEW LINE - do not put multiple bullets on the same line
6. Phased Implementation: Each phase title MUST be followed by a blank line before the description
7. Success Metrics: Each field (What it is, How to measure, Target, Why it matters, Example) MUST start on a NEW LINE with bullet (•)
8. Risk Assessment: Table with Risk, Category, Likelihood, Impact, Mitigation columns. Use ONLY "Low", "Medium", or "High" for Likelihood and Impact (NO EMOJIS)
9. Related Opportunities: Each field (What it is, How it connects, Recommended tools, Setup time, Potential impact) MUST start on a NEW LINE with bullet (•)
10. Make "Strengths:", "Best for:", "Integration:", "Trade-off:" bold in the Check Alternative AI Tools section

CRITICAL: Put line breaks between bullet points. Do NOT combine multiple bullets on one line.
"""
        
        user_prompt = f"""
Problem/Goal: {query}

Context:
- Report Purpose: {context.get('report_purpose', 'Not specified')}
- Primary Audience: {context.get('primary_audience', 'Not specified')}
- Budget: {context.get('budget', 'Not specified')}
- Existing Tools: {context.get('existing_tools', 'None specified')}

Generate the complete AI Stack Advisory Report following the exact structure provided.
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
    print("BulWise Flask API - COMPLETE VERSION")
    print("=" * 60)
    print(f"✅ Rate Limiting: 3 requests per day per IP")
    print(f"✅ Monthly Budget Cap: ${MONTHLY_BUDGET_CAP}")
    print(f"✅ Tools in Database: {len(all_tools)}")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
