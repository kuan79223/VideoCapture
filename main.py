import datetime
import os
import sys
import time
import numpy as np
import cv2
import threading
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QFileDialog, QMainWindow, QGraphicsScene, QApplication

import camera_ui


WIDTH = 1920
HEIGHT = 1080
COM = 0

VIDEO = cv2.VideoCapture(COM, cv2.CAP_DSHOW)


# 即時顯示影像與處理影像
class CameraThread(QThread):
    SIGNAL_FRAME = pyqtSignal(np.ndarray)
    SIGNAL_PROCESS_IMAGE = pyqtSignal(QImage)

    def __init__(self, main):
        super(CameraThread, self).__init__()
        self.main = main
        self.running = True
        self.isDetectCamera = True
        self.frame = None  # 用於處理影像
        # initialize binary, dilate, erode, guass value
        self.binary_value = 0
        # kernel value
        self.dilate_value = 0
        self.erode_value = 0

        self.blur_value = 1
        self.binary_frame = None  # 預設二值化變數

    def run(self):
        set_pixels(VIDEO)  # 設定像素
        while self.running:
            time.sleep(0.001)
            if VIDEO.isOpened() is True:
                ret, frame = VIDEO.read()  # 讀取影像回傳 bool 與 影像，bool 代表相機有讀取到影像
                self.frame = frame

                if ret:
                    self.SIGNAL_FRAME.emit(frame)  # 傳遞原圖影像信號

                    # 影像處理之前會先做二值化
                    gray = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
                    _, self.binary_frame = cv2.threshold(gray, self.binary_value, 255, cv2.THRESH_BINARY)

                    img_process = cv2.GaussianBlur(self.binary_frame, (self.blur_value, self.blur_value), 10)

                    kernel_dilate = np.ones((self.dilate_value, self.dilate_value), np.uint8)  # 膨脹 kernel
                    img_process = cv2.dilate(img_process, kernel_dilate, iterations=1)

                    kernel_erode = np.ones((self.erode_value, self.erode_value), np.uint8)  # 侵蝕 kernel
                    img_process = cv2.erode(img_process, kernel_erode, iterations=1)

                    height, width = img_process.shape[:2]
                    # 假如影像有處理就以 2 通道來顯示，否則就以原圖 3 通道呈現
                    if len(img_process.shape) == 2:
                        bytesPerline = width
                        qimg = QImage(img_process.data, width, height, bytesPerline, QImage.Format_Grayscale8)
                    else:
                        bytesPerline = width * 3
                        qimg = QImage(img_process.data, width, height, bytesPerline, QImage.Format_BGR888)

                    self.SIGNAL_PROCESS_IMAGE.emit(qimg)  # 傳遞處理後的影像信號

    # slider bar 觸發連接
    def update_process(self):
        object_name = self.sender().objectName()

        if object_name == 'slider_binary':
            self.binary_value = self.sender().value()
            self.main.label_binary.setText(str(self.binary_value))

        elif object_name == 'slider_dilate':
            self.dilate_value = self.sender().value()
            self.main.label_dilate.setText(str(self.dilate_value))

        elif object_name == 'slider_erode':
            self.erode_value = self.sender().value()
            self.main.label_erode.setText(str(self.erode_value))

        elif object_name == 'spinBox_guass':
            self.blur_value = self.sender().value()

    def stop(self):
        self.running = False
        VIDEO.release()
        sys.exit()


class CamaraCapture(QMainWindow, camera_ui.Ui_MainWindow):

    def __init__(self):
        super(CamaraCapture, self).__init__()
        self.setupUi(self)

        self.setFixedSize(1280, 768)  # 設定介面大小
        self.setWindowTitle('CamaraCapture')  # 介面標題
        self.setWindowFlags(Qt.FramelessWindowHint)

        self.lineEdit.textEdited.connect(self.validate_path)
        self.btn_select_path.clicked.connect(self.open_dialog)  # 開啟選擇路徑的信號連接
        self.open_dialog_thread = None

        self.btn_capture.clicked.connect(self.capture)
        self.btn_close_sys.clicked.connect(self.close_sys)

        self.frame = None
        self.save_path = ''
        # 打開應用程式就啟動執行緒捕捉畫面
        self.camera_thread = CameraThread(self)
        self.camera_thread.SIGNAL_FRAME.connect(self.display_video)
        self.camera_thread.SIGNAL_PROCESS_IMAGE.connect(self.display_process_video)
        self.camera_thread.start()

        self.slider_binary.valueChanged.connect(self.camera_thread.update_process)
        self.slider_dilate.valueChanged.connect(self.camera_thread.update_process)
        self.slider_erode.valueChanged.connect(self.camera_thread.update_process)

        self.spinBox_guass.valueChanged.connect(self.camera_thread.update_process)

    @pyqtSlot(QImage)  # 處理影像執行緒的信號槽
    def display_process_video(self, qimg):
        scene_processed = QGraphicsScene()
        scene_processed.addPixmap(QPixmap(qimg))
        self.graph_process.setScene(scene_processed)
        # 讓場景自適應視圖 兩個與法都可以用，第一個參數代表 場景的邊界框
        self.graph_process.fitInView(scene_processed.sceneRect(), Qt.KeepAspectRatio)

    def open_dialog(self):
        self.open_dialog_thread = threading.Thread(target=self.show_dialog)
        self.open_dialog_thread.start()

    # 選擇儲放影像的路徑
    def show_dialog(self):

        self.save_path = QFileDialog.getExistingDirectory(self, '選擇儲存路徑', 'D:')
        # print(self.save_path)
        if self.save_path:
            self.lineEdit.setText(self.save_path)

    # 判斷 line edit 是否存在字串內容
    def validate_path(self):
        text = self.lineEdit.text()
        if text:
            self.save_path = text
        else:
            self.save_path = ''

    @pyqtSlot(np.ndarray)  # 顯示影像執行緒的信號槽
    def display_video(self, frame):
        self.frame = frame
        height, width = frame.shape[:2]
        qimg = QImage(bytes(frame), width, height, 3 * width, QImage.Format_BGR888)
        scene_origin = QGraphicsScene()
        scene_origin.addPixmap(QPixmap(qimg))
        self.graph_origin.setScene(scene_origin)
        # 讓場景自適應視圖 兩個與法都可以用，第一個參數代表 場景的邊界框
        self.graph_origin.fitInView(scene_origin.sceneRect(), Qt.KeepAspectRatio)

    # 拍照
    def capture(self):

        if os.path.exists(self.save_path):
            # 設定要儲存的影像檔名格式
            date_time = str(datetime.datetime.today())
            # print(date_time)
            mDate, mTime = date_time.split(' ')
            mDate = mDate.replace('-', '')
            mTime = mTime.replace(':', '').replace('.', '')[:-2]
            img_name = mDate + '_' + mTime + '.png'

            cv2.imwrite(os.path.join(self.save_path, img_name), self.frame)
            # print('儲存影像: ' + os.path.join(self.save_path, img_name))

    # 離開應用程式
    def close_sys(self):
        try:
            self.camera_thread.stop()
            self.open_dialog_thread.stop()
        except Exception as exc:
            print(exc)


# 設定相機解析度
def set_pixels(cap):
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, 24)  # FPS


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = CamaraCapture()
    win.show()
    sys.exit(app.exec())
