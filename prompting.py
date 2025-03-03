import ast
import re
import sympy
from fire import Fire
from pydantic import BaseModel

from data_loading import Sample, select_data
from sudoku_tree import SudokuTree
from graphcoloring_tree import GraphColoringTree
from game24_tree import GameOf24Tree
from gridpuzzle_tree import LogicGridPuzzleTree


class Prompter(BaseModel):
    def run(self, sample: Sample) -> str:
        raise NotImplementedError


class SudokuEndToEndPrompter(Prompter):
    solution: list = []
    def run(self, sample: Sample) -> str:
        instruction = "You are given a 9x9 Sudoku grid represented as a list of lists, where empty cells are represented as 0. Your task is to fill the empty cells, ensuring that each row, column, and 3x3 subgrid contains unique numbers from 1 to 9."
        initial_grid = sample.inputs["initial"]
        solution = sample.outputs["final"]
        self.solution = solution
        anser_format = "End your answer with \"Solution: \{grid\}\" where grid is in the same format as the Initial Grid."
        return f"{instruction}\nInitial Grid: {initial_grid}\nLet's think step by step. Do not solve using programming.\n{anser_format}"
    
    def get_answer(self, raw: str) -> str:
        raw = raw.split("Solution:")[-1]
        try:
            pattern = r'\[(\d,\s*\d,\s*\d,\s*\d,\s*\d,\s*\d,\s*\d,\s*\d,\s*\d)\]'
            matches = re.findall(pattern, raw)[-9:]
            result = []
            for match in matches:
                integer_list = [int(x.strip()) for x in match.split(',')]
                result.append(integer_list)
            if result == self.solution:
                return "1"
            return "0"
        except:
            return "parsing error"


class SudokuStateCheckingPrompter(Prompter):
    def run(self, sample: Sample) -> str:
        instruction = "You are given a partially filled 9x9 Sudoku grid represented as a list of lists, where empty cells are represented as 0. Your task is to determine if this current state can lead to a solvable solution. Specifically, use lookahead techniques to determine if it's possible to fill the remaining cells according to standard Sudoku rules, ensuring that each row, column, and 3x3 subgrid contains unique numbers from 1 to 9."
        extra_information = "Additionally, you are provided with a previously explored next state that has been proven to be unsolvable. Use this information to avoid revisiting this failed path and leverage it to make a more informed decision about the current state."
        output_format = '''Let's think step by step, considering the failed state to avoid unnecessary exploration. Do not solve using programming.\nChoose from (A) Solvable (B) Unsolvable. End your answer with "Answer: (A)" or "Answer: (B)".'''
        current_state = sample.inputs["current"]
        unsolvable_child = sample.inputs["unsolvable_child"]
        return f"{instruction}\n{extra_information}\nCurrent state:\n{current_state}\nExplored next state that leads to an unsolvable path:\n{unsolvable_child}\n{output_format}"
    
    def get_answer(self, raw: str) -> str:
        letters = "AB"
        matches = re.findall(f"\(([{letters}])\)", raw)
        if matches:
            if matches[-1] == "A":
                return "Solvable"
            elif matches[-1] == "B":
                return "Unsolvable"

        answer = raw.split("Answer:")[-1]
        if "Solvable" in answer:
            return "Solvable"
        elif "Unsolvable" in answer:
            return "Unsolvable"
        elif "A" in answer:
            return "Solvable"
        elif "B" in answer:
            return "Unsolvable"

        return raw


class SudokuStateTransitionPrompter(Prompter):
    parent_state: list = []
    current_state: list = []
    unsolvable_child: list = []
    current_status: str = ""
    def run(self, sample: Sample) -> str:
        instruction = "You are given an initial Sudoku puzzle S(0), followed by a sequence of progressive states leading to the current state S(i). Alongside each state, its solvability status L(*) is given. Your task is to determine the next state by making exactly one move, ensuring progress toward a valid solution. A valid Sudoku solution requires that each row, column, and 3x3 subgrid contains the numbers 1 to 9 without repetition."
        move_definition = "**A move is defined as either:**\n"
        move_definition += "1. Filling: Replacing a 0 in exactly one empty cell with a value from 1 to 9.\n"
        move_definition += "2. Removing: Replacing a value in exactly one filled cell with 0."
        extra_information = "Additionally, you are provided with a previously explored next state that has been proven to be unsolvable. Use this information to avoid revisiting this failed path."
        initial_state = sample.inputs["initial"]
        grandparent_state = sample.inputs["grandparent"]
        parent_state = sample.inputs["parent"]
        current_state = sample.inputs["current"]
        current_status = sample.outputs["current_status"]
        unsolvable_child = sample.inputs["unsolvable_child"]
        self.parent_state = parent_state
        self.current_state = current_state
        self.current_status = current_status
        self.unsolvable_child = unsolvable_child
        output_format = '''Let's think step by step. Analyze the progress made so far and determine the immediate next move. End your answer with \"Next state: \{grid\}\", where \{grid\} is in the same python list format as the previous states.'''
        full_prompt = f"{instruction}\n"
        full_prompt += f"{extra_information}\n"
        full_prompt += f"{move_definition}\n"
        full_prompt += f"**Initial puzzle:**\nS(0) = {initial_state}\nL(0) = Solvable\n"
        full_prompt += f"**Two moves ago:**\nS(i-2) = {grandparent_state}\nL(i-2) = Solvable\n"
        full_prompt += f"**One move ago:**\nS(i-1) = {parent_state}\nL(i-1) = Solvable\n"
        full_prompt += f"**Current state:**\nS(i) = {current_state}\nL(i) = {current_status}\n"
        full_prompt += f"**Explored next state:**\nS(i+1) = {unsolvable_child}\nL(i+1) = Unsolvable\n"
        full_prompt += f"{output_format}"
        return full_prompt

    def get_answer(self, raw: str) -> str:
        raw = raw.split("Next state:")[-1]
        try:
            pattern = r'\[(\d,\s*\d,\s*\d,\s*\d,\s*\d,\s*\d,\s*\d,\s*\d,\s*\d)\]'
            matches = re.findall(pattern, raw)[-9:]
            result = []
            for match in matches:
                integer_list = [int(x.strip()) for x in match.split(',')]
                result.append(integer_list)

            # if the current state is unsolvable, the next state should be the parent state
            if self.current_status == "Unsolvable":
                if result == self.parent_state:
                    return "1"
                else:
                    sudoku_tree = SudokuTree(self.parent_state)
                    is_next_state = sudoku_tree.is_next_state(self.parent_state, result)
                    if is_next_state == "1":
                        return "sibling"
                    return "backtracking failure"

            # if the current state is solvable, the next state should be the current state
            else:
                sudoku_tree = SudokuTree(self.current_state)
                is_next_state = sudoku_tree.is_next_state(self.current_state, result)
                if is_next_state == "1":
                    if result != self.unsolvable_child:
                        return "1"
                    else:
                        return "unsolvable child"
                else:
                    return is_next_state

        except:
            return "parsing error"


class GraphColoringEndToEndPrompter(Prompter):
    graph: list = []
    chromatic_number: int = 0
    def run(self, sample: Sample) -> str:
        graph = sample.inputs["graph"]
        chromatic_number = sample.inputs["chromatic_number"]
        self.graph = graph
        self.chromatic_number = chromatic_number
        initial_state = [0] * len(graph)
        input_format = "You are given a graph represented as an adjacency list, where each index corresponds to a vertex, and the list at that index represents its adjacent vertices. You are also given the initial coloring state of the graph in a list, where each index represents the corresonding vertex, and the number at that index represents its color (0 indicates an uncolored vertex)."
        instruction = f"Your task is to color the vertices such that no two adjacent vertices share the same color, using no more than {chromatic_number} colors in total."
        output_format = "Let's think step by step. Do not solve using programming.\nEnd your answer with \"Solution: \{coloring\}\" where coloring is in the same format as the Initial Coloring."
        full_prompt = f"{input_format}\n"
        full_prompt += f"{instruction}\n"
        full_prompt += f"Graph: {graph}\n"
        full_prompt += f"Initial Coloring: {initial_state}\n"
        full_prompt += f"{output_format}"
        return full_prompt
    
    def get_answer(self, raw: str) -> str:
        raw = raw.split("Solution:")[-1]
        try:
            coloring = re.findall(r"\d+", raw)
            if not coloring:
                return "no coloring found"

            coloring = [int(x) for x in coloring]
            if len(coloring) != len(self.graph):
                return "invalid coloring"

            non_zero_colors = set()
            for color in coloring:
                if color != 0:
                    non_zero_colors.add(color)
            if len(non_zero_colors) > self.chromatic_number:
                return "too many colors"

            graph_coloring_tree = GraphColoringTree(self.graph, self.chromatic_number)
            if graph_coloring_tree.is_valid_coloring(coloring):
                return "1"
            return "0"

        except:
            return "parsing error"


class GraphColoringStateCheckingPrompter(Prompter):
    def run(self, sample: Sample) -> str:
        graph = sample.inputs["graph"]
        chromatic_number = sample.inputs["chromatic_number"]
        current_state = sample.inputs["current"]
        unsolvable_child = sample.inputs["unsolvable_child"]

        input_format = "You are given a graph represented as an adjacency list, where each index corresponds to a vertex, and the list at that index represents its adjacent vertices. You are also given the current coloring state of the graph in a list, where each index represents the corresonding vertex, and the number at that index represents its color (0 indicates an uncolored vertex)." 
        instruction = f"Your task is to determine if this current state can lead to a valid coloring. Specifically, use lookahead techniques to determine if it's possible to color the remaining vertices such that no two adjacent vertices share the same color, using no more than {chromatic_number} colors in total."
        extra_information = "Additionally, you are provided with a previously explored next state that has been proven to be uncolorable. Use this information to avoid revisiting this failed path and leverage it to make a more informed decision about the current state."
        output_format = '''Let's think step by step, considering the failed state to avoid unnecessary exploration. Do not solve using programming.\nChoose from (A) Colorable (B) Uncolorable. End your answer with "Answer: (A)" or "Answer: (B)".'''
        full_prompt = f"{input_format}\n"
        full_prompt += f"{instruction}\n"
        full_prompt += f"{extra_information}\n"
        full_prompt += f"**Graph adjacency list:**\n{graph}\n"
        full_prompt += f"**Current coloring state:**\n{current_state}\n"
        full_prompt += f"**Explored next state that leads to an uncolorable path:**\n{unsolvable_child}\n"
        full_prompt += f"{output_format}"
        return full_prompt

    def get_answer(self, raw: str) -> str:
        letters = "AB"
        matches = re.findall(f"\(([{letters}])\)", raw)
        if matches:
            if matches[-1] == "A":
                return "Solvable"
            elif matches[-1] == "B":
                return "Unsolvable"

        answer = raw.split("Answer:")[-1]
        if "Colorable" in answer:
            return "Solvable"
        elif "Uncolorable" in answer:
            return "Unsolvable"
        elif "A" in answer:
            return "Solvable"
        elif "B" in answer:
            return "Unsolvable"

        return raw


class GraphColoringStateTransitionPrompter(Prompter):
    graph: list = []
    chromatic_number: int = 0
    parent_state: list = []
    current_state: list = []
    unsolvable_child: list = []
    current_status: str = ""
    def run(self, sample: Sample) -> str:
        graph = sample.inputs["graph"]
        chromatic_number = sample.inputs["chromatic_number"]
        self.graph = graph
        self.chromatic_number = chromatic_number
        instruction = f"You are given a graph represented as an adjacency list, where each index corresponds to a vertex, and the list at that index represents its adjacent vertices. You are also given a sequence of partial coloring states leading to the current coloring state S(i). The coloring state is a list, where each index represents the corresonding vertex in the graph, and the number at that index represents its color (0 indicates an uncolored vertex). Alongside each state, its colorability status L(*) is given. Your task is to determine the next state by making exactly one move, ensuring progress toward a valid coloring with no more than {chromatic_number} colors. A valid coloring requires that no two adjacent vertices share the same color."
        extra_information = "Additionally, you are provided with a previously explored next state that has been proven to be uncolorable. Use this information to avoid revisiting this failed path."
        move_definition = "**A move is defined as either:**\n"
        move_definition += f"1. Coloring: Replacing a 0 in exactly one uncolored vertex with a value from 1 to {chromatic_number}.\n"
        move_definition += "2. Removing a color: Replacing a value in exactly one colored vertex with 0."
        grandparent_state = sample.inputs["grandparent"]
        parent_state = sample.inputs["parent"]
        current_state = sample.inputs["current"]
        current_status = "Colorable" if sample.outputs["current_status"] == "Solvable" else "Uncolorable"
        unsolvable_child = sample.inputs["unsolvable_child"]
        self.parent_state = parent_state
        self.current_state = current_state
        self.current_status = current_status
        self.unsolvable_child = unsolvable_child
        output_format = '''Let's think step by step. Analyze the progress made so far and determine the immediate next move. End your answer with \"Next state: \{coloring\}\", where \{coloring\} is in the same python list format as the previous states.'''
        full_prompt = f"{instruction}\n"
        full_prompt += f"{extra_information}\n"
        full_prompt += f"{move_definition}\n"
        full_prompt += f"**Graph adjacency list:**\n{graph}\n"
        full_prompt += f"**Two moves ago:**\nS(i-2) = {grandparent_state}\nL(i-2) = Colorable\n"
        full_prompt += f"**One move ago:**\nS(i-1) = {parent_state}\nL(i-1) = Colorable\n"
        full_prompt += f"**Current coloring state:**\nS(i) = {current_state}\nL(i) = {current_status}\n"
        full_prompt += f"**Explored next state:**\nS(i+1) = {unsolvable_child}\nL(i+1) = Uncolorable\n"
        full_prompt += f"{output_format}"
        return full_prompt

    def get_answer(self, raw: str) -> str:
        raw = raw.split("Next state:")[-1]
        coloring = re.findall(r"\d+", raw)
        if not coloring:
            return "no coloring found"

        coloring = [int(x) for x in coloring]
        if len(coloring) != len(self.graph):
            return "invalid coloring"

        non_zero_colors = set()
        for color in coloring:
            if color != 0:
                non_zero_colors.add(color)
        if len(non_zero_colors) > self.chromatic_number:
            return "too many colors"

        graph_coloring_tree = GraphColoringTree(self.graph, self.chromatic_number)
        if self.current_status == "Uncolorable":
            if coloring == self.parent_state:
                return "1"
            else:
                if graph_coloring_tree.is_next_state(self.parent_state, coloring) == "1":
                    return "sibling"
                else:
                    return "backtracking failure"
        else:
            is_next_state = graph_coloring_tree.is_next_state(self.current_state, coloring)
            if is_next_state == "1":
                if coloring != self.unsolvable_child:
                    return "1"
                else:
                    return "unsolvable child"
            else:
                return is_next_state


class Game24EndToEndPrompter(Prompter):
    numbers: list = []
    def run(self, sample: Sample) -> str:
        initial_state = sample.inputs["initial_state"]
        self.numbers = [int(num) for num in initial_state]

        input_format = "You are given four numbers for the Game of 24."
        instruction = f"Your task is to use basic arithmetic operations (+ - * /) to reach exactly 24. You must use each number exactly once."
        output_format = "Let's think step by step. Do not solve using programming.\nEnd your answer with \"Solution: expression\", e.g., \"Solution: 5 + 5 + 5 + 9 = 24\"."
        full_prompt = f"{input_format}\n"
        full_prompt += f"{instruction}\n"
        full_prompt += f"Numbers: {self.numbers}\n"
        full_prompt += f"{output_format}"
        return full_prompt
    
    def get_answer(self, raw: str) -> str:
        raw = raw = raw.split("**Solution:**")[-1].split("Solution:")[-1]
        try:
            expression = (
                raw.strip().split("=")[0]
            )
            expression = expression.replace("\\(", "").replace("\\[", "").replace("\\{", "").replace("\\times", "*").replace("\\div", "/")
            numbers = re.findall(r"\d+", expression)
            numbers = [int(x) for x in numbers]
            if sorted(numbers) != sorted(self.numbers):
                return "different numbers"

            return str(int(sympy.simplify(expression) == 24))
            
        except Exception as e:
            return "parsing error"


class Game24StateCheckingPrompter(SudokuStateCheckingPrompter):
    def run(self, sample: Sample) -> str:
        numbers = sample.inputs["initial_state"]
        current_state = sample.inputs["current"]
        unsolvable_child = sample.inputs["unsolvable_child"]
        input_format = "You are given four numbers and the current calculation state for the Game of 24." 
        instruction = "Your task is to determine if this current state can lead to a solvable solution. Specifically, use lookahead techniques to determine if the remaining numbers can be combined using basic arithmetic operations (+ - * /) to reach exactly 24. You must use each number exactly once."
        extra_information = "Additionally, you are provided with a previously explored next state that has been proven to be unsolvable. Use this information to avoid revisiting this failed path and leverage it to make a more informed decision about the current state."
        output_format = '''Let's think step by step, considering the failed state to avoid unnecessary exploration. Do not solve using programming.\nChoose from (A) Solvable (B) Unsolvable. End your answer with "Answer: (A)" or "Answer: (B)".'''

        full_prompt = f"{input_format}\n"
        full_prompt += f"{instruction}\n"
        full_prompt += f"{extra_information}\n"
        full_prompt += f"**Numbers:**\n{numbers}\n"
        full_prompt += f"**Current calculation state:**\n{current_state}\n"
        full_prompt += f"**Explored next state that leads to an unsolvable path:**\n{unsolvable_child}\n"
        full_prompt += f"{output_format}"
        return full_prompt


class Game24StateTransitionPrompter(Prompter):
    parent_state: list = []
    current_state: list = []
    unsolvable_child: list = []
    current_status: str = ""
    numbers: list = []
    def run(self, sample: Sample) -> str:
        initial_state = sample.inputs["initial_state"]
        grandparent_state = sample.inputs["grandparent"]
        parent_state = sample.inputs["parent"]
        current_state = sample.inputs["current"]
        current_status = sample.outputs["current_status"]
        unsolvable_child = sample.inputs["unsolvable_child"]
        self.parent_state = parent_state
        self.current_state = current_state
        self.current_status = current_status
        self.unsolvable_child = unsolvable_child
        self.numbers = [int(num) for num in initial_state]

        instruction = "You are given an initial Game of 24 configuration S(0), followed by a sequence of progressive states leading to the current state S(i). Alongside each state, its solvability status L(*) is given. Your task is to determine the next state by making exactly one move, ensuring progress toward a valid solution. A valid solution requires using each of the four initial numbers exactly once, using only basic arithmetic operations (+ - * /), and ultimately evaluating to 24."
        extra_information = "Additionally, you are provided with a previously explored next state that has been proven to be unsolvable. Use this information to avoid revisiting this failed path."
        move_definition = "**A move is defined as either:**\n"
        move_definition += "1. Applying an operation: Combining two expressions using a basic arithmetic operation (+ - * /), reducing the number of expressions by 1.\n"
        move_definition += "2. Reverting an operation: Removing the last operation applied to the expressions, increasing the number of expressions by 1."
        output_format = '''Let's think step by step. Analyze the progress made so far and determine the immediate next move. End your answer with \"Next state: \{expressions\}\", where \{expressions\} is in the same python list format as the previous states.'''
        full_prompt = f"{instruction}\n"
        full_prompt += f"{extra_information}\n"
        full_prompt += f"{move_definition}\n"
        full_prompt += f"**Initial configuration:**\nS(0) = {initial_state}\nL(0) = Solvable\n"
        if grandparent_state:
            full_prompt += f"**One move ago:**\nS(i-1) = {parent_state}\nL(i-1) = Solvable\n"
        full_prompt += f"**Current state:**\nS(i) = {current_state}\nL(i) = {current_status}\n"
        full_prompt += f"**Explored next state:**\nS(i+1) = {unsolvable_child}\nL(i+1) = Unsolvable\n"
        full_prompt += f"{output_format}"
        return full_prompt

    def get_answer(self, raw: str) -> str:
        raw = raw.split("Next state:")[-1]
        try:
            pattern = r"\[[^\]]*\]"
            match = re.findall(pattern, raw)[-1]
            result = ast.literal_eval(match)
            # Check if the next expressions contain all 4 numbers exactly once
            numbers = []
            for expression in result:
                numbers.extend(re.findall(r"\d+", expression))
            numbers = [int(num) for num in numbers]
            if sorted(numbers) != sorted(self.numbers):
                return "different numbers"

            game24_tree = GameOf24Tree(self.numbers)
            if self.current_status == "Unsolvable":
                if result == self.parent_state:
                    return "1"
                else:
                    if game24_tree.is_next_state(self.parent_state, result) == "1":
                        return "sibling"
                    return "backtracking failure"
            else:
                is_next_state = game24_tree.is_next_state(self.current_state, result)
                if is_next_state == "1":
                    if result != self.unsolvable_child:
                        return "1"
                    else:
                        return "unsolvable child"
                else:
                    return is_next_state
        except:
            return "parsing error"


class GridPuzzleEndToEndPrompter(Prompter):
    solution: list = []
    def run(self, sample: Sample) -> str:
        question = sample.inputs["question"]
        categories = sample.inputs["categories"]
        clues = sample.inputs["clues"]
        text_clues = []
        for num, value in clues.items():
            text = value["text"]
            text_clues.append(f"{num}. {text}")
        initial_state = sample.inputs["initial"]
        solution = sample.outputs["solution"]
        self.solution = solution

        input_format = "You are given a logic grid puzzle represented as a table, where each column corresponds to a specific category, and each row represents attributes of a distinct entry. Empty cells are represented as the empty string ('')."
        instruction = "Your task is to assign the attributes from categories based on the clues."
        output_format = "Let's think step by step. Do not solve using programming.\nEnd your answer with \"Solution: \{table\}\" where table is in the same format as the Initial Table."
        full_prompt = f"{input_format}\n"
        full_prompt += f"{instruction}\n"
        full_prompt += f"Question:\n{question}\n"
        full_prompt += f"Categories:\n{categories}\n"
        full_prompt += f"Clues:\n"
        for text in text_clues:
            full_prompt += f"{text}\n"
        full_prompt += f"Initial Table:\n{initial_state}\n"
        full_prompt += f"{output_format}"
        return full_prompt

    def get_answer(self, raw: str) -> str:
        raw = raw.split("Solution:")[-1]
        raw = raw.replace("\n", "")
        try:
            pattern = r"\[\s*\[.*?\]\s*\]"
            match = re.findall(pattern, raw, re.DOTALL)[-1]
            result = ast.literal_eval(match)
            if result == self.solution:
                return "1"
            else:
                return "0"
        except:
            return "parsing error"


class GridPuzzleStateCheckingPrompter(SudokuStateCheckingPrompter):
    def run(self, sample: Sample) -> str:
        question = sample.inputs["question"]
        categories = sample.inputs["categories"]
        clues = sample.inputs["clues"]
        text_clues = []
        for num, value in clues.items():
            text = value["text"]
            text_clues.append(f"{num}. {text}")
        initial_state = sample.inputs["initial"]
        intermediate_states = sample.inputs["initial_to_current"][1:-1]
        current_state = sample.inputs["current"]
        current_status = sample.outputs["current_status"]
        unsolvable_child = sample.inputs["unsolvable_child"]
        applied_clues = sample.inputs["applied_clues"]
        clue_applied_to_unsolvable_child = sample.inputs["clue_applied_to_unsolvable_child"]
        input_format = "You are given a partially filled logic grid puzzle represented as a table, where each column corresponds to a specific category, and each row represents attributes of a distinct entry. Empty cells are represented as the empty string ('')." 
        instruction = "Your task is to determine if this current state can lead to a solvable solution. Specifically, use lookahead techniques to determine if the current configuration can lead to a valid solution under standard logic puzzle constraints (each option in every category must only appear once and adhere to the given clues)."
        extra_information = "Additionally, you are provided with a previously explored next state that has been proven to be unsolvable. Use this information to avoid revisiting this failed path and leverage it to make a more informed decision about the current state."
        output_format = '''Let's think step by step, considering the failed state to avoid unnecessary exploration. Do not solve using programming.\nChoose from (A) Solvable (B) Unsolvable. End your answer with "Answer: (A)" or "Answer: (B)".'''

        full_prompt = f"{input_format}\n"
        full_prompt += f"{instruction}\n"
        full_prompt += f"{extra_information}\n"
        full_prompt += f"**Question:**\n{question}\n"
        full_prompt += f"**Categories:**\n{categories}\n"
        full_prompt += f"**Clues:**\n"
        for text in text_clues:
            full_prompt += f"{text}\n"
        full_prompt += f"**Initial state:**\nS(0) = {initial_state}\n"
        for i, state in enumerate(intermediate_states):
            full_prompt += f"**State {i+1}:**\n"
            full_prompt += f"Clue applied: {applied_clues[i]}\n"
            full_prompt += f"S({i+1}) = {state}\n"
        i = len(intermediate_states)
        full_prompt += f"**State {i+1} (Current state):**\n"
        full_prompt += f"Clue applied: {applied_clues[i]}\n"
        full_prompt += f"S({i+1}) = {current_state}\n"
        full_prompt += f"**Explored next state that leads to an unsolvable path:**\n"
        full_prompt += f"Clue applied: {clue_applied_to_unsolvable_child}\n"
        full_prompt += f"S({i+2}) = {unsolvable_child}\n"
        full_prompt += f"{output_format}"
        return full_prompt


class GridPuzzleStateTransitionPrompter(Prompter):
    initial_state: list = []
    parent_state: list = []
    current_state: list = []
    unsolvable_child: list = []
    current_status: str = ""
    applied_clues: list = []
    all_clues: dict = {}
    domain: dict = {}

    def run(self, sample: Sample) -> str:
        question = sample.inputs["question"]
        categories = sample.inputs["categories"]
        clues = sample.inputs["clues"]
        text_clues = []
        for num, value in clues.items():
            text = value["text"]
            text_clues.append(f"{num}. {text}")
        initial_state = sample.inputs["initial"]
        intermediate_states = sample.inputs["initial_to_current"][1:-1]
        parent_state = sample.inputs["initial_to_current"][-2]
        current_state = sample.inputs["current"]
        current_status = sample.outputs["current_status"]
        unsolvable_child = sample.inputs["unsolvable_child"]
        applied_clues = sample.inputs["applied_clues"]
        clue_applied_to_unsolvable_child = sample.inputs["clue_applied_to_unsolvable_child"]
        solution = sample.outputs["solution"]
        domains = {}
        headers = solution[0]  
        for col_index, column_name in enumerate(headers):
            unique_values = set()
            for row in solution[1:]:
                unique_values.add(row[col_index])
            domains[column_name] = sorted(unique_values)

        self.initial_state = initial_state
        self.parent_state = parent_state
        self.current_state = current_state
        self.current_status = current_status
        self.unsolvable_child = unsolvable_child
        self.applied_clues = applied_clues
        self.all_clues = clues
        self.domain = domains

        instruction = "You are given a logic grid puzzle represented as a table, where each column corresponds to a specific category, and each row represents attributes of a distinct entry. Empty cells are represented as the empty string (''). You are also given a sequence of progressive states from the initial state S(0) to the current state S(n). Alongside each state, its solvability status L(*) is provided. Your task is to determine the next state by making exactly one move, ensuring progress toward a valid solution. A valid solution requires that each option in every category appears only once, strictly following the given clues."
        extra_information = "Additionally, you are provided with a previously explored next state that has been proven to be unsolvable. Use this information to avoid revisiting this failed path."
        move_definition = "**A move is defined as either:**\n"
        move_definition += "1. Applying a clue: Filling the table with the values indicated by that clue, as long as it does not conflict with any existing clues or placed options.\n"
        move_definition += "2. Reverting a clue: Removing the last operation applied to the table."
        output_format = '''Let's think step by step. Analyze the progress made so far and determine the immediate next move. End your answer with \"Next state: \{table\}\", where \{table\} is in the same python list format as the previous states.'''
        full_prompt = f"{instruction}\n"
        full_prompt += f"{extra_information}\n"
        full_prompt += f"{move_definition}\n"
        full_prompt += f"**Question:**\n{question}\n"
        full_prompt += f"**Categories:**\n{categories}\n"
        full_prompt += f"**Clues:**\n"
        for text in text_clues:
            full_prompt += f"{text}\n"
        full_prompt += f"**Initial state:**\nS(0) = {initial_state}\nL(0) = Solvable\n"
        for i, state in enumerate(intermediate_states):
            full_prompt += f"**State {i+1}:**\n"
            full_prompt += f"Clue applied: {applied_clues[i]}\n"
            full_prompt += f"S({i+1}) = {state}\n"
            full_prompt += f"L({i+1}) = Solvable\n"
        i = len(intermediate_states)
        full_prompt += f"**State {i+1} (Current state):**\n"
        full_prompt += f"Clue applied: {applied_clues[i]}\n"
        full_prompt += f"S({i+1}) = {current_state}\n"
        full_prompt += f"L({i+1}) = {current_status}\n"
        full_prompt += f"**Explored next state:**\n"
        full_prompt += f"Clue applied: {clue_applied_to_unsolvable_child}\n"
        full_prompt += f"S({i+2}) = {unsolvable_child}\nL({i+2}) = Unsolvable\n"
        full_prompt += f"{output_format}"
        return full_prompt

    def get_answer(self, raw: str) -> str:
        raw = raw.split("Next state:")[-1]
        raw = raw.replace("\n", "")
        try:
            pattern = r"\[\s*\[.*?\]\s*\]"
            match = re.findall(pattern, raw, re.DOTALL)[-1]
            result = ast.literal_eval(match)

            all_conditions = []
            for num, value in self.all_clues.items():
                all_conditions.append(value["conditions"])
            puzzle = LogicGridPuzzleTree(self.initial_state, self.domain, all_conditions)
            
            if self.current_status == "Unsolvable":
                if result == self.parent_state:
                    return "1"
                else:
                    applied_clues = self.applied_clues[:-1]
                    unapplied_clues = [self.all_clues[num]["conditions"] for num in self.all_clues if num not in applied_clues]
                    if puzzle.is_next_state(self.parent_state, result, unapplied_clues):
                        return "sibling"
                    return "backtracking failure"
            else:
                unapplied_clues = [self.all_clues[num]["conditions"] for num in self.all_clues if num not in self.applied_clues]
                if puzzle.is_next_state(self.current_state, result, unapplied_clues):
                    if result != self.unsolvable_child:
                        return "1"
                    else:
                        return "unsolvable child"
                else:
                    return "invalid move"
        
        except:
            return "parsing error"


def select_prompter(name: str) -> Prompter:
    if name == "sudoku_e2e":
        return SudokuEndToEndPrompter()
    elif name == "sudoku_state_checking":
        return SudokuStateCheckingPrompter()
    elif name == "sudoku_state_transition":
        return SudokuStateTransitionPrompter()
    elif name == "graphcoloring_e2e":
        return GraphColoringEndToEndPrompter()
    elif name == "graphcoloring_state_checking":
        return GraphColoringStateCheckingPrompter()
    elif name == "graphcoloring_state_transition":
        return GraphColoringStateTransitionPrompter()
    elif name == "game24_e2e":
        return Game24EndToEndPrompter()
    elif name == "game24_state_checking":
        return Game24StateCheckingPrompter()
    elif name == "game24_state_transition":
        return Game24StateTransitionPrompter()
    elif name == "gridpuzzle_e2e":
        return GridPuzzleEndToEndPrompter()
    elif name == "gridpuzzle_state_checking":
        return GridPuzzleStateCheckingPrompter()
    elif name == "gridpuzzle_state_transition":
        return GridPuzzleStateTransitionPrompter()
    else:
        raise KeyError(name)


def test_prompter(data_name: str, prompter_name: str):
    data = select_data(data_name)
    prompter = select_prompter(prompter_name)
    sample = data.samples[0]
    print(prompter.run(sample))


if __name__ == "__main__":
    Fire()