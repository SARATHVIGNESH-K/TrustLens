import numpy as np

def calculate_iou(box1, box2):
    """
    Calculate Intersection over Union (IoU) between two bounding boxes.
    Boxes are in [x, y, w, h] format.
    """
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2
    
    # Calculate coordinates of the intersection rectangle
    x_left = max(x1, x2)
    y_top = max(y1, y2)
    x_right = min(x1 + w1, x2 + w2)
    y_bottom = min(y1 + h1, y2 + h2)
    
    if x_right < x_left or y_bottom < y_top:
        return 0.0
        
    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    
    box1_area = w1 * h1
    box2_area = w2 * h2
    
    iou = intersection_area / float(box1_area + box2_area - intersection_area)
    return iou

class FaceTracker:
    def __init__(self, iou_threshold=0.3, max_disappeared=5):
        self.next_object_id = 0
        self.objects = {}  # object_id -> last_box
        self.disappeared = {}  # object_id -> frames_disappeared
        self.iou_threshold = iou_threshold
        self.max_disappeared = max_disappeared

    def update(self, rects):
        """
        Update the tracker with a list of bounding boxes [x, y, w, h].
        Returns a dict mapping object_id to bounding box for the current frame.
        """
        if len(rects) == 0:
            for obj_id in list(self.disappeared.keys()):
                self.disappeared[obj_id] += 1
                if self.disappeared[obj_id] > self.max_disappeared:
                    del self.objects[obj_id]
                    del self.disappeared[obj_id]
            return {}

        if len(self.objects) == 0:
            for i in range(len(rects)):
                self.objects[self.next_object_id] = rects[i]
                self.disappeared[self.next_object_id] = 0
                self.next_object_id += 1
            return self.objects.copy()

        object_ids = list(self.objects.keys())
        object_boxes = list(self.objects.values())

        # Compute IoU matrix between existing objects and new rects
        iou_matrix = np.zeros((len(object_boxes), len(rects)), dtype=np.float32)
        for i, obj_box in enumerate(object_boxes):
            for j, rect in enumerate(rects):
                iou_matrix[i, j] = calculate_iou(obj_box, rect)

        # Simple greedy assignment
        assigned_objects = set()
        assigned_rects = set()
        
        updates = {}

        # Sort IoU values descending
        indices = np.dstack(np.unravel_index(np.argsort(-iou_matrix.ravel()), iou_matrix.shape))[0]
        
        for r, c in indices:
            if iou_matrix[r, c] < self.iou_threshold:
                break
            if r not in assigned_objects and c not in assigned_rects:
                obj_id = object_ids[r]
                self.objects[obj_id] = rects[c]
                self.disappeared[obj_id] = 0
                updates[obj_id] = rects[c]
                assigned_objects.add(r)
                assigned_rects.add(c)

        # Handle disappeared objects
        for r, obj_id in enumerate(object_ids):
            if r not in assigned_objects:
                self.disappeared[obj_id] += 1
                if self.disappeared[obj_id] > self.max_disappeared:
                    del self.objects[obj_id]
                    del self.disappeared[obj_id]

        # Handle new objects
        for c in range(len(rects)):
            if c not in assigned_rects:
                self.objects[self.next_object_id] = rects[c]
                self.disappeared[self.next_object_id] = 0
                updates[self.next_object_id] = rects[c]
                self.next_object_id += 1

        return updates
