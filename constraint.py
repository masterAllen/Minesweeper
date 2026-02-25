from typing import Iterator

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


class ConstraintsDict(dict):
    """
    自动处理约束更新的字典
    使用方式: constraints[coordinates] = (min_val, max_val)
    会自动合并已有约束，取交集
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def __setitem__(self, key, value):
        """
        重写赋值操作，自动处理约束合并
        key: 坐标列表/元组，会自动转换为 Constraint
        value: (min_mine_count, max_mine_count)
        """
        # 确保 key 是 Constraint 类型
        if not isinstance(key, Constraint):
            key = Constraint(key)
        
        min_mine_count, max_mine_count = value

        # 如果这个约束其实没有意义，则忽略
        if min_mine_count == 0 and max_mine_count == len(key):
            return
        
        # 空坐标不处理
        if len(key) == 0:
            return
        
        # 基本校验
        if min_mine_count > max_mine_count:
            raise ValueError(f'min_mine_count > max_mine_count: {min_mine_count} > {max_mine_count}')
        if len(key) < min_mine_count:
            raise ValueError(f'min_mine_count > len(coordinates): {min_mine_count} > {len(key)}')
        
        # 如果已存在，合并约束（取交集）
        if key in self:
            old_min, old_max = super().__getitem__(key)
            
            # 检查是否矛盾
            if min_mine_count > old_max:
                raise ValueError(f'min_mine_count > old_max: {min_mine_count} > {old_max}')
            if max_mine_count < old_min:
                raise ValueError(f'max_mine_count < old_min: {max_mine_count} < {old_min}')
            
            # 取交集
            new_min = max(min_mine_count, old_min)
            new_max = min(max_mine_count, old_max)
            
            # 只有真正更新时才赋值
            if new_min != old_min or new_max != old_max:
                super().__setitem__(key, (new_min, new_max))
        else:
            # 新约束直接添加
            super().__setitem__(key, (min_mine_count, max_mine_count))
    
    def set_force(self, key, value):
        """强制设置，不做合并检查"""
        if not isinstance(key, Constraint):
            key = Constraint(key)
        super().__setitem__(key, value)
