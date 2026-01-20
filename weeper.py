'''
扫雷游戏类
'''
import os
import sys
import numpy as np
from typing import Iterator
from window_analyzer import WindowAnalyzer
import itertools
import math
import time

class Constraint:
    def __init__(self, coordinates: list):
        # self.coordinates = tuple(coordinates)
        # 按照顺序排序
        coordinates_sorted = sorted(coordinates, key=lambda x: (x[0], x[1]))
        self.coordinates = tuple(coordinates_sorted)

    def __repr__(self) -> str:
        return f'{[x for x in self.coordinates]}'

    def __iter__(self) -> Iterator[tuple[int, int]]:
        return iter(self.coordinates)

    def __sub__(self, other: 'Constraint') -> 'Constraint':
        my_coordinates_set = set(self.coordinates)
        other_coordinates_set = set(other.coordinates)
        return Constraint(list(my_coordinates_set - other_coordinates_set))

    def __and__(self, other: 'Constraint') -> 'Constraint':
        my_coordinates_set = set(self.coordinates)
        other_coordinates_set = set(other.coordinates)
        return Constraint(list(my_coordinates_set.intersection(other_coordinates_set)))

    def __or__(self, other: 'Constraint') -> 'Constraint':
        my_coordinates_set = set(self.coordinates)
        other_coordinates_set = set(other.coordinates)
        return Constraint(list(my_coordinates_set.union(other_coordinates_set)))

    def is_subset(self, other: 'Constraint') -> bool:
        return set(self.coordinates).issubset(set(other.coordinates))

    def __len__(self) -> int:
        return len(self.coordinates)

    def __hash__(self) -> int:
        return hash(self.coordinates)

    def __eq__(self, other: 'Constraint') -> bool:
        return set(self.coordinates) == set(other.coordinates)

def two_constraints(A: Constraint, B: Constraint) -> tuple[Constraint, Constraint, Constraint]:
    """
    返回 A_only, B_only, A_and_B
    """
    A_only = A - B
    B_only = B - A
    A_and_B = A & B
    return A_only, B_only, A_and_B

def union_constraints(A: Constraint, B: Constraint) -> Constraint:
    return A | B

class Weeper:
    def __init__(self, table: np.ndarray, mine_total: int) -> None:
        self.mine_total = mine_total
        self.mine_count = mine_total
        self.unknown_count = None
        self.table = table
        
        if table is None:
            window_title = "Minesweeper Variants"
            self.window_analyzer = WindowAnalyzer(window_title)

    def refresh_table(self, refresh_by_screenshot: bool = True):
        if refresh_by_screenshot:
            screenshot = self.window_analyzer.capture_window_screenshot()
            self.table = self.window_analyzer.parse_img_to_table(screenshot)

        # 统计 unknown 数量
        self.unknown_count = np.sum(self.table == 'unknown')
        self.mine_count = self.mine_total - np.sum(self.table == 'mine')

    def print_table(self, table: np.ndarray):
        print(f'============ 剩余雷: {self.mine_count}，未知格: {self.unknown_count} ============')
        for i in range(table.shape[0]):
            print('-' * (table.shape[1] * 4 + 1))
            for j in range(table.shape[1]):
                print('|', end=' ')
                if table[i, j] == 'unknown':
                    print(' ', end=' ')
                elif table[i, j] == 'mine':
                    print('*', end=' ')
                elif table[i, j] == 'question':
                    print('?', end=' ')
                else:
                    print(table[i, j], end=' ')
            print('|')
        print('-' * (table.shape[1] * 4 + 1))

    def _update_constraints(self, constraints: dict, coordinates: Constraint, min_mine_count: int, max_mine_count: int) -> tuple[bool, int, int]:
        if len(coordinates) == 0:
            return False, 0, 0

        if min_mine_count > max_mine_count:
            raise ValueError(f'min_mine_count > max_mine_count: {min_mine_count} > {max_mine_count}')

        is_update = False
        new_min, new_max = 0, 0
        if coordinates in constraints:
            if min_mine_count > constraints[coordinates][0] or max_mine_count < constraints[coordinates][1]:
                new_min = max(min_mine_count, constraints[coordinates][0])
                new_max = min(max_mine_count, constraints[coordinates][1])
                is_update = True
        else:
            new_min = min_mine_count
            new_max = max_mine_count
            is_update = True

        return is_update, new_min, new_max

    '''
    constraints:
        k --> 坐标集合
        v --> 雷的数量（最小值、最大值）
    '''
    def create_table_constraints(self, table: np.ndarray, mine_count: int) -> np.ndarray:
        constraints = dict()
        unknown_coordinates = list()

        # 先遍历所有格子，创建约束
        for i in range(table.shape[0]):
            for j in range(table.shape[1]):
                if table[i, j].isdigit():
                    coordinates, mine_count = self.create_cell_contraint(i, j, table)
                    if len(coordinates) > 0:
                        constraints[coordinates] = (mine_count, mine_count)
                if table[i, j] == 'unknown':
                    unknown_coordinates.append((i, j))

        # [Q] 的规则，2x2 至少有一个
        for i in range(table.shape[0]-1):
            for j in range(table.shape[1]-1):
                coordinates = []
                already_has_mine = False
                for dx in [0, 1]:
                    for dy in [0, 1]:
                        if table[i+dx, j+dy] == 'unknown':
                            coordinates.append((i+dx, j+dy))
                        if table[i+dx, j+dy] == 'mine':
                            already_has_mine = True
                if len(coordinates) > 0 and not already_has_mine:
                    is_update, new_min, new_max = self._update_constraints(constraints, Constraint(coordinates), 1, len(coordinates))
                    if is_update:
                        constraints[Constraint(coordinates)] = (new_min, new_max)


        # 全局数量也有一个约束
        if self.mine_count < 10 and self.unknown_count < 20:
            constraints[Constraint(unknown_coordinates)] = (self.mine_count, self.mine_count)
        # for coordinates, (min_mine_count, max_mine_count) in constraints.items():
        #     print(coordinates, min_mine_count, max_mine_count)
        # print('--------------------------------------------')

        return constraints

    def refresh_constraints(self, constraints: dict, thresh: int) -> int:
        print(f'--> Constraints NUM: {len(constraints)}')
        if len(constraints) > thresh:
            return 0

        new_constraints = {}
        for A, (minA, maxA) in constraints.items():
            for B, (minB, maxB) in constraints.items():
                A_only, B_only, A_and_B = two_constraints(A, B)

                # A_and_B 范围
                z_min = max(0, minA - len(A_only), minB - len(B_only))
                z_max = min(maxA, maxB, len(A_and_B))

                if z_min > z_max:
                    print(A, minA, maxA)
                    print(B, minB, maxB)
                    print(A_and_B, z_min, z_max)
                    print('--------------------------------------------')

                is_update, new_min, new_max = self._update_constraints(constraints, A_and_B, z_min, z_max)
                if is_update:
                    new_constraints[A_and_B] = (new_min, new_max)

                # A_only, B_only 范围
                x_min = max(0, minA - z_max)
                x_max = min(len(A_only), maxA - z_min)
                is_update, new_min, new_max = self._update_constraints(constraints, A_only, x_min, x_max)
                if is_update:
                    new_constraints[A_only] = (new_min, new_max)

                y_min = max(0, minB - z_max)
                y_max = min(len(B_only), maxB - z_min)
                is_update, new_min, new_max = self._update_constraints(constraints, B_only, y_min, y_max)
                if is_update:
                    new_constraints[B_only] = (new_min, new_max)

                # # A U B 范围
                # A_union_B = union_constraints(A, B)
                # u_min = max(0, minA + minB - z_max)
                # u_max = min(len(A_union_B), maxA + maxB - z_min)
                # is_update, new_min, new_max = self._update_constraints(constraints, A_union_B, u_min, u_max)
                # if is_update:
                #     new_constraints[A_union_B] = (new_min, new_max)


        # print('=================================')
        # for new_coordinates, (new_min_mine_count, new_max_mine_count) in new_constraints.items():
        #     print(f'new_coordinates: {new_coordinates}, {new_min_mine_count} ~ {new_max_mine_count}')
        # print('=================================')

        for key, value in new_constraints.items():
            constraints[key] = value

        return len(new_constraints)

    def create_cell_contraint(self, i: int, j: int, table: np.ndarray):
        # table[i, j] 必须是数字
        assert(table[i, j].isdigit())

        coordinates = []
        found_mines = 0
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                ni = i + dx
                nj = j + dy
                if ni < 0 or ni >= table.shape[0] or nj < 0 or nj >= table.shape[1]:
                    continue

                if table[ni, nj] == 'mine':
                    found_mines += 1
                if table[ni, nj] == 'unknown':
                    coordinates.append((ni, nj))

        return Constraint(coordinates), int(table[i, j]) - found_mines

    def init(self):
        self.refresh_table(refresh_by_screenshot=True)
        self.mine_count = self.mine_total
        
    def deduce_table_with_assumptions(self, try_count: int = 5):
        # 刷新一次 Table
        self.refresh_table(refresh_by_screenshot=False)

        for _ in range(try_count):
            constraints = self.create_table_constraints(self.table, self.mine_count)
            mine_marked, safe_marked = set(), set()

            try:
                # 这里的规则和主循环有所不同，这里强制循环多次，尽可能获得足够多的 Hints，这样确保暴力破解的时候覆盖全了
                for _ in range(3):
                    num_updated = self.refresh_constraints(constraints, 600)
                    if num_updated == 0:
                        break

                # 1. 检查是否有哪个数字可以直接告诉我们信息
                new_mine_marked, new_safe_marked = self.solve_by_ensure(constraints)
                mine_marked.update(new_mine_marked)
                safe_marked.update(new_safe_marked)
            except:
                # 发生错误，那么就说明这个假设不应该存在，是错误
                return False

            # 不进行点击，也不进行刷新。只是更新是否有雷或者是否安全
            for coordinate in mine_marked:
                self.table[coordinate[0], coordinate[1]] = 'mine'

            # 由于我们是在推测，所以只知道这里不是雷，没办法真正鼠标点击它查看具体的数字，所以这里标记为 question
            for coordinate in safe_marked:
                self.table[coordinate[0], coordinate[1]] = 'question'

            self.mine_count -= len(mine_marked)
            self.unknown_count -= (len(safe_marked) + len(mine_marked))

            # 退出条件：雷 = 0，unkown = 0
            if self.mine_count == 0 and self.unknown_count == 0:
                break

            # 如果没找到，也提前终止
            if len(mine_marked) == 0 and len(safe_marked) == 0:
                break

        return True


    def solve(self, rounds: int = 200):
        for i in range(rounds):
            print(f'处理第 {i} 个表格.......................')

            self.init()
            is_done = False
            for _ in range(40):
                constraints = self.create_table_constraints(self.table, self.mine_count)
                mine_marked, safe_marked = set(), set()
                    
                for refresh_count in range(10):
                    num_updated = self.refresh_constraints(constraints, 1000)
                    if num_updated == 0:
                        break

                    if len(constraints) < 200 and refresh_count < 5:
                        continue

                    # 1. 检查是否有哪个数字可以直接告诉我们信息
                    new_mine_marked, new_safe_marked = self.solve_by_ensure(constraints)
                    mine_marked.update(new_mine_marked)
                    safe_marked.update(new_safe_marked)

                    # 2. 检查交叠区域是否可以有确定信息
                    if (len(mine_marked) == 0 and len(safe_marked) == 0):
                        new_mine_marked, new_safe_marked = self.solve_by_intersect(constraints)
                        mine_marked.update(new_mine_marked)
                        safe_marked.update(new_safe_marked)

                    if (len(mine_marked) + len(safe_marked)) > 0:
                        break

                    if (num_updated < 10):
                        break


                # 3. 如果不可以，那就需要穷举遍历了
                if (len(mine_marked) == 0 and len(safe_marked) == 0):
                    new_mine_marked, new_safe_marked = self.solve_by_force(constraints)
                    mine_marked.update(new_mine_marked)
                    safe_marked.update(new_safe_marked)

                for coordinate in mine_marked:
                    print(f'Mine: {coordinate}')
                    self.table[coordinate[0], coordinate[1]] = 'mine'
                    self.window_analyzer.click_cell(coordinate[0], coordinate[1], 'right')

                for coordinate in safe_marked:
                    print(f'Safe: {coordinate}')
                    self.window_analyzer.click_cell(coordinate[0], coordinate[1], 'left')

                self.mine_count -= len(mine_marked)
                self.unknown_count -= (len(safe_marked) + len(mine_marked))

                # 退出条件：雷 = 0，unkown = 0
                if self.mine_count == 0 and self.unknown_count == 0:
                    is_done = True
                    break

                if len(safe_marked) > 0:
                    self.refresh_table()

                self.print_table(self.table)
            
            if is_done:
                self.window_analyzer.click_goto_next_level()
            else:
                self.window_analyzer.click_skip_this_level()


    def solve_by_ensure(self, constraints: dict) -> tuple[set, set]:
        new_safe_marked = set()
        new_mine_marked = set()
        for coordinates, (min_mine_count, max_mine_count) in constraints.items():
            if len(coordinates) == min_mine_count:
                for coordinate in coordinates:
                    new_mine_marked.add(coordinate)

            if max_mine_count == 0:
                for coordinate in coordinates:
                    new_safe_marked.add(coordinate)

            # 如果小于，那么报错
            if len(coordinates) < min_mine_count:
                raise ValueError(f'len(coordinates) < min_mine_count: {len(coordinates)} < {min_mine_count}')
            if min_mine_count > max_mine_count:
                raise ValueError(f'min_mine_count > max_mine_count: {min_mine_count} > {max_mine_count}')

        return (new_mine_marked, new_safe_marked)
                

    def solve_by_intersect(self, constraints: dict):
        new_mine_marked = set()
        new_safe_marked = set()

        # for now_coordinates, now_mine_count in constraints.items():
        #     for other_coordinates, other_mine_count in constraints.items():
        #         new_coordinates = other_coordinates - now_coordinates
        #         new_mine_count = other_mine_count - now_mine_count

        #         # 这里不应该等于 0，等于 0 意味着 []，即两个集合相等
        #         if len(new_coordinates) == new_mine_count and new_mine_count > 0:
        #             for coordinate in new_coordinates:
        #                 new_mine_marked.add(coordinate)

        #             # 这里提前返回，因为两重循环复杂度太高了
        #             return new_mine_marked, new_safe_marked
        
        return new_mine_marked, new_safe_marked

    def solve_by_force(self, constraints: dict):
        scores = []
        coordinates_list = []
        # 只选择确定雷数的
        for coordinates, (min_mine_count, max_mine_count) in constraints.items():
            # print(coordinates, min_mine_count, max_mine_count)
            if len(coordinates) < 10 and min_mine_count == max_mine_count:
                score = math.comb(len(coordinates), min_mine_count)
                scores.append(score)
                coordinates_list.append(coordinates)

                # print("-------> score: ", score)

        # 排序，优先选择 scores 最低的
        idx = sorted(range(len(scores)), key=lambda i: scores[i])
        coordinates_list = [coordinates_list[i] for i in idx]
        scores = [scores[i] for i in idx]

        # 每次尝试去暴力遍历，直到找到一个确定解
        for i in range(len(coordinates_list)):
            print('尝试暴力遍历:', coordinates_list[i], scores[i])

            # 临时把 print 关掉
            # sys.stdout = open(os.devnull, 'w')
            # sys.stderr = open(os.devnull, 'w')

            coordinates = coordinates_list[i]
            min_mine_count, max_mine_count = constraints[coordinates]

            table_bak = self.table.copy()

            # 从 coordinates 中随机选择 mine_count 个坐标，设置为 mine
            tables = []
            assumptions = []
            for idx, marked_mine_coordinates in enumerate(itertools.combinations(coordinates, min_mine_count)):
                # sys.stdout = sys.__stdout__
                print(idx, '-->', marked_mine_coordinates)
                # sys.stdout = open(os.devnull, 'w')

                self.table = table_bak.copy()
                for coordinate in marked_mine_coordinates:
                    self.table[coordinate[0], coordinate[1]] = 'mine'
                # 尝试五次分析
                is_ok = self.deduce_table_with_assumptions(try_count=5)
                if is_ok:
                    tables.append(self.table.copy())
                    assumptions.append(marked_mine_coordinates)

            # sys.stdout = sys.__stdout__
            # for assumption, table in zip(assumptions, tables):
            #     print(assumption)
            #     self.print_table(table)
            #     print('--------------------------------------------')
            # sys.stdout = open(os.devnull, 'w')

            new_mine_marked = set()
            new_safe_marked = set()

            self.table = table_bak.copy()
            for i in range(self.table.shape[0]):
                for j in range(self.table.shape[1]):
                    if self.table[i, j] == 'unknown':
                        # 检查 tables 中是否全部是 mine
                        is_all_mine = True
                        for table in tables:
                            if table[i, j] != 'mine':
                                is_all_mine = False
                                break
                        if is_all_mine:
                            new_mine_marked.add((i, j))

                        is_all_safe = True
                        for table in tables:
                            if table[i, j] != 'question':
                                is_all_safe = False
                                break
                        if is_all_safe:
                            new_safe_marked.add((i, j))
            
            # 恢复 print
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

            # 恢复现场 
            self.table = table_bak.copy()
            self.refresh_table(refresh_by_screenshot=False)

            print(f'本次遍历结果: mine={new_mine_marked}, safe={new_safe_marked}')

            if len(new_mine_marked) > 0 or len(new_safe_marked) > 0:
                return (new_mine_marked, new_safe_marked)

        return (set(), set())



if __name__ == "__main__":
    weeper = Weeper(None, mine_total=26)
    weeper.solve(120)

    # table = np.array([
    #     ['unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown'],
    #     ['unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown'],
    #     ['unknown', 'unknown', 'unknown', 'unknown', 'unknown', 2,         'unknown'],
    #     [1,         'unknown', 'unknown', 'unknown', 'unknown', 4,         'unknown'],
    #     ['unknown', 'unknown', 4,          3,        'unknown', 'unknown', 'unknown'],
    #     ['unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown'],
    #     ['unknown', 'unknown', 1,         'unknown', 'unknown', 'unknown', 'unknown'],
    # ])

    # weeper = Weeper(table, 20)
    # weeper.solve_one()