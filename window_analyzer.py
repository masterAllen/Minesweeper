"""
使用 pywinauto 分析窗口结构的简单程序
"""
import os
import time
import pywinauto
from pywinauto import Application
import numpy as np
import cv2
from PIL import Image
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

        app = Application(backend="uia").connect(title=self.title)
        self.window = app.window(title=self.title)

        # 获取窗口在屏幕上左上角的位置
        window_rect = self.window.rectangle()
        self.win_left_top = [window_rect.left, window_rect.top]
        self.window_width = window_rect.right - window_rect.left
        self.window_height = window_rect.bottom - window_rect.top

        if use_ocr:
            from paddleocr import PaddleOCR
            os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
            # 初始化 PaddleOCR 实例
            self.ocr = PaddleOCR(
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False
            )

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
            screenshot = self.window.capture_as_image()
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


    def parse_img_to_table(self, screenshot: Image.Image) -> np.ndarray:
        """
        从图像中解析表格。
        """
        screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        cv2.imwrite("screenshot.png", screenshot)

        rows, cols = screenshot.shape[0:2]
        self.table_left_top = [cols*2//10, rows*2//10]
        self.table_right_bottom = [cols*8//10, rows*95//100]
        tableimg = screenshot[
            self.table_left_top[1]:self.table_right_bottom[1], 
            self.table_left_top[0]:self.table_right_bottom[0]
        ]
        # cv2.imwrite("table.png", tableimg)

        '''
        边界提取，本来是打算做直线检测等复杂算法，但是想想算了...
        更简单的方法：直接从上往下、从左往右扫，如果连续一片都是直线那就说明是框...
        '''
        rows, cols = tableimg.shape[0:2]

        # 从上往下：中间开始 1/4 到 3/4 之间
        row_border = []
        prev_is_border = False
        for i in range(rows):
            is_border = np.all(tableimg[i, int(cols*0.4):int(cols*0.6), 1] > 200)
            if is_border and not prev_is_border:
                row_border.append(i)
            prev_is_border = is_border
        
        # 从左往右：上下 1/4 到 3/4 之间
        col_border = []
        prev_is_border = False
        for j in range(cols):
            is_border = np.all(tableimg[int(rows*0.4):int(rows*0.6), j, 1] > 200)
            if is_border and not prev_is_border:
                col_border.append(j)
            prev_is_border = is_border

        self.table_left_top = [self.table_left_top[0] + col_border[0], self.table_left_top[1] + row_border[0]]
        self.cell_w, self.cell_h = col_border[1] - col_border[0], row_border[1] - row_border[0]

        '''
        每个单元格解析
        '''
        table_data = np.empty((len(row_border) - 1, len(col_border) - 1), dtype=object)
        for i in range(len(row_border) - 1):
            for j in range(len(col_border) - 1):
                cell_img = tableimg[row_border[i]:row_border[i+1], col_border[j]:col_border[j+1]]
                cell_img = cell_img[int(self.cell_h*0.1):int(self.cell_h*0.9), int(self.cell_w*0.1):int(self.cell_w*0.9)]
                cv2.imwrite(f'cell_{i}_{j}.png', cell_img)
                table_data[i, j] = self._check_cell_data(cell_img)
        return table_data

    def click_cell(self, i, j, left_or_right):
        row = self.win_left_top[1] + self.table_left_top[1] + int((i+0.5) * self.cell_h)
        col = self.win_left_top[0] + self.table_left_top[0] + int((j+0.5) * self.cell_w)
        pywinauto.mouse.move(coords=(col, row))
        time.sleep(0.2)
        pywinauto.mouse.click(coords=(col, row), button=left_or_right)

    def _check_cell_data(self, cell_img: np.ndarray) -> str:
        assert(len(cell_img.shape) == 3)

        # # 检查是否是空，判断：全部为黑
        # if np.all(cell_img[:, :, 1] < 32):
        #     return 'unknown'
        # if np.all((70 < cell_img[:, :, 1]) & (cell_img[:, :, 1] < 82)):
        #     return 'unknown'

        # 遍历 Template
        is_first = True
        best, best_score = None, 1e9
        for fname in os.listdir('templates'):
            template = cv2.imread(f'templates/{fname}')
            if is_first:
                matched = cv2.resize(cell_img, (template.shape[1], template.shape[0]))
                # is_first = False

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
        return name

    def parse_base_information(self) -> Tuple[int, str, str]:

        src = self.capture_window_screenshot()
        src = np.array(src)

        rows, cols = src.shape[0:2]
        src = src[int(rows*0.1):int(rows*0.9), int(cols*0.02):int(cols*0.98)]
        _, thresh = cv2.threshold(src, 180, 255, cv2.THRESH_BINARY)

        rows, cols = thresh.shape[0:2]
        thresh = thresh[0:int(rows*0.3), 0:int(cols*0.4)]

        rows, cols = thresh.shape[0:2]
        ratio = 500 / rows
        thresh = cv2.resize(thresh, (int(cols*ratio), int(rows*ratio)))
        cv2.imwrite('thresh.png', thresh)

        # 对示例图像执行 OCR 推理 
        result = self.ocr.predict(thresh)
        text = result[0]['rec_texts']

        assert(text[0][0] == '[' and text[0][2] == ']')
        assert(text[1][0] == '[' and text[1][2] == ']')
        assert(text[2][0] == '[' and text[2][2] == ']')

        type1 = text[1][1]
        type2 = text[2][1]

        row_text = text[0].replace('：', ':')
        mine_total = int(row_text.split(':')[1].split()[0])

        return mine_total, type1, type2


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
    table_data = analyzer.parse_img_to_table(screenshot)
    print(table_data)

    # analyzer.click_goto_next_level()
    # analyzer.click_skip_this_level()