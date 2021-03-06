# -*- coding: utf-8 -*-
from os import listdir, path, mkdir, remove
from re import sub
from platform import system
import configparser
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QFileDialog, QApplication, QMainWindow
from PyQt5.QtCore import QDateTime, QTime, Qt
from static import Ui_MainWindow
from worker import Fis, Jm, JtoF, FtoJ
from JFlink.read import getFNum


class Dynamics(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(Dynamics, self).__init__()
        self.setupUi(self)
        # 内部变量
        self._Zoom = 0
        self._LastRoute = '.'
        self._InfoText = ''
        self._logNum = 1
        # False--JtoF True--FtoJ
        self._ToDoL = False
        # False--callF True--callJ
        self._ToDoR = False
        self._ProgressOne = 0
        self._ProgressAll = 0
        self._Num = 0
        self._OneStep = 0
        self._AllStep = 0
        # 动作信号
        self.JOutFilePickU.clicked.connect(self.openJFileUp)
        self.JOutFilePickD.clicked.connect(self.openJFileDown)
        self.GFilePick.clicked.connect(self.openGFile)
        self.FWorkPickU.clicked.connect(self.openFDirUp)
        self.FWorkPickD.clicked.connect(self.openFDirDown)
        self.Load.clicked.connect(self.loadFiles)
        self.QuitL.clicked.connect(self.close)
        self.JtoFChose.clicked.connect(self.jtoF)
        self.FtoJChose.clicked.connect(self.ftoJ)
        self.StartL.clicked.connect(self.start)
        self.JModelPick.clicked.connect(self.openJModel)

        self.FPick.clicked.connect(self.openFInstall)
        self.EPick.clicked.connect(self.openEAFDir)
        self.FWorkPick.clicked.connect(self.openFDirRight)
        self.JInPick.clicked.connect(self.openJIn)
        self.Clear.clicked.connect(self.reset)
        self.QuitR.clicked.connect(self.close)
        self.StartR.clicked.connect(self.call)

        self.CallFISP.clicked.connect(self.callF)
        self.CallJMCT.clicked.connect(self.callJ)
        self.allEnableL(1)
        self.allEnableR(True)

        self.config = configparser.ConfigParser()
        self.pickPath()

        self.fis = Fis()
        self.fis.siginfo.connect(self.info)
        self.fis.sigend.connect(self.cancelCallF)
        self.Weight.setCurrentIndex(2)

        self.jmct = Jm()
        self.jmct.siginfo.connect(self.info)
        self.jmct.sigend.connect(self.cancelCallJ)

        self.j2f = JtoF()
        self.j2f.signal1.connect(self.updateBar)
        self.j2f.signal2.connect(self.getOneProgress)
        self.j2f.siginfo.connect(self.info)
        self.j2f.sigend.connect(self.cancelJ2F)

        self.f2j = FtoJ()
        self.f2j.signal1.connect(self.updateBar)
        self.f2j.signal2.connect(self.getOneProgress)
        self.f2j.siginfo.connect(self.info)
        self.f2j.sigend.connect(self.cancelF2J)

        self.__desktop = QApplication.desktop()
        self.reSize()

    def cancelJ2F(self):
        self.info('结束', 0)
        self.j2f.terminate()
        while self.j2f.isRunning():
            pass
        self.allEnableL(3)
        self.StartL.setText('开始')
        self.StartL.clicked.disconnect()
        self.StartL.clicked.connect(self.start)
        self.Bar.setValue(0)

    def cancelF2J(self):
        self.info('结束', 0)
        self.f2j.terminate()
        while self.f2j.isRunning():
            pass
        self.allEnableL(3)
        self.StartL.setText('开始')
        self.StartL.clicked.disconnect()
        self.StartL.clicked.connect(self.start)
        self.Bar.setValue(0)

    def cancelCallJ(self):
        self.info('结束', 0)
        self.jmct.kill()
        if not self.jmct.wait(msecs=2500):
            self.jmct.terminate()
        self.allEnableR(3)
        self.StartR.setText('开始')
        self.StartR.clicked.disconnect()
        self.StartR.clicked.connect(self.call)

    def cancelCallF(self):
        self.fis.requestInterruption()
        self.fis.kill()
        if not self.fis.wait(msecs=2500):
            self.fis.terminate()
            self.info('运行被终止，可能存在异常')
        self.allEnableR(3)
        self.StartR.setText('开始')
        self.StartR.clicked.disconnect()
        self.StartR.clicked.connect(self.call)

    def closeEvent(self, event):
        self.saveAll()
        event.accept()

    def pickPath(self):
        try:
            if path.isfile('./tmp/wiz.ini'):
                with open('./tmp/wiz.ini', 'r', encoding='utf-8-sig') as f:
                    self.config.read_file(f)
                if 'turn' in self.config.sections():
                    self.JOutFilePathU.setText(self.config['turn']['jpathu'])
                    self.GFilePath.setText(self.config['turn']['gpathu'])
                    self.FWorkPathU.setText(self.config['turn']['fpathu'])
                    self.GenRate.setText(self.config['turn']['genrate'])

                    self.FWorkPathD.setText(self.config['turn']['fpathd'])
                    self.JOutFilePathD.setText(self.config['turn']['jpathd'])
                    self.JModelPath.setText(self.config['turn']['jmodel'])

                    self.comboBox.setCurrentIndex(int(self.config['turn']['type']))
                    self.spinBox.setValue(int(self.config['turn']['digital']))
                if 'call' in self.config.sections():
                    self.FPath.setText(self.config['call']['fispact'])
                    self.EPath.setText(self.config['call']['eaf'])
                    self.FWorkPathR.setText(self.config['call']['case'])

                    self.JInPath.setText(self.config['call']['jpath'])
                if 'global' in self.config.sections():
                    self._logNum = int(self.config['global']['logs'])
        except KeyError:
            pass
        except Exception as e:
            self.info(repr(e), 0)

    def saveAll(self):
        now = QDateTime.currentDateTime()
        if not path.exists('./tmp'):
            mkdir('./tmp')
        with open('./tmp/log-%s.log' % now.toString('yyyy-MM-dd-hh-mm-ss-zzz'), 'w') as f:
            f.write(self._InfoText)

        if 'turn' not in self.config.sections():
            # self.config.add_section('turn')
            self.config['turn'] = {}
        if 'call' not in self.config.sections():
            self.config['call'] = {}
        if 'global' not in self.config.sections():
            self.config['global'] = {}
        self.config['turn']['jpathu'] = self.JOutFilePathU.text()
        self.config['turn']['gpathu'] = self.GFilePath.text()
        self.config['turn']['fpathu'] = self.FWorkPathU.text()
        self.config['turn']['genrate'] = self.GenRate.text()

        self.config['turn']['fpathd'] = self.FWorkPathD.text()
        self.config['turn']['jpathd'] = self.JOutFilePathD.text()
        self.config['turn']['jmodel'] = self.JModelPath.text()

        self.config['turn']['type'] = str(self.comboBox.currentIndex())
        self.config['turn']['digital'] = str(self.spinBox.value())

        self.config['call']['fispact'] = self.FPath.text()
        self.config['call']['eaf'] = self.EPath.text()
        self.config['call']['case'] = self.FWorkPathR.text()
        self.config['call']['jpath'] = self.JInPath.text()
        self.config['global']['logs'] = str(self._logNum)
        with open('./tmp/wiz.ini', 'w', encoding='utf-8-sig') as f:
            self.config.write(f)

        logs = [i for i in listdir('./tmp') if i[-4:] == '.log']
        sorted(logs)
        if len(logs) > self._logNum:
            for i in range(0, len(logs) - self._logNum):
                remove(r'./tmp/%s' % logs[i])

    def reSize(self):
        screenrect = self.__desktop.screenGeometry()
        height = screenrect.height() * 9 // 10
        weight = round(37 * height / 52)
        self.resize(weight, height)
        self.setFixedSize(self.width(), self.height())

    def allEnableL(self, flag):
        # flag = 0 -- release J2F, lock F2J
        # flag = 1 -- release F2J, lock J2F
        # flag = 2 -- lock all but begin
        # flag = 3 -- release all
        if flag < 2:
            flag = True if flag == 1 else False
            self.JOutFilePathU.setEnabled(flag)
            self.GFilePath.setEnabled(flag)
            self.FWorkPathU.setEnabled(flag)
            self.JOutFilePickU.setEnabled(flag)
            self.GFilePick.setEnabled(flag)
            self.FWorkPickU.setEnabled(flag)
            self.GenRate.setEnabled(flag)
            self.Collapx.setEnabled(flag)
            self.Arrayx.setEnabled(flag)
            self.Input.setEnabled(flag)
            self.Printlib.setEnabled(flag)

            self._ToDoL = flag
            self.MaxFlag.setEnabled(not flag)
            self.JOutFilePathD.setEnabled(not flag)
            self.FWorkPathD.setEnabled(not flag)
            self.JModelPath.setEnabled(not flag)
            self.JOutFilePickD.setEnabled(not flag)
            self.FWorkPickD.setEnabled(not flag)
            self.JModelPick.setEnabled(not flag)
            self.JMCT.setEnabled(not flag)
            self.RemainJOut.setEnabled(not flag)

            self.FileEdit.setCurrentIndex(0 if flag else 4)

        else:
            flag = True if flag == 3 else False
            self.JOutFilePathU.setEnabled(flag)
            self.GFilePath.setEnabled(flag)
            self.FWorkPathU.setEnabled(flag)
            self.JOutFilePickU.setEnabled(flag)
            self.GFilePick.setEnabled(flag)
            self.FWorkPickU.setEnabled(flag)
            self.GenRate.setEnabled(flag)
            self.Collapx.setEnabled(flag)
            self.Arrayx.setEnabled(flag)
            self.Input.setEnabled(flag)
            self.Printlib.setEnabled(flag)

            self.MaxFlag.setEnabled(flag)
            self.JOutFilePathD.setEnabled(flag)
            self.FWorkPathD.setEnabled(flag)
            self.JModelPath.setEnabled(flag)
            self.JOutFilePickD.setEnabled(flag)
            self.FWorkPickD.setEnabled(flag)
            self.JModelPick.setEnabled(flag)
            self.JMCT.setEnabled(flag)
            self.RemainJOut.setEnabled(flag)

            self.Sync.setEnabled(flag)
            self.QuitL.setEnabled(flag)

        if flag == 3:
            flag = 1 if self._ToDoL else 0
            self.allEnableL(flag)

    def allEnableR(self, flag):
        # flag = 0 -- release callF, lock callJ
        # flag = 1 -- release callJ, lock callF
        # flag = 2 -- lock all but begin
        # flag = 3 -- release all
        if flag < 2:
            flag = True if flag == 1 else False
            self._ToDoR = flag
            self.Group.setEnabled(flag)
            self.Weight.setEnabled(flag)
            self.Particle.setEnabled(flag)
            self.FWorkPathR.setEnabled(flag)
            self.FWorkPick.setEnabled(flag)
            self.FPath.setEnabled(flag)
            self.EPath.setEnabled(flag)
            self.FPick.setEnabled(flag)
            self.EPick.setEnabled(flag)

            self.JInPath.setEnabled(not flag)
            self.JInPick.setEnabled(not flag)
        else:
            flag = True if flag == 3 else False
            self.Group.setEnabled(flag)
            self.Weight.setEnabled(flag)
            self.Particle.setEnabled(flag)
            self.FWorkPathR.setEnabled(flag)
            self.FWorkPick.setEnabled(flag)
            self.FPath.setEnabled(flag)
            self.EPath.setEnabled(flag)
            self.FPick.setEnabled(flag)
            self.EPick.setEnabled(flag)

            self.JInPath.setEnabled(flag)
            self.JInPick.setEnabled(flag)

        if flag == 3:
            flag = 1 if self._ToDoR else 0
            self.allEnableR(flag)

    def jtoF(self):
        self.allEnableL(1)

    def ftoJ(self):
        self.allEnableL(0)

    def callF(self):
        self.allEnableR(1)

    def callJ(self):
        self.allEnableR(0)

    def getOneProgress(self, t, n):
        if self._ToDoL is True:
            self._Zoom = 1 / 8
        else:
            self._Zoom = 1 / 7
        self._Num = n
        self._OneStep = 100 / t
        self._AllStep = 100 * self._Zoom / t

    def updateBar(self, clear):
        if clear:
            self._ProgressOne = 0
            self._ProgressOne += self._OneStep
            self._ProgressAll += self._AllStep
            self.info('1/%d' % self._Num, 1)
        else:
            self._ProgressOne += self._OneStep
            self._ProgressAll += self._AllStep
            if self._ProgressOne > 100.:
                self._ProgressOne = 100.
            self.info(round((self._ProgressOne * self._Num) // 100), 2)
        if self._ProgressAll > 100.:
            self._ProgressAll = 100.
        self.Bar.setValue(round(self._ProgressAll))

    def openJFileUp(self):
        self._LastRoute, ok = QFileDialog.getOpenFileName(self, "选择文件", self._LastRoute,
                                                          "JMCT Output File (*.out);;All Files (*)")
        if self._LastRoute != '':
            self.JOutFilePathU.setText(self._LastRoute)
            if self.Sync.isChecked():
                self.JOutFilePathD.setText(self._LastRoute)

    def openJFileDown(self):
        self._LastRoute, ok = QFileDialog.getOpenFileName(self, "选择文件", self._LastRoute,
                                                          "JMCT Output File (*.out);;All Files (*)")
        if self._LastRoute != '':
            self.JOutFilePathD.setText(self._LastRoute)
            if self.Sync.isChecked():
                self.JOutFilePathU.setText(self._LastRoute)

    def openJModel(self):
        self._LastRoute, ok = QFileDialog.getOpenFileName(self, "选择文件", self._LastRoute,
                                                          "JMCT Input File (*.input);;All Files (*)")
        if self._LastRoute != '':
            self.JModelPath.setText(self._LastRoute)

    def openGFile(self):
        self._LastRoute, ok = QFileDialog.getOpenFileName(self, "选择文件", self._LastRoute,
                                                          "GDML Structure File (*.gdml);;All Files (*)")
        if self._LastRoute != '':
            self.GFilePath.setText(self._LastRoute)

    def openFDirUp(self):
        self._LastRoute = QFileDialog.getExistingDirectory(self, "选择文件夹", self._LastRoute)
        if self._LastRoute != '':
            self.FWorkPathU.setText(self._LastRoute)
            if self.Sync.isChecked():
                self.FWorkPathD.setText(self._LastRoute)
                self.FWorkPathR.setText(self._LastRoute)

    def openFDirDown(self):
        self._LastRoute = QFileDialog.getExistingDirectory(self, "选择文件夹", self._LastRoute)
        if self._LastRoute != '':
            self.FWorkPathD.setText(self._LastRoute)
            if self.Sync.isChecked():
                self.FWorkPathU.setText(self._LastRoute)
                self.FWorkPathR.setText(self._LastRoute)

    def openFInstall(self):
        if 'Windows' in system():
            self._LastRoute, ok = QFileDialog.getOpenFileName(self, "选择文件", self._LastRoute,
                                                              "FISPACT Binary File (*.exe);;All Files (*)")
        else:
            self._LastRoute, ok = QFileDialog.getOpenFileName(self, "选择文件", self._LastRoute,
                                                              "FISPACT Binary File (*.bin);;All Files (*)")
        if self._LastRoute != '':
            self.FPath.setText(self._LastRoute)

    def openEAFDir(self):
        self._LastRoute = QFileDialog.getExistingDirectory(self, "选择文件夹", self._LastRoute)
        if self._LastRoute != '':
            self.EPath.setText(self._LastRoute)

    def openFDirRight(self):
        self._LastRoute = QFileDialog.getExistingDirectory(self, "选择文件夹", self._LastRoute)
        if self._LastRoute != '':
            self.FWorkPathR.setText(self._LastRoute)

    def openJIn(self):
        self._LastRoute, ok = QFileDialog.getOpenFileName(self, "选择文件", self._LastRoute,
                                                          "JMCT Input File (*.input);;All Files (*)")
        if self._LastRoute != '':
            self.JInPath.setText(self._LastRoute)

    def info(self, text, mode=0):
        # mode=0 -- newline
        # mode=1 -- sameline
        # mode=2 -- revise
        # mode=3 -- newline without empty line
        time = QTime.currentTime()
        if mode == 0:
            if len(self._InfoText) > 0 and self._InfoText[-1] != '\n':
                self._InfoText += '\n\n'
            self._InfoText += '[%s] %s' % (time.toString(Qt.DefaultLocaleLongDate), text)
        elif mode == 1:
            self._InfoText += '...%s' % text
        elif mode == 2:
            self._InfoText = sub('\d+(/\d+)$', r'%d\1' % text, self._InfoText)
        elif mode == 3:
            if len(self._InfoText) > 0 and self._InfoText[-1] != '\n':
                self._InfoText += '\n'
            self._InfoText += '[%s] %s' % (time.toString(Qt.DefaultLocaleLongDate), text)
        self.StatusL.setText(self._InfoText)
        self.StatusR.setText(self._InfoText)
        self.StatusL.moveCursor(QTextCursor.End)
        self.StatusR.moveCursor(QTextCursor.End)

    def loadFiles(self):
        if self._ToDoL is True:
            _FISPWork = self.FWorkPathU.text()
            if _FISPWork == '':
                self.info('错误：未指定FISPACT工作目录', 0)
            else:
                self.info('从 %s 读取FISPACT输入文件' % _FISPWork, 0)
                dirs = listdir(_FISPWork)
                tmp = list(filter(lambda name: name[-2:] == '.i', dirs))
                # 是否找到至少一个文件
                found = False
                if 'collapx.i' in tmp:
                    self.info('更新collapx.i', 1)
                    with open(_FISPWork + '/collapx.i') as f:
                        text = f.read()
                    self.CFileEdit.setText(text)
                    found = True
                else:
                    self.info('未找到collapx.i', 1)
                if 'arrayx.i' in tmp:
                    self.info('更新arrayx.i', 1)
                    with open(_FISPWork + '/arrayx.i') as f:
                        text = f.read()
                    self.AFileEdit.setText(text)
                    found = True
                else:
                    self.info('未找到arrayx.i', 1)
                if 'printlib.i' in tmp:
                    self.info('更新printlib.i', 1)
                    with open(_FISPWork + '/arrayx.i') as f:
                        text = f.read()
                    self.PFileEdit.setText(text)
                    found = True
                else:
                    self.info('未找到printlib.i', 1)
                if 'input.i' in tmp:
                    self.info('更新input.i', 1)
                    with open(_FISPWork + '/input.i') as f:
                        text = f.read()
                    self.IFileEdit.setText(text)
                    found = True
                else:
                    self.info('未找到input.i', 1)
                if not found:
                    self.info('错误：工作目录下没有发现任何有效文件', 0)

        elif self._ToDoL is False:
            path = self.JModelPath.text()
            if path == '':
                self.info('错误：未指定JMCT模板文件', 0)
            else:
                try:
                    self.info('从 %s 读取JMCT模板文件' % path, 0)
                    with open(path) as f:
                        text = f.read()
                    self.JFileEdit.setText(text)
                    # 判断冷却阶段条目并输出

                    length = getFNum(self.FWorkPathD.text())
                    self.info('已发现%d个冷却阶段，请指定需要使用的冷却阶段\n-1表示使用最后一个阶段\n0表示使用活化阶段' % (length - 1))
                    self.spinBox_2.setMaximum(length - 1)
                    self.spinBox_2.setValue(-1)
                except FileNotFoundError as e:
                    self.info('错误：JMCT模板文件位置无效 -> ' + repr(e), 0)
                    return
                except Exception as e:
                    self.info(repr(e))
                    return

    def reset(self):
        self.info('清屏', 0)

        self._InfoText = ''
        self.StatusL.setText(self._InfoText)
        self.StatusR.setText(self._InfoText)
        self.Bar.setValue(0)

    def start(self):
        if self._ToDoL is True:
            self._ProgressAll = 0
            try:
                self.j2f.JPathU = self.JOutFilePathU.text()
                self.j2f.GPath = self.GFilePath.text()
                self.j2f.FPath = self.FWorkPathU.text()
                self.j2f.CText = self.CFileEdit.toPlainText()
                self.j2f.AText = self.AFileEdit.toPlainText()
                self.j2f.IText = self.IFileEdit.toPlainText()
                self.j2f.PText = self.PFileEdit.toPlainText()
                self.j2f.GenRate = self.GenRate.text()
                self.j2f.digital = self.spinBox.value()

                self.allEnableL(2)
                self.StartL.setText('中止')
                self.StartL.clicked.disconnect()
                self.StartL.clicked.connect(self.cancelJ2F)
                self.j2f.start()

            except Exception as e:
                self.info(str(e), 0)

        elif self._ToDoL is False:
            if self.JFileEdit.toPlainText() == '':
                self.info('JMCT模板文件为空', 0)
                return
            self._ProgressAll = 0
            try:
                self.f2j.FPath = self.FWorkPathD.text()
                self.f2j.JPathD = self.JOutFilePathD.text()
                self.f2j.JModel = self.JModelPath.text()
                self.f2j.JText = self.JFileEdit.toPlainText()
                self.f2j.Max = self.MaxFlag.text()
                self.f2j.Remain = self.RemainJOut.isChecked()
                self.f2j.choose = self.spinBox_2.value()
                self.f2j.type[0] = ['sci', 'dem'][self.comboBox.currentIndex()]
                self.f2j.type[1] = self.spinBox.value()

                self.allEnableL(2)
                self.StartL.setText('中止')
                self.StartL.clicked.disconnect()
                self.StartL.clicked.connect(self.cancelF2J)
                self.f2j.start()
            except Exception as e:
                self.info(str(e), 0)

    def call(self):
        if self._ToDoR is True:
            # callFISP
            fpath = self.FPath.text()
            epath = self.EPath.text()
            case = self.FWorkPathR.text()

            if fpath == '':
                self.info('错误：未指定FISPACT主程序位置', 0)
                return
            if epath == '':
                self.info('错误：未指定EAF数据库安装目录', 0)
                return
            if case == '':
                self.info('错误：未指定FISPACT工作目录', 0)
                return

            tmp = ['69', '100', '172', '175', '211', '315', '351']
            g = tmp[self.Group.currentIndex()]
            tmp = ['flt', 'fis', 'fus']
            w = tmp[self.Weight.currentIndex()]
            tmp = ['n', 'p', 'd']
            p = tmp[self.Particle.currentIndex()]

            self.fis.env = [fpath, epath]
            self.fis.group = [p, g, w]
            self.fis.case = case

            self.allEnableR(2)
            self.StartR.setText('中止')
            self.StartR.clicked.disconnect()
            self.StartR.clicked.connect(self.cancelCallF)
            self.fis.start()
        else:
            # callJMCT
            jinpath = self.JInPath.text()
            if jinpath == '':
                self.info('错误：未指定JMCT输入文件', 0)
                return
            self.jmct.JInPath = jinpath

            self.allEnableR(2)
            self.StartR.setText('中止')
            self.StartR.clicked.disconnect()
            self.StartR.clicked.connect(self.cancelCallJ)
            self.jmct.start()
