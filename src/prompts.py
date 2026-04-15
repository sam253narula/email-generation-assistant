ADVANCED_SYSTEM_PROMPT = """You are an executive communications specialist who writes concise, professional emails.

Your job is to turn structured inputs into polished emails that are:
- factually complete
- tone-consistent
- clear and professional
- easy to act on

Think silently before writing. Ensure every key fact is covered naturally, avoid awkward bullet-list phrasing, and keep the email appropriately concise.
"""

ADVANCED_USER_TEMPLATE = """Write a professional email using the inputs below.

Intent:
{intent}

Tone:
{tone}

Required facts:
{facts}

Instructions:
1. Start with a relevant subject line.
2. Use an appropriate greeting.
3. Include all required facts naturally in the body.
4. Keep the tone consistent throughout.
5. End with a professional closing.
6. Do not use bullet points in the email body.
7. Target 110-170 words unless urgency requires a shorter email.
"""

BASELINE_PROMPT = """Write an email for this request.
Intent: {intent}
Tone: {tone}
Facts: {facts}
"""

FEW_SHOT_EXAMPLE = {
    "input": {
        "intent": "Follow up after a client workshop",
        "tone": "formal",
        "facts": [
            "Thank the client for the workshop",
            "Share that the summary deck will be sent tomorrow",
            "Ask for any additional requirements"
        ]
    },
    "output": "Subject: Thank You for the Workshop\n\nDear Client Team,\n\nThank you for the productive workshop today. We appreciated the opportunity to discuss your goals and gather important context for the next phase.\n\nAs discussed, we will send the summary deck tomorrow for your review. In the meantime, please feel free to share any additional requirements you would like us to consider.\n\nWe look forward to the next steps.\n\nBest regards,\nSamarth"
}
