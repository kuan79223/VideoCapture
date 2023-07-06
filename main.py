import datetime
import os
import sys
import time

import cv2
from PyQt5 import QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QImage, QPixmap, QPainter
from PyQt5.QtWidgets import QGraphicsScene, QVBoxLayout, QGraphicsView, QPushButton, QHBoxLayout, QLineEdit, QFileDialog

WIDTH = 1920
HEIGHT = 1080
COM = 0
VIDEO = cv2.VideoCapture(COM, cv2.CAP_DSHOW)


class ShowThread(QThread):
    SIGNAL_FRAME = pyqtSignal(object)

    def __init__(self, main):
        super(ShowThread, self).__init__()
        self.main = main
        self.SIGNAL_FRAME.connect(self.main.display)

        self.running = True
        self.isDetectCamera = True

    def run(self):

        set_pixels(VIDEO)  # 設定像素
        while self.running:
            time.sleep(0.000001)
            if VIDEO.isOpened() is True:

                ret, frame = VIDEO.read()

                if ret:
                    self.SIGNAL_FRAME.emit(frame)

    def stop(self):
        self.running = False
        sys.exit()


class CamaraCapture(QtWidgets.QWidget):

    def __init__(self):
        super(CamaraCapture, self).__init__()
        self.setFixedSize(800, 600) # 設定介面大小
        self.setWindowTitle('CamaraCapture')  # 介面標題

        layout = QVBoxLayout()  # 主視窗布局

        self.graph_view = QGraphicsView()
        layout.addWidget(self.graph_view)

        path_layout = QHBoxLayout()  # 選擇路徑與顯示路徑的布局

        self.path_edit = QLineEdit()
        self.path_edit.setFixedSize(600, 50)
        font = self.path_edit.font()
        font.setPointSize(16)
        self.path_edit.setFont(font)
        self.path_edit.textChanged.connect(self.validate_path)

        path_layout.addWidget(self.path_edit)
        # 選擇儲存路徑的按鈕設定與事件
        select_btn = QPushButton('路徑')
        select_btn.setFixedSize(100, 50)
        path_layout.addWidget(select_btn)
        select_btn.clicked.connect(self.select_save_path)

        btn_layout = QHBoxLayout()  # 按鈕布局
        # 捕捉影像的按鈕事件設定與觸發事件
        btn_capture = QPushButton('拍照')
        btn_capture.setFixedSize(100, 50)
        btn_capture.clicked.connect(self.capture)
        btn_layout.addWidget(btn_capture)

        # 離開應用程式的按鈕設定與觸發事件
        btn_leave = QPushButton('關閉應用程式')
        btn_leave.setFixedSize(100, 50)
        btn_leave.clicked.connect(self.leave_sys)
        btn_layout.addWidget(btn_leave)

        self.frame = None
        self.save_path = ''
        self.scene = QGraphicsScene()
        # 影像自適應 graph view
        self.graph_view.setScene(self.scene)
        self.graph_view.setRenderHint(QPainter.Antialiasing)
        self.graph_view.setRenderHint(QPainter.SmoothPixmapTransform)

        # 打開應用程式就啟動執行緒捕捉畫面
        self.thread = ShowThread(self)
        self.thread.start()

        layout.addLayout(path_layout)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def select_save_path(self):

        self.save_path = QFileDialog.getExistingDirectory(self, '選擇儲存路徑', 'D:')

        if self.save_path == '':
            print('\n取消選擇')
            return
        else:
            self.path_edit.setText(self.save_path)

    def validate_path(self):
        text = self.path_edit.text()
        if text:
            print('路徑存在')
        else:
            print('路徑不存在')

    def display(self, frame):
        self.frame = frame
        height, width = frame.shape[:2]

        qimg = QImage(bytes(frame), width, height, 3 * width, QImage.Format_BGR888)
        pixmap = QPixmap(qimg)

        self.scene.clear()
        self.scene = QGraphicsScene()
        self.scene.addPixmap(pixmap)
        self.graph_view.setScene(self.scene)
        self.graph_view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    def capture(self):
        if self.save_path:
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
    def leave_sys(self):
        try:
            self.thread.stop()
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
