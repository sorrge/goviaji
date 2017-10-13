class Substitution:
    def __init__(self):
        self.replacements = {}

    def replace(self, var, expr):
        assert expr is not None
        self.replacements[var] = expr

    def transform(self, expr_node):
        if expr_node in self.replacements:
            return self.replacements[expr_node]

        return expr_node

    def apply(self, expr):
        if not self.replacements:
            return expr

        return expr.transform_leaves(self.transform)

    def compose(self, subs, add=True):
        for var, expr in self.replacements.items():
            self.replacements[var] = subs.apply(expr)

        if add:
            for var, expr in subs.replacements.items():
                self.replacements[var] = expr

    def filter_variables(self, vars_to_keep):
        vars_to_remove = self.replacements.keys() - vars_to_keep
        for var in vars_to_remove:
            del self.replacements[var]

    def to_str(self):
        return ", ".join(var.to_str() + " -> " + expr.to_str() for var, expr in self.replacements.items())

    def __repr__(self):
        return self.to_str()

    def __getitem__(self, var):
        return self.replacements[var]

    def __len__(self):
        return len(self.replacements)

    def __contains__(self, var):
        return var in self.replacements

    def items(self):
        return self.replacements.items()
