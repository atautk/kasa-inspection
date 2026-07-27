import cv2
import numpy as np
import time


class Dashboard:

    def __init__(self):

        self.width = 1600
        self.height = 900

        self.background = (35, 35, 35)
        self.panel = (50, 50, 50)
        self.border = (90, 90, 90)

        self.font = cv2.FONT_HERSHEY_SIMPLEX

        self.window_name = "Dashboard"

        cv2.namedWindow(
            self.window_name,
            cv2.WINDOW_NORMAL
        )

        cv2.resizeWindow(
            self.window_name,
            self.width,
            self.height
        )

    # -------------------------------------------------
    # Dashboard Oluştur
    # -------------------------------------------------

    def create_canvas(self):

        canvas = np.full(
            (
                self.height,
                self.width,
                3
            ),
            self.background,
            dtype=np.uint8
        )

        return canvas

    # -------------------------------------------------
    # Panel
    # -------------------------------------------------

    def draw_panel(
        self,
        image,
        x,
        y,
        w,
        h,
        title
    ):

        cv2.rectangle(
            image,
            (x, y),
            (x + w, y + h),
            self.panel,
            -1
        )

        cv2.rectangle(
            image,
            (x, y),
            (x + w, y + h),
            self.border,
            2
        )

        cv2.putText(
            image,
            title,
            (x + 10, y + 30),
            self.font,
            0.8,
            (255,255,255),
            2
        )
            # -------------------------------------------------
    # Görüntü Yerleştir
    # -------------------------------------------------

    def draw_image(
        self,
        canvas,
        image,
        x,
        y,
        w,
        h
    ):

        if image is None:
            return

        resized = cv2.resize(image, (w, h))

        #eğer görüntü gri ise renklendir
        if len(resized.shape) == 2:
            resized = cv2.cvtColor(
                resized,
                cv2.COLOR_GRAY2BGR
            )

        canvas[
            y:y+h,
            x:x+w
        ] = resized

    # -------------------------------------------------
    # Başlık
    # -------------------------------------------------

    def draw_header(
        self,
        canvas,
        recipe,
        mode,
        camera_status,
        fps
    ):

        cv2.rectangle(
            canvas,
            (0, 0),
            (self.width, 60),
            (25,25,25),
            -1
        )

        cv2.putText(
            canvas,
            "KASA INSPECTION SYSTEM",
            (20,40),
            self.font,
            1.0,
            (255,255,255),
            2
        )

        cv2.putText(
            canvas,
            f"Recipe : {recipe}",
            (420,40),
            self.font,
            0.7,
            (0,255,255),
            2
        )

        cv2.putText(
            canvas,
            f"Mode : {mode}",
            (700,40),
            self.font,
            0.7,
            (255,255,255),
            2
        )

        color = (0,255,0)

        if camera_status != "CONNECTED":
            color = (0,0,255)

        cv2.putText(
            canvas,
            f"Camera : {camera_status}",
            (980,40),
            self.font,
            0.7,
            color,
            2
        )

        cv2.putText(
            canvas,
            f"FPS : {fps:.1f}",
            (1380,40),
            self.font,
            0.8,
            (0,255,0),
            2
        )

    # -------------------------------------------------
    # Üst Paneller
    # -------------------------------------------------

    def draw_top_panels(
        self,
        canvas,
        frame,
        reference,
        difference
    ):

        panel_y = 70

        panel_h = 330

        panel_w = 500

        self.draw_panel(
            canvas,
            20,
            panel_y,
            panel_w,
            panel_h,
            "LIVE CAMERA"
        )

        self.draw_panel(
            canvas,
            550,
            panel_y,
            panel_w,
            panel_h,
            "REFERENCE FRAME"
        )

        self.draw_panel(
            canvas,
            1080,
            panel_y,
            panel_w,
            panel_h,
            "DIFFERENCE"
        )

        self.draw_image(
            canvas,
            frame,
            30,
            110,
            480,
            280
        )

        self.draw_image(
            canvas,
            reference,
            560,
            110,
            480,
            280
        )

        self.draw_image(
            canvas,
            difference,
            1090,
            110,
            480,
            280
        )
            # -------------------------------------------------
    # ROI Tablosu
    # -------------------------------------------------

    def draw_results_table(
        self,
        canvas,
        results
    ):

        x = 20
        y = 430
        w = 1560
        h = 250

        self.draw_panel(
            canvas,
            x,
            y,
            w,
            h,
            "ROI RESULTS"
        )

        headers = [
            "ROI",
            "STATE",
            "EXPECTED",
            "RESULT",
            "DIFF %",
            "PIXELS"
        ]

        columns = [30, 170, 340, 560, 760, 960]

        for header, col in zip(headers, columns):

            cv2.putText(
                canvas,
                header,
                (col, y + 60),
                self.font,
                0.65,
                (255,255,255),
                2
            )

        row = 95

        for roi_name, data in sorted(results.items()):

            color = (0,255,0)

            if not data["ok"]:
                color = (0,0,255)

            values = [

                roi_name,

                data["state"],

                data["expected"],

                "OK" if data["ok"] else "NG",

                f"{data['change_ratio']:.2f}",

                str(data["changed_pixels"])

            ]

            for value, col in zip(values, columns):

                cv2.putText(

                    canvas,

                    value,

                    (col, y + row),

                    self.font,

                    0.60,

                    color,

                    2

                )

            row += 35

    # -------------------------------------------------
    # Sistem Bilgileri
    # -------------------------------------------------

    def draw_status(
        self,
        canvas,
        inspection_time,
        total_ok,
        total_ng
    ):

        y = 700

        self.draw_panel(
            canvas,
            20,
            y,
            760,
            180,
            "SYSTEM STATUS"
        )

        cv2.putText(
            canvas,
            f"Inspection Time : {inspection_time:.1f} ms",
            (40, y + 55),
            self.font,
            0.65,
            (255,255,255),
            2
        )

        cv2.putText(
            canvas,
            f"OK : {total_ok}",
            (40, y + 95),
            self.font,
            0.65,
            (0,255,0),
            2
        )

        cv2.putText(
            canvas,
            f"NG : {total_ng}",
            (40, y + 135),
            self.font,
            0.65,
            (0,0,255),
            2
        )

    # -------------------------------------------------
    # LOG
    # -------------------------------------------------

    def draw_logs(
        self,
        canvas,
        logs
    ):

        x = 820
        y = 700

        self.draw_panel(
            canvas,
            x,
            y,
            760,
            180,
            "LOG"
        )

        offset = 45

        for line in logs[-6:]:

            cv2.putText(

                canvas,

                line,

                (x + 20, y + offset),

                self.font,

                0.55,

                (220,220,220),

                1

            )

            offset += 25

    # -------------------------------------------------
    # Render
    # -------------------------------------------------

    def show(
        self,
        result,
        recipe,
        fps,
        inspection_time,
        logs
    ):

        canvas = self.create_canvas()

        frame = result["frame"]

        reference = result["reference_display"]

        difference = result["difference"]

        results = result["results"]

        localization = result["localization"]

        mode = "FAIL"

        if localization is not None:

            mode = localization["mode"]

        camera_status = "CONNECTED"

        if not result["success"]:

            camera_status = "ERROR"

        self.draw_header(

            canvas,

            recipe,

            mode,

            camera_status,
            
            fps
        )

        self.draw_top_panels(
            canvas,
            frame,
            reference,
            difference
        )

        self.draw_results_table(
            canvas,
            results
        )

        total_ok = sum(
            1 

            for r in results.values()

            if r.get("ok",False)
        )

        total_ng = len(results) - total_ok

        self.draw_status(
            canvas,
            inspection_time,
            total_ok,
            total_ng
        )

        self.draw_logs(
            canvas,
            logs
        )

        cv2.imshow(
            self.window_name,
            canvas
        )

        return canvas

    def close(self):

        try:
            cv2.destroyWindow(
                self.window_name
            )

        except cv2.error:

            pass