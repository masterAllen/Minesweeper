from typing import Iterator

class Constraint:
    """
    优化后的约束类，使用 frozenset 作为内部存储
    避免重复排序和 set 转换
    """
    __slots__ = ('_coords_set', '_coords_tuple', '_hash')
    
    def __init__(self, coordinates):
        """
        Args:
            coordinates: 坐标列表/元组/frozenset
        """
        # 直接用 frozenset 存储，避免重复转换
        if isinstance(coordinates, frozenset):
            self._coords_set = coordinates
        else:
            self._coords_set = frozenset(coordinates)
        self._coords_tuple = None  # 延迟计算
        self._hash = None  # 延迟计算
    
    @property
    def coordinates(self):
        """延迟排序，只在需要时才计算"""
        if self._coords_tuple is None:
            self._coords_tuple = tuple(sorted(self._coords_set, key=lambda x: (x[0], x[1])))
        return self._coords_tuple

    def __repr__(self) -> str:
        return f'{list(self.coordinates)}'

    def __iter__(self) -> Iterator[tuple[int, int]]:
        return iter(self._coords_set)

    def __sub__(self, other: 'Constraint') -> 'Constraint':
        # 直接用 frozenset 操作，避免创建中间对象
        return Constraint(self._coords_set - other._coords_set)

    def __and__(self, other: 'Constraint') -> 'Constraint':
        return Constraint(self._coords_set & other._coords_set)

    def __or__(self, other: 'Constraint') -> 'Constraint':
        return Constraint(self._coords_set | other._coords_set)

    def is_subset(self, other: 'Constraint') -> bool:
        return self._coords_set.issubset(other._coords_set)

    def __len__(self) -> int:
        return len(self._coords_set)

    def __hash__(self) -> int:
        if self._hash is None:
            self._hash = hash(self._coords_set)
        return self._hash

    def __eq__(self, other: 'Constraint') -> bool:
        return self._coords_set == other._coords_set


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
        min_mine_count = max(min_mine_count, 0)
        max_mine_count = min(max_mine_count, len(key))

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
                super().__setitem__(key, (int(new_min), int(new_max)))
        else:
            # 新约束直接添加
            super().__setitem__(key, (int(min_mine_count), int(max_mine_count)))
    

class ConstraintsDictV2(dict):
    """
    自动处理约束更新的字典，使用方式: constraints[coordinates] = {n1, n2, ...}
    key: 坐标列表/元组，会自动转换为 Constraint
    value: 集合，包含所有可能的雷数
    会自动合并已有约束，取交集
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        """
        重写赋值操作，自动处理约束合并
        key: 坐标列表/元组，会自动转换为 Constraint
        value: 可能的雷数
        """
        # 确保 key 是 Constraint 类型
        if not isinstance(key, Constraint):
            key = Constraint(key)
        
        # 空坐标不处理
        if len(key) == 0:
            return

        # 如果已存在，合并约束（取交集）
        if key in self:
            old_value = super().__getitem__(key)
            value = old_value & value

        if len(value) == 0:
            raise ValueError(f'len(value) == 0, key = {key}, value = {value}')

        super().__setitem__(key, value)