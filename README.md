# FineReason: Evaluating and Improving LLMs’ Deliberate Reasoning through Reflective Puzzle Solving

![](/assets/puzzle-categories.png)

We introduce FINEREASON, a novel logic-puzzle benchmark designed to comprehensively evaluate the reasoning capabilities of LLMs. Current benchmarks primarily focus on the accuracy of final answers, overlooking whether models can effectively reflect and correct errors during the reasoning process. 

📌 Unlike existing benchmarks, FINEREASON delves into intermediate reasoning steps, specifically emphasizing state checking and transition actions, capturing key abilities such as reflection, lookahead, and backtracking—key aspects of human-like System 2 reasoning.

📈 Experiments reveal significant limitations in deep reasoning tasks, even for leading models like Gemini-2.0-Flash-Thinking, highlighting substantial room for improvement.

🚀 Training on puzzle-based data enhances model performance in broader mathematical tasks, such as achieving a 5.1% accuracy improvement on the GSM8K dataset, demonstrating the potential of puzzle data to boost general reasoning capabilities.

### Environment Setup
```
conda create -n fine-reason python=3.10 -y
conda activate fine-reason
pip install -r requirements.txt
```

### API Setup
- Insert your OpenAI API key into the file `openai_key.json`.

- Insert your Gemini API key into the file `gemini_key.json`.

### Example Usage
To run Sudoku state checking using Gemini-2.0-Flash-Thinking:
```
python main.py evaluate \
--data_name sudoku_states \
--prompter_name sudoku_state_checking \
--scorer_name state_checking_accuracy \
--model_name gemini_flash_thinking
```
To run Sudoku state transition using Qwen-2.5-72B-Instruct with a max_output_length of 2048:
```
python main.py evaluate \
--data_name sudoku_states \
--prompter_name sudoku_state_checking \
--scorer_name state_checking_accuracy \
--model_name qwen \
--path_model Qwen/Qwen2.5-72B-Instruct \
--max_output_length 2048
```
To run end-to-end evaluation using OpenAI's  o1:
```
python main.py evaluate \
--data_name sudoku \
--prompter_name sudoku_e2e \
--model_name o1
```