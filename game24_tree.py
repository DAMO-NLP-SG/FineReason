from collections import Counter
from fire import Fire

class Node:
    def __init__(self, numbers, expressions, move=None, parent=None):
        self.numbers = numbers          # List of numbers
        self.expressions = expressions  # List of expressions corresponding to the numbers
        self.move = move                # The move that led to this state (num1, op, num2, result)
        self.parent = parent            # Reference to the parent node
        self.children = []              # List of children nodes
        self.solvable = None            # Whether this node leads to a solution (True/False)


class GameOf24Tree:
    def __init__(self, numbers):
        # Initialize the root node with the initial numbers and their string representations
        expressions = [str(num) for num in numbers]
        self.root = Node(numbers, expressions)
        self.solutions = []

    def is_next_state(self, previous_expressions, next_expressions):
        # Check length difference
        if len(next_expressions) != len(previous_expressions) - 1:
            return "length difference is not 1"

        prev_count = Counter(previous_expressions)
        next_count = Counter(next_expressions)

        # Identify the new expression
        added = next_count - prev_count  
        if len(added) != 1:
            return "no new expression or more than one new expression found"
        new_expression = list(added.elements())[0]

        # Identify which two expressions were used to form the new one
        removed = prev_count - next_count
        if sum(removed.values()) != 2:
            return "number of used expressions is not 2"
        used_expressions = list(removed.elements())

        # Check if the new expression is derived from the used expressions
        for expr in used_expressions:
            new_expression = new_expression.replace(expr, "")
        used_expressions = [expr.replace("(", "").replace(")", "") for expr in used_expressions]
        for expr in used_expressions:
            new_expression = new_expression.replace(expr, "")
        new_expression = new_expression.replace(" ", "").replace("(", "").replace(")", "")
        # Check if only one operator is left
        if len(new_expression) != 1:
            return "more than 1 operator"
        # Check if the operator is one of the four operators
        if new_expression not in ['+', '-', '*', '/']:
            return "invalid operator"

        return "1"


if __name__ == "__main__":
    Fire()