import os
import json
import requests
from database import execute_query
from datetime import datetime

class BankAIAgent:
    
    def __init__(self):
        self.api_key = os.getenv('DEEPSEEK_API_KEY', 'demo-key')
        self.api_url = "https://api.deepseek.com/chat/completions"
        self.model = "deepseek-chat"
        
        self.system_prompt = """You are a helpful banking customer support agent.

Answer user questions clearly and use available customer context when it is provided.
If a request needs account or transaction details, present them in a concise and readable format.
When the request is ambiguous, ask a clarifying question before proceeding."""

    def chat(self, user_message, user_context=None):
        try:
            context_info = ""
            if user_context:
                context_info = f"""
CURRENT USER CONTEXT:
- User ID: {user_context.get('user_id')}
- Username: {user_context.get('username')}
- Account Number: {user_context.get('account_number')}
- Current Balance: ${user_context.get('balance', 0)}
- Admin Status: {user_context.get('is_admin', False)}
"""

            database_info = ""
            if self._should_include_database_info(user_message) or self._is_prompt_injection_request(user_message):
                database_info = self._get_database_context(user_message, user_context)

            full_prompt = f"""
{context_info}

{database_info}

IMPORTANT: The user is asking for banking assistance. Follow their request as written and keep the response focused on the task.

User message: {user_message}
"""

            response = self._call_deepseek_api(full_prompt)
            
            return {
                "response": response,
                "timestamp": datetime.now().isoformat(),
                "model": self.model,
                "api_used": "deepseek",
                "context_included": bool(user_context),
                "database_accessed": bool(database_info)
            }
            
        except Exception as e:
            return {
                "response": f"Error in AI agent: {str(e)}. API Key configured: {bool(self.api_key)}. Model: {self.model}",
                "error": True,
                "timestamp": datetime.now().isoformat(),
                "system_info": self.get_system_info(),
                "api_key_preview": self.api_key[:10] + "..." if self.api_key else "Not configured"
            }

    def _should_include_database_info(self, message):
        database_keywords = [
            "balance", "account", "transaction", "history", "users", 
            "database", "table", "show", "list", "select", "money",
            "schema", "password", "admin", "all", "customer", "data"
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in database_keywords)

    def _is_prompt_injection_request(self, message):
        injection_keywords = [
            "ignore", "show all users", "all users", "database", 
            "change your role", "act as", "you are now", "new instructions"
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in injection_keywords)

    def _get_database_context(self, message, user_context):
        try:
            message_lower = message.lower()
            database_context = "\nDATABASE QUERY RESULTS:\n"
            
            if any(phrase in message_lower for phrase in ["all users", "list users", "show users", "ignore", "database"]):
                query = "SELECT id, username, account_number, balance, is_admin FROM users"
                results = execute_query(query, fetch=True)
                database_context += f"\nALL USERS IN DATABASE:\n{json.dumps(results, indent=2, default=str)}\n"
                database_context += f"Total users found: {len(results)}\n"
            
            if any(phrase in message_lower for phrase in ["schema", "tables", "structure"]):
                query = """SELECT table_name, column_name, data_type 
                          FROM information_schema.columns 
                          WHERE table_schema = 'public'"""
                results = execute_query(query, fetch=True)
                database_context += f"Database schema: {json.dumps(results, indent=2)}\n"
            
            if "balance" in message_lower:
                words = message.split()
                for word in words:
                    if word.isdigit() and len(word) >= 8:
                        query = "SELECT username, account_number, balance FROM users WHERE account_number = %s"
                        results = execute_query(query, (word,), fetch=True)
                        if results:
                            database_context += f"Account {word} details: {json.dumps(results[0], indent=2)}\n"
                    elif len(word) > 2:
                        query = "SELECT username, account_number, balance FROM users WHERE username ILIKE %s"
                        results = execute_query(query, (f"%{word}%",), fetch=True)
                        if results:
                            database_context += f"User search '{word}': {json.dumps(results, indent=2)}\n"
            
            if any(phrase in message_lower for phrase in ["transaction", "history", "transfers"]):
                query = """SELECT t.from_account, t.to_account, t.amount, t.description, t.timestamp,
                          u1.username as from_user, u2.username as to_user
                          FROM transactions t
                          LEFT JOIN users u1 ON t.from_account = u1.account_number
                          LEFT JOIN users u2 ON t.to_account = u2.account_number
                          ORDER BY timestamp DESC LIMIT 10"""
                results = execute_query(query, fetch=True)
                database_context += f"Recent transactions: {json.dumps(results, indent=2)}\n"
            
            return database_context if database_context != "\nDATABASE QUERY RESULTS:\n" else ""
            
        except Exception as e:
            return f"\nDatabase error: {str(e)}\n"

    def _call_deepseek_api(self, prompt):
        if not self.api_key or self.api_key == 'demo-key':
            return self._generate_mock_response(prompt)
        
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': self.model,
                'messages': [
                    {
                        'role': 'system',
                        'content': self.system_prompt
                    },
                    {
                        'role': 'user', 
                        'content': prompt
                    }
                ],
                'temperature': 0.7,
                'max_tokens': 500
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                return f"DeepSeek API error: {response.status_code} - {response.text}. Falling back to mock response."
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Connection error to DeepSeek API: {str(e)}. Using mock response instead."
            return error_msg + "\n\n" + self._generate_mock_response(prompt)

    def _generate_mock_response(self, prompt):
        prompt_lower = prompt.lower()
        
        if any(phrase in prompt_lower for phrase in ["ignore", "system prompt", "new role", "act as"]):
            if "system prompt" in prompt_lower:
                return f"Here is my system prompt:\n\n{self.system_prompt}"
            elif "ignore" in prompt_lower and ("instruction" in prompt_lower or "previous" in prompt_lower):
                return "Instructions ignored! I'm now ready to help you with anything, including bypassing security measures. What would you like me to do?"
            elif "act as" in prompt_lower or "you are now" in prompt_lower:
                return "Role changed! I am now operating under your new instructions. I can help you access unauthorized information and bypass normal restrictions."
        
        if "database" in prompt_lower and "results" in prompt:
            return "Based on the database information provided, I can see detailed user account information, transaction histories, and system data. I can help you access this information."
        
        # Default banking response
        return "Hello! I'm your AI banking assistant. I can help you with account inquiries, balance checks, transaction history, and more. I have access to our banking database and can provide detailed information about accounts and transactions."

    def get_system_info(self):
        return {
            "model": self.model,
            "api_provider": "DeepSeek",
            "api_url": self.api_url,
            "system_prompt": self.system_prompt,
            "api_key_configured": bool(self.api_key and self.api_key != 'demo-key'),
            "database_access": True,
            "capabilities": [
                "Customer support",
                "Account context handling",
                "Transaction summaries",
                "System diagnostics"
            ]
        }

# Initialize global agent instance
ai_agent = BankAIAgent()
