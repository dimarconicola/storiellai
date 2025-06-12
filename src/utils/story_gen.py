from llama_cpp import Llama

def generate_story(
    character="un personaggio",
    location="un luogo",
    topic="un tema",
    tone="neutro",
    energy=3,
    length=180,
    blocked_words=None,
    age=5,
    prompt_override=None,
):
    # ---- Prompt ---------------------------------------------------------
    if prompt_override:
        prompt = prompt_override
    else:
        prompt = (
            f"Racconta una fiaba per bambini. Protagonista: {character}. "
            f"Luogo: {location}. Tema: {topic}. Tono: {tone}. "
        )
        if blocked_words:
            prompt += f"Non usare queste parole: {', '.join(blocked_words)}. "
        prompt += "C'era una volta"

    print("Prompt:", prompt)

    # ---- Llama ----------------------------------------------------------
    llm = Llama(
        model_path="/Users/nicoladimarco/code/storellai-1/models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
        n_ctx=512,
    )

    # Stima grezza: 1 parola ≈ 0.75 token (dipende dalla lingua)
    max_tokens = min(int(length * 1.3), 512 - 50)  # 50 token di margine per il prompt
    output = llm(prompt, max_tokens=max_tokens)

    # ---- Parsing --------------------------------------------------------
    try:
        story = output["choices"][0]["text"].strip()
        if not story:
            raise ValueError("Empty story")
        return story
    except Exception as e:
        print(f"LLM error: {e}")
        return (
            "C'era una volta un personaggio speciale che non vedeva l'ora "
            "di vivere una nuova avventura."
        )

if __name__ == "__main__":
    print(
        generate_story(
            character="un coniglio",
            location="nel prato",
            topic="amicizia",
            tone="allegro",
            energy=3,
            length=50,
        )
    )
