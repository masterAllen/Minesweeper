'''
扫雷游戏类
'''
from multiprocessing import Value
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

import random
import numpy as np
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

# 导入规则模块
from rules import V, Q, C, T, O, D, S, B, M
from constraint import Constraint, ConstraintsDict
import utils

class Weeper:
    def __init__(self, table: np.ndarray, mine_total: int, is_V: bool = True, \
        is_Q: bool = False, is_C: bool = False, is_T: bool = False, is_O: bool = False, is_D: bool = False, \
        is_S: bool = False, is_B: bool = False, is_M: bool = False) -> None:
        self.mine_total = mine_total
        self.mine_count = mine_total
        self.unknown_count = None
        self.table = table

        self.is_V = is_V
        self.is_Q = is_Q
        self.is_C = is_C
        self.is_T = is_T
        self.is_O = is_O
        self.is_D = is_D
        self.is_S = is_S
        self.is_B = is_B
        self.is_M = is_M
        
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

    def check_rules(self, table: np.ndarray) -> bool:
        """
        检查当前表格是否符合所有规则
        """
        if self.is_V and not V.is_legal(table):
            return False
        if self.is_Q and not Q.is_legal(table):
            return False
        if self.is_C and not C.is_legal(table):
            return False
        if self.is_T and not T.is_legal(table):
            return False
        if self.is_O and not O.is_legal(table, self.mine_count, self):
            return False
        if self.is_D and not D.is_legal(table, self):
            return False
        if self.is_S and not S.is_legal(table, self.mine_count, self.mine_total, self):
            return False
        if self.is_B and not B.is_legal(table, self.mine_total):
            return False
        if self.is_M and not M.is_legal(table):
            return False
        
        return True

    '''
    constraints:
        k --> 坐标集合
        v --> 雷的数量（最小值、最大值）
    '''
    def create_table_constraints(self, table: np.ndarray, mine_count: int) -> ConstraintsDict:
        constraints = ConstraintsDict()

        if self.mine_count == 0:
            self.check_rules(table)
        
        # 收集各个规则的约束
        rule_constraints_list = []
        
        if self.is_V:
            rule_constraints_list.append(V.create_constraints(table))
        if self.is_Q:
            rule_constraints_list.append(Q.create_constraints(table))
        if self.is_C:
            rule_constraints_list.append(C.create_constraints(table))
        if self.is_T:
            rule_constraints_list.append(T.create_constraints(table))
        if self.is_O:
            rule_constraints_list.append(O.create_constraints(table, mine_count))
        if self.is_D:
            rule_constraints_list.append(D.create_constraints(table))
        if self.is_S:
            rule_constraints_list.append(S.create_constraints(table, mine_count))
        if self.is_B:
            rule_constraints_list.append(B.create_constraints(table, self.mine_total))
        if self.is_M:
            rule_constraints_list.append(M.create_constraints(table))

        # 合并所有规则的约束
        for rule_constraints in rule_constraints_list:
            if rule_constraints is None:
                continue
            for coords, (min_val, max_val) in rule_constraints.items():
                constraints[coords] = (min_val, max_val)

        # 全局数量也有一个约束；不过为了防止加入之后，导致 constraints 过多，这里做个判断
        unknown_coordinates = [(i, j) for i in range(table.shape[0]) for j in range(table.shape[1]) if table[i, j] == 'unknown']
        
        is_add = False
        if len(constraints) < 100:
            is_add = True
        else:
            if self.mine_count < 10 and self.unknown_count < 30:
                is_add = True

        if is_add:
            constraints[unknown_coordinates] = (self.mine_count, self.mine_count)

        return constraints


    def refresh_constraints(self, constraints: ConstraintsDict, new_constraints: ConstraintsDict, thresh: int) -> ConstraintsDict:
        # print(f'--> Constraints NUM: {len(constraints)}')
        if len(constraints) > thresh:
            return ConstraintsDict()

        return_new_constraints = utils.refresh_constraints(constraints, new_constraints)

        # 检查各个规则
        if self.is_D:
            assert(D.check_constraints(constraints))

        return return_new_constraints


    def init(self):
        self.refresh_table(refresh_by_screenshot=True)
        # self.mine_count = self.mine_total
        
    def deduce_table_with_assumptions(self, depth: int, max_depth: int, old_constraints: ConstraintsDict, try_count: int = 5):
        # 刷新一次 Table
        self.refresh_table(refresh_by_screenshot=False)

        for _ in range(try_count):
            try:
                constraints = self.create_table_constraints(self.table, self.mine_count)
            except:
                # import traceback
                # traceback.print_exc()
                # print(f'depth = {depth}, create_constraints error')
                return False
            mine_marked, safe_marked = set(), set()

            try:
                new_constraints = constraints.copy()
                # 这里的规则和主循环有所不同，这里强制循环多次，尽可能获得足够多的 Hints，这样确保暴力破解的时候覆盖全了
                for _ in range(3):
                    new_constraints = self.refresh_constraints(constraints, new_constraints, 600)
                    if len(new_constraints) == 0:
                        break
            except:
                # 发生错误，那么就说明这个假设不应该存在，是错误
                # import traceback
                # traceback.print_exc()
                # print('refresh_constraints error')
                return False

            try:
                # 1. 检查是否有哪个数字可以直接告诉我们信息
                new_mine_marked, new_safe_marked = self.solve_by_ensure(constraints)
                mine_marked.update(new_mine_marked)
                safe_marked.update(new_safe_marked)

                # 不进行点击，也不进行刷新。只是更新是否有雷或者是否安全
                for coordinate in new_mine_marked:
                    self.table[coordinate[0], coordinate[1]] = 'mine'

                # 由于我们是在推测，所以只知道这里不是雷，没办法真正鼠标点击它查看具体的数字，所以这里标记为 question
                for coordinate in new_safe_marked:
                    self.table[coordinate[0], coordinate[1]] = 'question'

                self.refresh_table(refresh_by_screenshot=False)

                assert(self.check_rules(self.table))

            except:
                # import traceback
                # traceback.print_exc()
                # print('solve_by_ensure_with_rules error')
                return False

            try:
                # 如果没找到，也提前终止
                if len(mine_marked) == 0 and len(safe_marked) == 0:
                    # 2. 再次进行 solve_by_force，此时数量可以少一点
                    try:
                        new_mine_marked, new_safe_marked = self.solve_by_force(depth+1, max_depth, old_constraints, constraints, 9, 100)
                    except:
                        return False
                    mine_marked.update(new_mine_marked)
                    safe_marked.update(new_safe_marked)

                    # 不进行点击，也不进行刷新。只是更新是否有雷或者是否安全
                    for coordinate in new_mine_marked:
                        self.table[coordinate[0], coordinate[1]] = 'mine'

                    # 由于我们是在推测，所以只知道这里不是雷，没办法真正鼠标点击它查看具体的数字，所以这里标记为 question
                    for coordinate in new_safe_marked:
                        self.table[coordinate[0], coordinate[1]] = 'question'

                    self.refresh_table(refresh_by_screenshot=False)

                    assert(self.check_rules(self.table))
            
            except:
                # import traceback
                # traceback.print_exc()
                # print('solve_by_force error')
                return False

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
                    raise ValueError(f'solve_by_ensure_with_rules 失败')

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
                    import traceback
                    traceback.print_exc()
                    print('refresh_constraints 出错')
                    return False

                if len(new_constraints) == 0:
                    break

            # 2. 如果不可以，那就小范围穷举，检查是否有的格子一定是雷或者一定是安全的
            if (len(mine_marked) == 0 and len(safe_marked) == 0):
                new_mine_marked, new_safe_marked = self.solve_by_force(0, 0, ConstraintsDict(), constraints, 61, 100)
                print(f'====> 根据方法二确定：{new_mine_marked} {new_safe_marked}')
                mine_marked.update(new_mine_marked)
                safe_marked.update(new_safe_marked)

            # 3. 更进一步：穷举的时候再次穷举
            if (len(mine_marked) == 0 and len(safe_marked) == 0):
                new_mine_marked, new_safe_marked = self.solve_by_force(0, 1, ConstraintsDict(), constraints, 61, 100)
                print(f'====> 根据方法二（穷举+再次穷举）确定：{new_mine_marked} {new_safe_marked}')
                mine_marked.update(new_mine_marked)
                safe_marked.update(new_safe_marked)

            # 3. 如果不可以，那么尝试用暴力 + rules 去求解
            if (len(mine_marked) == 0 and len(safe_marked) == 0):
                s_mine_marked, s_safe_marked = self.solve_by_rules(constraints)
                print(f'====> 根据方法三（rules）确定：{s_mine_marked} {s_safe_marked}')
                mine_marked.update(s_mine_marked)
                safe_marked.update(s_safe_marked)


            # 4. 如果还是不行，那么就要回溯全局求解了
            if (len(mine_marked) == 0 and len(safe_marked) == 0):
                # V1: 我们直接遍历所有的未知点，为了加速，我们先粗略计算每个坐标是雷的概率
                # V2: 遍历所有的组合，如果某个组合中都能 continue 才进行下一个组合
                self.refresh_table(refresh_by_screenshot=True)

                scores = []
                coordinates_list = []
                # 只选择确定雷数的
                for coordinates, (min_mine_count, max_mine_count) in constraints.items():
                    # if max_mine_count == min_mine_count and len(coordinates) < 9:
                    if max_mine_count == min_mine_count:
                        score = math.comb(len(coordinates), min_mine_count)
                        scores.append(score)
                        coordinates_list.append(coordinates)

                # if len(coordinates_list) == 0:
                #     for coordinates, (min_mine_count, max_mine_count) in constraints.items():
                #         if max_mine_count == min_mine_count:
                #             score = math.comb(len(coordinates), min_mine_count)
                #             scores.append(score)
                #             coordinates_list.append(coordinates)

                # 排序，优先选择 scores 最低的
                idx = sorted(range(len(scores)), key=lambda i: scores[i])
                coordinates_list = [coordinates_list[i] for i in idx]
                scores = [scores[i] for i in idx]

                table_bak = self.table.copy()

                # 每次尝试去暴力遍历，直到找到一个确定解
                for i in range(len(coordinates_list)):
                    coordinates = coordinates_list[i]
                    min_mine_count, max_mine_count = constraints[coordinates]

                    print(f'坐标: {coordinates}，长度: {len(coordinates)}, 雷数: {min_mine_count} ~ {max_mine_count}')
                    if scores[i] < 1000:
                        combinations = []
                        for idx, marked_mine_coordinates in enumerate(itertools.combinations(coordinates, min_mine_count)):
                            combinations.append(tuple(marked_mine_coordinates))
                        # 打乱顺序
                        # random.shuffle(combinations)
                    else:
                        combinations = itertools.combinations(coordinates, min_mine_count)

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

                        info1 = f'====> 尝试方法三暴力遍历（{idx}/{scores[i]}）（{i}/{len(coordinates_list)}）；'
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
                        if error_count == scores[i] - 1 and idx == scores[i] - 2:
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
                self.print_table(self.table)
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
            print(f'mine_count > unknown_count: {self.mine_count} > {self.unknown_count}')
            return False

        if not self.check_rules(self.table):
            # self.print_table(self.table)
            # print('check_rules 出错')
            return False

        # 退出条件：雷 = 0，unkown = 0
        if self.mine_count == 0 and self.unknown_count == 0:
            return True

        try:
            constraints = self.create_table_constraints(self.table, self.mine_count)
        except:
            import traceback
            traceback.print_exc()
            self.print_table(self.table)
            print(f'create_constrains error')
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
                    # import traceback
                    # traceback.print_exc()
                    # print('solve_by_ensure 出错')
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
                    # import traceback
                    # traceback.print_exc()
                    print('refresh_constraints 出错')
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
                    # if len(coordinates) < 10 and max_mine_count == min_mine_count:
                    if max_mine_count == min_mine_count:
                        score = math.comb(len(coordinates), min_mine_count)
                        scores.append(score)
                        coordinates_list.append(coordinates)

                # 如果没有 coordinates_list，那就放宽条件
                # if len(coordinates_list) == 0:
                #     for coordinates, (min_mine_count, max_mine_count) in constraints.items():
                #         if max_mine_count == min_mine_count:
                #             score = math.comb(len(coordinates), min_mine_count)
                #             scores.append(score)
                #             coordinates_list.append(coordinates)

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

                    if scores[i] < 1000:
                        combinations = []
                        for idx, marked_mine_coordinates in enumerate(itertools.combinations(coordinates, min_mine_count)):
                            combinations.append(tuple(marked_mine_coordinates))
                    else:
                        combinations = itertools.combinations(coordinates, min_mine_count)

                    for idx, marked_mine_coordinates in enumerate(combinations):
                        self.table = table_bak.copy()
                        for coordinate in coordinates:
                            if coordinate not in marked_mine_coordinates:
                                self.table[coordinate[0], coordinate[1]] = 'question'
                            else:
                                self.table[coordinate[0], coordinate[1]] = 'mine'

                        self.refresh_table(refresh_by_screenshot=False)

                        info_str1 = f'暴力推测 {marked_mine_coordinates} ({idx}/{scores[i]})'
                        info_str2 = f'剩余雷数： {self.mine_count}；未知格： {self.unknown_count}'

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
                exit(0)
                # self.window_analyzer.click_skip_this_level()


    def solve_by_ensure(self, constraints: ConstraintsDict) -> tuple[set, set]:
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

    def solve_by_rules(self, constraints: ConstraintsDict) -> tuple[set, set]:
        mine_marked = set()
        safe_marked = set()

        if self.is_S:
            mine_marked, safe_marked = self.solve_by_snake(constraints)
        if self.is_O:
            mine_marked, safe_marked = self.solve_by_outer(constraints)

        return (mine_marked, safe_marked)

                

    def solve_by_force(self, depth: int, max_depth: int, old_constraints: ConstraintsDict, constraints: ConstraintsDict, thresh: int, max_count: int = None):
        def my_print(s):
            if depth < 1:
                print(s)
            else:
                pass

        if depth > max_depth:
            return set(), set()

        constraints_bak = constraints.copy()

        scores = []
        coordinates_list = []
        # 只选择确定雷数的
        for coordinates, (min_mine_count, max_mine_count) in constraints.items():
            # 这里一开始强制是 min==max，但其实没必要，这里应该是有雷的坐标
            # 但还是先优先选择 max == min
            if len(coordinates) > 9 or min_mine_count == 0:
                continue

            if min(min_mine_count, len(coordinates)-min_mine_count) > 3:
                continue

            # 如果是旧的 constraints 里面存在，那么不遍历（因为上层会遍历的）
            if coordinates in old_constraints:
                old_min, old_max = old_constraints[coordinates]
                if old_min == old_max and old_min == min_mine_count:
                    continue

            if max_mine_count == min_mine_count:
                score = math.comb(len(coordinates), min_mine_count)
                if score < thresh:
                    scores.append(score)
                    coordinates_list.append(coordinates)

            # 只有第一层才会多进行选择
            elif depth == 0 and max_mine_count - min_mine_count < 3:
                score = math.comb(len(coordinates), min_mine_count)
                if score < thresh:
                    scores.append(score * 100)
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

            my_print(f'depth = {depth}，尝试方法二暴力遍历（{i}/{len(coordinates_list)}），坐标: {coordinates}, 雷数: {min_mine_count} ~ {max_mine_count}')

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

                # 开始推测
                if marked_mine_coordinates in record_tables:
                    is_ok, self.table = record_tables[marked_mine_coordinates]
                else:
                    is_ok = self.deduce_table_with_assumptions(depth, max_depth, constraints_bak, try_count=5)
                    record_tables[marked_mine_coordinates] = (is_ok, self.table.copy())
                my_print(f'猜测 {marked_mine_coordinates} 的结果: {is_ok}')

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

            # 如果 max == mine 的时候，发现没有找到合适解，说明这个是错的
            if max_mine_count == min_mine_count and len(tables) == 0:
                raise ValueError(f'max_mine_count == min_mine_count and len(tables) == 0')

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

    def solve_by_snake(self, constraints) -> tuple[set, set]:
        '''
        基于 [S] 的规则，检查是否有可通路
        '''
        mine_marked, safe_marked = set(), set()
        path_results = dict()
        table_copy = self.table.copy()

        # [S] 规则，暴力破解，查看是否有解
        coordinates_possible = dict()
        # 优先找概率大的点
        for coordinates, (min_mine_count, max_mine_count) in constraints.items():
            if len(coordinates) > 9 or min_mine_count == 0 or min_mine_count != max_mine_count:
                continue

            score = math.comb(len(coordinates), min_mine_count)
            for coordinate in coordinates:
                coordinates_possible[coordinate] = score

        for i in range(self.table.shape[0]):
            for j in range(self.table.shape[1]):
                if self.table[i, j] == 'unknown' and (i, j) not in coordinates_possible:
                    coordinates_possible[(i, j)] = 100000

        # 优先选择小的点
        coordinates_possible = sorted(coordinates_possible.items(), key=lambda x: x[1])
        for coordinate, score in coordinates_possible:

            self.table = table_copy.copy()
            self.table[coordinate[0], coordinate[1]] = 'mine'
            self.refresh_table(refresh_by_screenshot=False)

            import utils
            now_mine_coordinates = utils.bfs_connected_region(self.table, [coordinate], connected_type=4, allowed_cell_types={'mine'})
            is_snake, head, tail = S._is_snake_and_find_endpoints(now_mine_coordinates, self.table.shape)
            if not is_snake:
                safe_marked.add(coordinate)
                break
            now_mine_coordinates = tuple(sorted(now_mine_coordinates, key=lambda x: (x[0], x[1])))

            is_ok = self.is_resolvable_by_snake(1, now_mine_coordinates, [head, tail], path_results)
            print(f'Solve By Snake: {coordinate} -> {is_ok}')
            if not is_ok:
                safe_marked.add(coordinate)
                break

        for path in path_results:
            if path_results[path] == True and len(path) == self.mine_total:
                print(path)

        # print(coordinates_possible)
        # print(safe_marked)
        # print(mine_marked)
        # exit(0)

        self.table = table_copy.copy()
        self.refresh_table(refresh_by_screenshot=False)

        return (mine_marked, safe_marked)

    def is_resolvable_by_snake(self, depth: int, mine_coordinates: tuple, endpoints: list, path_results: dict):
        '''
        递归去判断此时是否能找到合适的 [S] 蛇形路径
        mine_coordinates: 当前进行扩展的 mines
        endpoints: mines 的一/两个端点
        '''
        def my_print(*args, **kwargs):
            if depth <= 0:
                print(*args, **kwargs)
                self.print_table(self.table)
                # S.is_legal(self.table, self.mine_count, self, print_flag=True)

        import utils
        self.refresh_table(refresh_by_screenshot=False)
        if self.mine_count == 0:
            self.table[self.table == 'unknown'] = 'question'
            self.refresh_table(refresh_by_screenshot=False)

            is_ok = True
            try:
                assert(self.check_rules(self.table))
            except:
                is_ok = False
            path_results[mine_coordinates] = is_ok
            return is_ok

        # 获取可以扩展的列表
        unknown_coordinates = set()
        for endpoint in endpoints:
            for neigbor in utils.get_four_directions(endpoint, self.table.shape):
                if self.table[neigbor] == 'unknown':
                    unknown_coordinates.add(neigbor)

        # 开始遍历
        table_copy = self.table.copy()

        # 检查新扩展的列表是否符合要求，如果 deg 是 1，那么没问题；如果 deg 是 2，需要进行检查
        for coordinate in unknown_coordinates:
            self.table = table_copy.copy()
            self.table[coordinate[0], coordinate[1]] = 'mine'
            self.refresh_table(refresh_by_screenshot=False)


            mine_count = 0
            for neigbor in utils.get_four_directions(coordinate, self.table.shape):
                if self.table[neigbor] == 'mine':
                    mine_count += 1

            if mine_count > 2:
                continue

            now_mine_coordinates = None
            now_endpoints = None
            if mine_count == 2:
                now_mine_coordinates = utils.bfs_connected_region(self.table, [coordinate], connected_type=4, allowed_cell_types={'mine'})
                is_snake, head, tail = S._is_snake_and_find_endpoints(now_mine_coordinates, self.table.shape)
                if not is_snake:
                    continue
                now_endpoints = [head, tail]

            if mine_count == 1:
                now_mine_coordinates = set(mine_coordinates)
                now_mine_coordinates.add(coordinate)
                is_snake, head, tail = S._is_snake_and_find_endpoints(now_mine_coordinates, self.table.shape)
                now_endpoints = [head, tail]

            if mine_count == 0:
                self.print_table(self.table)
                print(f'minecount == 0; coordinate = {coordinate}; endpoints = {endpoints}')
                exit(0)

            now_mine_coordinates = tuple(sorted(now_mine_coordinates, key=lambda x: (x[0], x[1])))

            if now_mine_coordinates in path_results:
                if path_results[now_mine_coordinates] == True:
                    return True
                continue

            my_print(f'----'*(depth+1) + f'--> Snake depth = {depth}，坐标: {coordinate}, 候选: {unknown_coordinates}, len(path_results): {len(path_results)}')

            is_ok = True
            # while True:
            #     try:
            #         constraints = self.create_table_constraints(self.table, self.mine_count)
            #         mine_marked, safe_marked = self.solve_by_ensure(constraints)

            #         # 如果找到确定解，那么退出
            #         new_constraints = constraints.copy()
            #         while (len(mine_marked) + len(safe_marked)) == 0:
            #             if len(constraints) > 1000 or len(new_constraints) == 0:
            #                 break
            #             new_constraints = self.refresh_constraints(constraints, new_constraints, 500)
            #             mine_marked, safe_marked = self.solve_by_ensure(constraints)
            #     except Exception as e:
            #         is_ok = False
            #         break

            #     if (len(mine_marked) + len(safe_marked)) == 0:
            #         break

            #     for coordinate in mine_marked:
            #         self.table[coordinate] = 'mine'
            #     for coordinate in safe_marked:
            #         self.table[coordinate] = 'question'
            #     self.refresh_table(refresh_by_screenshot=False)

            try:
                assert(self.check_rules(self.table))
            except:
                path_results[now_mine_coordinates] = False
                # import traceback
                # traceback.print_exc()
                # self.print_table(self.table)
                # print('check_rules error, return False')
                continue

            if not is_ok:
                path_results[now_mine_coordinates] = False
                continue

            is_ok = self.is_resolvable_by_snake(depth+1, now_mine_coordinates, now_endpoints, path_results)
            if is_ok:
                path_results[now_mine_coordinates] = True
                return True

        path_results[mine_coordinates] = False
        return False

    def solve_by_outer(self, constraints) -> tuple[set, set]:
        '''
        基于 [O] 的规则，检查是否有可通路
        '''
        mine_marked, safe_marked = set(), set()
        table_copy = self.table.copy()

        # [S] 规则，暴力破解，查看是否有解
        coordinates_possible = dict()
        # 优先找概率大的点
        for coordinates, (min_mine_count, max_mine_count) in constraints.items():
            if len(coordinates) > 9 or min_mine_count == 0 or min_mine_count != max_mine_count:
                continue

            score = math.comb(len(coordinates), min_mine_count)
            for coordinate in coordinates:
                coordinates_possible[coordinate] = score

        for i in range(self.table.shape[0]):
            for j in range(self.table.shape[1]):
                if self.table[i, j] == 'unknown' and (i, j) not in coordinates_possible:
                    coordinates_possible[(i, j)] = 100000

        # 优先选择小的点
        coordinates_possible = sorted(coordinates_possible.items(), key=lambda x: x[1])
        for coordinate, score in coordinates_possible:

            self.table = table_copy.copy()
            self.table[coordinate[0], coordinate[1]] = 'mine'
            self.refresh_table(refresh_by_screenshot=False)

            is_ok = self.is_resolvable_by_outer(constraints)
            print(f'Solve By Outer: {coordinate} -> {is_ok}')
            if not is_ok:
                safe_marked.add(coordinate)
                break

        self.table = table_copy.copy()
        self.refresh_table(refresh_by_screenshot=False)

        return (mine_marked, safe_marked)

    def is_resolvable_by_outer(self, constraints):
        table_bak = self.table.copy()
        for coordinates, (min_mine_count, max_mine_count) in constraints.items():
            # 每次试一下是否能联通
            # 但还是先优先选择 max == min
            if len(coordinates) > 9 or min_mine_count == 0 or min_mine_count != max_mine_count:
                continue

            is_resolvable = False
            for idx, marked_mine_coordinates in enumerate(itertools.combinations(coordinates, min_mine_count)):
                self.table = table_bak.copy()
                for coordinate in coordinates:
                    if coordinate not in marked_mine_coordinates:
                        self.table[coordinate[0], coordinate[1]] = 'question'
                    else:
                        self.table[coordinate[0], coordinate[1]] = 'mine'

                self.refresh_table(refresh_by_screenshot=False)

                try:
                    is_resolvable = self.check_rules(self.table)
                except:
                    pass
                if is_resolvable:
                    break

            if not is_resolvable:
                return False
        return True



if __name__ == "__main__":
    is_V = False
    is_Q = False
    is_C = False
    is_T = False
    is_O = False
    is_D = False
    is_S = False
    is_B = False
    is_M = True
    weeper = Weeper(None, mine_total=26, is_V=is_V, is_Q=is_Q, is_C=is_C, is_T=is_T, is_O=is_O, is_D=is_D, is_S=is_S, is_B=is_B, is_M=is_M)
    weeper.solve(100)
    weeper.window_analyzer.click_goto_next_level()

    # table = np.array([
    #     ['?', '2', '*', '*', '*', '*', '?', ' '],
    #     ['0', '?', '*', '?', '?', '*', ' ', ' '],
    #     ['?', '1', '2', '3', '?', ' ', ' ', ' '],
    #     ['1', '?', '3', '*', '*', '?', ' ', '0'],
    #     ['?', '*', '*', '?', '*', '*', '4', '?'],
    #     [' ', ' ', ' ', ' ', '*', ' ', ' ', ' '],
    #     [' ', ' ', ' ', ' ', '*', ' ', ' ', ' '],
    #     [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
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