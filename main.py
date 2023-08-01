import datetime
import os
import sys
import threading
import time

import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QFileDialog, QMainWindow, QGraphicsScene, QApplication

import camera_ui

WIDTH = 1920
HEIGHT = 1080
COM = 0

VIDEO = cv2.VideoCapture(COM, cv2.CAP_DSHOW)


# 即時顯示影像與處理影像
class ProcessThread(QThread):
    SIGNAL_FRAME = pyqtSignal(np.ndarray)  # 傳遞原圖的信號
    SIGNAL_HANDLE_IMAGE = pyqtSignal(np.ndarray, int, int)  # 傳遞處理後的影像信號

    def __init__(self, main):
        super(ProcessThread, self).__init__()
        self.main = main
        self.running = True
        self.isDetectCamera = True
        self.frame = None  # 處理影像的變數
        # initialize binary, dilate, erode, gaussian value
        self.binary_value = 0
        # kernel value
        self.dilate_value = 0
        self.erode_value = 0
        self.blur_value = 1
        self.binary_frame = None  # 預設二值化變數
        self.image_dir = ''  # 設定一個接收匯入圖片的變數
        self.change_state = False  # 設定 slider_bar modify 的狀態

    def run(self):
        set_pixels(VIDEO)  # 設定像素

        while self.running:
            time.sleep(0.001)
            # 相機有開啟
            if VIDEO.isOpened() is True:
                ret, frame = VIDEO.read()  # 讀取影像回傳 bool 與 影像，bool 代表相機有讀取到影像
                if ret:
                    self.frame = frame

                    height, width, img_process = self.handle_image()

                    self.SIGNAL_HANDLE_IMAGE.emit(img_process, height, width)  # 傳遞處理後的影像信號

                    contours, hierarchy = cv2.findContours(img_process, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    # 複製原圖避免每一次進 for loop 都會被覆蓋
                    img_draw = self.frame.copy()
                    for i in range(0, len(contours)):
                        rx_min, ry_min, rw, rh = cv2.boundingRect(contours[i])
                        rx_max = rx_min + rw
                        ry_max = ry_min + rh
                        # 將繪製矩形的影像再回放
                        img_draw = cv2.rectangle(img_draw, (rx_min, ry_min), (rx_max, ry_max),
                                                 (255, 0, 0), 3)

                    if len(contours) != 0:
                        # 左側畫框的影像
                        self.SIGNAL_FRAME.emit(img_draw)
                    else:
                        # 左側原圖影像
                        self.SIGNAL_FRAME.emit(self.frame)

            else:
                # 讀取圖片
                while self.running:
                    time.sleep(0.001)
                    # 判斷 讀取影像路徑的變數 和 讀取影像狀態是否成立
                    if self.main.image_dir and self.main.isLoad_img:
                        self.frame = cv2.imread(self.main.image_dir)
                        # 將 讀取到的影像路徑變數放在記憶體中
                        # self.image_dir = self.main.image_dir
                        # 因為是按鈕觸發，所以當影像路徑存到變數之後，將狀態改為 False
                        self.main.isLoad_img = False

                    # 判斷讀取的影像是否成立
                    if self.frame is not None:
                        height, width, img_process = self.handle_image()
                        self.SIGNAL_HANDLE_IMAGE.emit(img_process, height, width)  # 傳遞處理後的影像

                        # 找輪廓 - 且在原圖上進行繪圖
                        contours, hierarchy = cv2.findContours(img_process, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        total_avg = []
                        img_draw = self.frame.copy()
                        for i in range(0, len(contours)):
                            # area = cv2.contourArea(contours[i])  # 取得輪廓面積
                            rx_min, ry_min, rw, rh = cv2.boundingRect(contours[i])
                            rx_max = rx_min + rw
                            ry_max = ry_min + rh
                            # print(rx_min, ry_min, rx_max, ry_max)

                            rect_ = cv2.rectangle(img_draw, (rx_min, ry_min), (rx_max, ry_max), (255, 0, 0), 3)

                            crop_img = self.frame[ry_min:ry_max, rx_min:rx_max]
                            text = str(int(crop_img.mean()))  # 計算 RGB 均值
                            total_avg.append(crop_img.mean())
                            # 在影像上顯示數值
                            cv2.putText(rect_, text, (rx_min + int(rw / 2), ry_min + int(rh / 2)), cv2.FONT_HERSHEY_SIMPLEX,
                                        1, (0, 0, 255), 2)

                        self.main.lb_avg.setText('輪廓總均值:  '+ str(int(sum(total_avg) / len(contours))))
                        # 狀態改變時，更新視圖
                        if self.change_state:
                            if len(contours) != 0:

                                # 左側畫框的影像
                                self.SIGNAL_FRAME.emit(img_draw)
                            else:
                                # 左側原圖影像
                                self.SIGNAL_FRAME.emit(self.frame)

                            self.change_state = False

    # 影像處理
    def handle_image(self):
        # 影像處理之前會先做二值化
        gray = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
        _, self.binary_frame = cv2.threshold(gray, self.binary_value, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        img_process = cv2.GaussianBlur(self.binary_frame, (self.blur_value, self.blur_value), 10)

        kernel_dilate = np.ones((self.dilate_value, self.dilate_value), np.uint8)  # 膨脹 kernel
        img_process = cv2.dilate(img_process, kernel_dilate, iterations=1)

        kernel_erode = np.ones((self.erode_value, self.erode_value), np.uint8)  # 侵蝕 kernel
        img_process = cv2.erode(img_process, kernel_erode, iterations=1)

        height, width = img_process.shape[:2]

        return height, width, img_process

    # slider bar 觸發連接
    def update_process(self):
        object_name = self.sender().objectName()

        if object_name == 'slider_binary':
            self.binary_value = self.sender().value()
            self.main.label_binary.setText(str(self.binary_value))
            self.change_state = True

        elif object_name == 'slider_dilate':
            self.dilate_value = self.sender().value()
            self.main.label_dilate.setText(str(self.dilate_value))
            self.change_state = True

        elif object_name == 'slider_erode':
            self.erode_value = self.sender().value()
            self.main.label_erode.setText(str(self.erode_value))
            self.change_state = True

        elif object_name == 'spinBox_guass':
            self.blur_value = self.sender().value()
            self.change_state = True

    def stop(self):
        self.running = False
        VIDEO.release()


class ImageProcess(QMainWindow, camera_ui.Ui_MainWindow):
    SIGNAL_SHOW_DIALOG = pyqtSignal()  # 開啟對話方塊的信號

    def __init__(self):
        super(ImageProcess, self).__init__()
        self.setupUi(self)

        self.setFixedSize(1280, 768)  # 設定介面大小
        self.setWindowTitle('CamaraCapture')  # 介面標題
        self.setWindowFlags(Qt.FramelessWindowHint)

        self.btn_capture.clicked.connect(self.capture)
        self.btn_close_sys.clicked.connect(self.close_sys)

        self.lineEdit.textEdited.connect(self.validate_path)
        self.btn_save_path.clicked.connect(self.open_select_dir_dialog)  # 開啟選擇路徑的信號連接
        self.select_dir_thread = None

        self.frame = None
        self.save_path = ''

        # 打開應用程式就啟動執行緒捕捉畫面
        self.camera_thread = ProcessThread(self)
        self.camera_thread.SIGNAL_FRAME.connect(self.display_video)
        self.camera_thread.SIGNAL_HANDLE_IMAGE.connect(self.display_process_video)
        self.camera_thread.start()
        # Slider Bar 變動的連接
        self.slider_binary.valueChanged.connect(self.camera_thread.update_process)
        self.slider_dilate.valueChanged.connect(self.camera_thread.update_process)
        self.slider_erode.valueChanged.connect(self.camera_thread.update_process)
        # SpinBox 變動的連接
        self.spinBox_guass.valueChanged.connect(self.camera_thread.update_process)

        self.btn_upload.clicked.connect(self.open_upload_dialog)

        if VIDEO.isOpened() is not True:
            self.btn_upload.setEnabled(True)
        else:
            self.btn_upload.setEnabled(False)

        self.SIGNAL_SHOW_DIALOG.connect(self.show_dialog)  # 傳遞開啟對話視窗的連接

        self.scene_origin = QGraphicsScene()  # 原始畫面
        self.scene_adjusting = QGraphicsScene()  # 調整的畫面

        self.image_dir = None  # 讀取圖片路徑的變數
        self.isLoad_img = False  # 讀取圖片的狀態

    # 匯入圖片按鈕觸發傳遞信號
    def open_upload_dialog(self):

        self.SIGNAL_SHOW_DIALOG.emit()

    # 彈出匯入圖片的對話視窗
    def show_dialog(self):
        # 相機未開啟
        if VIDEO.isOpened() is not True:

            self.image_dir, _ = QFileDialog.getOpenFileName(self, '載入圖像', 'D:', "Image Files (*.jpg *.jpeg *.png)")  # 設置文件擴展名過濾,用雙分號間隔
            # 選擇到影像路徑之後，改變狀態
            if self.image_dir:
                self.isLoad_img = True
                self.camera_thread.change_state = True

    @pyqtSlot(np.ndarray, int, int)  # 調整影像執行緒的信號槽
    def display_process_video(self, npImg, height, width):

        qimg = get_q_img(img=npImg, w=width, h=height)
        self.scene_adjusting.clear()  # 動態執行影像，清理Scene
        self.scene_adjusting.addPixmap(QPixmap(qimg))
        self.graph_process.setScene(self.scene_adjusting)
        self.graph_process.fitInView(self.scene_adjusting.sceneRect(), Qt.KeepAspectRatio)

    # 開啟選取儲存路徑資料夾的按鈕事件
    def open_select_dir_dialog(self):

        self.select_dir_thread = threading.Thread(target=self.run_dir_dialog)
        self.select_dir_thread.start()

    # 選擇儲放影像的路徑
    def run_dir_dialog(self):

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
        self.scene_origin.clear()  # 動態執行影像，清理Scene
        self.scene_origin.addPixmap(QPixmap(qimg))
        self.graph_origin.setScene(self.scene_origin)
        self.graph_origin.fitInView(self.scene_origin.sceneRect(), Qt.KeepAspectRatio)

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
            sys.exit()
        except Exception as exc:
            print(exc)


# 設定相機解析度
def set_pixels(cap):
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, 24)  # FPS


# 判斷 影像為幾通道，給予對應的 qimg
def get_q_img(img, w, h):
    # 假如影像有處理就以 2 通道來顯示，否則就以原圖 3 通道呈現
    if len(img.shape) == 2:
        bytesPerline = w
        qimg = QImage(img.data, w, h, bytesPerline, QImage.Format_Grayscale8)
    else:
        bytesPerline = w * 3
        qimg = QImage(img.data, w, h, bytesPerline, QImage.Format_BGR888)

    return qimg


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = ImageProcess()
    win.show()
    sys.exit(app.exec())
