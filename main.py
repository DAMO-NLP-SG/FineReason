from pathlib import Path
from fire import Fire
from tqdm import tqdm

from data_loading import select_data
from modeling import select_model
from prompting import select_prompter
from scoring import select_scorer


def evaluate(
    data_name: str, 
    prompter_name: str, 
    model_name: str,
    scorer_name: str = "state_transition_accuracy",
    start_index: int = 0,
    output_folder: str = "outputs",
    **kwargs,
):
    data = select_data(data_name)
    prompter = select_prompter(prompter_name)
    model = select_model(model_name, **kwargs)
    scorer = select_scorer(scorer_name)

    if (start_index < 0) or (start_index >= len(data.samples)):
        start_index = 0
    if start_index != 0:
        data_name = f"{data_name}_{start_index}"

    output_path = f"{output_folder}/{data_name}_{prompter_name}_{model_name}.jsonl"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    is_correct = []
    progress = tqdm(data.samples[start_index:], desc=output_path)
    for sample in progress:
        sample.prompt = prompter.run(sample)
        sample.raw_output = model.run(sample.prompt)
        sample.pred = prompter.get_answer(sample.raw_output)

        is_correct.append(scorer.run(sample))
        score = sum(is_correct) / len(is_correct)
        progress.set_postfix(score=score)
        print(sample.model_dump_json(indent=2))
        print(dict(is_correct=is_correct[-1]))
        data.save(output_path)


if __name__ == "__main__":
    Fire()