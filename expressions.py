from substitution import Substitution
import hashes


class Expression:
    def to_str(self, top_level=True):
        if isinstance(self, Application):
            text = "" if top_level else "("
            text += " ".join(e.to_str(False) for e in self.collect_level())
            if not top_level:
                text += ")"

            return text
        else:
            return self.name

    def transform_leaves(self, transform):
        if isinstance(self, Application):
            return Application(*(e.transform_leaves(transform) for e in self.elems))

        return transform(self)

    def transform_nodes(self, transform):
        r = transform(self)
        if r is None:
            if isinstance(self, Application):
                r = Application(*(e.transform_nodes(transform) for e in self.elems))
            else:
                r = self

        return r

    def any_leaf(self, predicate):
        if isinstance(self, Application):
            return any(e.any_leaf(predicate) for e in self.elems)

        return predicate(self)

    def is_ground(self):
        return not self.any_leaf(lambda l: isinstance(l, Variable))

    def contains_leaf(self, to_find):
        return self.any_leaf(lambda l: l is to_find)

    def for_all_leaves(self, process):
        if isinstance(self, Application):
            for e in self.elems:
                e.for_all_leaves(process)
        else:
            process(self)

    def collect_variables(self, accum_vars=None):
        if accum_vars is None:
            accum_vars = set()

        def var_accumulator(leaf):
            if isinstance(leaf, Variable):
                accum_vars.add(leaf)

        self.for_all_leaves(var_accumulator)
        return accum_vars

    def collect_constants(self, accum_consts=None):
        if accum_consts is None:
            accum_consts = set()

        def const_accumulator(leaf):
            if isinstance(leaf, Constant):
                accum_consts.add(leaf)

        self.for_all_leaves(const_accumulator)
        return accum_consts

    def count_leaves(self, counter=None):
        if counter is None:
            counter = {}

        def leaf_counter(leaf):
            if leaf not in counter:
                counter[leaf] = 0

            counter[leaf] += 1

        self.for_all_leaves(leaf_counter)
        return counter

    def unify(self, expr):
        subs = Substitution()
        eqs = [(self, expr)]
        while eqs:
            lhs, rhs = eqs.pop()
            if lhs is rhs:
                continue
            elif isinstance(lhs, Application) and isinstance(rhs, Application):
                eqs.extend(zip(lhs.elems, rhs.elems))
            elif isinstance(lhs, Variable) or isinstance(rhs, Variable):
                if not isinstance(lhs, Variable):
                    lhs, rhs = rhs, lhs

                if isinstance(rhs, Variable) or not rhs.contains_leaf(lhs):
                    add_subs = Substitution()
                    add_subs.replace(lhs, rhs)
                    subs.compose(add_subs)
                    eqs = [(add_subs.apply(lhs), add_subs.apply(rhs)) for lhs, rhs in eqs]
                else:
                    return None
            else:
                return None

        return subs

    def tree_equal(self, e):
        if type(self) != type(e):
            return False

        if isinstance(self, Application):
            return self.elems[0].tree_equal(e.elems[0]) and self.elems[1].tree_equal(e.elems[1])

        return self is e

    def __repr__(self):
        return self.to_str()

    def get_hash(self):
        variables_idx = {}

        return self.calc_hash(variables_idx)


class Constant(Expression):
    def __init__(self, name, generated=False):
        self.name = name
        self.hash = hashes.new_hash()
        self.generated = generated

    def collect_level(self):
        return [self]

    def calc_hash(self, variables_idx):
        if self.generated:
            if self not in variables_idx:
                variables_idx[self] = len(variables_idx)

            return hashes.get_hash_for_idx(variables_idx[self], 1)
        else:
            return self.hash


class Variable(Expression):
    def __init__(self, name):
        self.name = name

    def collect_level(self):
        return [self]

    def calc_hash(self, variables_idx):
        if self not in variables_idx:
            variables_idx[self] = len(variables_idx)

        return hashes.get_hash_for_idx(variables_idx[self], 0)


class Application(Expression):
    def __init__(self, left, right):
        self.elems = left, right

    def __iter__(self):
        return self.elems

    def collect_level(self):
        left = self.elems[0].collect_level()
        left.append(self.elems[1])
        return left

    def calc_hash(self, variables_idx):
        return hashes.combine_hashes(self.elems[0].calc_hash(variables_idx), self.elems[1].calc_hash(variables_idx))


# inverse of collect_level
def expression_from_list(l):
    if len(l) == 1:
        return l[0]

    return expression_from_list([Application(l[0], l[1])] + l[2:])
