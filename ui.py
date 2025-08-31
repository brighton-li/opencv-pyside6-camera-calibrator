from PySide6.QtCore import (QCoreApplication, QMetaObject, QRect, QSize, Qt)
from PySide6.QtWidgets import (QApplication, QGridLayout, QLabel,QScrollArea,QStatusBar,
                               QMainWindow, QPlainTextEdit, QPushButton,QComboBox,
                               QSizePolicy, QSpinBox, QVBoxLayout, QWidget,QHBoxLayout)
from PySide6.QtGui import QIntValidator 

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        #MainWindow.setTitle()
        MainWindow.resize(900, 600)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
        self.centralwidget.setStyleSheet("font-size:13px")
        # 左侧控制面板
        self.ctrl_layout = QVBoxLayout()
        self.ctrl_layout.setObjectName("ctrl_layout")
        
        self.btn_open_cam = QPushButton("打开相机")
        self.btn_open_cam.setObjectName("btn_open_cam")
        self.ctrl_layout.addWidget(self.btn_open_cam)

        self.combobox_layout = QHBoxLayout()
        self.combobox_cam = QComboBox(self,fixedWidth = 40)
        self.combobox_cam.setEditable(True)
        self.combobox_cam.addItems(["0","1","2","3"])  # 下拉显示
        int_validator = QIntValidator(self)
        int_validator.setRange(0,9)                # 允许填入的
        self.combobox_cam.setValidator(int_validator)
        self.cam_label = QLabel("请确定相机索引：", maximumWidth = 100)
        self.cam_label.setStyleSheet("font-size : 12px")
        self.combobox_cam.setStyleSheet("border : none; font-size : 12px")
        self.combobox_layout.addWidget(self.cam_label)
        self.combobox_layout.addWidget(self.combobox_cam)
        self.ctrl_layout.addLayout(self.combobox_layout)

        self.btn_file = QPushButton("请一次导入所有本地图片")
        self.ctrl_layout.addWidget(self.btn_file)

        self.btn_detect = QPushButton("检测图片")
        self.btn_detect.setObjectName("btn_detect")
        self.btn_detect.setEnabled(False)
        self.ctrl_layout.addWidget(self.btn_detect)
        

        self.btn_calibrate = QPushButton("开始标定")
        self.btn_calibrate.setObjectName("btn_calibrate")
        self.btn_calibrate.setEnabled(False)
        self.ctrl_layout.addWidget(self.btn_calibrate)

        self.btn_save = QPushButton("保存结果")
        self.btn_save.setObjectName("btn_save")
        self.btn_save.setEnabled(False)
        self.ctrl_layout.addWidget(self.btn_save)

        self.label_input = QLabel("已本地导入：0 张")
        self.label_count = QLabel("已采集检测: 0 张")
        self.label_tip1   = QLabel("出错请从头导入与检测，自动重置")
        self.label_tip2   = QLabel("需要至少采集9张才可标定")
        self.ctrl_layout.addWidget(self.label_input)
        self.ctrl_layout.addWidget(self.label_count)
        self.ctrl_layout.addWidget(self.label_tip1)
        self.ctrl_layout.addWidget(self.label_tip2)

        self.ctrl_layout.addStretch(3)

        self.label_pattern = QLabel("棋盘格内部交叉点数目 (x y):")
        self.ctrl_layout.addWidget(self.label_pattern)
        self.cb_pattern_x = QSpinBox()
        self.cb_pattern_x.setMinimum(3)
        self.cb_pattern_x.setMaximum(20)
        self.cb_pattern_x.setValue(9)
        self.ctrl_layout.addWidget(self.cb_pattern_x)
        self.cb_pattern_y = QSpinBox()
        self.cb_pattern_y.setMinimum(3)
        self.cb_pattern_y.setMaximum(20)
        self.cb_pattern_y.setValue(6)
        self.ctrl_layout.addWidget(self.cb_pattern_y)

        self.log_edit = QPlainTextEdit()
        self.log_edit.setMaximumSize(QSize(220, 200))
        self.log_edit.setStyleSheet("color:gray; border: 3px solid white;border-radius:12px")
        self.ctrl_layout.addWidget(self.log_edit)

        self.gridLayout.addLayout(self.ctrl_layout, 0, 0, 1, 1)

        # 右侧图像区域
        # 创建滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.image_label = QLabel()
        self.image_label.setMinimumSize(QSize(120, 240))
        #self.image_label.setFrameShape(QFrame.Box)
        self.image_label.setAlignment(Qt.AlignCenter)

        self.gridLayout.addWidget(self.image_label, 0, 1, 1, 1)
        self.gridLayout.addWidget(self.scroll_area, 0, 2, 5, 5)
        #self.statusbar = QStatusBar()
        self.statusBar().addPermanentWidget(QLabel("V1.0"))

        MainWindow.setCentralWidget(self.centralwidget)
        self.retranslateUi(MainWindow)
        QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow",
                                "相机标定工具 By bighton-li  图片请用全英文路径", None))