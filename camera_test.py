from modules.core.camera import Camera

camera = Camera()

if camera.open():

    print("Camera OK")

    while True:

        frame = camera.read()

        if frame is None:
            break

        import cv2

        cv2.imshow("Camera", frame)

        key = cv2.waitKey(1)

        if key == 27:
            break

camera.release()

cv2.destroyAllWindows()