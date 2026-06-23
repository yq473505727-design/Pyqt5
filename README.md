# Pyqt5

PYQT5开发

## 新界面启动说明

此目录中的 `main.py` 是新 UI 的业务入口，`win.py` 仍然是由 Qt Designer / `pyuic5` 生成的界面文件。

推荐使用已经安装 PyQt5 的 Python 3 环境启动：

```powershell
C:\Users\47350\.conda\envs\py310\python.exe C:\Users\47350\PycharmProjects\pythonProject\new\main.py
```

普通“保存定轨方案”默认写入 `new\scheme`，会生成 `GCP`、`LCP`、`SimCP`、`StaCP` 四类控制卡片。

点击“开始定轨”会异步启动 `new\external\TestOrbitProgram.exe`，并把该程序的标准输出和标准错误实时追加到“定轨输出”页面。测试程序会读取当前方案目录的 `GCP`、`LCP`、`SimCP`、`StaCP`，随后输出模拟定轨迭代信息。程序运行期间可用“清空/停止”终止进程。

测试程序源代码位于 `new\test_program\test_orbit_program.py`。需要重新生成 EXE 时执行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\test_program\build_test_exe.ps1
```

生成位置固定为 `new\external\TestOrbitProgram.exe`，不会修改 `dist`。以后接入真实定轨程序时，可在 `main.py` 中修改 `ORBIT_PROGRAM`；若真实程序不是 UTF-8 输出，同时修改 `ORBIT_OUTPUT_ENCODING`。

旧 `pyqt5demo` 中的主要模块已经以同名方式嵌入到 `new`：`Chart.py`、`Input.py`、`Output.py`、`Residual.py`、`UIStart.py`、`UseFortran.py`、`iconsource_rc.py`。顶部快捷按钮使用 `new\assets\icons` 中的 PNG 图标。
