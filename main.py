import datetime
import os
import sys
import time
import numpy as np
import cv2
from PyQt5 import QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QVBoxLayout, QPushButton, QHBoxLayout, QLineEdit, \
    QFileDialog, QGridLayout, QLabel

WIDTH = 1920
HEIGHT = 1080
THRESH = 128
MAXVAL = 255
COM = 0
VIDEO = cv2.VideoCapture(COM, cv2.CAP_DSHOW)

# 影像處理狀態切換
PROCESS_STATUS = 'default'


class CameraThread(QThread):
    SIGNAL_FRAME = pyqtSignal(QImage)
    SIGNAL_PROCESS_IMAGE = pyqtSignal(QImage)
    process = ''

    def __init__(self, main):
        super(CameraThread, self).__init__()
        self.main = main
        self.running = True
        self.isDetectCamera = True

    def run(self):
        set_pixels(VIDEO)  # 設定像素
        while self.running:

            time.sleep(0.000001)
            if VIDEO.isOpened() is True:
                ret, frame = VIDEO.read()
                if ret:
                    height, width = frame.shape[:2]
                    image = QImage(bytes(frame), width, height, 3 * width, QImage.Format_BGR888)
                    self.SIGNAL_FRAME.emit(image)

                    kernel_dilate = np.ones((5, 5), np.uint8)  # 膨脹 kernel
                    kernel_erode = np.ones((5, 5), np.uint8)  # 侵蝕 kernel

                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    _, binary_frame = cv2.threshold(gray, THRESH, MAXVAL, cv2.THRESH_BINARY)

                    # 二值化
                    if self.process == 'btn_binary':
                        height, width = binary_frame.shape[:2]
                        binary_image = QImage(bytes(binary_frame), width, height, QImage.Format_Grayscale8)
                        self.SIGNAL_PROCESS_IMAGE.emit(binary_image)
                    # 高斯模糊
                    elif self.process == 'btn_gaussian_blur':
                        blur = cv2.GaussianBlur(frame, (15, 15), 10)
                        height, width = blur.shape[:2]
                        blur_image = QImage(bytes(blur), width, height, QImage.Format_Grayscale8)
                        self.SIGNAL_PROCESS_IMAGE.emit(blur_image)
                    # 膨脹
                    elif self.process == 'btn_dilate':
                        dilate = cv2.dilate(binary_frame, kernel_dilate, iterations=10)
                        height, width = dilate.shape[:2]
                        dilate_image = QImage(bytes(dilate), width, height, QImage.Format_Grayscale8)
                        self.SIGNAL_PROCESS_IMAGE.emit(dilate_image)
                    # 侵蝕
                    elif self.process == 'btn_erode':
                        erode = cv2.erode(binary_frame, kernel_erode, iterations=1)  # 侵蝕次數
                        height, width = erode.shape[:2]
                        erode_image = QImage(bytes(erode), width, height, QImage.Format_Grayscale8)
                        self.SIGNAL_PROCESS_IMAGE.emit(erode_image)
    def stop(self):
        self.running = False
        VIDEO.release()
        sys.exit()

class CamaraCapture(QtWidgets.QWidget):

    def __init__(self):
        super(CamaraCapture, self).__init__()
        self.setFixedSize(1024, 768) # 設定介面大小
        self.setWindowTitle('CamaraCapture')  # 介面標題
        self.setWindowFlags(Qt.FramelessWindowHint)
        layout = QVBoxLayout()  # 主視窗布局

        view_layout = QHBoxLayout()
        self.origin_label = QLabel()
        self.origin_label.setScaledContents(True)  # 畫面自適應label
        view_layout.addWidget(self.origin_label)

        self.process_label = QLabel()
        self.process_label.setScaledContents(True)  # 畫面自適應label
        view_layout.addWidget(self.process_label)

        layout.addLayout(view_layout)

        path_layout = QHBoxLayout()  # 選擇路徑與顯示路徑的布局

        self.path_edit = QLineEdit()
        self.path_edit.setFixedSize(600, 50)
        font = self.path_edit.font()
        font.setPointSize(16)
        self.path_edit.setFont(font)
        self.path_edit.textEdited.connect(self.validate_path)
        path_layout.addWidget(self.path_edit)

        # 選擇儲存路徑的按鈕設定與事件
        select_btn = QPushButton('路徑')
        select_btn.setFixedSize(100, 50)
        path_layout.addWidget(select_btn)
        select_btn.clicked.connect(self.select_save_path)

        grid_layout = QGridLayout()  # 使用網格布局按鈕
        # --------- 按鈕設定與觸發事件 -------------
        btn_binary = QPushButton('二值化')
        btn_binary.setFixedSize(100, 50)
        btn_binary.clicked.connect(lambda: self.button_clicked('btn_binary'))

        btn_gaussian_blur = QPushButton('高斯模糊')
        btn_gaussian_blur.setFixedSize(100, 50)
        btn_gaussian_blur.clicked.connect(lambda: self.button_clicked('btn_gaussian_blur'))

        btn_dilate = QPushButton('膨脹')
        btn_dilate.setFixedSize(100, 50)
        btn_dilate.clicked.connect(lambda: self.button_clicked('btn_dilate'))

        btn_erode = QPushButton('侵蝕')
        btn_erode.setFixedSize(100, 50)
        btn_erode.clicked.connect(lambda: self.button_clicked('btn_erode'))

        btn_capture = QPushButton('拍照')
        btn_capture.setFixedSize(100, 50)
        btn_capture.clicked.connect(self.capture)

        btn_leave = QPushButton('關閉應用程式')
        btn_leave.setFixedSize(100, 50)
        btn_leave.clicked.connect(self.leave_sys)
        # 按鈕佈進網格內
        grid_layout.addWidget(btn_binary, 0, 1)
        grid_layout.addWidget(btn_gaussian_blur, 0, 2)
        grid_layout.addWidget(btn_dilate, 0, 3)
        grid_layout.addWidget(btn_erode, 0, 4)
        grid_layout.addWidget(btn_capture, 1, 1)
        grid_layout.addWidget(btn_leave, 1, 2)
        self.frame = None
        self.save_path = ''

        # 打開應用程式就啟動執行緒捕捉畫面
        self.camera_thread = CameraThread(self)
        self.camera_thread.SIGNAL_FRAME.connect(self.display_frame)
        self.camera_thread.SIGNAL_PROCESS_IMAGE.connect(self.process_image)
        self.camera_thread.start()

        layout.addLayout(path_layout)
        layout.addLayout(grid_layout)
        self.setLayout(layout)

    def button_clicked(self, flag):
        sender_name = self.sender().objectName()
        # print(sender_name)
        # self.process_thread.process = sender_name
        # global PROCESS_STATUS
        # 接收按鈕觸發的狀態
        if flag == 'btn_binary':
            self.camera_thread.process = 'btn_binary'
        elif flag == 'btn_gaussian_blur':
            self.camera_thread.process = 'btn_gaussian_blur'
        elif flag == 'btn_dilate':
            self.camera_thread.process = 'btn_dilate'
        elif flag == 'btn_erode':
            self.camera_thread.process = 'btn_erode'

    @pyqtSlot(QImage)  # 處理影像執行緒的信號槽
    def process_image(self, process_frame):
        self.process_label.setPixmap(QPixmap.fromImage(process_frame))

    # 選擇儲放影像的路徑
    def select_save_path(self):

        self.save_path = QFileDialog.getExistingDirectory(self, '選擇儲存路徑', 'D:')

        if self.save_path == '':
            print('\n取消選擇')
            return
        else:
            self.path_edit.setText(self.save_path)

    # 判斷 line edit 是否存在字串內容
    def validate_path(self):
        text = self.path_edit.text()
        if text:
            self.save_path = text
        else:
            self.save_path = ''

    @pyqtSlot(QImage)  # 顯示影像執行緒的信號槽
    def display_frame(self, frame):
        self.frame = frame
        self.origin_label.setPixmap(QPixmap.fromImage(frame))

    # 拍照
    def capture(self):

        if os.path.exists(self.save_path):
            # 設定要儲存的影像檔名格式
            date_time = str(datetime.datetime.today())
            print(date_time)
            mDate, mTime = date_time.split(' ')
            mDate = mDate.replace('-', '')
            mTime = mTime.replace(':', '').replace('.', '')[:-2]
            imgName = mDate + '_' + mTime + '.png'

            cv2.imwrite(os.path.join(self.save_path, imgName), self.frame)
            print('儲存影像: ' + os.path.join(self.save_path, imgName))

        else:
            return

    # 離開應用程式
    def leave_sys(self):
        try:
            self.camera_thread.stop()
            self.process_thread.stop()
        except Exception as exc:
            print(exc)


# 設定相機解析度
def set_pixels(cap):
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, 24)  # FPS


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    form = CamaraCapture()
    form.show()
    sys.exit(app.exec())
