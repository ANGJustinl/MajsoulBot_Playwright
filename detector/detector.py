import logging
import numpy as np
from ultralytics import YOLO
from paddleocr import PaddleOCR
import supervision as sv
import cv2
import os
import torch

def area(xyxy):
    return 0 if xyxy[2] < xyxy[0] or xyxy[3] < xyxy[1] else (xyxy[2] - xyxy[0]) * (xyxy[3] - xyxy[1])

def iou_ratio(xyxy_1, xyxy_2):
    xyxy_u = (
        max(xyxy_1[0], xyxy_2[0]), max(xyxy_1[1], xyxy_2[1]), min(xyxy_1[2], xyxy_2[2]), min(xyxy_1[3], xyxy_2[3]))
    area_u = area(xyxy_u)
    return 0 if area_u == 0 else area_u / (area(xyxy_1) + area(xyxy_2) - area_u)

class Detector:
    def __init__(self):
        weight_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mahjong.pt')
        self.mahjong_model = YOLO(weight_path, verbose=False)
        weight_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'majsoul_UI.pt')
        self.majsoul_model = YOLO(weight_path, verbose=False)
        self.ocr_model = PaddleOCR(lang='ch')
        logging.getLogger("ppocr").setLevel(logging.WARNING)  # verbose=False 以及这行都是用来不显示调试信息的
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f'device: {device}')
        self.mahjong_model = self.mahjong_model.to(device)
        self.majsoul_model = self.majsoul_model.to(device)

    def detect_tiles(self, image=None):
        height, width = len(image), len(image[0])
        left, right, top, bottom = width//10, width//10*9, height//4*3, height
        # left, right, top, bottom = 0, width, 0, height
        image = image[top: bottom, left: right]  # hand region
        results = self.mahjong_model.predict(source=image, imgsz=(224, 1024), augment=True)

        detections = sv.Detections.from_ultralytics(results[0])
        xyxy_ = np.array(detections.xyxy.tolist())
        confidence_ = detections.confidence
        tiles_ = detections.data['class_name'].tolist()

        if len(tiles_):
            # what is a tile looks like?
            feature_funcs = [
                lambda a: a[:, 2] - a[:, 0],  # width
                lambda a: a[:, 3] - a[:, 1],  # height
                lambda a: a[:, 3] + a[:, 1],  # sum_y
                lambda a: (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1])  # area
            ]
            features = np.array([func(xyxy_) for func in feature_funcs])
            medians = np.median(features, axis=1)
            
            # Calculate relative differences for all features at once
            rel_diff = np.abs(features - medians[:, np.newaxis]) / np.maximum(features, medians[:, np.newaxis])
            valid_mask = np.all(rel_diff < 0.2, axis=0)
            
            xyxy_ = xyxy_[valid_mask].tolist()
            confidence_ = confidence_[valid_mask].tolist()
            tiles_ = [t for t, m in zip(tiles_, valid_mask) if m]

            if len(xyxy_):
                tile_width = np.median([x[2] - x[0] for x in xyxy_])
                left_margin = min(x[0] for x in xyxy_)
                
                n_tiles = 160
                xyxy = [None] * n_tiles
                tiles = [None] * n_tiles
                confidence = np.full(n_tiles, -1.0)
                
                positions = np.array([int(round(float(x[0] - left_margin) / tile_width)) for x in xyxy_])
                for i, pos in enumerate(positions):
                    if pos < n_tiles and confidence_[i] > confidence[pos]:
                        confidence[pos] = confidence_[i]
                        xyxy[pos] = xyxy_[i]
                        tiles[pos] = tiles_[i]

                for i in range(1, 12):
                    if (tiles[i] is None and tiles[i-1] == tiles[i+1] and 
                        tiles[i-1] is not None):
                        tiles[i] = tiles[i-1]
                        xyxy[i] = [xyxy[i-1][2], xyxy[i-1][1], 
                                 xyxy[i+1][0], xyxy[i+1][3]]

                valid_indices = [i for i, x in enumerate(xyxy) if x is not None]
                xyxy = [xyxy[i] for i in valid_indices]
                tiles = [tiles[i] for i in valid_indices]

                for box in xyxy:
                    box[0] += left
                    box[1] += top
                    box[2] += left
                    box[3] += top
            else:
                xyxy = []
                tiles = []
        else:
            xyxy = []
            tiles = []

        return xyxy, tiles

    def detect_frame(self, image=None):
        height, width = len(image), len(image[0])
        results = self.majsoul_model.predict(source=image, augment=True)

        detections = sv.Detections.from_ultralytics(results[0])
        xyxy = np.array(detections.xyxy.tolist())
        confidence = detections.confidence
        buttons = detections.data['class_name'].tolist()

        if len(buttons):
            # Calculate IoU matrix
            n = len(xyxy)
            ious = np.zeros((n, n))
            for i in range(n):
                for j in range(i+1, n):
                    ious[i,j] = iou_ratio(xyxy[i], xyxy[j])
                    ious[j,i] = ious[i,j]
            
            # Create mask for high confidence predictions
            mask = np.ones(n, dtype=bool)
            for i in range(n):
                overlaps = ious[i] > 0.5
                if any(overlaps & (confidence > confidence[i])):
                    mask[i] = False
            
            xyxy = xyxy[mask].tolist()
            buttons = [b for b, m in zip(buttons, mask) if m]
        else:
            xyxy = []
            buttons = []

        return xyxy, buttons

    def detect_characters(self, image=None):
        height, width = len(image), len(image[0])
        image[int(height * 0.2): int(height * 0.6), 
              int(width * 0.1):] = 0
        
        result = self.ocr_model.ocr(image, cls=False)
        return_dict = {}
        
        keyword_map = {
            '终局': 'zhongju',
            '确认': 'queren',
            '再来一场': 'zailaiyichang',
            '理和鸣切拔': 'lhmqb'
        }
        
        for res in result:
            for line in res:
                xyxy = (line[0][0][0], line[0][0][1], line[0][2][0], line[0][2][1])
                text = line[1][0]
                
                if text in keyword_map:
                    if text == '确认':
                        if 'queren' in return_dict:
                            return_dict['2queren'] = True
                            if xyxy[0] < return_dict['queren'][0]:
                                return_dict['queren'] = xyxy
                        else:
                            return_dict['queren'] = xyxy
                    elif text == '再来一场' and xyxy[1] > height // 2:
                        return_dict[keyword_map[text]] = xyxy
                    else:
                        return_dict[keyword_map[text]] = xyxy
        
        return return_dict
