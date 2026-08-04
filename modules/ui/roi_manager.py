import cv2
import json
import os
import uuid
import numpy as np

from modules.utils import accessibility_settings as a11y


class ROIManager:

    def __init__(self):

        self.rois = []

        self.current_polygon = []

        self.selected_roi = None

        self.dragging = False

        self.drag_start = None

    # -----------------------------------------
    # Mouse
    # -----------------------------------------

    def mouse_callback(self, event, x, y, flags, param):

        # SOL TIK

        if event == cv2.EVENT_LBUTTONDOWN:

            roi = self.find_polygon(x, y)

            # Polygon seç

            if roi is not None:

                self.selected_roi = roi

                self.dragging = True

                self.drag_start = (x, y)

                return

            # Yeni polygon noktası

            self.current_polygon.append([x, y])

        # Mouse Hareketi

        elif event == cv2.EVENT_MOUSEMOVE:

            if self.dragging and self.selected_roi is not None:

                dx = x - self.drag_start[0]
                dy = y - self.drag_start[1]

                self.move_polygon(
                    self.selected_roi,
                    dx,
                    dy
                )

                self.drag_start = (x, y)

        # SOL TUŞ BIRAK

        elif event == cv2.EVENT_LBUTTONUP:

            self.dragging = False

            self.drag_start = None

        # SAĞ TIK

        elif event == cv2.EVENT_RBUTTONDOWN:

            if len(self.current_polygon) >= 3:

                self.add_polygon()

            self.current_polygon = []

    # -----------------------------------------
    # Çizim
    # -----------------------------------------

    def draw(self, image):

        output = image.copy()

        # Kayıtlı Polygonlar

        for roi in self.rois:

            pts = np.array(
                roi["points"],
                dtype=np.int32
            )

            color = (0,255,0)

            if roi == self.selected_roi:

                color = (0,0,255)

            cv2.polylines(

                output,

                [pts],

                True,

                color,

                2

            )

            x,y = pts[0]

            cv2.putText(

                output,

                roi["name"],

                (x,y-5),

                cv2.FONT_HERSHEY_SIMPLEX,

                0.6,

                color,

                2

            )

            # Köşe noktaları

            for p in pts:

                cv2.circle(

                    output,

                    tuple(p),

                    4,

                    color,

                    -1

                )

        # Çizilen Polygon

        if len(self.current_polygon) > 0:

            pts = np.array(

                self.current_polygon,

                dtype=np.int32

            )

            cv2.polylines(

                output,

                [pts],

                False,

                (255,0,0),

                2

            )

            for p in pts:

                cv2.circle(

                    output,

                    tuple(p),

                    4,

                    (255,0,0),

                    -1

                )

        return output
    
    # -----------------------------------------
    # Polygon İşlemleri
    # -----------------------------------------

    def add_polygon(self):

        roi = {

            "id": str(uuid.uuid4()),

            "name": f"G{len(self.rois)+1:02}",

            "points": self.current_polygon.copy()

        }

        self.rois.append(roi)

    def find_polygon(self, x, y):

        point = (float(x), float(y))

        for roi in reversed(self.rois):

            polygon = np.array(
                roi["points"],
                dtype=np.float32
            )

            inside = cv2.pointPolygonTest(
                polygon,
                point,
                False
            )

            if inside >= 0:

                return roi

        return None

    def move_polygon(self, roi, dx, dy):

        for point in roi["points"]:

            point[0] += dx
            point[1] += dy

    def delete_selected(self):

        if self.selected_roi is None:

            return

        self.rois.remove(self.selected_roi)

        self.selected_roi = None

    # -----------------------------------------
    # Klavye
    # -----------------------------------------

    def key_handler(self, key):

        if key == 127:          # Delete (Linux)

            self.delete_selected()

        elif key == 8:          # Delete (Windows)

            self.delete_selected()

        elif key == ord("d"):   # yedek

            self.delete_selected()

    # -----------------------------------------
    # JSON
    # -----------------------------------------

    def save(self, filename):

        folder = os.path.dirname(filename)

        if folder:
            os.makedirs(folder, exist_ok=True)

        data = {
            "rois": self.rois
        }

        with open(filename, "w", encoding="utf-8") as f:

            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )

        print(f"[INFO] {len(self.rois)} ROI kaydedildi.")

    def load(self, filename):

        if not os.path.exists(filename):

            print("[INFO] ROI dosyası bulunamadı.")

            return False

        with open(filename, "r", encoding="utf-8") as f:

            data = json.load(f)

        self.rois = data.get("rois", [])

        self.selected_roi = None

        self.current_polygon = []

        print(f"[INFO] {len(self.rois)} ROI yüklendi.")

        return True

    # -----------------------------------------
    # Yardımcı
    # -----------------------------------------

    def clear(self):

        self.rois.clear()

        self.current_polygon.clear()

        self.selected_roi = None

        self.dragging = False

        self.drag_start = None

    def get_rois(self):

        return self.rois
    

    def draw_results(self, image, results):

        output = image.copy()

        for roi in self.rois:

            name = roi["name"]

            pts = self.points_to_numpy(roi["points"])

            color = (150, 150, 150)
            
            text = name

            if name in results:

                if results[name]["ok"]:
                    color = a11y.get_ok_color_bgr()
                    text = f"{name} OK"

                else:
                    color = a11y.get_ng_color_bgr()
                    text = f"{name} NG"

            cv2.polylines(
                output,
                [pts],
                True,
                color,
                2
            )
            x = pts[:,0].min()
            y = pts[:,1].min()

            cv2.putText(
                output,
                text,
                (x, y-8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2
            )

        return output
    
    def points_to_numpy(self,points):

        return np.array(
            points,
            dtype=np.int32
        )

    def draw_info(self,image):

        output = image.copy()

        cv2.rectangle(
            output,
            (0,0),
            (output.shape[1],60),
            (40,40,40)
            -1
        )

        text = f"ROI Count: {len(self.rois)}"

        if self.selected_roi is not None:
             text += f"    Selected : {self.selected_roi['name']}"

        cv2.putText(
            output,
            text,
            (15, 38),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255,255,255),
            2
        )

        return output
























