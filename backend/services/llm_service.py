import ollama

class LLMService:
    def __init__(self):
        self.default_model = "llama3.1:8b"

    def chat(self, message: str, model: str = None, system_prompt: str = None) -> str:
        if model is None:
            model = self.default_model
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": message})

        try:
            response = ollama.chat(
                model=model,
                messages=messages
            )
            return response["message"]["content"]
        except Exception as e:
            print(f"LLM Error: {e}")
            raise e

    def list_models(self):
        return ollama.list()

    def extract_information(self, text: str, model: str = None) -> dict:
        """
        Extract user profile information and goals from text using LLM.
        Expected format: JSON
        """
        if model is None:
            model = self.default_model

        prompt = f"""
        Analyze the following text and extract information to build a memory of the user.
        
        Text to analyze:
        "{text}"

        Extract:
        1. User Profile: Permanent facts about the user (name, personality, likes, dislikes, skills, jobs, relationships).
        2. Goals: Specific objectives the user wants to achieve (including deadline and priority if mentioned).

        Return ONLY a raw JSON object (no markdown formatting, no explanations) with the following structure:
        {{
            "user_profile": [
                {{"key": "short_key_name", "value": "fact content", "category": "category_name"}}
            ],
            "goals": [
                {{"title": "goal title", "description": "details", "deadline": "YYYY-MM-DD or null", "priority": "low/medium/high"}}
            ]
        }}
        
        If no relevant information is found, return empty lists.
        Example categories: 'personal', 'work', 'hobby', 'preference'.
        """

        try:
            response = ollama.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                format="json" # Ollama supports json mode for some models
            )
            content = response["message"]["content"]
            import json
            return json.loads(content)
        except Exception as e:
            print(f"Extraction Error: {e}")
            return {"user_profile": [], "goals": []}
