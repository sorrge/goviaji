from expressions import Constant, Variable, Application
from substitution import Substitution


class RulesError(Exception):
    pass


def get_constant_in_front(expr):
    front = expr
    while isinstance(front, Application):
        front = front.elems[0]

    if isinstance(front, Constant):
        return front

    return None


def get_constant_in_second_place(expr):
    if not isinstance(expr, Application):
        return None

    front = expr
    while isinstance(front.elems[0], Application):
        front = front.elems[0]

    if isinstance(front.elems[1], Constant):
        return front.elems[1]

    return None


class Rules:
    def __init__(self):
        self.constants = {}
        self.introduced_vars = 0
        self.introduced_constants = 0
        self.rules_by_name = {}
        self.rules_in_order = []
        self.definitions = {}
        self.rules_by_constant_in_front = {}
        self.rules_by_constant_in_second_place = {}

    def introduce_constant(self):
        while True:
            new_name = "_" + str(self.introduced_constants)
            self.introduced_constants += 1
            if new_name not in self.constants:
                break

        c = Constant(new_name, generated=True)
        self.constants[new_name] = c
        return c

    def introduce_variable(self, original_var=None):
        if original_var is None:
            new_name = "Var$" + str(self.introduced_vars)
        else:
            if "$" in original_var.name:
                new_name = original_var.name[:original_var.name.find("$")] + "$" + str(self.introduced_vars)
            else:
                new_name = original_var.name + "$" + str(self.introduced_vars)

        v = Variable(new_name)

        self.introduced_vars += 1
        return v

    def add_constant_by_name(self, name):
        if name not in self.constants:
            self.constants[name] = Constant(name)

        return self.constants[name]

    def add_constant(self, expr):
        if isinstance(expr, Constant):
            return self.add_constant_by_name(expr.name)

        return expr

    def process_constants(self, expr):
        return expr.transform_leaves(self.add_constant)

    def add_rule(self, rule):
        if rule.name in self.rules_by_name:
            raise RulesError("duplicate rule %s. Previous definition:\n%s\nDuplicate definition:\n%s" %
                             (rule.name.name, self.rules_by_name[rule.name].definition_src, rule.definition_src))

        constant_in_front = get_constant_in_front(rule.conclusion)
        if constant_in_front:
            if constant_in_front not in self.rules_by_constant_in_front:
                self.rules_by_constant_in_front[constant_in_front] = []

            self.rules_by_constant_in_front[constant_in_front].append(rule)

        constant_in_second_place = get_constant_in_second_place(rule.conclusion)
        if constant_in_second_place:
            if constant_in_second_place not in self.rules_by_constant_in_second_place:
                self.rules_by_constant_in_second_place[constant_in_second_place] = []

            self.rules_by_constant_in_second_place[constant_in_second_place].append(rule)

        self.rules_by_name[rule.name] = rule
        self.rules_in_order.append(rule)
        return rule

    def get_applicable_rules(self, goal_expr):
        rule_set = []
        constant_in_front = get_constant_in_front(goal_expr)
        if constant_in_front and constant_in_front in self.rules_by_constant_in_front:
            rule_set = self.rules_by_constant_in_front[constant_in_front]

        constant_in_second_place = get_constant_in_second_place(goal_expr)
        if constant_in_second_place and constant_in_second_place in self.rules_by_constant_in_second_place:
            rule_set.extend(self.rules_by_constant_in_second_place[constant_in_second_place])

        if not constant_in_front and not constant_in_second_place:
            rule_set = self.rules_in_order

        for rule in rule_set:
            subs = rule.unify(goal_expr)
            if subs is not None:
                yield subs, rule

    def refreshing_substitution(self, vars):
        refreshing_subs = Substitution()
        for v in vars:
            refreshing_subs.replace(v, self.introduce_variable(v))

        return refreshing_subs

    def refresh_free_variables(self, expr):
        refresh = {}

        def refreshing_transform(leaf):
            if leaf in refresh:
                return refresh[leaf]

            if isinstance(leaf, Variable):
                new_var = self.introduce_variable(leaf)
                refresh[leaf] = new_var
                return new_var

            return leaf

        return expr.transform_leaves(refreshing_transform)

    def add_definition(self, name, expr, definition_src):
        if name in self.definitions:
            raise RulesError("duplicate def %s. Previous definition:\n%s\nDuplicate definition:\n%s" %
                             (name.name, self.definitions[name][1], definition_src))

        proc = VarProcessor(self)
        expr = proc.process_vars(expr)
        self.definitions[name] = expr, definition_src

    def instantiate_free_variables(self, expr):
        vars = expr.collect_variables()
        instantiate_vars_subs = Substitution()
        for v in vars:
            instantiate_vars_subs.replace(v, self.introduce_constant())

        return instantiate_vars_subs.apply(expr)

    def transfrom_def_instantiate(self, leaf):
        if leaf in self.definitions:
            return self.instantiate_free_variables(self.definitions[leaf][0])

        return leaf

    def instantiate_definitions(self, expr):
        return expr.transform_leaves(self.transfrom_def_instantiate)

    def transfrom_def_refresh(self, leaf):
        if leaf in self.definitions:
            return self.refresh_free_variables(self.definitions[leaf][0])

        return leaf

    def expand_definition_with_variables(self, expr):
        return expr.transform_leaves(self.transfrom_def_refresh)

    def collapse_node_definition(self, node):
        if isinstance(node, Variable):
            return None

        for name, (expr, src) in self.definitions.items():
            if expr.unify(node) is not None:
                return name

        return None

    def collapse_definitions(self, expr):
        return expr.transform_nodes(self.collapse_node_definition)

    def flatten_definitions(self):
        for name_1, (expr_1, src_1) in self.definitions.items():
            if expr_1.contains_leaf(name_1):
                raise RulesError("def %s is recursive:\n%s" % (name_1, src_1))

            def expand_def(leaf):
                if leaf is name_1:
                    return self.refresh_free_variables(expr_1)

                return leaf

            for name_2, (expr_2, src_2) in self.definitions.items():
                expanded_expr_2 = expr_2.transform_leaves(expand_def)
                self.definitions[name_2] = expanded_expr_2, src_2

        for rule in self.rules_in_order:
            rule.conclusion = self.expand_definition_with_variables(rule.conclusion)
            rule.premises = list(map(self.expand_definition_with_variables, rule.premises))


class VarProcessor:
    def __init__(self, rules):
        self.rules = rules
        self.vars_by_name = {}

    def process_var(self, v):
        if isinstance(v, Variable):
            if v.name not in self.vars_by_name:
                self.vars_by_name[v.name] = self.rules.introduce_variable(v)

            return self.vars_by_name[v.name]

        return v

    def process_vars(self, expr):
        return expr.transform_leaves(self.process_var)


class Rule:
    def __init__(self, premises, conclusion, name, definition_src, rules):
        self.name = name
        self.definition_src = definition_src
        self.rules_db = rules

        proc = VarProcessor(rules)
        self.premises = list(map(proc.process_vars, premises))
        self.conclusion = proc.process_vars(conclusion)
        self.variables = set()
        self.conclusion.collect_variables(self.variables)
        for p in self.premises:
            p.collect_variables(self.variables)

    def __repr__(self):
        return self.to_str()

    def to_str(self):
        return "rule " + self.name.name + " = " + self.conclusion.to_str() + \
        (" :- " + ", ".join(p.to_str() for p in self.premises)) * (len(self.premises) > 0)

    def check_number_of_premises(self, selected_premises):
        if len(selected_premises) != len(self.premises):
            raise RuntimeError("Number of premises didn't match when applying rule " + self.name.name +
                               ": expected " + str(len(self.premises)) + ", got " + str(len(selected_premises)))

    def unify(self, goal):
        return self.conclusion.unify(goal)
