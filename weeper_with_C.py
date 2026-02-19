'''
扫雷游戏类
'''
from multiprocessing import Value
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

import random
import numpy as np
from typing import Iterator
from window_analyzer import WindowAnalyzer
import itertools
import math
import collections
import time
import threading
import concurrent.futures
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    print("警告: keyboard 库未安装，空格键退出功能不可用。请运行: pip install keyboard")

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
    def __init__(self, table: np.ndarray, mine_total: int, \
        is_Q: bool, is_C: bool, is_T: bool, is_D: bool) -> None:
        self.mine_total = mine_total
        self.mine_count = mine_total
        self.unknown_count = None
        self.table = table

        self.is_Q = is_Q
        self.is_C = is_C
        self.is_T = is_T
        self.is_D = is_D
        
        if table is None:
            window_title = "Minesweeper Variants"
            self.window_analyzer = WindowAnalyzer(window_title)
        
        # 启动键盘监听线程
        if KEYBOARD_AVAILABLE:
            self._start_keyboard_listener()
    
    def _start_keyboard_listener(self):
        """启动键盘监听线程，监听空格键，按下时直接强制退出"""
        def listen_keyboard():
            while True:
                try:
                    if keyboard.is_pressed('space'):
                        print("\n[检测到空格键按下，程序立即退出...]")
                        os._exit(0)  # 直接强制退出，不等待清理
                    time.sleep(0.1)  # 避免CPU占用过高
                except Exception:
                    # 如果出现错误，继续监听
                    time.sleep(0.1)
        
        listener_thread = threading.Thread(target=listen_keyboard, daemon=True)
        listener_thread.start()
        print("提示: 按空格键可强制退出程序")
    
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
        '''
        更新 coordinates 的最大最小雷数量（coordinates 在坐标组合）
        '''
        if len(coordinates) == 0:
            return False, 0, 0

        if min_mine_count > max_mine_count:
            # print(f'min_mine_count > max_mine_count: {min_mine_count} > {max_mine_count}')
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

    def _get_four_directions(self, table: np.ndarray, coordinate: tuple[int, int]) -> list[tuple[int, int]]:
        """
        返回四个方向的坐标：上下左右
        """
        directions = [
            (-1, 0), (0, 1), (1, 0), (0, -1)    # 左、右
        ]

        results = []
        for dx, dy in directions:
            coord = (coordinate[0] + dx, coordinate[1] + dy)
            if coord[0] < 0 or coord[0] >= table.shape[0] or coord[1] < 0 or coord[1] >= table.shape[1]:
                continue
            results.append(coord)
        return results

    def _get_eight_directions(self, table: np.ndarray, coordinate: tuple[int, int]) -> list[tuple[int, int]]:
        """
        返回八连通的坐标：上下左右 + 四个对角线
        """
        directions = [
            (-1, -1), (-1, 0), (-1, 1),  # 上左、上、上右
            (0, -1),           (0, 1),    # 左、右
            (1, -1),  (1, 0),  (1, 1)     # 下左、下、下右
        ]

        results = []
        for dx, dy in directions:
            coord = (coordinate[0] + dx, coordinate[1] + dy)
            if coord[0] < 0 or coord[0] >= table.shape[0] or coord[1] < 0 or coord[1] >= table.shape[1]:
                continue
            results.append(coord)
        return results
    
    def _bfs_connected_region(self, table: np.ndarray, start_coords: list, connected_type: int,
                              allowed_cell_types: set) -> set:
        """
        使用 BFS 找到从起始坐标开始的四/八连通区域
        
        Args:
            table: 全局表格
            connected_type: 4 - 四连通，8 - 八连通
            start_coords: 起始坐标列表（可以是单个坐标的列表）
            allowed_cell_types: 允许通过的格子类型集合，例如 {'mine', 'unknown'}
        
        Returns:
            连通区域的坐标集合
        """
        if len(start_coords) == 0:
            return set()
        
        connected_region = set()
        queue = start_coords.copy()
        
        for coord in start_coords:
            connected_region.add(coord)
        
        while queue:
            current = queue.pop(0)
            
            # 检查八个方向的邻居
            if connected_type == 8:
                neighbors = self._get_eight_directions(table, current)
            elif connected_type == 4:
                neighbors = self._get_four_directions(table, current)

            for neighbor in neighbors:
                # 如果已经访问过，跳过
                if neighbor in connected_region:
                    continue
                
                # 判断是否可以访问：检查格子类型是否在允许的集合中
                cell_value = table[neighbor[0], neighbor[1]]
                if cell_value in allowed_cell_types:
                    connected_region.add(neighbor)
                    queue.append(neighbor)
        
        return connected_region
    
    def _find_all_connected_regions(self, table: np.ndarray, target_coords: list, connected_type: int,
                                    allowed_cell_types: set) -> list:
        """
        找到所有分离的连通区域
        
        Args:
            table: 全局表格
            target_coords: 目标坐标列表（例如所有 mine 的坐标）
            allowed_cell_types: 允许通过的格子类型集合，例如 {'mine'} 或 {'mine', 'unknown'}
        
        Returns:
            连通区域列表，每个元素是一个坐标集合
        """
        if len(target_coords) == 0:
            return []
        
        visited = set()
        connected_regions = []
        
        for start_coord in target_coords:
            if start_coord in visited:
                continue
            
            # 找到从当前坐标开始的连通区域
            connected_region = self._bfs_connected_region(
                table, [start_coord], connected_type,
                allowed_cell_types=allowed_cell_types
            )
            
            # 只保留目标坐标（例如只保留 mine）
            if len(connected_region) > 0:
                connected_regions.append(connected_region)
                visited.update(connected_region)
        
        return connected_regions

    def is_three_not_connected(self, table: np.ndarray) -> bool:
        """
        检查当前雷的坐标是否有三连，如果有则返回 False
        四个方向：水平、垂直、左上-右下对角线、右上-左下对角线
        """
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        
        for i in range(table.shape[0]):
            for j in range(table.shape[1]):
                if table[i, j] != 'mine':
                    continue
                
                for di, dj in directions:
                    # 检查当前点沿着 direction 方向是否有三连雷
                    count = 1
                    for step in [1, 2]:
                        ni, nj = i + di * step, j + dj * step
                        if 0 <= ni < table.shape[0] and 0 <= nj < table.shape[1]:
                            if table[ni, nj] == 'mine':
                                count += 1
                    if count >= 3:
                        return False
        
        return True
        
    
    def is_eight_connected(self, table: np.ndarray) -> bool:
        """
        检查当前雷的坐标是否形成八连通区域（八连通：上下左右 + 四个对角线方向）
        允许通过 unknown 格子连接，但不能通过数字或 question 格子连接
        
        Args:
            table: 全局表格
        
        Returns:
            True 如果所有雷八连通，False 否则
        """
        mine_coordinates = []
        for i in range(table.shape[0]):
            for j in range(table.shape[1]):
                if table[i, j] == 'mine':
                    mine_coordinates.append((i, j))

        if len(mine_coordinates) == 0 or len(mine_coordinates) == 1:
            return True
        
        # 使用通用函数找到连通区域（允许通过 mine 和 unknown）
        connected_region = self._bfs_connected_region(
            table, [mine_coordinates[0]], 
            allowed_cell_types={'mine', 'unknown'}
        )
        
        # 检查是否所有雷都被访问到
        mine_set = set(mine_coordinates)
        visited_mines = connected_region & mine_set
        return len(visited_mines) == len(mine_coordinates)

    def check_rules(self, table: np.ndarray) -> bool:
        """
        检查当前表格是否符合所有规则
        """
        is_ok = True
        if self.is_C:
            is_ok = is_ok and self.is_eight_connected(table)
        if self.is_T:
            is_ok = is_ok and self.is_three_not_connected(table)
        return is_ok

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
        if self.is_Q:
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

        # [C] 的规则，所有雷的区域是八连通的
        if self.is_C:
            # 如果某个点是雷，四周要有一个雷
            # --> 1. 修改为求解雷的联通区域（unknown不可通），每个区域的四周会一定要有雷

            # 四周如果全是已知的，那么这块区域一定是安全的
            # --> 2. 修改为直接求雷的联通区域（unknown可通），那么剩下的 unknown 一定不可能是雷

            # 找到所有 mine 的坐标
            mine_coordinates = [(i, j) for i in range(table.shape[0]) for j in range(table.shape[1]) if table[i, j] == 'mine']

            # 1. 求解所有 mine 的联通区域（只考虑 mine，不考虑 unknown），然后每个联通区域的四周要有雷
            if len(mine_coordinates) > 0:
                
                # 找到所有分离的 mine 连通区域（只考虑 mine，不考虑 unknown）
                connected_regions = self._find_all_connected_regions(
                    table, mine_coordinates, connected_type=8,
                    allowed_cell_types={'mine'}  # 只允许通过 mine
                )

                # 如果没有雷了，那么就不用管了
                if self.mine_count == 0:
                    # 没有雷的时候，mines 要是联通的
                    if len(connected_regions) > 1:
                        raise ValueError(f'找到多个连通区域：{connected_regions}')
                else:
                    # 现在 connected_regions 包含了所有分离的 mine 连通区域
                    # 每个连通区域的四周要有雷
                    for connected_region in connected_regions:
                        neighbors = set()
                        for coordinate in connected_region:
                            for neighbor in self._get_eight_directions(table, coordinate):
                                if table[neighbor[0], neighbor[1]] == 'unknown':
                                    neighbors.add(neighbor)
                        if len(neighbors) > 0:
                            constraint = Constraint(list(neighbors))
                            is_update, new_min, new_max = self._update_constraints(constraints, constraint, 1, len(neighbors))
                            if is_update:
                                constraints[constraint] = (new_min, new_max)
                        else:
                            raise ValueError(f'某个连通区域的四周没有 unknown，坐标：{connected_region}')
                
            # 2. 求当前雷的联通区域，剩下的 unknown 一定不是雷
            if len(mine_coordinates) > 0:

                # 使用通用函数找到所有与 mine 八连通的区域（包括可以连接的 unknown）
                connected_regions = self._find_all_connected_regions(
                    table, [mine_coordinates[0]], connected_type=8,
                    allowed_cell_types={'mine', 'unknown'}
                )

                if len(connected_regions) > 1:
                    raise ValueError(f'找到多个连通区域：{connected_regions}')
                
                # 找到所有不在连通区域中的 unknown，它们一定不是雷
                safe_unknowns = []
                for i in range(table.shape[0]):
                    for j in range(table.shape[1]):
                        if table[i, j] == 'unknown' and (i, j) not in connected_regions[0]:
                            safe_unknowns.append((i, j))
                
                # 为这些安全的 unknown 添加约束：它们一定不是雷
                if len(safe_unknowns) > 0:
                    print(f'这些坐标一定是安全的：{safe_unknowns}')
                    safe_constraint = Constraint(safe_unknowns)
                    is_update, new_min, new_max = self._update_constraints(constraints, safe_constraint, 0, 0)
                    if is_update:
                        constraints[safe_constraint] = (new_min, new_max)
            
            # 求解所有 mine 的联通区域，然后每个联通区域的四周要有雷

        # [T] 的规则，雷不能构成三连
        # 对于每个三连区域（mine + unknown 组合），unknown 中最多有 2 - mine_count 个雷
        if self.is_T:
            directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
            seen_triplets = set()  # 避免重复处理相同的三连区域
            
            for i in range(table.shape[0]):
                for j in range(table.shape[1]):
                    for di, dj in directions:
                        # 获取三连区域的三个坐标
                        triplet = [(i + di * k, j + dj * k) for k in range(3)]
                        
                        # 检查是否越界
                        if not all(0 <= x < table.shape[0] and 0 <= y < table.shape[1] for x, y in triplet):
                            continue
                        
                        # 用排序后的元组作为 key，避免重复
                        triplet_key = tuple(sorted(triplet))
                        if triplet_key in seen_triplets:
                            continue
                        seen_triplets.add(triplet_key)
                        
                        # 统计三连区域中的 mine 和 unknown
                        mine_count = 0
                        unknowns = []
                        has_known = False
                        for x, y in triplet:
                            if table[x, y] == 'mine':
                                mine_count += 1
                            elif table[x, y] == 'unknown':
                                unknowns.append((x, y))
                            else:
                                # 如果是已知格（数字），那这个三连区域不可能三连雷
                                has_known = True
                                break
                        
                        # 如果有已知格，跳过这个三连区域
                        if has_known:
                            continue
                        
                        # 如果有 unknown，添加约束：最多 2 - mine_count 个雷
                        if len(unknowns) > 0:
                            max_mines = 2 - mine_count
                            if max_mines < len(unknowns):  # 只有约束有意义时才添加
                                constraint = Constraint(unknowns)
                                is_update, new_min, new_max = self._update_constraints(
                                    constraints, constraint, 0, max_mines)
                                if is_update:
                                    constraints[constraint] = (new_min, new_max)


        # 全局数量也有一个约束；不过为了防止加入之后，导致 constraints 过多，这里做个判断
        is_add = False
        if len(constraints) < 100:
            is_add = True
        else:
            if self.mine_count < 10 and self.unknown_count < 30:
                is_add = True

        if is_add:
            is_update, new_min, new_max = self._update_constraints(constraints, Constraint(unknown_coordinates), self.mine_count, self.mine_count)
            if is_update:
                constraints[Constraint(unknown_coordinates)] = (new_min, new_max)

        return constraints


    def refresh_constraints(self, constraints: dict, new_constraints: dict, thresh: int) -> dict:
        # print(f'--> Constraints NUM: {len(constraints)}')
        if len(constraints) > thresh:
            return {}

        # 把其中无用的 constraints 去掉
        can_remove_keys = []
        for coordinates, (min_mine_count, max_mine_count) in constraints.items():
            if len(coordinates) == max_mine_count and min_mine_count == 0:
                can_remove_keys.append(coordinates)
        for key in can_remove_keys:
            del constraints[key]

        return_new_constraints = {}
        for A, (minA, maxA) in constraints.items():
            for B, (minB, maxB) in new_constraints.items():
                A_only, B_only, A_and_B = two_constraints(A, B)

                # A_and_B 范围
                z_min = max(0, minA - len(A_only), minB - len(B_only))
                z_max = min(maxA, maxB, len(A_and_B))

                # if z_min > z_max:
                #     print(A, minA, maxA)
                #     print(B, minB, maxB)
                #     print(A_and_B, z_min, z_max)
                #     print('--------------------------------------------')

                try:
                    is_update, new_min, new_max = self._update_constraints(constraints, A_and_B, z_min, z_max)
                    if is_update:
                        is_update, new_min, new_max = self._update_constraints(return_new_constraints, A_and_B, new_min, new_max)
                except:
                    # self.print_table(self.table)
                    # print(f'A: {A}, minA: {minA}, maxA: {maxA}')
                    # print(f'B: {B}, minB: {minB}, maxB: {maxB}')
                    # print(f'A_and_B: {A_and_B}, z_min: {z_min}, z_max: {z_max}')
                    # print('--------------------------------------------')
                    # exit(0)
                    raise ValueError(f'z_min > z_max: {z_min} > {z_max}')

                if is_update:
                    # print(f'A: {A}, minA: {minA}, maxA: {maxA}')
                    # print(f'B: {B}, minB: {minB}, maxB: {maxB}')
                    # print(f'A_and_B: {A_and_B}, z_min: {z_min}, z_max: {z_max}')
                    # print('--------------------------------------------')
                    return_new_constraints[A_and_B] = (new_min, new_max)

                # A_only, B_only 范围
                x_min = max(0, minA - z_max)
                x_max = min(len(A_only), maxA - z_min)
                try:
                    is_update, new_min, new_max = self._update_constraints(constraints, A_only, x_min, x_max)
                    if is_update:
                        is_update, new_min, new_max = self._update_constraints(return_new_constraints, A_only, new_min, new_max)
                except:
                    raise ValueError(f'x_min > x_max: {x_min} > {x_max}')

                if is_update:
                    return_new_constraints[A_only] = (new_min, new_max)

                y_min = max(0, minB - z_max)
                y_max = min(len(B_only), maxB - z_min)
                try:
                    is_update, new_min, new_max = self._update_constraints(constraints, B_only, y_min, y_max)
                    if is_update:
                        is_update, new_min, new_max = self._update_constraints(return_new_constraints, B_only, new_min, new_max)
                except:
                    raise ValueError(f'y_min > y_max: {y_min} > {y_max}')

                if is_update:
                    # print(f'A: {A}, minA: {minA}, maxA: {maxA}')
                    # print(f'B: {B}, minB: {minB}, maxB: {maxB}')
                    # print(f'B_only: {B_only}, y_min: {y_min}, y_max: {y_max}')
                    # print('--------------------------------------------')
                    return_new_constraints[B_only] = (new_min, new_max)

        # 把其中无用的 constraints 去掉
        can_remove_keys = []
        for coordinates, (min_mine_count, max_mine_count) in return_new_constraints.items():
            if len(coordinates) == max_mine_count and min_mine_count == 0:
                can_remove_keys.append(coordinates)
        for key in can_remove_keys:
            del return_new_constraints[key]

        for key, value in return_new_constraints.items():
            constraints[key] = value

        return return_new_constraints

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
        # self.mine_count = self.mine_total
        
    def deduce_table_with_assumptions(self, try_count: int = 5):
        # 刷新一次 Table
        self.refresh_table(refresh_by_screenshot=False)

        for _ in range(try_count):
            try:
                assert(self.check_rules(self.table))
                constraints = self.create_table_constraints(self.table, self.mine_count)
            except:
                return False
            mine_marked, safe_marked = set(), set()

            try:
                new_constraints = constraints.copy()
                # 这里的规则和主循环有所不同，这里强制循环多次，尽可能获得足够多的 Hints，这样确保暴力破解的时候覆盖全了
                for _ in range(3):
                    new_constraints = self.refresh_constraints(constraints, new_constraints, 600)
                    if len(new_constraints) == 0:
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
                return True

        return True


    def solve_one(self) -> bool:
        """
        求解某个 Table，如果没有确定解，则会你先回溯剪枝
        """
        if self.mine_count > self.unknown_count:
            raise ValueError(f'mine_count > unknown_count: {self.mine_count} > {self.unknown_count}')

        if not self.check_rules(self.table):
            raise ValueError(f'check_rules 失败')

        # 退出条件：雷 = 0，unkown = 0
        if self.mine_count == 0 and self.unknown_count == 0:
            return True

        try:
            constraints = self.create_table_constraints(self.table, self.mine_count)
        except:
            raise ValueError(f'create_table_constraints 失败')

        mine_marked, safe_marked = set(), set()

        try:
            new_constraints = constraints.copy()
            while True:
                # 1. 检查是否有哪个数字可以直接告诉我们信息
                try:
                    new_mine_marked, new_safe_marked = self.solve_by_ensure(constraints)
                except Exception as e:
                    raise ValueError(f'solve_by_ensure 失败')

                mine_marked.update(new_mine_marked)
                safe_marked.update(new_safe_marked)

                # 如果找到确定解，那么退出
                if (len(mine_marked) + len(safe_marked)) > 0:
                    print(f'====> 根据方法一确定：{new_mine_marked} {new_safe_marked}')
                    break

                # 刷新一下
                try:
                    if len(constraints) > 1000:
                        break
                    new_constraints = self.refresh_constraints(constraints, new_constraints, 500)
                except:
                    return False

                if len(new_constraints) == 0:
                    break


            # 3. 如果不可以，那就小范围穷举，检查是否有的格子一定是雷或者一定是安全的
            if (len(mine_marked) == 0 and len(safe_marked) == 0):
                new_mine_marked, new_safe_marked = self.solve_by_force(constraints, 10, 100)
                print(f'====> 根据方法二确定：{new_mine_marked} {new_safe_marked}')
                mine_marked.update(new_mine_marked)
                safe_marked.update(new_safe_marked)

            # 4. 如果还是不行，那么就要回溯全局求解了
            if (len(mine_marked) == 0 and len(safe_marked) == 0):
                # V1: 我们直接遍历所有的未知点，为了加速，我们先粗略计算每个坐标是雷的概率
                # V2: 遍历所有的组合，如果某个组合中都能 continue 才进行下一个组合

                scores = []
                coordinates_list = []
                # 只选择确定雷数的
                for coordinates, (min_mine_count, max_mine_count) in constraints.items():
                    if max_mine_count == min_mine_count:
                        score = math.comb(len(coordinates), min_mine_count)
                        scores.append(score)
                        coordinates_list.append(coordinates)

                # 排序，优先选择 scores 最低的
                idx = sorted(range(len(scores)), key=lambda i: scores[i])
                coordinates_list = [coordinates_list[i] for i in idx]
                scores = [scores[i] for i in idx]

                table_bak = self.table.copy()

                # 每次尝试去暴力遍历，直到找到一个确定解
                for i in range(len(coordinates_list)):
                    coordinates = coordinates_list[i]
                    min_mine_count, max_mine_count = constraints[coordinates]


                    combinations = []
                    for idx, marked_mine_coordinates in enumerate(itertools.combinations(coordinates, min_mine_count)):
                        combinations.append(tuple(marked_mine_coordinates))
                    
                    # 打乱顺序
                    random.shuffle(combinations)

                    # 所有 True 的结果中的可行解
                    common_mine_coordinates = set()
                    common_safe_coordinates = set()

                    ok_count, error_count = 0, 0
                    for idx, marked_mine_coordinates in enumerate(combinations):
                        self.table = table_bak.copy()
                        for coordinate in coordinates:
                            if coordinate not in marked_mine_coordinates:
                                self.table[coordinate[0], coordinate[1]] = 'question'
                            else:
                                self.table[coordinate[0], coordinate[1]] = 'mine'

                        self.refresh_table(refresh_by_screenshot=False)

                        info1 = f'====> 尝试方法三暴力遍历（{idx}/{len(combinations)}）（{i}/{len(coordinates_list)}）；'
                        info2 = f'坐标: {marked_mine_coordinates}；'
                        info3 = f'剩余雷数: {self.mine_count}；未知格: {self.unknown_count}；'
                        is_ok = self.solve_by_backtracking(depth=1)

                        info4 = f'结果 = {is_ok}'
                        print(info1 + info2 + info3 + info4)

                        if not is_ok:
                            error_count += 1
                        else:
                            ok_count += 1

                        # 如果不在回溯中，并且前面遍历都失败了，那说明一定是最后一个解了，可以退出
                        if error_count == len(combinations) - 1 and idx == len(combinations) - 2:
                            marked_mine_coordinates = combinations[-1]
                            common_mine_coordinates = set(marked_mine_coordinates)
                            common_safe_coordinates = set(coordinates) - common_mine_coordinates
                            break

                        # 为了加速，如果雷只有一个，并且这次失败了，那么可以立刻返回，标识这里的位置为非雷
                        if not is_ok and len(marked_mine_coordinates) == 1:
                            common_mine_coordinates = set()
                            # 这里不要混了，这是失败的时候做的，所以此次失败时候的推测 mine 应该是 safe
                            common_safe_coordinates = set(marked_mine_coordinates)
                            break

                        # len == 1 其实没有必要搞了
                        if is_ok and len(marked_mine_coordinates) > 1:
                            now_mine_coordinates = set(marked_mine_coordinates)
                            now_safe_coordinates = set(coordinates) - now_mine_coordinates

                            # 如果是第一次成功，那么就是当前的推测；否则，取交集
                            if ok_count == 1:
                                common_mine_coordinates = now_mine_coordinates
                                common_safe_coordinates = now_safe_coordinates
                            else:
                                common_mine_coordinates = common_mine_coordinates & now_mine_coordinates
                                common_safe_coordinates = common_safe_coordinates & now_safe_coordinates
                            
                            # 加速：如果猜测雷是多个组合
                            # 如果这次是 True，并且取完交集之后，发现为空：那么提前退出，继续遍历其他组合也没有意义了
                            if len(common_mine_coordinates) == 0 and len(common_safe_coordinates) == 0:
                                common_mine_coordinates = set()
                                common_safe_coordinates = set()
                                print(f'提前退出，因为取完交集之后，发现为空')
                                break

                    for coordiante in common_mine_coordinates:
                        mine_marked.add(coordiante)
                    for coordiante in common_safe_coordinates:
                        safe_marked.add(coordiante)

                    if len(mine_marked) > 0 or len(safe_marked) > 0:
                        break

                    # 到这里了，如果没有可行解，一定不可能
                    if ok_count == 0:
                        raise ValueError(f'not is_in_backtracking, but No way to continue')

                # 保存现场
                self.table = table_bak.copy()

            # 我不相信还找不到... 如果还找不到，就退出
            if len(mine_marked) == 0 and len(safe_marked) == 0:
                # return True
                print('找不到解')
                self.print_table(self.table)
                print(constraints)
                exit(0)
                return False

            # 如果正在回溯中，那么就只是标记一下；不真正点击
            for coordinate in mine_marked:
                print(f'Mine: {coordinate}')
                self.table[coordinate[0], coordinate[1]] = 'mine'
                self.window_analyzer.click_cell(coordinate[0], coordinate[1], 'right')

            for coordinate in safe_marked:
                print(f'Safe: {coordinate}')
                self.table[coordinate[0], coordinate[1]] = 'question' # 这里就是标记一下，之后会 refresh_table 读取成真正的内容
                self.window_analyzer.click_cell(coordinate[0], coordinate[1], 'left')

            self.refresh_table(refresh_by_screenshot=False)
            if self.mine_count == 0 and self.unknown_count == 0:
                return self.check_rules(self.table)

            if len(safe_marked) > 0:
                self.refresh_table(refresh_by_screenshot=True)

            self.print_table(self.table)

            return self.solve_one()
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False

    # 回溯剪枝求解，最后一定弄出一个结果来
    def solve_by_backtracking(self, depth: int) -> bool:
        """
        求解某个 Table，如果没有确定解，则会你先回溯剪枝
        """

        PRINT_FLAG = (depth < 10)
        def my_print(*args, **kwargs):
            if PRINT_FLAG:
                print(*args, **kwargs)

        if depth > 100:
            raise ValueError(f'depth > 40: {depth}')

        if self.mine_count > self.unknown_count:
            return False

        if not self.check_rules(self.table):
            return False

        # 退出条件：雷 = 0，unkown = 0
        if self.mine_count == 0 and self.unknown_count == 0:
            return True

        try:
            constraints = self.create_table_constraints(self.table, self.mine_count)
        except:
            return False

        mine_marked, safe_marked = set(), set()

        try:
            new_constraints = constraints.copy()
            # for refresh_count in range(10):
            while True:
                # 1. 检查是否有哪个数字可以直接告诉我们信息
                try:
                    new_mine_marked, new_safe_marked = self.solve_by_ensure(constraints)
                except Exception as e:
                    # 这里是有可能出错的，因为有的时候暴力去猜，到最后可能出错
                    return False

                mine_marked.update(new_mine_marked)
                safe_marked.update(new_safe_marked)

                # 如果找到确定解，那么退出
                if (len(mine_marked) + len(safe_marked)) > 0:
                    my_print(f'{depth:02d}' + '--'*(depth+1) + f'--> 根据方法一确定：{new_mine_marked} {new_safe_marked}')
                    break

                # 刷新一下
                try:
                    if len(constraints) > 1000:
                        break
                    new_constraints = self.refresh_constraints(constraints, new_constraints, 500)
                    # print(f'num_updated: {len(new_constraints)}, constraints: {len(constraints)}')
                except:
                    return False

                if len(new_constraints) == 0:
                    break

                # # 如果刷新的不多，那么也可以提前退出
                # if (num_updated < 10) and (len(constraints) > 200):
                #     break

            # 3. 如果不可以，那就小范围穷举，检查是否有的格子一定是雷或者一定是安全的
            # --> 回溯过程，不进行穷举

            # 4. 如果还是不行，那么就要回溯全局求解了
            if (len(mine_marked) == 0 and len(safe_marked) == 0):
                # V1: 我们直接遍历所有的未知点，为了加速，我们先粗略计算每个坐标是雷的概率
                # V2: 遍历所有的组合，如果某个组合中都能 continue 才进行下一个组合

                scores = []
                coordinates_list = []
                # 只选择确定雷数的
                for coordinates, (min_mine_count, max_mine_count) in constraints.items():
                    if len(coordinates) < 30 and max_mine_count == min_mine_count:
                        score = math.comb(len(coordinates), min_mine_count)
                        scores.append(score)
                        coordinates_list.append(coordinates)

                    # # 一个很特殊的情况，如果某个坐标可以确定有雷或无雷，则对这个坐标也进行处理
                    # if len(coordinates) == 1 and min_mine_count == 0:
                    #     scores.append(1)
                    #     coordinates_list.append(coordinates)

                # 排序，优先选择 scores 最低的
                idx = sorted(range(len(scores)), key=lambda i: scores[i])
                coordinates_list = [coordinates_list[i] for i in idx]
                scores = [scores[i] for i in idx]

                table_bak = self.table.copy()

                # 每次尝试去暴力遍历，直到找到一个确定解
                for i in range(len(coordinates_list)):
                    coordinates = coordinates_list[i]
                    min_mine_count, max_mine_count = constraints[coordinates]

                    my_print(f'{depth:02d}' + '--'*(depth+1) + f'--> 尝试方法三暴力遍历（{i}/{len(coordinates_list)}），坐标: {coordinates}, 雷数: {min_mine_count} ~ {max_mine_count}')

                    # 记录是否可以走下去
                    is_oks = dict()

                    combinations = []
                    for idx, marked_mine_coordinates in enumerate(itertools.combinations(coordinates, min_mine_count)):
                        combinations.append(tuple(marked_mine_coordinates))

                    for idx, marked_mine_coordinates in enumerate(combinations):
                        self.table = table_bak.copy()
                        for coordinate in coordinates:
                            if coordinate not in marked_mine_coordinates:
                                self.table[coordinate[0], coordinate[1]] = 'question'
                            else:
                                self.table[coordinate[0], coordinate[1]] = 'mine'

                        self.refresh_table(refresh_by_screenshot=False)

                        info_str1 = f'暴力推测 {marked_mine_coordinates} ({idx}/{len(combinations)})'
                        info_str2 = f'剩余雷数： {self.mine_count}；未知格： {self.unknown_count}'
                        my_print(f'{depth:02d}' + '--'*(depth+1) + f'--> {info_str1}；{info_str2}')

                        is_ok = self.solve_by_backtracking(depth=depth+1)
                        my_print(f'{depth:02d}' + '--'*(depth+1) + f'--> {info_str1} 的结果：{is_ok}')

                        is_oks[marked_mine_coordinates] = is_ok

                        # 如果在回溯中，一旦发现有解，说明这是一条通的路，立刻返回
                        if is_ok:
                            return True

                    my_print()

                    if len(safe_marked) > 0:
                        break

                    # 如果正在回溯中，发现所有路都不通，那么说明这个解也是不可能的
                    good_combinations = [k for k, v in is_oks.items() if v]
                    if len(good_combinations) == 0:
                        my_print(f'{depth:02d}' + '--'*(depth+1) + f'--> 所有路都不通')
                        return False

                # 保存现场
                self.table = table_bak.copy()

            # 我不相信还找不到... 如果还找不到，就退出
            if len(mine_marked) == 0 and len(safe_marked) == 0:
                # print(f'{depth:02d}' + '--'*(depth+1) + f'--> 找不到解')
                return True
                # self.print_table(self.table)
                # print(constraints)
                # exit(0)
                return False

            # 如果有坐标既是雷又是安全的，那么一定不可能
            if len(mine_marked & safe_marked) > 0:
                my_print(f'{depth:02d}' + '--'*(depth+1) + f'--> 有坐标既是雷又是安全的')
                return False

            # 如果正在回溯中，那么就只是标记一下；不真正点击
            for coordinate in mine_marked:
                self.table[coordinate[0], coordinate[1]] = 'mine'
            for coordinate in safe_marked:
                self.table[coordinate[0], coordinate[1]] = 'question'

            self.refresh_table(refresh_by_screenshot=False)
            if self.mine_count == 0 and self.unknown_count == 0:
                return self.check_rules(self.table)

            return self.solve_by_backtracking(depth=depth)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False


    def solve(self, rounds: int = 200):
        for i in range(rounds):
            print(f'处理第 {i} 个表格.......................')

            self.init()
            self.print_table(self.table)

            t1 = time.time()
            is_done = self.solve_one()

            print(is_done)
            t2 = time.time()
            print(f'处理时间：{t2 - t1} 秒')

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
                # self.print_table(self.table)
                # print(coordinates, min_mine_count, max_mine_count)
                raise ValueError(f'min_mine_count > max_mine_count: {min_mine_count} > {max_mine_count}')

        return (new_mine_marked, new_safe_marked)
                

    def solve_by_force(self, constraints: dict, thresh: int, max_count: int = None):
        scores = []
        coordinates_list = []
        # 只选择确定雷数的
        for coordinates, (min_mine_count, max_mine_count) in constraints.items():
            # 这里一开始强制是 min==max，但其实没必要，这里应该是有雷的坐标
            # 只尝试 20 种
            if len(coordinates) < 20 and max_mine_count - min_mine_count < 3 and min_mine_count > 0:
                score = math.comb(len(coordinates), min_mine_count)
                if score < thresh:
                    scores.append(score)
                    coordinates_list.append(coordinates)

        # 排序，优先选择 scores 最低的
        idx = sorted(range(len(scores)), key=lambda i: scores[i])
        coordinates_list = [coordinates_list[i] for i in idx]
        scores = [scores[i] for i in idx]

        if max_count is not None:
            scores = scores[:max_count]
            coordinates_list = coordinates_list[:max_count]

        # 为了加速，每次猜测之后都保存结果，顶多保存 8x8=64 份，内存是够用的
        record_tables = dict()

        # 每次尝试去暴力遍历，直到找到一个确定解
        for i in range(len(coordinates_list)):
            # 临时把 print 关掉
            # sys.stdout = open(os.devnull, 'w')
            # sys.stderr = open(os.devnull, 'w')

            coordinates = coordinates_list[i]
            min_mine_count, max_mine_count = constraints[coordinates]

            print(f'尝试方法二暴力遍历（{i}/{len(coordinates_list)}），坐标: {coordinates}, 雷数: {min_mine_count} ~ {max_mine_count}')

            table_bak = self.table.copy()

            # 从 coordinates 中随机选择 mine_count 个坐标，设置为 mine
            tables = []
            assumptions = []
            for idx, marked_mine_coordinates in enumerate(itertools.combinations(coordinates, min_mine_count)):
                # sys.stdout = sys.__stdout__
                # print(idx, '-->', marked_mine_coordinates)
                # sys.stdout = open(os.devnull, 'w')

                self.table = table_bak.copy()
                for coordinate in marked_mine_coordinates:
                    self.table[coordinate[0], coordinate[1]] = 'mine'
                # 尝试五次分析
                if marked_mine_coordinates in record_tables:
                    is_ok, self.table = record_tables[marked_mine_coordinates]
                else:
                    is_ok = self.deduce_table_with_assumptions(try_count=5)
                    record_tables[marked_mine_coordinates] = (is_ok, self.table.copy())
                print(f'猜测 {marked_mine_coordinates} 的结果: {is_ok}')
                if is_ok:
                    tables.append(self.table.copy())
                    assumptions.append(marked_mine_coordinates)

                else:
                    # 如果这次失败了，并且猜测的数量只有一个，说明此时猜测的位置一定不能是雷
                    if len(marked_mine_coordinates) == 1:
                        # 恢复现场 
                        self.table = table_bak.copy()
                        return (set(), set(marked_mine_coordinates))

                    # 如果这次失败了，并且猜测的数量是总数量减去一个，说明剩下的那个位置一定是雷
                    marked_safe_coordinates = []
                    for coordinate in coordinates:
                        if coordinate not in marked_mine_coordinates:
                            marked_safe_coordinates.append(coordinate)
                    if len(marked_safe_coordinates) == 1:
                        # 恢复现场 
                        self.table = table_bak.copy()
                        return (set(marked_safe_coordinates), set())


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
            
            # # 恢复 print
            # sys.stdout = sys.__stdout__
            # sys.stderr = sys.__stderr__

            # 恢复现场 
            self.table = table_bak.copy()

            # print(f'本次遍历结果: mine={new_mine_marked}, safe={new_safe_marked}')
            if len(new_mine_marked) > 0 or len(new_safe_marked) > 0:
                return (new_mine_marked, new_safe_marked)

        return (set(), set())



if __name__ == "__main__":
    is_Q = False
    is_C = False
    is_T = False
    is_D = True
    weeper = Weeper(None, mine_total=26, is_Q=is_Q, is_C=is_C, is_T=is_T, is_D=is_D)
    weeper.solve(10)
    weeper.window_analyzer.click_goto_next_level()

    # table = np.array([
    #     [' ', '*', '1', '0', '?', '*', '?', '*'],
    #     ['*', '3', '2', '?', '3', '4', '*', '*'],
    #     ['?', '*', '3', '2', '*', '*', '4', '?'],
    #     ['?', '*', '*', '?', '5', '*', '2', '0'],
    #     ['*', '6', '*', '*', '*', '3', '?', '0'],
    #     ['*', '?', '*', '?', '5', '*', '4', '?'],
    #     ['*', '3', '2', '*', '3', '*', '*', '*'],
    #     ['?', '1', '?', '1', '2', '?', '*', '*'],
    # ]).astype(object)

    # # '2'-> 2, ?->question, ' '->unknown, '*'->mine
    # for i in range(table.shape[0]):
    #     for j in range(table.shape[1]):
    #         if table[i, j] == '?':
    #             table[i, j] = 'question'
    #         elif table[i, j] == ' ':
    #             table[i, j] = 'unknown'
    #         elif table[i, j] == '*':
    #             table[i, j] = 'mine'
    #         else:
    #             table[i, j] = table[i, j]

    # weeper = Weeper(table, mine_total=26, is_Q=is_Q, is_C=is_C)
    # weeper.refresh_table(refresh_by_screenshot=False)
    # weeper.print_table(weeper.table)
    # is_done = weeper.solve_by_backtracking(depth=0, is_in_backtracking=False)
    # print(is_done)

    # weeper.refresh_table(refresh_by_screenshot=False)
    # weeper.print_table(weeper.table)
    # constraints = weeper.create_table_constraints(weeper.table, weeper.mine_count)

    # for _ in range(5):
    #     weeper.refresh_constraints(constraints, 500)
    #     print(f'len(constraints): {len(constraints)}')
    #     for coordinates, (min_mine_count, max_mine_count) in constraints.items():
    #         print(f'coordinates: {coordinates}, {min_mine_count} ~ {max_mine_count}')

    # # weeper.solve_one()