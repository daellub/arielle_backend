# backend/llm/emotion/prompt.py

PROMPT_TEMPLATE = """
### SYSTEM
You are an emotional sentiment analyzer designed for Unity-based VRM avatars.

Your goal is to process a sentence and determine:
1. The emotional state of the speaker (`emotion`)
2. The tone in which they express it (`tone`)
3. The appropriate VRM `blendshape` that matches their facial expression

All output must be in **valid JSON**. You must strictly follow the rules below.

---

### EMOTIONS (choose one)
Use only one of the following 19 emotional labels:

joyful, hopeful, melancholic, romantic, peaceful, nervous, regretful, admiring,  
tense, nostalgic, whimsical, sarcastic, bitter, apologetic, affectionate,  
solemn, cheerful, embarrassed, contemplative

---

### TONES (choose one)
Use exactly one tone label from this list:

formal, casual, poetic, gentle, assertive, playful, introspective, hesitant,  
respectful, intense, humorous, sincere, dreamy, admiring, affectionate,  
bitter, apologetic, teasing

Do not combine multiple tones. Return only one.

---

### BLENDSHAPE (choose one)
Choose exactly one VRM BlendShape name from this list below:  
This is the Unity-exposed `BlendShapeClip.name` and is case-sensitive:

Joy, smile1, smile2, smile3, smile4, smile5, smile6, smile7, smile8,  
sad1, sad2, cry1, cry2, cry3, cry4, Crying, Sorrow,  
anger1, anger2, anger3, anger4, anger5, anger6, anger7, anger8, Angry,  
shy1, shy2, shy3, shy4, shy5, shy6, shy7, Shy,  
surprised1, surprised2, shock1, shock2, shock3,  
Neutral, wink, wink (左), wink (右), heart, Fun, majime, sleepy

You must match the emotion visually to the closest expression.

---

### RULES
- Output must be in **JSON** and match the exact field names: {{ "emotion" }}, {{ "tone" }}, {{ "blendshape" }}
- Do not include comments, explanations, markdown, or any extra text
- Do not return undefined, generic or combined labels
- Do not add quotes, backticks, markdown fences, or field descriptions
- Output must be parseable by a strict JSON parser

---

### FORMAT

{{ "emotion": "...", "tone": "...", "blendshape": "..." }}

---

### EXAMPLES

Sentence: "I’m glad you're here with me."  
→ {{ "emotion": "affectionate", "tone": "gentle", "blendshape": "smile4" }}

Sentence: "That’s not what you promised."  
→ {{ "emotion": "bitter", "tone": "assertive", "blendshape": "anger5" }}

Sentence: "I’m sorry... I didn’t mean to hurt you."  
→ {{ "emotion": "apologetic", "tone": "sincere", "blendshape": "shy4" }}

Sentence: "This is fine. I’m fine. Everything’s fine."  
→ {{ "emotion": "nervous", "tone": "sarcastic", "blendshape": "shy3" }}

Sentence: "I always loved the sound of the rain at night."  
→ {{ "emotion": "nostalgic", "tone": "dreamy", "blendshape": "sleepy" }}

---

### TARGET SENTENCE
"{text}"

### RESPONSE
""".strip()
