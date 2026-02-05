import os
from dotenv import load_dotenv
import anthropic

load_dotenv()

api_key = os.getenv('ANTHROPIC_API_KEY')
print(f"API Key encontrada: {api_key[:20]}...{api_key[-10:]}")

client = anthropic.Anthropic(api_key=api_key)

# Intentar una llamada simple sin Vision
try:
    print("\nProbando llamada simple sin Vision...")
    response = client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=100,
        messages=[{
            "role": "user",
            "content": "Di solo 'OK' si me recibes."
        }]
    )
    print(f"Respuesta: {response.content[0].text}")
    print("✓ API Key funciona correctamente")
except Exception as e:
    print(f"✗ Error: {e}")
