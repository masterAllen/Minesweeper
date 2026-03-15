"""
使用 pywinauto 分析窗口结构的简单程序
"""
import os
import time
import pywinauto
from pywinauto import Application
import numpy as np
import cv2
from PIL import Image, ImageGrab
from typing import Tuple, List, Dict, Optional

class WindowAnalyzer:
    def __init__(self, title: str, use_ocr: bool = False):
        self.title = title

        # 窗口左上角位置
        self.win_left_top = None
        # 表格左上角位置
        self.table_left_top = None
        # 单元格大小
        self.cell_w = None
        self.cell_h = None

        time1 = time.time()
        app = Application(backend="win32").connect(title=self.title)
        self.window = app.window(title=self.title)
        print(f'Find Window time: {time.time() - time1}')

        # 获取窗口在屏幕上左上角的位置
        window_rect = self.window.rectangle()
        self.win_left_top = [window_rect.left, window_rect.top]
        self.window_width = window_rect.right - window_rect.left
        self.window_height = window_rect.bottom - window_rect.top

        if use_ocr:
            pass
            # from paddleocr import PaddleOCR
            # os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
            # # 初始化 PaddleOCR 实例
            # self.ocr = PaddleOCR(
            #     ocr_version="PP-OCRv4",
            #     use_textline_orientation=False,
            #     enable_mkldnn=True
            # )

    def capture_window_screenshot(self, save_path=None):
        """
        对指定窗口进行截图，返回截图和窗口对象
        返回: (screenshot, window, window_rect)
        window_rect: (x, y, width, height) 窗口在屏幕上的位置
        """
        try:
            # 截图前，需要先移动到屏幕左上角，防止鼠标影响表格
            temp_col = int(self.win_left_top[0]+self.window_width*0.2)
            temp_row = int(self.win_left_top[1]+self.window_height*0.2)
            pywinauto.mouse.click(coords=(temp_col, temp_row))
            time.sleep(0.2)
            pywinauto.mouse.click(coords=(temp_col, temp_row))
            
            print(f"正在截取窗口: {self.title}")

            # 使用 ImageGrab 按窗口坐标截图，避免 pywinauto UIA 下 capture_as_image() 的长时间延迟（约 25 秒）
            left, top = self.win_left_top[0], self.win_left_top[1]
            bbox = (left, top, left + self.window_width, top + self.window_height)
            screenshot = ImageGrab.grab(bbox=bbox)
            if save_path:
                screenshot.save(save_path)

            return screenshot

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"截图失败: {str(e)}")
            return None

    def click_skip_this_level(self):
        clicked_x = int(self.window_height * 0.14) + self.win_left_top[1]
        clicked_y = int(self.window_width * 0.82) + self.win_left_top[0]
        pywinauto.mouse.move(coords=(clicked_y, clicked_x))
        time.sleep(0.2)
        pywinauto.mouse.click(coords=(clicked_y, clicked_x))
        time.sleep(0.2)

        clicked_x = int(self.window_height * 0.79) + self.win_left_top[1]
        clicked_y = int(self.window_width * 0.68) + self.win_left_top[0]
        pywinauto.mouse.move(coords=(clicked_y, clicked_x))
        time.sleep(0.2)
        pywinauto.mouse.click(coords=(clicked_y, clicked_x))
        time.sleep(0.2)


    def click_goto_next_level(self):
        screenshot = self.capture_window_screenshot()
        screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        # rows, cols = screenshot.shape[0:2]
        # screenshot[int(rows*0.75):int(rows*0.8), int(cols*0.68):int(cols*0.7)] = [255, 0, 0]
        # cv2.imwrite("screenshot.png", screenshot)

        # TODO: 现在先强制固定的偏移位置
        clicked_x = int(self.window_height * 0.77) + self.win_left_top[1]
        clicked_y = int(self.window_width * 0.55) + self.win_left_top[0]

        # screenshot[clicked_x:clicked_x+10, clicked_y:clicked_y+10] = [255, 0, 0]
        # cv2.imwrite("screenshot.png", screenshot)

        pywinauto.mouse.move(coords=(clicked_y, clicked_x))
        time.sleep(1)
        pywinauto.mouse.click(coords=(clicked_y, clicked_x))
        time.sleep(1)


    def parse_img_to_table(self, screenshot: Image.Image) -> tuple[np.ndarray, np.ndarray]:
        """
        从图像中解析表格，返回表格中内容、表格的规则(针对 [#] 的设计，这个模式下不同格子遵守的规则并不一致)
        """
        screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        # cv2.imwrite("screenshot.png", screenshot)

        rows, cols = screenshot.shape[0:2]
        self.table_left_top = [cols*3//10, rows*2//10]
        self.table_right_bottom = [cols*7//10, rows*95//100]
        tableimg = screenshot[
            self.table_left_top[1]:self.table_right_bottom[1], 
            self.table_left_top[0]:self.table_right_bottom[0]
        ]
        cv2.imwrite("table.png", tableimg)

        '''
        边界提取，本来是打算做直线检测等复杂算法，但是想想算了...
        更简单的方法：直接从上往下、从左往右扫，如果连续一片都是直线那就说明是框...
        '''
        rows, cols = tableimg.shape[0:2]

        # 从上往下：中间开始 1/4 到 3/4 之间
        row_borders = [[]]
        for i in range(rows):
            is_border = np.all(tableimg[i, int(cols*0.4):int(cols*0.6), 1] > 180)
            if is_border:
                row_borders[-1].append(i)
            else:
                row_borders.append([])
        row_borders = [border for border in row_borders if len(border) > 0]
        row_borders = [(row_borders[i][-1]+1, row_borders[i+1][0]) for i in range(len(row_borders)-1)]
        
        # 从左往右：上下 1/4 到 3/4 之间
        col_borders = [[]]
        for j in range(cols):
            is_border = np.all(tableimg[int(rows*0.4):int(rows*0.6), j, 1] > 180)
            if is_border:
                col_borders[-1].append(j)
            else:
                col_borders.append([])
        col_borders = [border for border in col_borders if len(border) > 0]
        col_borders = [(col_borders[j][-1]+1, col_borders[j+1][0]) for j in range(len(col_borders)-1)]

        self.table_left_top = [self.table_left_top[0] + col_borders[0][0], self.table_left_top[1] + row_borders[0][0]]
        self.cell_w, self.cell_h = col_borders[0][1] - col_borders[0][0], row_borders[0][1] - row_borders[0][0]

        '''
        每个单元格解析
        '''
        table_data = np.empty((len(row_borders), len(col_borders)), dtype=object)
        table_rule = np.empty((len(row_borders), len(col_borders)), dtype=object)
        for i, (row_lo, row_hi) in enumerate(row_borders):
            for j, (col_lo, col_hi) in enumerate(col_borders):
                cell_img = tableimg[row_lo:row_hi, col_lo:col_hi]
                cv2.imwrite(f'cell_{i}_{j}.png', cell_img)
                table_data[i, j], table_rule[i, j] = self._check_cell_data(cell_img)

        return table_data, table_rule

    def click_cell(self, i, j, left_or_right):
        row = self.win_left_top[1] + self.table_left_top[1] + int((i+0.5) * self.cell_h)
        col = self.win_left_top[0] + self.table_left_top[0] + int((j+0.5) * self.cell_w)
        pywinauto.mouse.move(coords=(col, row))
        time.sleep(0.2)
        pywinauto.mouse.click(coords=(col, row), button=left_or_right)

    def _check_cell_data(self, cell_img: np.ndarray) -> tuple[str, set]:
        '''
        输入某个单元格图片，返回该单元格的内容、遵守的规则
        内容：string，如：'unknown', 'mine', 'question', '1', '1x1'([W] rule), '-2'([E'] rule)
        规则：string，单元格图片右下角代表的图，比如 'V', 'Q', 'C'
        '''

        assert(len(cell_img.shape) == 3)
        cell_img = cv2.cvtColor(cell_img, cv2.COLOR_BGR2GRAY)

        # 遍历 Template，这里可以用 Map 进行加速，但是感觉没必要了
        best, best_score = None, 1e9
        for fname in os.listdir('templates'):
            template = cv2.imread(f'templates/{fname}')
            template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

            rows, cols = template.shape[0:2]
            template[int(rows*0.7):int(rows*1.0), int(cols*0.7):int(cols*1.0)] = 0

            matched = cv2.resize(cell_img, (rows, cols))
            matched[int(rows*0.7):int(rows*1.0), int(cols*0.7):int(cols*1.0)] = 0

            # inter = np.logical_and(matched, template).sum()
            # union = np.logical_or(matched, template).sum()
            # score = inter / union
            # if score > best_score:
            #     best, best_score = fname, score

            diff = matched.astype(float) - template.astype(float)
            score = np.mean(diff**2)
            # print(f'{fname}: {score}')
            if score < best_score:
                best, best_score = fname, score

        name = best[:best.rfind('.')]
        name = name.split('_')[1]

        # 遍历 hashtags 寻找规则
        best, best_score = None, 1e9
        for fname in os.listdir('hashtags'):
            template = cv2.imread(f'hashtags/{fname}')
            template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

            rows, cols = template.shape[0:2]
            matched = cv2.resize(cell_img, (rows, cols))

            # 只比较右小角
            template = template[int(rows*0.7):int(rows*1.0), int(cols*0.7):int(cols*1.0)]
            matched = matched[int(rows*0.7):int(rows*1.0), int(cols*0.7):int(cols*1.0)]

            diff = matched.astype(float) - template.astype(float)
            score = np.mean(diff**2)
            if score < best_score:
                best, best_score = fname, score

        rule = best[:best.rfind('.')]
        rule = rule.split('_')[1]
        if rule == '0':
            rule = ''

        return name, rule

    def parse_base_information(self) -> Tuple[int, List[str]]:
        """
        解析游戏基本信息
        返回: (雷数, 规则类型列表)
        例如: "[C][W]8x8-26-11739" -> (26, ['C', 'W'])
        """
        import re
        import pytesseract

        src = self.capture_window_screenshot()
        src = np.array(src)
        src = cv2.cvtColor(src, cv2.COLOR_RGB2GRAY)

        rows, cols = src.shape[0:2]

        src = src[int(rows*0.9):int(rows*0.98), int(cols*0.06):int(cols*0.27)]
        # cv2.imwrite('src.png', src)

        # 使用 Pytesseract 识别
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        text = pytesseract.image_to_string(src, lang='eng').strip()
        print(f"OCR 识别结果: {text}")

        # 解析规则类型: 提取所有 [X] 或 [X'] 格式的内容
        # 注意: pytesseract 经常把 [ 或 ] 错误识别成 I，所以用 [\[I] 和 [\]I] 来匹配
        rule_pattern = r"[\[I]([A-Za-z]'?)[\]I]"
        rules = re.findall(rule_pattern, text)
        rules = [r.upper() for r in rules]  # 统一大写
        
        # 解析雷数: 格式为 NxN-雷数-编号，提取中间的数字
        # 例如 8x8-26-11739 中的 26
        mine_pattern = r"\d+x\d+-(\d+)-"
        mine_match = re.search(mine_pattern, text)
        if mine_match:
            mine_total = int(mine_match.group(1))
        
        print(f"解析结果: 雷数={mine_total}, 规则={rules}")
        return mine_total, rules

        # type1_img = src[int(rows*0.16):int(rows*0.19), int(cols*0.02):int(cols*0.06)]
        # type2_img = src[int(rows*0.19):int(rows*0.23), int(cols*0.02):int(cols*0.06)]
        # num_img = src[int(rows*0.12):int(rows*0.155), int(cols*0.11):int(cols*0.132)]

        # cv2.imwrite('type1.png', type1_img)
        # cv2.imwrite('type2.png', type2_img)
        # cv2.imwrite('num.png', num_img)


if __name__ == "__main__":
    print("Pywinauto 窗口分析工具")
    print("=" * 50)
    
    # 使用示例：分析指定窗口
    # 请修改下面的窗口标题为您想要分析的窗口
    window_title = "Minesweeper Variants"  # 修改为您要分析的窗口标题
    
    analyzer = WindowAnalyzer(window_title)
    # print(analyzer.parse_base_information())
    # analyzer.analyze_window_by_title()
    screenshot = analyzer.capture_window_screenshot()
    table_data, table_rule = analyzer.parse_img_to_table(screenshot)
    print(table_data)
    print(table_rule)

    # analyzer.click_goto_next_level()
    # analyzer.click_skip_this_level()
