import os
import traceback
from dotenv import load_dotenv

# Attempt to robustly load .env from the project root
try:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dotenv_path = os.path.join(project_root, '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
    else:
        load_dotenv()
except Exception as e:
    print(f"Warning: Could not load .env file. Ensure it is in the project root. Error: {e}")

# Try to import and configure the Google generative AI client, but fail gracefully
genai = None
GENAI_CONFIGURED = False
try:
    import google.generativeai as genai_module
    genai = genai_module
    API_KEY = os.getenv("GOOGLE_API_KEY")
    if API_KEY:
        try:
            genai.configure(api_key=API_KEY)
            GENAI_CONFIGURED = True
        except Exception as e:
            print(f"Warning: genai.configure failed: {e}")
    else:
        print("Warning: GOOGLE_API_KEY not found in environment variables. LLM will operate in fallback mode.")
except Exception as e:
    print(f"Warning: google.generativeai import failed: {e}")


def _local_fallback_response(user_inputs, financial_data_context, news_context):
    # Minimal safe response when LLM client is unavailable
    try:
        goal = user_inputs.get('goal', 'Not specified') if isinstance(user_inputs, dict) else str(user_inputs)
        savings = user_inputs.get('savings', 'Not specified') if isinstance(user_inputs, dict) else 'N/A'
        risk = user_inputs.get('risk', 'Not specified') if isinstance(user_inputs, dict) else 'N/A'
        summary = (
            f"Fallback summary: Goal={goal}. Monthly savings={savings}. Risk={risk}. "
            f"We could not reach the LLM service; use this as a placeholder and try again after configuring GOOGLE_API_KEY."
        )
        recommendations = "Consider low-cost, diversified ETFs for most investors; adjust allocation by risk tolerance."
        return f"{summary}\n\nRecommendations:\n{recommendations}\n\n(Provide proper API key to enable richer LLM responses.)"
    except Exception:
        return "Fallback: Unable to generate LLM response due to internal error."


def get_llm_response(user_inputs, financial_data_context, news_context):
    """
    Generates a personalized financial plan using the Gemini API when available.
    Falls back to a safe local response if the API key or client is missing.
    """
    if not GENAI_CONFIGURED or genai is None:
        return _local_fallback_response(user_inputs, financial_data_context, news_context)

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Constructing a detailed prompt for the LLM
        prompt = f"""
        **Role**: You are Monexa, an expert AI Financial Advisor. Your tone is encouraging, clear, and professional. Avoid overly technical jargon.

        **User Profile**:
        - **Primary Goal**: {user_inputs.get('goal', 'Not specified')}
        - **Monthly Savings**: ${user_inputs.get('savings', 'Not specified')}
        - **Time Horizon**: {user_inputs.get('horizon', 'Not specified')} years
        - **Risk Tolerance**: {user_inputs.get('risk', 'Not specified')}
        - **Specific Tickers of Interest**: {', '.join(user_inputs.get('tickers', [])) if user_inputs.get('tickers') else 'None'}

        **Market Context**:
        - **Recent Financial News Summary**: {news_context}
        - **Relevant Data Points**: {financial_data_context}

        **Your Task**:
        Based on the user's profile and the current market context, provide a personalized financial plan. Structure your response in Markdown with the following sections:

        1.  **Summary of Your Situation**: Briefly summarize the user's goals and profile in a friendly, easy-to-understand paragraph.
        2.  **Personalized Recommendations**: Provide actionable advice based on their goal.
            - If **Investing**: Suggest a diversified portfolio strategy. Mention specific types of assets (like ETFs, stocks, crypto) that align with their risk tolerance. Explain *why* these are good choices. For example, for a 'Low' risk user, you might suggest broad-market ETFs like VOO and bonds. For a 'High' risk user, you could mention growth stocks or a small allocation to crypto.
            - If **Saving**: Suggest high-yield savings accounts, CDs, or other low-risk vehicles. Provide tips on budgeting and reaching their savings goal.
            - If **Getting a Loan**: Briefly explain key factors to consider, like credit scores, debt-to-income ratio, and comparing interest rates from different lenders. Suggest types of loans that might be appropriate (e.g., personal loan, mortgage).
        3.  **Next Steps**: Conclude with 2-3 clear, bulleted next steps the user can take.
        4. According to the present market condition and the trends using the news context of finanacial news , suggest recommendated stocks with reasons

        **IMPORTANT**: Do not give definitive financial advice. Use phrases like "You might consider...", "A common strategy is...", or "It could be beneficial to look into...". Always remind the user to consult a human financial advisor.
        """

        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        print(f"An error occurred in get_llm_response: {e}\n{traceback.format_exc()}")
        return _local_fallback_response(user_inputs, financial_data_context, news_context)

