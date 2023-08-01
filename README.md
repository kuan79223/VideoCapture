# Image_capture 影響處理專案

這是一個使用 Opencv 套件與 Pyqt，實現影像處理與使用者界面的整合，
可以讓使用者在有相機的電腦上作即時影像的處理。


## 使用虛擬環境 (venv)

建議在專案中使用虛擬環境來隔離專案所需的 Python 套件。

## 依賴套件

專案所需的 Python 套件列於 `requirements.txt` 檔案中。

## 建立虛擬環境與啟動

shell -

    python -m venv venv


在 Windows 環境中，啟動虛擬環境：

shell -

    venv\Scripts\activate


在 macOS/Linux 環境中，啟動虛擬環境：

shell - 

    source venv/bin/activate


## 安裝所需套件與啟動應用程式

shell - 

    python -m venv venv
    
    pip install -r requirements.txt
    
    python main.py
