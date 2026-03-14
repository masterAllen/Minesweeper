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
from rules import V, Q, C, T, O, D, S, B, M, T2, D2, A, H, L, N, X, P, E, X2, K, W2, E2, W
from constraint import Constraint, ConstraintsDict
import utils
import settings

class Weeper:
    def __init__(self, table: np.ndarray, mine_total: int, is_plus: bool = False, is_hash: bool = False, \
        is_V: bool = True, is_Q: bool = False, is_C: bool = False, is_T: bool = False, \
        is_O: bool = False, is_D: bool = False, is_S: bool = False, is_B: bool = False, \
        is_M: bool = False, is_T2: bool = False, is_D2: bool = False, is_A: bool = False, \
        is_H: bool = False, is_L: bool = False, is_N: bool = False, is_X: bool = False, \
        is_P: bool = False, is_E: bool = False, is_X2: bool = False, is_K: bool = False, \
        is_W2: bool = False, is_E2: bool = False, is_W: bool = False) -> None:
        '''
        table: 当前的表格；如果为 None，则会自行调用 pywinauto 截图并解析
        mine_total: 总雷数；如果 is_plus 为 True，此时会自动解析
        is_plus: [+] 模式，即随机产生多种组合的题目；遇到 [+] 需要打开此开关；
                    为 True 时会调用 pywinauto 自行解析有哪些组合，此时 mine_total 和 后面的一系列 is_* 没有作用；
        is_hash: [#] 模式，即每个格子遵守的规则是不同的；遇到 [#] 时需要打开此开关
        '''
        self.is_plus = is_plus
        self.is_hash = is_hash

        self.mine_total = mine_total
        self.mine_count = mine_total
        self.unknown_count = None
        self.table = table
        self.table_rules = None

        self.is_V = is_V
        self.is_Q = is_Q
        self.is_C = is_C
        self.is_T = is_T
        self.is_O = is_O
        self.is_D = is_D
        self.is_S = is_S
        self.is_B = is_B
        self.is_M = is_M
        self.is_T2 = is_T2
        self.is_D2 = is_D2
        self.is_A = is_A
        self.is_H = is_H
        self.is_L = is_L
        self.is_N = is_N
        self.is_X = is_X
        self.is_P = is_P
        self.is_E = is_E
        self.is_X2 = is_X2
        self.is_K = is_K
        self.is_W2 = is_W2
        self.is_E2 = is_E2
        self.is_W = is_W

        # 如果是 [+] 或者 [#] 模式，上面的格式全部先变为 False
        if is_plus or is_hash:
            for key in settings.all_rules:
                setattr(self, f'is_{key}', False)

        if table is not None: 
            self.table_rules = self._init_rule_table(table.shape)

        if table is None:
            window_title = "Minesweeper Variants"
            self.window_analyzer = WindowAnalyzer(window_title, is_plus)

        # 启动键盘监听线程
        if KEYBOARD_AVAILABLE:
            self._start_keyboard_listener()

        self.record_tables = dict()

        # 最新更新的坐标
        self.newest_coordinates = (6, 7)

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
            time1 = time.time()
            screenshot = self.window_analyzer.capture_window_screenshot()
            print(f'capture_window_screenshot time: {time.time() - time1}')
            
            time2 = time.time()
            self.table, special_table_rules = self.window_analyzer.parse_img_to_table(screenshot)
            print(f'parse_img_to_table time: {time.time() - time2}')

            self.table_rules = self._init_rule_table(self.table.shape)

            # 如果是 [#] 模式，那么把每个单元格各自遵守的规则加进去；其实可以不用判断 is_hash 的，因为正常的时候，如果发现右下角为空，返回的时候空字符串 
            if self.is_hash:
                for i in range(self.table.shape[0]):
                    for j in range(self.table.shape[1]):
                        self.table_rules[i, j].add(special_table_rules[i, j])

        # 统计 unknown 数量
        self.unknown_count = np.sum(self.table == 'unknown')
        self.mine_count = self.mine_total - np.sum(self.table == 'mine')

    def print_table(self, table: np.ndarray):
        print(f'============ 剩余雷: {self.mine_count}，未知格: {self.unknown_count} ============')
        for i in range(table.shape[0]):
            print('-' * (table.shape[1] * 9 + 1))
            for j in range(table.shape[1]):
                print('|', end=' ')

                now_str = ''
                if table[i, j] == 'unknown':
                    now_str = ' '
                elif table[i, j] == 'mine':
                    now_str = '*'
                elif table[i, j] == 'question':
                    now_str = '?'
                else:
                    now_str = table[i, j]
                print(f' {now_str:^5} ', end='')
            print('|')
        print('-' * (table.shape[1] * 9 + 1))

        print(self.table_rules)

    def check_rules(self, table: np.ndarray, table_rules: np.ndarray) -> bool:
        """
        检查当前表格是否符合所有规则；table_rules 是每个单元格各自遵守的规则
        """
        if self.mine_count < 0 or self.unknown_count < 0:
            return False
        if self.is_V and not V.is_legal(table, table_rules):
            return False
        if self.is_Q and not Q.is_legal(table, table_rules):
            return False
        if self.is_C and not C.is_legal(table, table_rules):
            return False
        if self.is_T and not T.is_legal(table, table_rules):
            return False
        if self.is_O and not O.is_legal(table, table_rules):
            return False
        if self.is_D and not D.is_legal(table, table_rules):
            return False
        if self.is_S and not S.is_legal(table, table_rules, self.mine_count, self.mine_total):
            return False
        if self.is_B and not B.is_legal(table, table_rules, self.mine_total):
            return False
        if self.is_M and not M.is_legal(table, table_rules):
            return False
        if self.is_T2 and not T2.is_legal(table, table_rules):
            return False
        if self.is_D2 and not D2.is_legal(table, table_rules):
            return False
        if self.is_A and not A.is_legal(table, table_rules):
            return False
        if self.is_H and not H.is_legal(table, table_rules):
            return False
        if self.is_L and not L.is_legal(table, table_rules):
            return False
        if self.is_N and not N.is_legal(table, table_rules):
            return False
        if self.is_X and not X.is_legal(table, table_rules):
            return False
        if self.is_P and not P.is_legal(table, table_rules):
            return False
        if self.is_E and not E.is_legal(table, table_rules):
            return False
        if self.is_X2 and not X2.is_legal(table, table_rules):
            return False
        if self.is_K and not K.is_legal(table, table_rules):
            return False
        if self.is_W2 and not W2.is_legal(table, table_rules):
            return False
        if self.is_E2 and not E2.is_legal(table, table_rules):
            return False
        if self.is_W and not W.is_legal(table, table_rules):
            return False
        
        return True

    '''
    constraints:
        k --> 坐标集合
        v --> 雷的数量（最小值、最大值）
    '''
    def create_table_constraints(self, table: np.ndarray, table_rules: np.ndarray) -> ConstraintsDict:
        constraints = ConstraintsDict()

        if self.mine_count == 0:
            self.check_rules(table, table_rules)
        
        # 收集各个规则的约束
        rule_constraints_list = []
        
        if self.is_V:
            rule_constraints_list.append(V.create_constraints(table, table_rules))
        if self.is_Q:
            rule_constraints_list.append(Q.create_constraints(table, table_rules))
        if self.is_C:
            rule_constraints_list.append(C.create_constraints(table, table_rules, self.mine_count))
        if self.is_T:
            rule_constraints_list.append(T.create_constraints(table, table_rules))
        if self.is_O:
            rule_constraints_list.append(O.create_constraints(table, table_rules, self.mine_count))
        if self.is_D:
            rule_constraints_list.append(D.create_constraints(table, table_rules))
        if self.is_S:
            rule_constraints_list.append(S.create_constraints(table, table_rules, self.mine_count))
        if self.is_B:
            rule_constraints_list.append(B.create_constraints(table, table_rules, self.mine_total))
        if self.is_M:
            rule_constraints_list.append(M.create_constraints(table, table_rules))
        if self.is_T2:
            rule_constraints_list.append(T2.create_constraints(table, table_rules))
        if self.is_D2:
            rule_constraints_list.append(D2.create_constraints(table, table_rules))
        if self.is_A:
            rule_constraints_list.append(A.create_constraints(table, table_rules))
        if self.is_H:
            rule_constraints_list.append(H.create_constraints(table, table_rules))
        if self.is_L:
            rule_constraints_list.append(L.create_constraints(table, table_rules))
        if self.is_N:
            rule_constraints_list.append(N.create_constraints(table, table_rules))
        if self.is_X:
            rule_constraints_list.append(X.create_constraints(table, table_rules))
        if self.is_P:
            rule_constraints_list.append(P.create_constraints(table, table_rules))
        if self.is_E:
            rule_constraints_list.append(E.create_constraints(table, table_rules))
        if self.is_X2:
            rule_constraints_list.append(X2.create_constraints(table, table_rules))
        if self.is_K:
            rule_constraints_list.append(K.create_constraints(table, table_rules))
        if self.is_W2:
            rule_constraints_list.append(W2.create_constraints(table, table_rules))
        if self.is_E2:
            rule_constraints_list.append(E2.create_constraints(table, table_rules))
        if self.is_W:
            rule_constraints_list.append(W.create_constraints(table, table_rules))

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
        # 如果是 [+] 模式，自动分析有哪些 is_*
        if self.is_plus:
            time1 = time.time()
            mine_total, types = self.window_analyzer.parse_base_information()
            print(f'parse_base_information time: {time.time() - time1}')

            self.mine_total = mine_total
            self._set_rule_flags(types)

        # 如果是 [#] 模式，那些特殊的格式要设置为 True
        if self.is_hash:
            for rule in settings.rules_in_hash:
                setattr(self, f'is_{rule}', True)

        self.refresh_table(refresh_by_screenshot=True)

    def _init_rule_table(self, table_shape: tuple[int, int]) -> np.ndarray:
        table_rules = np.empty((table_shape[0], table_shape[1]), dtype=object)
        for i in range(table_shape[0]):
            for j in range(table_shape[1]):
                table_rules[i, j] = set()

        # 如果不是 [#] 模式，那么所有单元格遵守的规则都一样
        if not self.is_hash:
            considered_rules = set()
            for rule in settings.all_rules:
                if getattr(self, f'is_{rule}'):
                    considered_rules.add(rule)
            table_rules[:, :] = considered_rules
            return table_rules

        # 如果是 [#] 模式：
        # 1. 对于不在 rules_in_hash 中的规则，所有单元格遵守的规则都一样；
        # 2. 对于 rules_in_hash 中的规则，需要截图获取值的时候再加进去，也就是 refresh_table 的时候才会加进去
        for rule in settings.all_rules:
            if rule not in settings.rules_in_hash and getattr(self, f'is_{rule}'):
                for i in range(table_shape[0]):
                    for j in range(table_shape[1]):
                        table_rules[i, j].add(rule)
        return table_rules

    def _set_rule_flags(self, types: list[str]):
        """根据 type1 和 type2 设置对应的规则标志"""
        # 规则字符到属性名的映射（支持单字符和带撇号的规则）
        rule_map = {
            'V': 'is_V', 'Q': 'is_Q', 'C': 'is_C', 'T': 'is_T',
            'O': 'is_O', 'D': 'is_D', 'S': 'is_S', 'B': 'is_B',
            'M': 'is_M', 'A': 'is_A', 'H': 'is_H', 'L': 'is_L',
            'N': 'is_N', 'X': 'is_X', 'P': 'is_P', 'E': 'is_E',
            'K': 'is_K', 'W': 'is_W',
            # 带撇号的规则变体 (T' -> T2, D' -> D2, 等)
            "T'": 'is_T2', "D'": 'is_D2', "X'": 'is_X2',
            "W'": 'is_W2', "E'": 'is_E2',
            # 容易识别错误的情况
            '0': 'is_O', '5': 'is_S'
        }
        
        # 先把所有规则设置为 False
        for attr_name in settings.all_rules:
            setattr(self, f'is_{attr_name}', False)
        
        # 根据 type1 和 type2 设置对应的为 True
        for type_char in types:
            type_char = type_char.upper().strip()
            if type_char in rule_map:
                setattr(self, rule_map[type_char], True)
        
        print(f"规则设置完成: types={types}")
        
    '''
    根据现有表格，推出确定解
    '''
    def deduce_table_with_assumptions(self, try_count: int = 5):
        # 刷新一次 Table
        self.refresh_table(refresh_by_screenshot=False)

        table_hash = utils.hash_table(self.table)
        if table_hash in self.record_tables:
            is_ok, table = self.record_tables[table_hash]
            if is_ok:
                self.table = table.copy()
                return True
            else:
                return False

        mine_marked, safe_marked = set(), set()
        for _ in range(3):
            try:
                constraints = self.create_table_constraints(self.table, self.table_rules)
            except:
                import traceback
                traceback.print_exc()
                return False
            
            try:
                new_constraints = constraints.copy()
                # 这里的规则和主循环有所不同，这里强制循环多次，尽可能获得足够多的 Hints，这样确保暴力破解的时候覆盖全了
                for _ in range(try_count):
                    new_constraints = self.refresh_constraints(constraints, new_constraints, 600)
                    if len(new_constraints) == 0 or len(constraints) > 800:
                        break
            except:
                # 发生错误，那么就说明这个假设不应该存在，是错误
                import traceback
                traceback.print_exc()
                print('refresh_constraints error')
                self.record_tables[table_hash] = (False, None)
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

                self.print_table(self.table)
                assert(self.check_rules(self.table, self.table_rules))

            except:
                import traceback
                traceback.print_exc()
                print('solve_by_ensure_with_rules error')
                self.record_tables[table_hash] = (False, None)
                return False

            if len(new_mine_marked) + len(new_safe_marked) == 0:
                break

        self.record_tables[table_hash] = (True, self.table.copy())
        return True


    def solve_one(self) -> bool:
        """
        求解某个 Table，如果没有确定解，则会你先回溯剪枝
        """
        if self.mine_count > self.unknown_count:
            raise ValueError(f'mine_count > unknown_count: {self.mine_count} > {self.unknown_count}')

        if not self.check_rules(self.table, self.table_rules):
            raise ValueError(f'check_rules(self.table, self.table_rules) 失败')

        # 退出条件：雷 = 0，unkown = 0
        if self.mine_count == 0 and self.unknown_count == 0:
            return True

        try:
            self.record_tables = {}

            raw_table_bak = self.table.copy()
            mine_marked = set()
            safe_marked = set()

            if len(mine_marked) == 0 and len(safe_marked) == 0:
                for max_depth in range(2):
                    self.solve_by_oneassume(traverse_all=True, depth=1, max_depth=max_depth)

                    # 检查是否有新的解
                    for i in range(self.table.shape[0]):
                        for j in range(self.table.shape[1]):
                            if raw_table_bak[i, j] == 'unknown':
                                if self.table[i, j] == 'mine':
                                    mine_marked.add((i, j))
                                elif self.table[i, j] == 'question':
                                    safe_marked.add((i, j))

                    self.table = raw_table_bak.copy()
                    self.refresh_table(refresh_by_screenshot=False)
                    if len(mine_marked) + len(safe_marked) > 0:
                        break

            # 如果不可以，那么尝试用暴力 + rules 去求解
            if (len(mine_marked) == 0 and len(safe_marked) == 0):
                s_mine_marked, s_safe_marked = self.solve_by_rules({})
                print(f'====> 根据方法三（rules）确定：{s_mine_marked} {s_safe_marked}')
                mine_marked.update(s_mine_marked)
                safe_marked.update(s_safe_marked)

            if len(mine_marked) == 0 and len(safe_marked) == 0:
                for max_depth in range(2, 4):
                    self.solve_by_oneassume(traverse_all=True, depth=1, max_depth=max_depth)

                    # 检查是否有新的解
                    for i in range(self.table.shape[0]):
                        for j in range(self.table.shape[1]):
                            if raw_table_bak[i, j] == 'unknown':
                                if self.table[i, j] == 'mine':
                                    mine_marked.add((i, j))
                                elif self.table[i, j] == 'question':
                                    safe_marked.add((i, j))

                    self.table = raw_table_bak.copy()
                    self.refresh_table(refresh_by_screenshot=False)
                    if len(mine_marked) + len(safe_marked) > 0:
                        break
            

            # # 2. 如果不可以，那就小范围穷举，检查是否有的格子一定是雷或者一定是安全的
            # if (len(mine_marked) == 0 and len(safe_marked) == 0):
            #     new_mine_marked, new_safe_marked = self.solve_by_force(0, 0, ConstraintsDict(), constraints, 61, 100)
            #     print(f'====> 根据 ByForce 确定：{new_mine_marked} {new_safe_marked}')
            #     mine_marked.update(new_mine_marked)
            #     safe_marked.update(new_safe_marked)

            # # 3. 更进一步：穷举的时候再次穷举
            # if (len(mine_marked) == 0 and len(safe_marked) == 0):
            #     new_mine_marked, new_safe_marked = self.solve_by_force(0, 1, ConstraintsDict(), constraints, 61, 100)
            #     print(f'====> 根据方法二（穷举+再次穷举）确定：{new_mine_marked} {new_safe_marked}')
            #     mine_marked.update(new_mine_marked)
            #     safe_marked.update(new_safe_marked)

            # # 3. 如果不可以，那么尝试用暴力 + rules 去求解
            # if (len(mine_marked) == 0 and len(safe_marked) == 0):
            #     s_mine_marked, s_safe_marked = self.solve_by_rules(constraints)
            #     print(f'====> 根据方法三（rules）确定：{s_mine_marked} {s_safe_marked}')
            #     mine_marked.update(s_mine_marked)
            #     safe_marked.update(s_safe_marked)

            # # 上面有可能污染了，所以这里我就直接清空
            # self.record_tables = {}
            # if (len(mine_marked) == 0 and len(safe_marked) == 0):
            #     self.refresh_table(refresh_by_screenshot=True)

            # 我不相信还找不到... 如果还找不到，就退出
            if len(mine_marked) == 0 and len(safe_marked) == 0:
                # return True
                print('找不到解')
                self.print_table(self.table)
                exit(0)
                return False

            for coordinate in mine_marked:
                print(f'Mine: {coordinate}')
                self.table[coordinate[0], coordinate[1]] = 'mine'
                self.window_analyzer.click_cell(coordinate[0], coordinate[1], 'right')
                self.newest_coordinates = coordinate

            for coordinate in safe_marked:
                print(f'Safe: {coordinate}')
                self.table[coordinate[0], coordinate[1]] = 'question' # 这里就是标记一下，之后会 refresh_table 读取成真正的内容
                self.window_analyzer.click_cell(coordinate[0], coordinate[1], 'left')
                self.newest_coordinates = coordinate

            # 必须要在这里先刷新一下，这样可以满了之后就退出到下一关；没有这个，后面的 refresh_table 要截图识别就会失败（过关的时候有弹窗遮挡）
            self.refresh_table(refresh_by_screenshot=False)
            if self.mine_count == 0 and self.unknown_count == 0:
                return self.check_rules(self.table, self.table_rules)

            if len(safe_marked) > 0:
                self.refresh_table(refresh_by_screenshot=True)

            self.print_table(self.table)

            return self.solve_one()
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

    def solve_by_oneassume(self, traverse_all: bool = False, depth: int = 0, max_depth: int = 0) -> tuple[set, set]:
        '''
        traverse_all: 是否遍历所有的点；如果是 False，当某个点可以确定时，会直接返回，不遍历剩余点
        depth: 当前深度
        max_depth: 最大深度
        '''
        # 首先在这个基础上先推导出确定解
        is_ok = self.deduce_table_with_assumptions(try_count=5)
        if not is_ok:
            return False

        if depth > max_depth:
            return True

        # 优先找上一次附近的点，如果不是第一层，那么只考虑附近 3 个格子以内
        # 但是当未知格少的时候，考虑还是多一些
        center_thresh = None
        if self.unknown_count > 16 and depth != 1:
            center_thresh = 5
        remove_sparse = True
        possible_coordinates = utils.get_unknown_coordinates(self.table, self.newest_coordinates, center_thresh=center_thresh, remove_sparse=remove_sparse)

        # 上面的 possible_coordinates 是有可能推出的坐标；这里的 unknown_coordinates 是所有的坐标，最后要统计这个看看有没有可以确定的
        unknown_coordinates = utils.get_unknown_coordinates(self.table, self.newest_coordinates, None, False)

        for idx, point in enumerate(possible_coordinates):
            if self.table[point] != 'unknown':
                continue

            candidates = []
            table_bak = self.table.copy()

            '''
            假设是 mine
            '''
            print(f'   ' * (depth-1) + f'{point}, {idx}, {len(possible_coordinates)}: mine')
            self.table = table_bak.copy()
            self.table[point] = 'mine'
            self.newest_coordinates = point
            self.refresh_table(refresh_by_screenshot=False)

            # 进一步去推测一些别的点
            is_ok = self.solve_by_oneassume(traverse_all, depth+1, max_depth)
            if is_ok:
                candidates.append(self.table.copy())

            self.print_table(self.table)

            '''
            假设不是 mine
            '''
            print(f'   ' * (depth-1) + f'{point}, {idx}, {len(possible_coordinates)}: safe')
            self.table = table_bak.copy()
            self.table[point] = 'question'
            self.newest_coordinates = point
            self.refresh_table(refresh_by_screenshot=False)

            is_ok = self.solve_by_oneassume(traverse_all, depth+1, max_depth)
            if is_ok:
                candidates.append(self.table.copy())

            self.print_table(self.table)

            '''
            如果 candidates 为 0，说明这个推测必然不成立
            '''
            print(f'   ' * (depth-1) + f'{point}, {idx}, {len(possible_coordinates)}: {len(candidates)}')
            if len(candidates) == 0:
                return False

            '''
            查看有哪些点能是相同的，推出必然
            '''
            self.table = table_bak.copy()
            for p2 in unknown_coordinates:
                if candidates[0][p2] == candidates[-1][p2]:
                    self.table[p2] = candidates[0][p2]
            self.refresh_table(refresh_by_screenshot=False)

            # if depth == 1:
            #     self.print_table(self.table)

            '''
            如果不要遍历所有的点；检查当下是否有确定的点，如果有，那么就立刻退出
            '''
            if not traverse_all or depth == 1:
                for p2 in unknown_coordinates:
                    if self.table[p2] != 'unknown':
                        return True

        if len(unknown_coordinates) > 0:
            self.newest_coordinates = unknown_coordinates[0]
        return True


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
            elif (min_mine_count < 3 and max_mine_count < 5):
                score = math.comb(len(coordinates), min_mine_count)
                if score < thresh:
                    scores.append(score * 1000)
                    coordinates_list.append(coordinates)

        # 排序，优先选择 scores 最低的
        idx = sorted(range(len(scores)), key=lambda i: scores[i])
        coordinates_list = [coordinates_list[i] for i in idx]
        scores = [scores[i] for i in idx]

        if max_count is not None:
            scores = scores[:max_count]
            coordinates_list = coordinates_list[:max_count]

        # 为了加速，每次猜测之后都保存结果，顶多保存 8x8=64 份，内存是够用的
        record_tables = self.record_tables.copy() if depth == 0 else {}

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

        # 选择距离最近的点
        unknown_coordinates = utils.get_unknown_coordinates(self.table, self.newest_coordinates, center_thresh=None, remove_sparse=True)
        for coordinate in unknown_coordinates:

            self.table = table_copy.copy()
            self.table[coordinate[0], coordinate[1]] = 'mine'
            self.refresh_table(refresh_by_screenshot=False)

            now_mine_coordinates = utils.bfs_connected_region(self.table, [coordinate], connected_type=4, cell_types={'mine'}, types_is_allowed=True)
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
                assert(self.check_rules(self.table, self.table_rules))
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
                now_mine_coordinates = utils.bfs_connected_region(self.table, [coordinate], connected_type=4, cell_types={'mine'}, types_is_allowed=True)
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
                assert(self.check_rules(self.table, self.table_rules))
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
                    is_resolvable = self.check_rules(self.table, self.table_rules)
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
    is_M = False
    is_T2 = False
    is_D2 = False
    is_A = False
    is_H = False
    is_L = False
    is_N = False
    is_X = False
    is_P = False
    is_E = False
    is_X2 = False
    is_K = False
    is_W2 = False
    is_E2 = False
    is_W = False

    weeper = Weeper(
        None, mine_total=26, is_plus=True, is_hash=True,
        is_V=is_V, is_Q=is_Q, is_C=is_C, is_T=is_T, 
        is_O=is_O, is_D=is_D, is_S=is_S, is_B=is_B, 
        is_M=is_M, is_T2=is_T2, is_D2=is_D2, is_A=is_A,
        is_H=is_H, is_L=is_L, is_N=is_N, is_X=is_X,
        is_P=is_P, is_E=is_E, is_X2=is_X2, is_K=is_K,
        is_W2=is_W2, is_E2=is_E2, is_W=is_W
    )
    weeper.solve(100)

    # table_str = '''
    # -----------------------------
    # | 1 |   | ? |   |   | ? | * |
    # -----------------------------
    # |   | 1 | 2 | 2 |   | 2 | 2 |
    # -----------------------------
    # |   |   | 2 | * |   |   |   |
    # -----------------------------
    # |   |   | 2 | 2 |   |   |   |
    # -----------------------------
    # | 1 |   | 2 | 1 | * | * |   |
    # -----------------------------
    # | 1 |   |   | * | * | 2 | 2 |
    # -----------------------------
    # | ? |   | ? |   | 2 | * | 1 |
    # -----------------------------
    # '''

    # table_strs = table_str.split('\n')
    # tables = []
    # for i in range(2, len(table_strs)-1, 2):
    #     now_line = table_strs[i].split('|')
    #     tables.append([x.strip() for x in now_line[1:-1]])

    # table = np.array(tables).astype(object)
    # for i in range(table.shape[0]):
    #     for j in range(table.shape[1]):
    #         if table[i, j] == '?':
    #             table[i, j] = 'question'
    #         elif table[i, j] == '':
    #             table[i, j] = 'unknown'
    #         elif table[i, j] == '*':
    #             table[i, j] = 'mine'
    #         else:
    #             table[i, j] = table[i, j]

    # weeper = Weeper(
    #     table, mine_total=20, 
    #     is_V=is_V, is_Q=is_Q, is_C=is_C, is_T=is_T, 
    #     is_O=is_O, is_D=is_D, is_S=is_S, is_B=is_B, 
    #     is_M=is_M, is_T2=is_T2, is_D2=is_D2, is_A=is_A,
    #     is_H=is_H, is_L=is_L, is_N=is_N, is_X=is_X,
    #     is_P=is_P, is_E=is_E
    # )
    # weeper.refresh_table(refresh_by_screenshot=False)
    # weeper.print_table(weeper.table)
    # weeper.solve_one()