from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

model_name = "sshleifer/distilbart-cnn-12-6"

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)


def generate_summary(text):
    if not text:
        return "No abstract available"

    # Lower the threshold to 100 characters so more papers get summarized
    if len(text) < 100:
        return text

    inputs = tokenizer(
        text[:1024], # Hard limit to 1024 to prevent crash
        max_length=1024,
        truncation=True,
        return_tensors="pt"
    )

    summary_ids = model.generate(
        inputs["input_ids"],
        max_length=80,  # Shorter max length for punchier summaries
        min_length=20,  # Allow shorter summaries
        length_penalty=1.0, # Reduced penalty
        num_beams=2, # Reduced beams for speed
        early_stopping=True
    )

    return tokenizer.decode(summary_ids[0], skip_special_tokens=True)