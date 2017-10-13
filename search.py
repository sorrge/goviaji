# does not check for loops. Always returns failure path
def depth_first_search(start, gen_neighbors, is_goal, steps_budget=None):
    stack = [(start, [start])]
    steps_taken = 0
    while stack:
        steps_taken += 1
        if steps_budget is not None:
            if steps_taken >= steps_budget:
                yield steps_taken, None
                return

        (vertex, path) = stack.pop()
        new_neighbors = []
        for neighbor in gen_neighbors(vertex):
            if is_goal(neighbor):
                yield steps_taken, path + [neighbor]
            else:
                new_neighbors.append((neighbor, path + [neighbor]))

        stack.extend(reversed(new_neighbors))

    yield steps_taken, None
