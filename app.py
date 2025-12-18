"""
BulWise API Backend
Simple Flask API that generates AI stack advisory reports
"""

from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import anthropic
import os
import json

app = Flask(__name__)

# Simple CORS - allow all origins for testing
CORS(app, origins="*", methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type"])

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# AI Tools Database (same as your Streamlit app)
TOOLS_DATABASE = [
    {
        "name": "Perplexity Pro",
        "category": "Search & Research",
        "description": "AI-powered search with real-time web access and citations",
        "pricing_monthly": 20,
        "pricing_annual": 200,
        "url": "https://perplexity.ai"
    },
    {
        "name": "Claude Pro",
        "category": "LLM",
        "description": "Advanced AI for analysis, writing, and reasoning",
        "pricing_monthly": 20,
        "pricing_annual": 200,
        "url": "https://claude.ai"
    },
    {
        "name": "ChatGPT Plus",
        "category": "LLM",
        "description": "OpenAI's conversational AI with GPT-4",
        "pricing_monthly": 20,
        "pricing_annual": 240,
        "url": "https://chat.openai.com"
    },
    {
        "name": "Zapier Professional",
        "category": "Automation",
        "description": "Connect and automate workflows between 5000+ apps",
        "pricing_monthly": 20,
        "pricing_annual": 240,
        "url": "https://zapier.com"
    },
    {
        "name": "Make (Integromat)",
        "category": "Automation",
        "description": "Visual automation for complex workflows",
        "pricing_monthly": 9,
        "pricing_annual": 108,
        "url": "https://make.com"
    },
    {
        "name": "Beautiful.ai",
        "category": "Presentation",
        "description": "AI-powered presentation builder",
        "pricing_monthly": 12,
        "pricing_annual": 144,
        "url": "https://beautiful.ai"
    },
    {
        "name": "Notion AI",
        "category": "Productivity",
        "description": "AI writing assistant in Notion",
        "pricing_monthly": 10,
        "pricing_annual": 120,
        "url": "https://notion.so/product/ai"
    },
    {
        "name": "Midjourney",
        "category": "Image Generation",
        "description": "AI art generator from text prompts",
        "pricing_monthly": 10,
        "pricing_annual": 120,
        "url": "https://midjourney.com"
    },
    {
        "name": "ElevenLabs",
        "category": "Voice & Audio",
        "description": "Realistic AI voice generation",
        "pricing_monthly": 5,
        "pricing_annual": 60,
        "url": "https://elevenlabs.io"
    },
    {
        "name": "Grammarly",
        "category": "Writing",
        "description": "AI writing assistant for grammar and clarity",
        "pricing_monthly": 12,
        "pricing_annual": 144,
        "url": "https://grammarly.com"
    }
]


def generate_report(user_query, context):
    """
    Generate AI stack advisory report using Claude
    
    Args:
        user_query: User's problem description
        context: Dict with report_purpose, primary_audience, budget
    
    Returns:
        Markdown formatted report
    """
    
    # Build tools database string
    tools_info = "\n".join([
        f"- {tool['name']} ({tool['category']}): {tool['description']} | ${tool['pricing_monthly']}/month"
        for tool in TOOLS_DATABASE
    ])
    
    system_prompt = f"""You are BulWise, an AI Stack Advisory expert. Your job is to recommend specific AI tools and create detailed implementation plans.

AVAILABLE TOOLS DATABASE:
{tools_info}

CRITICAL INSTRUCTIONS:
1. Recommend SPECIFIC tools by name from the database above
2. Include exact monthly and annual costs
3. Provide day-by-day implementation roadmap
4. Include architecture diagram in Mermaid format
5. Add risk assessment with mitigation strategies
6. Be specific, actionable, and detailed

REPORT PURPOSE: {context.get('report_purpose', 'General guidance')}
PRIMARY AUDIENCE: {context.get('primary_audience', 'General')}
BUDGET: {context.get('budget', 'Not specified')}

Format your response as a professional markdown report with these sections:
1. Executive Summary
2. Recommended Stack (with specific tools and costs)
3. Architecture Diagram (Mermaid flowchart)
4. Implementation Timeline (Gantt chart + phase breakdown)
5. Day-by-Day Roadmap
6. Risk Assessment
7. Success Metrics
8. Related Opportunities"""

    # Call Claude API
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"Create a comprehensive AI stack advisory report for this use case:\n\n{user_query}"
            }
        ]
    )
    
    return message.content[0].text


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "BulWise API"})


@app.route('/api/generate', methods=['POST'])
def generate():
    """
    Generate AI stack advisory report
    
    Expected JSON body:
    {
        "query": "User's problem description",
        "context": {
            "report_purpose": "Investment decision / Executive presentation / etc",
            "primary_audience": "C-suite / Technical team / etc",
            "budget": "Under $100 / $100-500 / etc"
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({"error": "Missing 'query' in request body"}), 400
        
        user_query = data['query']
        context = data.get('context', {})
        
        # Generate report
        report = generate_report(user_query, context)
        
        return jsonify({
            "success": True,
            "report": report
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/followup', methods=['POST'])
def followup():
    """
    Answer follow-up questions about a report
    
    Expected JSON body:
    {
        "question": "User's follow-up question",
        "original_report": "The original report (optional for context)"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'question' not in data:
            return jsonify({"error": "Missing 'question' in request body"}), 400
        
        question = data['question']
        original_report = data.get('original_report', '')
        
        # Build context-aware prompt
        system_prompt = """You are BulWise, an AI Stack Advisory expert. Answer follow-up questions about AI tool recommendations with specific, actionable guidance."""
        
        user_message = f"Follow-up question: {question}"
        if original_report:
            user_message = f"Original report context:\n{original_report[:1000]}...\n\n{user_message}"
        
        # Call Claude API
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        )
        
        return jsonify({
            "success": True,
            "answer": message.content[0].text
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == '__main__':
    # For local development
    app.run(debug=True, host='0.0.0.0', port=5000)
