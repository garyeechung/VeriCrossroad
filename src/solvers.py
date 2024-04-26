from itertools import product

from z3 import And, Ints, Not, Or, Solver, sat

from .utils import convert_greenlights_to_routes, get_combinations


class Collision:

    def __init__(self, greenlights, n_ways: int = None):
        self.greenlights = greenlights
        if n_ways is None:
            self.n_ways = max(greenlights.keys()) + 1
        else:
            self.n_ways = n_ways

        self.reset_solver()
    
    def reset_solver(self):
        self.routes = convert_greenlights_to_routes(self.greenlights, self.n_ways)
        self.route_pairs = get_combinations(self.routes, self.n_ways)
        self.solver = Solver()
        self.s1, self.e1, self.s2, self.e2, self.sh = Ints('s1 e1 s2 e2 sh')

        # add possible route pairs
        route_pairs_constraints = []
        for pair in self.route_pairs:
            route_pairs_constraints.append(
                And(
                    self.s1 == pair[0][0],
                    self.e1 == pair[0][1],
                    self.s2 == pair[1][0],
                    self.e2 == pair[1][1],
                    self.sh == pair[2]
                )
            )
        self.solver.add(Or(route_pairs_constraints))

        # collision constraint 1
        collision_constraints_1 = And(
            And(self.s1 < self.s2, self.s2 < self.e1),
            Or(self.e1 < self.e2, self.e2 == self.s1)
        )
        # collision constraint 2
        collision_constraints_2 = And(
            self.e1 == self.s2,
            self.e2 > self.s1,  # s1 < e2 < e1
            self.e2 < self.e1
        )
        self.solver.add(Or(collision_constraints_1, collision_constraints_2))
    
    def check_unsafe_routes(self, verbose=False):
        unsafe_routes = dict()
        if verbose:
            print("Checking collision...")
        while self.solver.check() == sat:
            sol = self.solver.model()
            shift = sol[self.sh].as_long()
            start_1 = (sol[self.s1].as_long() + shift) % self.n_ways
            end_1 = (sol[self.e1].as_long() + shift) % self.n_ways
            start_2 = (sol[self.s2].as_long() + shift) % self.n_ways
            end_2 = (sol[self.e2].as_long() + shift) % self.n_ways
            if (start_1, end_1) not in unsafe_routes:
                unsafe_routes[(start_1, end_1)] = 1
            else:
                unsafe_routes[(start_1, end_1)] += 1
            
            if (start_2, end_2) not in unsafe_routes:
                unsafe_routes[(start_2, end_2)] = 1
            else:
                unsafe_routes[(start_2, end_2)] += 1
            
            if verbose:
                print(f"{start_1} -> {end_1}; {start_2} -> {end_2}")
            
            self.solver.add(Not(And(
                self.s1 == sol[self.s1],
                self.e1 == sol[self.e1],
                self.s2 == sol[self.s2],
                self.e2 == sol[self.e2],
                self.sh == sol[self.sh]
            )))
        if verbose:
            print("-" * 50)
            print("Unsafe routes:")
            for route, count in unsafe_routes.items():
                print(f"{route[0]} -> {route[1]}: {count}")

        return unsafe_routes
    
    def remove_greenlight(self, way: int, light: int):
        self.greenlights[way].remove(light)
        self.reset_solver()


class AddSafeRoute:
    def __init__(self, greenlights, n_ways: int = None):
        self.greenlights = greenlights
        if n_ways is None:
            self.n_ways = max(greenlights.keys()) + 1
        else:
            self.n_ways = n_ways

        self.reset_solver()
    
    def reset_solver(self):
        self.existing_routes = convert_greenlights_to_routes(self.greenlights, self.n_ways)
        self.candidate_routes = (product(range(self.n_ways), range(self.n_ways)))
        self.candidate_routes = [
            (route[0], route[1])
            for route in self.candidate_routes
            if (route not in self.existing_routes) and (route[0] != route[1])
        ]

        self.solver = Solver()
        self.s1, self.e1 = Ints('s1 e1')
        self.solver.add(Or([And(self.s1 == route[0], self.e1 == route[1])
                            for route in self.candidate_routes]))
        
        self.solver.add(And([self.get_not_collision_constraint(route[0], route[1])
                             for route in self.existing_routes]))

    
    def get_not_collision_constraint(self, s2: int, e2: int):
        # if s1 < s2
        collision_constraints_1_1 = And(
            self.s1 < s2,
            (s2-self.s1)%self.n_ways < (self.e1-self.s1)%self.n_ways,
            Or((self.e1-self.s1)%self.n_ways < (e2-self.s1)%self.n_ways, e2 == self.s1)
        )
        # if s1 > s2
        collision_constraints_1_2 = And(
            self.s1 > s2,
            (self.s1-s2)%self.n_ways < (e2-s2)%self.n_ways,
            Or((e2-s2)%self.n_ways < (self.e1-s2)%self.n_ways, self.e1 == s2)
        )

        # if e1 == s2
        collision_constraints_2_1 = And(
            self.e1 == s2,
            (e2-self.s1)%self.n_ways > 0,
            (e2-self.s1)%self.n_ways < (self.e1-self.s1)%self.n_ways
        )
        # if e2 == s1
        collision_constraints_2_2 = And(
            e2 == self.s1,
            (self.e1-s2)%self.n_ways > 0,
            (self.e1-s2)%self.n_ways < (e2-s2)%self.n_ways
        )

        totol_collision_constraints = Or(
            collision_constraints_1_1,
            collision_constraints_1_2,
            collision_constraints_2_1,
            collision_constraints_2_2
        )
        return Not(totol_collision_constraints)
    
    def check_safe_route(self, verbose=False):
        safe_routes = []
        if verbose:
            print("Checking safe route...")
        while self.solver.check() == sat:
            sol = self.solver.model()
            start = sol[self.s1].as_long()
            end = sol[self.e1].as_long()
            safe_routes.append((start, end))
            if verbose:
                print(f"{start} -> {end}")
            self.solver.add(Not(And(
                self.s1 == sol[self.s1],
                self.e1 == sol[self.e1]
            )))
        return safe_routes
    
    def add_safe_route(self, start: int, end: int):
        self.greenlights[start].append((end - start) % self.n_ways)
        self.reset_solver()


if __name__ == '__main__':
    greenlights = {
        0: [1, 2],
        1: [3],
        2: [1, 3],
        3: [2, 3],
    }

    print("=" * 50)
    collision = Collision(greenlights, 4)
    collision.check_unsafe_routes(verbose=True)

    print("=" * 50)
    start, end = 2, 1
    collision.remove_greenlight(start, (end - start) % collision.n_ways)

    print("=" * 50)
    collision.check_unsafe_routes(verbose=True)


    start, end = 1, 0
    collision.remove_greenlight(start, (end - start) % collision.n_ways)
    print(collision.greenlights)
    collision.check_unsafe_routes(verbose=True)
