from unsloth import FastLanguageModel
from unsloth import UnslothTrainer, UnslothTrainingArguments
from datasets import load_dataset

model, tokenizer = FastLanguageModel.from_pretrained(
    "unsloth/gemma-4-E2B-it-unsloth-bnb-4bit",
    max_seq_length=2048,
    load_in_4bit=True,
    dtype=None,
)

model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    lora_alpha=16,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=42,
)

dataset = load_dataset("json", data_files="sar_dataset.jsonl", split="train")

def format_prompt(example):
    return {"text": f"<start_of_turn>user\n{example['prompt']}<end_of_turn>\n<start_of_turn>model\n{example['completion']}<end_of_turn>"}

dataset = dataset.map(format_prompt)

trainer = UnslothTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=2048,
    args=UnslothTrainingArguments(
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        warmup_steps=5,
        num_train_epochs=3,
        learning_rate=2e-4,
        fp16=True,
        logging_steps=10,
        output_dir="sar_model_output",
        optim="adamw_8bit",
    ),
)

trainer.train()

model.save_pretrained_gguf(
    "sar_drone_e4b",
    tokenizer,
    quantization_method="q4_k_m"
)
