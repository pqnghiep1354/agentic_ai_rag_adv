#!/bin/bash
# Script to pull Vistral model after Ollama service is up

echo "🔍 Waiting for Ollama service to be ready..."

# Wait for Ollama to be healthy
until docker-compose exec -T ollama curl -f http://localhost:11434/api/tags &>/dev/null; do
    echo "⏳ Ollama is not ready yet... waiting 5s"
    sleep 5
done

echo "✅ Ollama is ready!"
echo "📦 Pulling Vistral 7B Q4_K_M model (this will take 5-10 minutes)..."

# Pull the model
docker-compose exec -T ollama ollama pull vistral:7b-chat-q4_K_M

echo "✅ Vistral model pulled successfully!"
echo "🧪 Testing model..."

# Test if model is available
docker-compose exec -T ollama ollama list

echo "✅ Setup complete! You can now use the model."
