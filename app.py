"""
BulWise API Backend
Simple Flask API that generates AI stack advisory reports
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS, cross_origin
import anthropic
import os
import json
import datetime
import io
from weasyprint import HTML, CSS

app = Flask(__name__)

# Simple CORS - allow all origins for testing
CORS(app, origins="*", methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type"])

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Analytics logging function
def log_analytics(event_type, data):
    """Log analytics data to a JSON file"""
    try:
        analytics_file = 'analytics_log.json'
        
        # Create log entry
        log_entry = {
            'timestamp': datetime.datetime.now().isoformat(),
            'event_type': event_type,
            'data': data
        }
        
        # Read existing logs
        if os.path.exists(analytics_file):
            with open(analytics_file, 'r') as f:
                logs = json.load(f)
        else:
            logs = []
        
        # Append new log
        logs.append(log_entry)
        
        # Write back
        with open(analytics_file, 'w') as f:
            json.dump(logs, f, indent=2)
            
    except Exception as e:
        print(f"Analytics logging error: {e}")
        # Don't fail the request if logging fails
        pass

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
2. Provide detailed analysis and step-by-step implementation guidance
3. Include architecture diagram in Mermaid format
4. Be specific, actionable, and detailed

REPORT PURPOSE: {context.get('report_purpose', 'General guidance')}
PRIMARY AUDIENCE: {context.get('primary_audience', 'General')}
BUDGET: {context.get('budget', 'Not specified')}
EXISTING TOOLS: {context.get('existing_tools', 'None specified')}

TODAY'S DATE: December 18, 2025

IMPORTANT: If user has existing tools, show how to integrate recommended AI tools with their current stack. Include connection details in "Detailed Architecture Breakdown" section.

Format your response as a professional markdown report with these EXACT sections:

## Executive Summary
Brief overview of the recommended solution

## Recommended Stack
Format as markdown table WITHOUT cost columns. Make tool names clickable links:
| Tool | Category | Purpose |
|------|----------|---------|
| [Tool Name](https://toolwebsite.com) | Category | What it does |

IMPORTANT: Every tool name must be a markdown link to its website.

## Architecture Diagram
```mermaid
graph TD
    A[Start] --> B[Tool 1]
    B --> C[Tool 2]
```

## Detailed Architecture Breakdown
Explain step-by-step how the tools connect using bullet points:
- **Tool A → Tool B**: Describe the connection and data flow
- **Tool B → Tool C**: Describe the connection and integration method
- **Tool C → Tool D**: Describe the connection
(Continue for all tools in the stack)

## Implementation Phases
Break into 4 phases with milestones:
**Phase 1: Setup (Weeks 1-2)**
- Milestone 1
- Milestone 2

**Phase 2: Integration (Weeks 3-4)**
- Milestone 1
- Milestone 2

(Continue for Phases 3 and 4)

## Detailed Tool Analysis
For each recommended tool:
**Tool Name**
- **Purpose**: What it does
- **Key Features**: List 3-4 features
- **Implementation Notes**: Specific setup considerations
- **Best Practices**: 2-3 tips

## Risk Assessment
Format as markdown table with color indicators:
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Risk description | 🔴 High / 🟡 Medium / 🟢 Low | 🔴 High / 🟡 Medium / 🟢 Low | How to mitigate |

Include 4-5 risks covering technical, organizational, and operational aspects.

## Success Metrics
For each metric (provide 3-4 metrics):

**Metric Name**
- **What it is**: Definition
- **How to measure**: Specific measurement method
- **Target**: Specific goal
- **Why it matters**: Business impact
- **Example**: Real-world scenario

## Related AI Opportunities
Show EXACTLY 3 opportunities:

**Opportunity 1 Title**
- **What it is**: Description
- **How it connects**: Connection to main use case
- **Recommended tools**: Specific tool names
- **Setup time**: Estimated time
- **Potential impact**: Expected benefit

(Repeat for 2 more opportunities)

CRITICAL FORMATTING RULES:
- Use EXACTLY these section headers (## Section Name)
- Include ALL sections listed above
- Use proper markdown tables where specified
- Use mermaid code blocks for diagrams
- Use color emoji indicators: 🔴 High, 🟡 Medium, 🟢 Low
- Be comprehensive - don't cut content short
- Provide complete implementation phases (all 4 phases)
- List ALL recommended tools in Detailed Tool Analysis

DO NOT INCLUDE:
- ROI calculations
- Classification sections
- Cost information in recommended stack table
- Dates before December 2025"""

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
        
        # Log analytics - user inputs
        log_analytics('report_generated', {
            'user_prompt': user_query,
            'report_purpose': context.get('report_purpose'),
            'primary_audience': context.get('primary_audience'),
            'budget': context.get('budget'),
            'existing_tools': context.get('existing_tools')
        })
        
        # Generate report
        report = generate_report(user_query, context)
        
        # Log analytics - report output
        log_analytics('report_output', {
            'report_length': len(report),
            'report_preview': report[:500] if len(report) > 500 else report
        })
        
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


@app.route('/api/generate-pdf', methods=['POST'])
def generate_pdf():
    """
    Generate PDF from HTML content using WeasyPrint
    This endpoint receives HTML and returns a properly formatted PDF
    with correct page breaks
    """
    try:
        data = request.get_json()
        html_content = data.get('html', '')
        
        if not html_content:
            return jsonify({
                "success": False,
                "error": "No HTML content provided"
            }), 400
        
        # CSS for proper page breaks and styling
        pdf_css = CSS(string='''
            @page {
                size: A4;
                margin: 15mm;
            }
            
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #2d3748;
            }
            
            /* Prevent sections from breaking across pages */
            .section-wrapper {
                page-break-inside: avoid;
                page-break-after: auto;
            }
            
            /* Prevent diagrams from splitting */
            .mermaid-diagram {
                page-break-inside: avoid !important;
                margin-top: 40px;
                margin-bottom: 40px;
            }
            
            /* Prevent tables from splitting */
            table {
                page-break-inside: avoid;
                margin-top: 40px;
                margin-bottom: 40px;
                border-collapse: collapse;
                width: 100%;
            }
            
            table th,
            table td {
                padding: 12px;
                text-align: left;
                border: 1px solid #e2e8f0;
            }
            
            table th {
                background-color: #667eea;
                color: white;
                font-weight: bold;
            }
            
            /* Prevent paragraphs from breaking */
            p {
                page-break-inside: avoid;
                margin-bottom: 16px;
            }
            
            /* Keep headings with content */
            h1, h2, h3 {
                page-break-after: avoid;
                color: #667eea;
                margin-top: 30px;
                margin-bottom: 16px;
            }
            
            h1 {
                font-size: 32px;
                border-bottom: 3px solid #667eea;
                padding-bottom: 16px;
            }
            
            h2 {
                font-size: 24px;
                margin-top: 40px;
            }
            
            h3 {
                font-size: 18px;
            }
            
            /* Lists */
            ul, ol {
                page-break-inside: avoid;
                margin-bottom: 20px;
            }
            
            li {
                margin-bottom: 8px;
            }
            
            /* Links */
            a {
                color: #667eea;
                text-decoration: none;
            }
            
            a:hover {
                text-decoration: underline;
            }
            
            /* Report summary box */
            .report-summary {
                background: #f7fafc;
                padding: 25px;
                border-radius: 8px;
                margin-bottom: 40px;
                page-break-inside: avoid;
                page-break-after: always;
            }
            
            /* Code blocks */
            pre, code {
                background: #f7fafc;
                padding: 12px;
                border-radius: 4px;
                font-family: monospace;
                page-break-inside: avoid;
            }
        ''')
        
        # Generate PDF
        pdf_bytes = HTML(string=html_content).write_pdf(stylesheets=[pdf_css])
        
        # Create file-like object
        pdf_file = io.BytesIO(pdf_bytes)
        pdf_file.seek(0)
        
        # Log analytics
        log_analytics('pdf_generated', {
            'html_length': len(html_content),
            'pdf_size': len(pdf_bytes)
        })
        
        # Return PDF file
        return send_file(
            pdf_file,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='BulWise-AI-Stack-Report.pdf'
        )
        
    except Exception as e:
        print(f"PDF Generation Error: {e}")
        return jsonify({
            "success": False,
            "error": f"Failed to generate PDF: {str(e)}"
        }), 500


if __name__ == '__main__':
    # For local development
    app.run(debug=True, host='0.0.0.0', port=5000)
