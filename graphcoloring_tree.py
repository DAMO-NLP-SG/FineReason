from fire import Fire

class Node:
    def __init__(self, coloring, move=None, parent=None):
        self.coloring = coloring      # List representing the coloring state
        self.move = move              # The move that led to this state (vertex index, color)
        self.parent = parent          # Reference to the parent node
        self.children = []            # List of children nodes
        self.solvable = None          # Whether this node leads to a solution (True/False)


class GraphColoringTree:
    def __init__(self, graph, max_colors):
        self.graph = graph                  # Adjacency list of the graph
        self.num_vertices = len(graph)
        self.max_colors = max_colors        # Maximum number of colors allowed
        self.root = Node([1] + [0] * (self.num_vertices - 1))
    
    def is_valid_move(self, coloring, vertex, color):
        # Check if assigning 'color' to 'vertex' is valid
        for neighbor in self.graph[vertex]:
            if coloring[neighbor] == color:
                return False
        return True
    
    def is_valid_coloring(self, coloring):
        # Check the entire coloring for validity
        for vertex, neighbors in enumerate(self.graph):
            vertex_color = coloring[vertex]
            if vertex_color == 0:
                continue  # Skip uncolored vertices
            for neighbor in neighbors:
                if coloring[neighbor] == vertex_color:
                    return False
        return True

    def is_next_state(self, previous_state, next_state):
        differences = []
        num_vertices = len(previous_state)
        
        # Collect the indices where the colorings differ
        for vertex in range(num_vertices):
            if previous_state[vertex] != next_state[vertex]:
                differences.append(vertex)
        
        # Check that there is exactly one difference
        if len(differences) != 1:
            return "multiple moves"
        
        vertex = differences[0]
        prev_color = previous_state[vertex]
        next_color = next_state[vertex]
        
        # The previous color should be 0 (uncolored), and the next color should be a valid color
        if prev_color != 0 or next_color == 0:
            return "invalid move"
        
        # Validate the move on the previous state
        if self.is_valid_move(previous_state, vertex, next_color):
            return "1"
        else:
            return "invalid move"


if __name__ == '__main__':
    Fire()