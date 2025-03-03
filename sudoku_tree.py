import copy
from fire import Fire

class Node:
    def __init__(self, board, move=None, parent=None):
        self.board = board            # Deep copy of the board state
        self.move = move              # The move that led to this state (row, col, num)
        self.parent = parent          # Reference to the parent node
        self.children = []            # List of children nodes
        self.solvable = None          # Whether this node leads to a valid solution (True/False/None)


class SudokuTree:
    def __init__(self, initial_board):
        self.root = Node(copy.deepcopy(initial_board))

    def is_valid_move(self, board, row, col, num):
        """
        Check whether placing 'num' at board[row][col] is valid
        """
        # Check row
        for j in range(9):
            if board[row][j] == num and j != col:
                return False

        # Check column
        for i in range(9):
            if board[i][col] == num and i != row:
                return False

        # Check the 3x3 box
        box_row = (row // 3) * 3
        box_col = (col // 3) * 3
        for i in range(box_row, box_row + 3):
            for j in range(box_col, box_col + 3):
                if board[i][j] == num and (i, j) != (row, col):
                    return False
        return True

    def is_next_state(self, previous_board, next_board):
        """
        Check if next_board differs from previous_board by exactly one valid move.
        Returns:
          "1" if valid next state,
          "invalid move" if the move is not a valid Sudoku move,
          "more than one difference" if >1 cell differs,
          "no difference" if no cells differ.
        """
        differences = []
        for r in range(9):
            for c in range(9):
                if previous_board[r][c] != next_board[r][c]:
                    differences.append((r, c))

        if len(differences) != 1:
            return "multiple moves"

        # Exactly one difference
        (row, col) = differences[0]
        prev_val = previous_board[row][col]
        next_val = next_board[row][col]

        # Check range of values
        if prev_val != 0 or not (1 <= next_val <= 9):
            return "invalid move"

        # Check if it's a valid Sudoku move
        temp_board = copy.deepcopy(previous_board)
        temp_board[row][col] = next_val
        if self.is_valid_move(temp_board, row, col, next_val):
            return "1"
        else:
            return "invalid move"


if __name__ == '__main__':
    Fire()