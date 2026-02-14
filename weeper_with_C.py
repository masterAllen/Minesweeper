'''
扫雷游戏类
'''
from multiprocessing import Value
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

import numpy as np
from typing import Iterator
from window_analyzer import WindowAnalyzer
import itertools
import math
import collections
import time
import threading
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
    def __init__(self, table: np.ndarray, mine_total: int, is_Q: bool = False, is_C: bool = False) -> None:
        self.mine_total = mine_total
        self.mine_count = mine_total
        self.unknown_count = None
        self.table = table

        self.is_Q = is_Q
        self.is_C = is_C
        
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

    def is_eight_connected(self, table: np.ndarray) -> bool:
        """
        检查当前雷的坐标是否形成八连通区域（八连通：上下左右 + 四个对角线方向）
        
        Args:
            tables: 全局表格
        
        Returns:
            True 如果所有坐标八连通，False 否则
        """
        coordinates = []
        for i in range(table.shape[0]):
            for j in range(table.shape[1]):
                if table[i, j] == 'mine':
                    coordinates.append((i, j))

        if len(coordinates) == 0 or len(coordinates) == 1:
            return True
        
        # 使用 BFS 从第一个坐标开始遍历
        visited = set()
        queue = [coordinates[0]]
        visited.add(coordinates[0])

        coordinates_set = set(coordinates)
        
        # 八连通的八个方向：上下左右 + 四个对角线
        directions = [
            (-1, -1), (-1, 0), (-1, 1),  # 上左、上、上右
            (0, -1),           (0, 1),    # 左、右
            (1, -1),  (1, 0),  (1, 1)     # 下左、下、下右
        ]
        
        while queue:
            current = queue.pop(0)
            x, y = current
            
            # 检查八个方向的邻居
            for dx, dy in directions:
                neighbor = (x + dx, y + dy)
                if neighbor in coordinates_set and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        
        # 如果所有坐标都被访问到，说明是连通的
        return len(visited) == len(coordinates)

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
            for i in range(table.shape[0]):
                for j in range(table.shape[1]):
                    # 如果他是雷，四周要有一个雷
                    if table[i, j] == 'mine':
                        coordinates = []
                        already_has_mine = False
                        for dx in [-1, 0, 1]:
                            for dy in [-1, 0, 1]:
                                if dx == 0 and dy == 0:
                                    continue

                                if i+dx < 0 or i+dx >= table.shape[0] or j+dy < 0 or j+dy >= table.shape[1]:
                                    continue

                                if table[i+dx, j+dy] == 'unknown':
                                    coordinates.append((i+dx, j+dy))
                                elif table[i+dx, j+dy] == 'mine':
                                    already_has_mine = True
                                    break
                        # 如果发现四周没找到 unknown，并且也没有雷，说明肯定错了
                        if len(coordinates) == 0 and not already_has_mine:
                            raise ValueError(f'四周没找到 unknown，并且也没有雷，coordiante = ({i}, {j})')

                        # 如果发现四周有 unknown，并且没有雷，那么要这四周一定要有雷才行
                        if len(coordinates) > 0 and not already_has_mine:
                            is_update, new_min, new_max = self._update_constraints(constraints, Constraint(coordinates), 1, len(coordinates))
                            if is_update:
                                constraints[Constraint(coordinates)] = (new_min, new_max)

                    # 四周如果全是已知的，那么这块区域一定是安全的
                    if table[i, j] == 'unknown':
                        is_must_safe = True
                        for dx in [-1, 0, 1]:
                            for dy in [-1, 0, 1]:
                                if dx == 0 and dy == 0:
                                    continue

                                if i+dx < 0 or i+dx >= table.shape[0] or j+dy < 0 or j+dy >= table.shape[1]:
                                    continue

                                if table[i+dx, j+dy] == 'mine' or table[i+dx, j+dy] == 'unknown':
                                    is_must_safe = False
                                    break
                        if is_must_safe:
                            constraints[Constraint([(i, j)])] = (0, 0)

        # 全局数量也有一个约束
        if self.mine_count < 10 and self.unknown_count < 20:
            constraints[Constraint(unknown_coordinates)] = (self.mine_count, self.mine_count)
        # for coordinates, (min_mine_count, max_mine_count) in constraints.items():
        #     print(coordinates, min_mine_count, max_mine_count)
        # print('--------------------------------------------')

        return constraints


    def refresh_constraints(self, constraints: dict, thresh: int) -> int:
        # print(f'--> Constraints NUM: {len(constraints)}')
        if len(constraints) > thresh:
            return 0

        new_constraints = {}
        for A, (minA, maxA) in constraints.items():
            for B, (minB, maxB) in constraints.items():
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
                    new_constraints[A_and_B] = (new_min, new_max)

                # A_only, B_only 范围
                x_min = max(0, minA - z_max)
                x_max = min(len(A_only), maxA - z_min)
                try:
                    is_update, new_min, new_max = self._update_constraints(constraints, A_only, x_min, x_max)
                except:
                    raise ValueError(f'x_min > x_max: {x_min} > {x_max}')

                if is_update:
                    # print(f'A: {A}, minA: {minA}, maxA: {maxA}')
                    # print(f'B: {B}, minB: {minB}, maxB: {maxB}')
                    # print(f'A_only: {A_only}, x_min: {x_min}, x_max: {x_max}')
                    # print('--------------------------------------------')
                    new_constraints[A_only] = (new_min, new_max)

                y_min = max(0, minB - z_max)
                y_max = min(len(B_only), maxB - z_min)
                try:
                    is_update, new_min, new_max = self._update_constraints(constraints, B_only, y_min, y_max)
                except:
                    raise ValueError(f'y_min > y_max: {y_min} > {y_max}')

                if is_update:
                    # print(f'A: {A}, minA: {minA}, maxA: {maxA}')
                    # print(f'B: {B}, minB: {minB}, maxB: {maxB}')
                    # print(f'B_only: {B_only}, y_min: {y_min}, y_max: {y_max}')
                    # print('--------------------------------------------')
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

    # 回溯剪枝求解，最后一定弄出一个结果来
    def solve_by_backtracking(self, depth: int, is_in_backtracking: bool) -> bool:
        """
        求解某个 Table，如果没有确定解，则会你先回溯剪枝
        args:
            is_in_backtracking: 是否在回溯剪枝中，如果是则不进行刷新，否则进行刷新
        """
        if depth > 100:
            raise ValueError(f'depth > 40: {depth}')

        if self.mine_count > self.unknown_count:
            return False

        PRINT_FLAG = (depth < 3)
        def my_print(*args, **kwargs):
            if PRINT_FLAG:
                print(*args, **kwargs)

        try:
            try:
                constraints = self.create_table_constraints(self.table, self.mine_count)
            except:
                return False
            mine_marked, safe_marked = set(), set()
                
            for refresh_count in range(5):
                # 1. 检查是否有哪个数字可以直接告诉我们信息
                try:
                    new_mine_marked, new_safe_marked = self.solve_by_ensure(constraints)
                except Exception as e:
                    # 这里是有可能出错的，因为有的时候暴力去猜，到最后可能出错
                    # import traceback
                    # traceback.print_exc()
                    # self.print_table(self.table)
                    # print(f'constraints: {constraints}')
                    # print('--------------------------------------------')
                    # exit(0)
                    return False
                mine_marked.update(new_mine_marked)
                safe_marked.update(new_safe_marked)

                # 如果找到确定解，那么退出
                if (len(mine_marked) + len(safe_marked)) > 0:
                    my_print(f'{depth:02d}' + '--'*(depth+1) + f'--> 根据方法一确定：{new_mine_marked} {new_safe_marked}')
                    break

                # 刷新一下
                try:
                    num_updated = self.refresh_constraints(constraints, 500)
                except:
                    return False

                if num_updated == 0:
                    break

                # 如果刷新的不多，那么也可以提前退出
                if (num_updated < 10) and (len(constraints) > 200):
                    break

            # # 3. 如果不可以，那就小范围穷举，检查是否有的格子一定是雷或者一定是安全的
            # if (len(mine_marked) == 0 and len(safe_marked) == 0):
            #     new_mine_marked, new_safe_marked = self.solve_by_force(constraints)
            #     print(f'{depth:02d}' + '--'*(depth+1) + f'--> 根据方法二确定：{new_mine_marked} {new_safe_marked}')
            #     mine_marked.update(new_mine_marked)
            #     safe_marked.update(new_safe_marked)


            # 4. 如果还是不行，那么就要回溯全局求解了
            if (len(mine_marked) == 0 and len(safe_marked) == 0):
                # 我们直接遍历所有的未知点，但我们先粗略计算每个坐标是雷的概率
                coordinates = []

                # 为什么取消了这个？比如二选一，看起来是对的，但实际上很有可能在当前的条件下，两个都能推出有解
                # for now_coordinates, (min_mine_count, max_mine_count) in constraints.items():
                #     if min_mine_count > 0:
                #         if len(now_coordinates) < len(coordinates) or len(coordinates) == 0:
                #             coordinates = now_coordinates

                if len(coordinates) == 0:
                    for i in range(self.table.shape[0]):
                        for j in range(self.table.shape[1]):
                            if self.table[i, j] == 'unknown':
                                coordinates.append((i, j))

                # 真正的概率 --> 1/v
                probabilities = {k: 1000 for k in coordinates}
                for now_coordinates, (min_mine_count, max_mine_count) in constraints.items():
                    if len(now_coordinates) < 10 and min_mine_count == max_mine_count:
                        probability = math.comb(len(now_coordinates), min_mine_count)
                        for coordinate in now_coordinates:
                            probabilities[coordinate] = min(probabilities[coordinate], probability)

                # for coordiante in coordinates:
                #     my_print(f'P({coordiante}): {probabilities[coordiante]}')
                # my_print('----------------------------------------')

                # 根据概率来排序
                coordinates = sorted(coordinates, key=lambda x: probabilities[x])

                table_bak = self.table.copy()

                cannot_continue = set()
                for idx, coordinate in enumerate(coordinates):
                    self.table = table_bak.copy()
                    self.table[coordinate[0], coordinate[1]] = 'mine'
                    self.refresh_table(refresh_by_screenshot=False)

                    my_print(f'{depth:02d}' + '--'*(depth+1) + f'--> 暴力推测 {coordinate} ({idx}/{len(coordinates)})')
                    # self.print_table(self.table)
                    is_ok = self.solve_by_backtracking(depth=depth+1, is_in_backtracking=True)
                    my_print(f'{depth:02d}' + '--'*(depth+1) + f'--> 暴力推测 {coordinate} 的结果：{is_ok}')

                    # 这里要结合是否回溯来看待
                    # is_ok==True 表示这条路有可能走，；is_ok==False 则表示这条路一定走不通，这是一个强限制
                    # 如果不在回溯中，如果哪条路不能走了，说明这一定不能是雷；立即退出
                    # 如果在回溯中，如果哪条路能走了，说明这个回溯还是有解的，也立刻退出
                    if not is_ok:
                        cannot_continue.add(coordinate)
                        if not is_in_backtracking:
                            safe_marked.add(coordinate)
                            break
                    else:
                        if is_in_backtracking:
                            return True

                # 保存现场
                self.table = table_bak.copy()

                if not is_in_backtracking:
                    if len(cannot_continue) == len(coordinates):
                        raise ValueError(f'not is_in_backtracking, but No way to continue')

                # 如果正在回溯中，发现所有路都不通，那么说明这个解也是不可能的
                if is_in_backtracking:
                    if len(cannot_continue) == len(coordinates):
                        return False
                    return True

            # 如果正在回溯中，那么就只是标记一下；不真正点击
            # 如果不在回溯中，那么就真正点击，并且刷新表
            if is_in_backtracking:
                for coordinate in mine_marked:
                    self.table[coordinate[0], coordinate[1]] = 'mine'
                for coordinate in safe_marked:
                    self.table[coordinate[0], coordinate[1]] = 'question'
            else:
                for coordinate in mine_marked:
                    my_print(f'Mine: {coordinate}')
                    self.table[coordinate[0], coordinate[1]] = 'mine'
                    self.window_analyzer.click_cell(coordinate[0], coordinate[1], 'right')

                for coordinate in safe_marked:
                    my_print(f'Safe: {coordinate}')
                    self.table[coordinate[0], coordinate[1]] = 'question' # 这里就是标记一下，之后会 refresh_table 读取成真正的内容
                    self.window_analyzer.click_cell(coordinate[0], coordinate[1], 'left')


            self.refresh_table(refresh_by_screenshot=False)

            # 退出条件：雷 = 0，unkown = 0
            if self.mine_count == 0 and self.unknown_count == 0:
                return self.is_eight_connected(self.table)

            if len(safe_marked) > 0 and not is_in_backtracking:
                self.refresh_table(refresh_by_screenshot=True)

            if not is_in_backtracking:
                self.print_table(self.table)

            return self.solve_by_backtracking(depth=depth, is_in_backtracking=is_in_backtracking)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False


    def solve(self, rounds: int = 200):
        for i in range(rounds):
            print(f'处理第 {i} 个表格.......................')

            self.init()
            is_done = self.solve_by_backtracking(depth=0, is_in_backtracking=False)
            
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
            # 这里一开始强制是 min==max，但其实没必要，这里应该是有雷的坐标
            # 只尝试 20 种
            if len(coordinates) < 10 and max_mine_count - min_mine_count < 3 and len(coordinates_list) < 20:
                score = math.comb(len(coordinates), min_mine_count)
                if score < 20:
                    scores.append(score)
                    coordinates_list.append(coordinates)


        # 排序，优先选择 scores 最低的
        idx = sorted(range(len(scores)), key=lambda i: scores[i])
        coordinates_list = [coordinates_list[i] for i in idx]
        scores = [scores[i] for i in idx]

        # 每次尝试去暴力遍历，直到找到一个确定解
        for i in range(len(coordinates_list)):
            # 临时把 print 关掉
            # sys.stdout = open(os.devnull, 'w')
            # sys.stderr = open(os.devnull, 'w')

            coordinates = coordinates_list[i]
            min_mine_count, max_mine_count = constraints[coordinates]

            print(f'尝试方法二暴力遍历（{i/len(coordinates_list)}），坐标: {coordinates}, 雷数: {min_mine_count} ~ {max_mine_count}')


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

            # print(f'本次遍历结果: mine={new_mine_marked}, safe={new_safe_marked}')
            if len(new_mine_marked) > 0 or len(new_safe_marked) > 0:
                return (new_mine_marked, new_safe_marked)

        return (set(), set())



if __name__ == "__main__":
    is_Q = False
    is_C = True
    weeper = Weeper(None, mine_total=14, is_Q=is_Q, is_C=is_C)
    weeper.solve(50)

    # table = np.array([
    #     ['?', '?', 2, '*', '*', '?'],
    #     [' ', '2', '?', '*', '?', '1'],
    #     [' ', '5', ' ', '*', '?', '?'],
    #     ['*', '*', '*', '*', '*', ' '],
    #     ['3', '?', ' ', ' ', ' ', ' '],
    #     ['?', '*', ' ', ' ', '2', '1'],
    # ])

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
    #             table[i, j] = int(table[i, j])

    # weeper = Weeper(table, mine_total=14, is_Q=is_Q, is_C=is_C)

    # weeper.refresh_table(refresh_by_screenshot=False)
    # weeper.print_table(weeper.table)
    # constraints = weeper.create_table_constraints(weeper.table, weeper.mine_count)

    # for _ in range(5):
    #     weeper.refresh_constraints(constraints, 500)
    #     print(f'len(constraints): {len(constraints)}')
    #     for coordinates, (min_mine_count, max_mine_count) in constraints.items():
    #         print(f'coordinates: {coordinates}, {min_mine_count} ~ {max_mine_count}')

    # # weeper.solve_one()