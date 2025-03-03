import copy
import ast
import re
from fire import Fire

class Node:
    def __init__(self, table, applied_clue=None, parent=None, relevance_scores=None):
        self.table = table
        self.applied_clue = applied_clue
        self.parent = parent
        self.children = []
        self.solvable = None
        self.relevance_scores = relevance_scores if relevance_scores else {}


class LogicGridPuzzleTree:
    def __init__(self, T, domains, clues):
        """
        T: initial table
        domains: dict mapping column headers to possible values
        clues: list of clues
        """
        self.root = Node(
            copy.deepcopy(T),
            relevance_scores=self.initialize_relevance_scores(clues, T, domains)
        )
        self.domains = domains
        self.clues = clues
        self.solutions = []

    def initialize_relevance_scores(self, clues, table, domains):
        """
        Create an initial relevance score for each clue. 
        For example, count '==' occurrences, references to known row items, etc.
        """
        relevance = {}
        for i, clue in enumerate(clues):
            score = 0
            score += clue.count('==')
            known_values = [str(row[0]) for row in table]
            for val in known_values:
                if val in clue:
                    score += 1
            relevance[i] = score
        return relevance

    def apply_clue_to_table(self, clue, table):
        """
        Assign only the values mentioned in the clue to the table.
        Returns a list of (new_table, assignments, mentioned_values).
        """
        mentioned_values = self.extract_values_from_clue(clue)
        if not mentioned_values:
            if self.evaluate_single_clue(clue, table):
                # Keep going with the same table if no contradiction
                return [(copy.deepcopy(table), [], [])]
            else:
                # Contradiction
                return []

        assignments = self.parse_clue_for_assignments(clue, mentioned_values, table)
        if not assignments:
            return []

        scenarios = []
        for assign in assignments:
            new_table = copy.deepcopy(table)
            for (r, c, val) in assign:
                new_table[r][c] = val
            scenarios.append((new_table, assign, mentioned_values))

        return scenarios

    def extract_values_from_clue(self, clue):
        """
        Extract all string and numeric values from the clue that are likely to be assigned.
        """
        string_values = re.findall(r"'([^']+)'", clue)
        numeric_values = re.findall(r'\b\d+\b', clue)
        all_values = list(set(string_values + numeric_values))
        return all_values

    def parse_clue_for_assignments(self, clue, mentioned_values, table):
        """
        Determine possible assignments for the mentioned values in the clue.
        Returns a list of valid assignment combos: [ [(row, col, val), ...], ... ] 
        """
        assignments = []
        # Identify the columns for each mentioned value based on domains
        value_to_column = {}
        for val in mentioned_values:
            if val.isnumeric():
                val = int(val)
            found = False
            for col, domain_values in self.domains.items():
                if val in domain_values:
                    col_idx = get_column_index(col, table)
                    if col_idx == -1:
                        continue
                    if self.is_value_assigned(val, col_idx, table):
                        found = False
                        break
                    value_to_column[val] = col
                    found = True
                    break

        if not value_to_column:
            if self.evaluate_single_clue(clue, table):
                return [[]]  # means "no changes needed, clue is satisfied"
            else:
                return []

        # For each value, find possible rows
        value_possible_rows = {}
        for val, col in value_to_column.items():
            col_idx = get_column_index(col, table)
            if col_idx == -1:
                continue
            possible_rows = []
            for i in range(1, len(table)):
                if table[i][col_idx] in ['', val]:
                    possible_rows.append(i)
            if not possible_rows:
                return []
            value_possible_rows[val] = possible_rows

        # Generate all possible combinations of row assignments for the values
        def backtrack(values, current_assignment):
            if not values:
                assignments.append(current_assignment.copy())
                return
            first_val = values[0]
            col = value_to_column[first_val]
            col_idx = get_column_index(col, table)
            for row in value_possible_rows[first_val]:
                current_assignment.append((row, col_idx, first_val))
                backtrack(values[1:], current_assignment)
                current_assignment.pop()

        backtrack(list(value_to_column.keys()), [])

        # Filter out combos that contradict the clue
        valid_assignments = []
        for combo in assignments:
            test_table = copy.deepcopy(table)
            for (r, c, v) in combo:
                test_table[r][c] = v
            if self.evaluate_single_clue(clue, test_table):
                valid_assignments.append(combo)

        return valid_assignments

    def is_next_state(self, previous_state, next_state, unapplied_clues):
        """
        Return True if 'next_state' is one of the valid next states of 'previous_state' obtained by applying exactly one of the 'unapplied_clues'.
        
        :param previous_state: A table (list of lists) in the same format as node.table
        :param next_state: Another table (list of lists) to check
        :param unapplied_clues: A list of clue strings that haven't been applied yet
        :return: True if next_state is a valid single-step successor of previous_state
        """
        possible_next_tables = []
        
        # For each clue that hasn't been applied yet, find all valid new states
        for clue in unapplied_clues:
            scenarios = self.apply_clue_to_table(clue, previous_state)
            for (scenario_table, _, _) in scenarios:
                possible_next_tables.append(scenario_table)
        
        return any(next_state == candidate for candidate in possible_next_tables)

    def is_value_assigned(self, value, col_idx, table):
        for i in range(1, len(table)):
            if table[i][col_idx] == value:
                return True
        return False

    def evaluate_single_clue(self, clue, table):
        return all(evaluate_conditions([clue], table))


class CellValue:

    def __init__(self, val):
        self.val = val

    def __eq__(self, other):
        if isinstance(other, CellValue):
            return self.val == other.val
        return self.val == other

    def __ne__(self, other):
        if isinstance(other, CellValue):
            return self.val != other.val
        return self.val != other

    def __lt__(self, other):
        other_val = other.val if isinstance(other, CellValue) else other
        return self.val < other_val

    def __le__(self, other):
        other_val = other.val if isinstance(other, CellValue) else other
        return self.val <= other_val

    def __gt__(self, other):
        other_val = other.val if isinstance(other, CellValue) else other
        return self.val > other_val

    def __ge__(self, other):
        other_val = other.val if isinstance(other, CellValue) else other
        return self.val >= other_val

    def __add__(self, other):
        other_val = other.val if isinstance(other, CellValue) else other
        return CellValue(self.val + other_val)

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        other_val = other.val if isinstance(other, CellValue) else other
        return CellValue(self.val - other_val)

    def __repr__(self):
        return f"CellValue({self.val})"


class Transformer(ast.NodeTransformer):
    def visit_BoolOp(self, node):
        self.generic_visit(node) 
        return node

    def visit_Subscript(self, node):
        self.generic_visit(node)
        # Check for the pattern T[r(x)][c(y)]
        if isinstance(node.value, ast.Subscript):
            if (isinstance(node.value.value, ast.Name) and node.value.value.id == 'T'):
                row_slice = node.value.slice
                col_slice = node.slice
                if (isinstance(row_slice, ast.Call) and row_slice.func.id == 'r'
                    and isinstance(col_slice, ast.Call) and col_slice.func.id == 'c'):
                    row_arg = row_slice.args[0]
                    col_arg = col_slice.args[0]
                    return ast.Call(
                        func=ast.Name(id='get_cell_value', ctx=ast.Load()),
                        args=[row_arg, col_arg],
                        keywords=[]
                    )
        return node


def transform_condition(cond_str):
    """
    Parse a condition string into an AST, then only replace T[r(...)] [c(...)] with get_cell_value(...) calls.
    """
    tree = ast.parse(cond_str, mode='eval')
    transformed = Transformer().visit(tree)
    ast.fix_missing_locations(transformed)
    return transformed


def get_column_index(x, T):
    """Return column index or -1 if not found."""
    headers = T[0]
    try:
        return headers.index(x)
    except ValueError:
        return -1


def get_row_index(x, T):
    """Return row index or -1 if not found."""
    for i in range(1, len(T)):
        if x in T[i]:
            return i
    return -1


def get_cell_value(row_key, col_key, T):
    row_idx = get_row_index(row_key, T)
    col_idx = get_column_index(col_key, T)
    if row_idx == -1 or col_idx == -1:
        return CellValue('')
    return CellValue(T[row_idx][col_idx])


def evaluate_conditions(conditions, T):
    """
    conditions: list of strings (clues).
    T: the table data
    """
    eval_env = {
        'get_cell_value': lambda row, col: get_cell_value(row, col, T),
        'CellValue': CellValue,
        '__builtins__': {}
    }

    results = []
    for cond_str in conditions:
        expr_ast = transform_condition(cond_str)
        compiled = compile(expr_ast, "<ast>", "eval")
        try:
            result = eval(compiled, eval_env)
        except Exception as e:
            result = False
        results.append(result)

    return results


def test_next_state():
    initial = [
        ["times","names","ailments","insurers"],
        [9,"","",""],
        [10,"","",""],
        [11,"","",""],
        [12,"","",""]
    ]

    solution = [
        ["times","names","ailments","insurers"],
        [9,"Terry","back pain","Lifealign"],
        [10,"Paul","shingles","Triflex"],
        [11,"Guy","vertigo","HealthCo"],
        [12,"Billy","hip pain","Ambercare"]
    ]

    domains = {}
    headers = solution[0]
    for col_index, column_name in enumerate(headers):
        unique_values = set()
        for row in solution[1:]:
            unique_values.add(row[col_index])
        domains[column_name] = sorted(unique_values)

    clues = {
        "1":{"text":"The person with Lifealign insurance has an appointment sometime before the patient suffering from shingles.","conditions":"(T[r('Lifealign')][c('times')] < T[r('shingles')][c('times')])"},
        "2":{"text":"The patient with the 12 noon appointment is either Terry or the patient with Ambercare insurance.","conditions":"(T[r(12)][c('names')] == 'Terry' or T[r(12)][c('insurers')] == 'Ambercare') and (T[r('Terry')][c('insurers')] != 'Ambercare')"},
        "3":{"text":"The patient suffering from back pain has an appointment 2 hours before Guy.","conditions":"(T[r('back pain')][c('times')] == T[r('Guy')][c('times')] - 2)"},
        "4":{"text":"The person with Ambercare insurance has an appointment sometime after the person suffering from vertigo.","conditions":"(T[r('Ambercare')][c('times')] > T[r('vertigo')][c('times')])"},
        "5":{"text":"Neither Billy nor the person suffering from shingles is the person with Lifealign insurance.","conditions":"(T[r('Billy')][c('insurers')] != 'Lifealign' and T[r('shingles')][c('insurers')] != 'Lifealign') and (T[r('Billy')][c('ailments')] != 'shingles')"},
        "6":{"text":"The person with the 9:00am appointment is either Paul or the patient suffering from back pain.","conditions":"(T[r(9)][c('names')] == 'Paul' or T[r(9)][c('ailments')] == 'back pain') and (T[r('Paul')][c('ailments')] != 'back pain')"},
        "7":{"text":"The patient with the 10:00am appointment has Triflex insurance.","conditions":"(T[r(10)][c('insurers')] == 'Triflex')"},
        "8":{"text":"Of the patient suffering from vertigo and the person with Ambercare insurance, one has the 11:00am appointment and the other is Billy.","conditions":"((T[r('vertigo')][c('times')] == 11 and T[r('Ambercare')][c('names')] == 'Billy') or (T[r('Ambercare')][c('times')] == 11 and T[r('vertigo')][c('names')] == 'Billy')) and (T[r('vertigo')][c('insurers')] != 'Ambercare') and (T[r(11)][c('names')] != 'Billy')"}
    }

    all_conditions = []
    for num, value in clues.items():
        all_conditions.append(value["conditions"])

    puzzle = LogicGridPuzzleTree(initial, domains, all_conditions)
    current_state = [["times","names","ailments","insurers"],[9,"","",""],[10,"","",""],[11,"","vertigo",""],[12,"Billy","","Ambercare"]]
    next_state = [['times', 'names', 'ailments', 'insurers'], [9, '', '', ''], [10, '', '', 'Triflex'], [11, '', 'vertigo', ''], [12, 'Billy', '', 'Ambercare']]
    applied_clues = ["8"]
    unapplied_clues = [clues[num]["conditions"] for num in clues if num not in applied_clues]

    print("unapplied_clues:", unapplied_clues)
    print(puzzle.is_next_state(current_state, next_state, unapplied_clues))


if __name__ == "__main__":
    Fire()