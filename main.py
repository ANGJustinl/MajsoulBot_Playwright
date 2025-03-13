import cv2
import numpy as np
from time import time, sleep
import colorama
from colorama import Fore
import datetime

from utils.click import MyClick
from utils.window import MajsoulWindow
from detector.detector import Detector
from strategy.strategy import step
from strategy.strategy import step
from config import config

class MajsoulGame:
    def __init__(self):
        # Initialize configuration from config
        self.MAX_QUEUE_TIME = config.MAX_QUEUE_TIME
        self.MAX_WAIT_TIME = config.MAX_WAIT_TIME
        self.ACCOUNT = config.ACCOUNT
        self.PASSWORD = config.PASSWORD
        self.MATCH_RANK = config.MATCH_RANK
        self.AUTO_CONTINUE = config.AUTO_CONTINUE
        
        colorama.init()
        print(Fore.WHITE)

        # Initialize Majsoul window
        try:
            self.window = MajsoulWindow(self.ACCOUNT, self.PASSWORD)
        except Exception as e:
            print(f"Failed to start: {e}")
            raise
        
        # Initialize other components
        self.click = MyClick(self.window.page)
        self.detector = Detector()
        self.step = step

        # Game state
        self.waiting = False
        self.queuing = False
        self.wait_time = None
        self.queue_time = None
        self.green_count = 0

    def is_green(self, image):
        # 获取图像的平均颜色值（BGR格式）
        mean_color = cv2.mean(image)[:3]
        b, g, r = mean_color
        print(f"RGB: {r}, {g}, {b}")  # 调试信息：输出RGB值
        
        # 计算各通道占比
        total = r + g + b
        if total == 0:  # 避免除零错误
            return False
            
        g_prop = g / total  # 绿色通道占比
        
        # 绿色判断条件优化
        
        # 1. 绿色通道为主导（绿色值大于红色和蓝色值）
        is_g_dominant = g > r and g > b
        
        # 2. 绿色与红色差值判断（降低阈值至3，适应自然绿色中含红成分较高的情况）
        is_g_red_diff = g - r > 3  # 原阈值20过高，导致误判
        
        # 3. 绿色与蓝色差值判断（保持阈值为20）
        is_g_blue_diff = g - b > 20
        
        # 4. 绿色通道占总颜色的比例判断
        is_g_proportionally_high = g_prop > 0.38  # 绿色至少占总颜色的38%
        
        # 5. 亮度判断（降低阈值至40，避免较暗绿色被错误排除）
        is_g_bright_enough = g > 40  # 原阈值50过高
        
        # 输出更详细的调试信息，便于问题诊断
        print(f"绿色主导: {is_g_dominant}, 绿-红差值: {g-r:.2f}, 绿-蓝差值: {g-b:.2f}")
        print(f"绿色占比: {g_prop:.2f}, 绿色亮度: {g:.2f}")
        
        # 综合判断条件（所有条件必须同时满足）
        return (is_g_dominant and 
                is_g_red_diff and 
                is_g_blue_diff and 
                is_g_proportionally_high and 
                is_g_bright_enough)

    def click_if_exists(self, buttons, button_name, xyxy_buttons):
        if button_name in buttons:
            self.click.click(xyxy_buttons[buttons.index(button_name)])
            return True
        return False

    def handle_matching(self, buttons, xyxy_buttons):
        """处理匹配状态"""
        print(Fore.GREEN + f'[{datetime.datetime.now()}]: 匹配中' + Fore.WHITE)
        self.waiting = False
        if self.queuing and time() - self.queue_time < self.MAX_QUEUE_TIME:
            return True

        if self.click_if_exists(buttons, '3p-east', xyxy_buttons):
            self.queuing = True
            self.queue_time = time()
            self.green_count = 0
        elif self.click_if_exists(buttons, 'match', xyxy_buttons):
            pass
        elif self.click_if_exists(buttons, self.MATCH_RANK, xyxy_buttons):
            pass

    def handle_game_end(self, char_dict, box):
        """处理终局界面"""
        print(Fore.GREEN + f'[{datetime.datetime.now()}]: 终局界面' + Fore.WHITE)
        self.waiting = self.queuing = False
        
        if ('2queren' in char_dict and 'queren' in char_dict):
            self.click.click(char_dict['queren'])
        elif 'zailaiyichang' in char_dict and self.AUTO_CONTINUE == True:
            self.click.click(char_dict['zailaiyichang'])
        elif 'queren' in char_dict:
            self.click.click(char_dict['queren'])
        else:  # 活动奖励界面，点击屏幕中间
            self.click.click((0, 0, box[2] - box[0], box[3] - box[1]))
        

    def handle_game_buttons(self, buttons, xyxy_buttons, tiles, xyxy_tiles, box):
        """处理游戏中的按钮操作"""
        self.waiting = False
        
        # Simple buttons
        for btn in ['zimo', 'he', 'babei']:
            if self.click_if_exists(buttons, btn, xyxy_buttons):
                return True

        # Handle furo (副露)
        if any(btn in buttons for btn in ['chi', 'peng', 'gang']) and \
           not any(btn in buttons for btn in ['lizhi', 'babei']):
            if 'tiaoguo' in buttons:
                self.click.click(xyxy_buttons[buttons.index('tiaoguo')])
            return True

        # Handle tile selection
        if len(tiles) == 14:
            tile, button = self.step(tiles)
            if button and button in buttons:
                self.click.click(xyxy_buttons[buttons.index(button)])
                sleep(0.3)
            if tile and tile in tiles:
                for _ in range(2):  # Double click for reliability
                    self.click.click(xyxy_tiles[tiles.index(tile)])
                    sleep(0.1)
                # Move mouse to center
                self.click.click((0, 0, box[2] - box[0], box[3] - box[1]))
            return True

        return False

    def handle_side_buttons(self, char_dict, image):
        """处理左侧按钮"""
        if 'lhmqb' not in char_dict:
            return

        xyxy = char_dict['lhmqb']
        height = (xyxy[3] - xyxy[1]) // 5
        
        if self.green_count < 5:
            for x in [0, 1, 2, 4]:  # 尝试点下五个按钮中的第x个
                left = int(xyxy[0])
                top = int(xyxy[1] + x * height)
                right = int(xyxy[2])
                bottom = int(xyxy[1] + (x + 1) * height)
                
                cropped = image[top:bottom, left:right]
                if not self.is_green(cropped):  # 不是按下状态
                    print(f"not pressed.{x}")
                    self.click.click((left, top, right, bottom))
                    self.green_count = 0
                else:
                    self.green_count += 1
        print(f"green count: {self.green_count}")

    def run(self):
        """Main game loop"""
        while True:
            try:
                # Get game window
                box = self.window()
                if not box:
                    break
                self.click.set_top_left_corner(box)

                # Get game screen
                screenshot = self.window.page.screenshot(type="jpeg", full_page=True)
                image = cv2.imdecode(np.frombuffer(screenshot, np.uint8), cv2.IMREAD_COLOR)
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

                # Detect game state
                xyxy_tiles, tiles = self.detector.detect_tiles(image)
                xyxy_buttons, buttons = self.detector.detect_frame(image)
                char_dict = self.detector.detect_characters(image)

                print(char_dict.keys())

                # Handle different game states
                if '3p-east' in buttons or 'match' in buttons or 'silver' in buttons:
                    if self.handle_matching(buttons, xyxy_buttons):
                        continue
                        
                elif 'zhongju' in char_dict or 'queren' in char_dict:
                    self.handle_game_end(char_dict, box)
                    self.green_count = 0
                    
                else:  # Game in progress
                    print(Fore.GREEN + f'[{datetime.datetime.now()}]: 游戏中' + Fore.WHITE)
                    
                    # Handle buttons
                    self.handle_side_buttons(char_dict, image)
                    
                    # Save waiting state
                    prev_waiting = self.waiting
                    if not self.handle_game_buttons(buttons, xyxy_buttons, tiles, xyxy_tiles, box):
                        # Restore waiting state if no button was handled
                        self.waiting = prev_waiting
                        
                        if not self.waiting:
                            print('begin wait.', self.wait_time)
                            self.waiting = True
                            self.wait_time = time()
                        elif time() - self.wait_time > self.MAX_WAIT_TIME:
                            print('wait long.', time())
                            self.waiting = False
                            # Click center multiple times
                            center = (0, 0, box[2] - box[0], box[3] - box[1])
                            for _ in range(7):
                                self.click.click(center)
                                sleep(0.05)

                # Keep mouse in center
                self.click.click((0, 0, box[2] - box[0], box[3] - box[1]), click=False)

            except Exception as e:
                print(f"Error in game loop: {e}")
                continue

        # Cleanup
        del self.window

if __name__ == '__main__':
    try:
        game = MajsoulGame()
        game.run()
    except Exception as e:
        print(f"Fatal error: {e}")
