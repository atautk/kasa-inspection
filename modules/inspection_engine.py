import cv2
import numpy as np
import os

class InspectionEngine:

    def crop_polygon(self, image, points):

        polygon = np.array(points, dtype=np.int32)

        mask = np.zeros(image.shape[:2], dtype=np.uint8)

        cv2.fillPoly(mask, [polygon], 255)

        masked = cv2.bitwise_and(image, image, mask=mask)

        x, y, w, h = cv2.boundingRect(polygon)

        return masked[y:y+h, x:x+w]


    def analyze(self, crop):

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

        blur = cv2.GaussianBlur(gray, (5, 5), 0)

        mean = float(np.mean(blur))

        std = float(np.std(blur))

        edges = cv2.Canny(blur, 75, 150)

        edge_count = int(cv2.countNonZero(edges))

        _, binary = cv2.threshold(
            blur,
            128,
            255,
            cv2.THRESH_BINARY
        )

        white_ratio = (
            cv2.countNonZero(binary) / (binary.size)
        )*100

        return {
            "mean": round(mean, 2),
            "std": round(std, 2),
            "edge_count": edge_count,
            "white_ratio": round(white_ratio, 2)
        }
    
    def save_reference(self, image, filename):
        
        cv2.imwrite(filename, image)
        
        print(f"[INFO] Reference kaydedildi: {filename}")


    def load_reference(self, filename):
        if not os.path.exists(filename):
            print(f"[INFO] Referans dosyası bulunamadı: {filename}")
            return None
        
        image = cv2.imread(filename)

        print(f"[INFO] Referans yüklendi: {filename}")
        
        return image
    
    def compare(self,referance_crop,current_crop):

        #Aynı boyuta getir
        current_crop = cv2.resize(
        current_crop,
        (reference_crop.shape[1], reference_crop.shape[0])
        )

        #Farkı hesapla
        difference = cv2.absdiff(reference_crop, current_crop)

        #Farkı gri tonlamaya çevir
        gray = cv2.cvtColor(difference, cv2.COLOR_BGR2GRAY)

        #Farkın eşik değerini al
        _, thresh = cv2.threshold(gray, 25, 255, cv2.THRESH_BINARY)

        changeed_pixels = cv2.countNonZero(thresh)

        return{
            "difference": difference,
            "threshold": thresh,
            "changed_pixels": changed_pixels
        }
    