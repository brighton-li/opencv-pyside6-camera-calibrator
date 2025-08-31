#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os, datetime, json
import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox, QLabel, QWidget, QGridLayout

from ui import Ui_MainWindow

class CameraThread(QThread):
    """后台线程：持续读取相机并发送帧"""
    frame_ready = Signal(np.ndarray)

    def __init__(self, cam_id=0):
        super().__init__()
        self.cam_id = cam_id
        self.cap = None
        self.running = False

    def run(self):
        self.cap = cv2.VideoCapture(self.cam_id)
        if not self.cap.isOpened():
            self.frame_ready.emit(None)
            return
        self.running = True
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.frame_ready.emit(frame)
            elif self.running:  # 如果仍在运行状态但无法读取帧，可能是用户权限终止
                # 发送特殊的None帧表示相机连接被意外终止
                self.frame_ready.emit(None)
                break
        self.cap.release()

    def stop(self):
        self.running = False
        self.wait()


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # 初始化成员
        self.cam_thread = None
        self.current_frame = None
        self.img_points = []      # 检测到的角点
        self.obj_points = []      # 对应 3D 坐标
        self.image_labels = []    # 存图片的标签
        self.img_group = []       # 存储图像的列表
        self.calib_result = None  # 标定结果 dict
        self.local_pic_id = 0     # 本地图片id
        self.total = 0            # 本地图片总数
        self.cam_id = 0
        self.camera_opening = False  # 防止重复尝试打开相机的标志

        # 创建右侧图片网格布局
        self.gallery_widget = QWidget()
        self.right_grid_layout = QGridLayout(self.gallery_widget)
        self.scroll_area.setWidget(self.gallery_widget)

        # 棋盘格参数
        self.pattern_size = (self.cb_pattern_x.value(),
                             self.cb_pattern_y.value())

        # 信号/槽
        self.btn_open_cam.clicked.connect(self.toggle_camera)
        self.btn_detect.clicked.connect(self.detect_image)
        self.btn_file.clicked.connect(self.input_local)
        self.btn_calibrate.clicked.connect(self.calibrate)
        self.btn_save.clicked.connect(self.save_result)
        self.cb_pattern_x.valueChanged.connect(self.update_pattern)
        self.cb_pattern_y.valueChanged.connect(self.update_pattern)
        self.combobox_cam.currentIndexChanged.connect(self.cam_change)

    # ----------------- 相机 -----------------
    def cam_change(self,index):
        self.cam_id = index

    def toggle_camera(self):
        # 如果已经在尝试打开相机，不重复尝试
        if self.camera_opening:
            return
            
        if self.cam_thread is None or not self.cam_thread.isRunning():
            self.log("打开相机...")
            self.camera_opening = True  # 设置正在打开标志
            try:
                self.cam_thread = CameraThread(cam_id = self.cam_id)
                self.cam_thread.frame_ready.connect(self.on_frame)
                self.cam_thread.start()
                self.btn_open_cam.setText("关闭相机")
                self.btn_detect.setEnabled(True)
            finally:
                # 确保无论如何都会清除标志
                self.camera_opening = False
        else:
            self.cam_thread.stop()
            self.btn_open_cam.setText("打开相机")
            self.btn_detect.setEnabled(False)
            self.btn_calibrate.setEnabled(bool(self.img_points))
            self.image_label.clear()

    def on_frame(self, frame):
        if frame is None:
            # 检查相机线程是否存在且正在运行
            if self.cam_thread and self.cam_thread.isRunning():
                # 如果相机已经成功打开过但现在收到None帧，很可能是用户权限终止
                QMessageBox.critical(self, "错误", "相机连接已被终止！\n可能是由于用户权限被撤销或其他系统原因。")
                self.log("相机连接被用户权限终止")
            else:
                # 初始打开相机失败
                QMessageBox.critical(self, "错误", "无法打开相机！\n请检查相机是否连接或尝试选择其他相机索引。")
                self.log("相机打开失败")
            # 直接更新UI状态
            if self.cam_thread:
                self.cam_thread.stop()
                self.cam_thread = None
            self.btn_open_cam.setText("打开相机")
            self.btn_detect.setEnabled(False)
            self.image_label.clear()
            return
        self.current_frame = frame.copy()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        self.image_label.setPixmap(QPixmap.fromImage(qimg))

    # ----------------- 本地文件 -----------------
    def input_local(self):
        files_path, _ = QFileDialog.getOpenFileNames(self, "选择所有待标定图片", "","图片（*.PNG *.JPG "
                                                 "*.JPEG *.BMP *.TIFF;;所有")
        # 添加新图片
        row, col = 0, 0
        max_columns = 5  # 每行最多显示k张图片
        self.total = 0
        self.local_pic_id = 0  # 重置本地图片索引
        # 清空原图片和数据
        self.clear_gallery()
        self.img_group.clear()  # 清空图片数据列表
        self.obj_points = []    # 清空检测到的角点
        self.img_points = []    # 清空对应的3D点
        self.label_count.setText(f"已采集: 0 张")
        self.image_label.setText("待检测后显示")
        self.btn_calibrate.setEnabled(False)
        self.log("已重置")

        for path in files_path:
            pixmap = QPixmap(path)
            self.img_group.append(cv2.imread(path))  # 采集角点会用
            if not pixmap.isNull():
                label = QLabel()
                label.setAlignment(Qt.AlignCenter)
                label.setPixmap(pixmap.scaled(
                    120, 120, 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                ))
                label.setStyleSheet("border: 1px solid gray; margin: 5px;")
                label.setToolTip(path)
                self.right_grid_layout.addWidget(label, row, col)
                label.setToolTip(path)
                col += 1
                self.total += 1
                if col >= max_columns:
                    col = 0
                    row += 1
        #self.log(f"已经本地导入{self.total} 张图片")
        self.label_input.setText(f"已本地导入: {self.total} 张")
        self.log(f"已导入本地图片 {self.total}张")
        self.btn_open_cam.setEnabled(False)
        if self.total >= 1:
            self.btn_detect.setEnabled(True)
        
    def clear_gallery(self):
        # 移除所有图片标签
        for label in self.image_labels:
            self.right_grid_layout.removeWidget(label)
            label.deleteLater()
        self.image_labels = []

    # ----------------- 检测角点 -----------------
    def detect_image(self):
        if self.current_frame is None and self.total == 0:
            return
        if self.current_frame is not None:
            gray = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2GRAY)
            ret, corners = cv2.findChessboardCorners(
                gray, self.pattern_size,
                cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_FAST_CHECK +
                cv2.CALIB_CB_NORMALIZE_IMAGE)
            if ret:
                cv2.cornerSubPix(gray, corners, (3, 3), (-1, -1),
                                criteria=(cv2.TERM_CRITERIA_EPS +
                                        cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001))
                self.img_points.append(corners)
                # 构建 object points，假设棋盘格边长 1
                objp = np.zeros((self.pattern_size[0] * self.pattern_size[1], 3),
                                np.float32)
                objp[:, :2] = np.mgrid[0:self.pattern_size[0],
                                    0:self.pattern_size[1]].T.reshape(-1, 2)
                self.obj_points.append(objp)
                self.label_count.setText(f"已采集: {len(self.img_points)} 张")
                self.btn_calibrate.setEnabled(True)
                self.log("采集成功，检测到角点")
                
                # 在图片上绘制角点并更新展示画面
                corners_img = self.current_frame.copy()
                cv2.drawChessboardCorners(corners_img, self.pattern_size, corners, ret)
                rgb = cv2.cvtColor(corners_img, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb.shape
                qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
                self.image_label.setPixmap(QPixmap.fromImage(qimg))
            else:
                self.log("未检测到棋盘格，请调整姿态再试")
            # 检测完当前帧后清除，确保下一次检测能继续处理本地图片
            self.current_frame = None
        elif self.total > 0:
            
            self.current_frame = self.img_group[self.local_pic_id].copy()
            current_pic_index = self.local_pic_id + 1
            self.local_pic_id += 1
            
            self.log(f"检测第 {current_pic_index}/{self.total} 张图片")
            gray = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2GRAY)
            ret, corners = cv2.findChessboardCorners(
                gray, self.pattern_size,
                cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_FAST_CHECK +
                cv2.CALIB_CB_NORMALIZE_IMAGE)
            if ret:
                cv2.cornerSubPix(gray, corners, (3, 3), (-1, -1),
                                criteria=(cv2.TERM_CRITERIA_EPS +
                                        cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001))
                self.img_points.append(corners)
                # 构建 object points，假设棋盘格边长 1
                objp = np.zeros((self.pattern_size[0] * self.pattern_size[1], 3),
                                np.float32)
                objp[:, :2] = np.mgrid[0:self.pattern_size[0],
                                    0:self.pattern_size[1]].T.reshape(-1, 2)
                self.obj_points.append(objp)
                self.label_count.setText(f"已采集: {len(self.img_points)} 张")
                self.btn_calibrate.setEnabled(True)
                self.log("采集成功，检测到角点")
                
                # 在本地图片上绘制角点并更新展示画面
                corners_img = self.current_frame.copy()
                cv2.drawChessboardCorners(corners_img, self.pattern_size, corners, ret)
                rgb = cv2.cvtColor(corners_img, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb.shape
                qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
                self.image_label.setPixmap(QPixmap.fromImage(qimg))
            else:
                self.log("未检测到棋盘格，请调整姿态再试")
            if self.local_pic_id > self.total:
                 self.btn_calibrate.setEnabled(False)
            # 检测完本地图片后清除，确保下一次检测能继续处理下一张图片
            self.current_frame = None

            if self.local_pic_id >= self.total:
                self.log("已检测完所有图片，可考虑标定")
                self.btn_detect.setEnabled(False) 

    # ----------------- 标定 -----------------
    def calibrate(self):
        if len(self.img_points) < 9:
            QMessageBox.warning(self, "提示", "至少需要 9 张图片")
            return
        self.log("开始标定...")
        # 使用最后一张成功检测的图片得到他们的图像尺寸，避免依赖self.current_frame
        if self.img_group and len(self.img_group) > 0:
            gray = cv2.cvtColor(self.img_group[-1], cv2.COLOR_BGR2GRAY)
        else:
            QMessageBox.warning(self, "错误", "未找到可用的图像数据")
            return
        ret, K, dist, rvecs, tvecs = cv2.calibrateCamera(
            self.obj_points, self.img_points,
            gray.shape[::-1], None, None)
        self.calib_result = {
            "reprojection_error": ret,
            "camera_matrix": K.tolist(),
            "dist_coeffs": dist.tolist(),
            "image_size": gray.shape[::-1]
        }
        self.btn_save.setEnabled(True)
        self.log("标定完成！重投影误差 = {:.3f}".format(ret))

    # ----------------- 保存 ------------------
    def save_result(self):
        if self.calib_result is None:
            return
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"calib_{ts}.json"
        path, _ = QFileDialog.getSaveFileName(self, "保存标定结果", default_name,
                                              "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.calib_result, f, indent=2, ensure_ascii=False)
            self.log("结果已保存：" + path)

    # ----------------- 其他 -----------------
    def update_pattern(self):
        self.pattern_size = (self.cb_pattern_x.value(),
                             self.cb_pattern_y.value())

    def log(self, text):
        self.log_edit.appendPlainText(text)
        self.log_edit.verticalScrollBar().setValue(
            self.log_edit.verticalScrollBar().maximum())

    def closeEvent(self, event):
        if self.cam_thread and self.cam_thread.isRunning():
            self.cam_thread.stop()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())