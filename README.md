# Pyqt5

PYQT5开发

## 新界面启动说明

此目录中的 `main.py` 是新 UI 的业务入口，`win.py` 仍然是由 Qt Designer / `pyuic5` 生成的界面文件。

推荐使用已经安装 PyQt5 的 Python 3 环境启动：

```powershell
C:\Users\47350\.conda\envs\py310\python.exe C:\Users\47350\PycharmProjects\pythonProject\new\main.py
```

普通“保存定轨方案”默认写入 `new\scheme`，会生成 `GCP`、`LCP`、`SimCP`、`StaCP` 四类控制卡片。

点击“开始定轨”会直接使用 `new\orbit_backend.py` 的 Python 内置二体动力学后端计算，不需要启动旧项目程序。结果写入 `new\output\orbit_result.csv` 和 `new\output\summary.txt`。如需用观测值修正初轨，可在方案目录放置 `observations.csv`，表头使用 `seconds,x,y,z` 或 `utc,x,y,z`。

旧 `pyqt5demo` 中的主要模块已经以同名方式嵌入到 `new`：`Chart.py`、`Input.py`、`Output.py`、`Residual.py`、`UIStart.py`、`UseFortran.py`、`iconsource_rc.py`。顶部快捷按钮使用 `new\assets\icons` 中的 PNG 图标。
