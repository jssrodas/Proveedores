import os
from dotenv import load_dotenv
import anthropic

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

# Probar diferentes modelos
models_to_test = [
    "claude-3-5-sonnet-20241022",
    "claude-3-opus-20240229",  
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307"
]

print("Probando modelos disponibles...\n")

for model in models_to_test:
    try:
        print(f"Probando: {model}... ", end="")
        response = client.messages.create(
            model=model,
            max_tokens=50,
            messages=[{"role": "user", "content": "Di OK"}]
        )
        print(f"✓ FUNCIONA - Respuesta: {response.content[0].text}")
        print(f"   >> USAR ESTE: {model}\n")
        break
    except Exception as e:
        error_type = str(e).split("'type': '")[1].split("'")[0] if "'type':" in str(e) else "unknown"
        print(f"✗ Error: {error_type}")

print("\nSi ninguno funcionó, la cuenta podría tener restricciones de acceso.")
