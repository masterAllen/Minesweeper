'''
[T]: 雷不能构成三连
'''
import numpy as np
import utils

def create_constraints(table: np.ndarray) -> dict:
    results = dict()

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

                if len(unknowns) == 0:
                    raise ValueError(f'某个三连区域全部是雷，坐标：{triplet}')
                
                # 如果有 unknown，添加约束：最多 2 - mine_count 个雷
                if len(unknowns) > 0:
                    results[tuple(unknowns)] = (0, 2 - mine_count)
    return results

def is_legal(table: np.ndarray) -> bool:
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