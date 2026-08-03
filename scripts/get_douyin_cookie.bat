@echo off
chcp 65001 >nul
title Douyin Cookie Helper
rem ============================================================
rem  抖音 Cookie 抓取助手（扫码登录，可移植版，无硬编码路径）
rem  前置：已把 jiji262/douyin-downloader 克隆到仓库根目录，
rem        且当前 python 已安装该项目的依赖。
rem ============================================================
set "BASE=%~dp0.."
set "DL_DIR=%BASE%\douyin-downloader"
if not exist "%DL_DIR%\run.py" (
  echo [错误] 未找到 douyin-downloader。请先克隆到仓库根目录：
  echo.
  echo    git clone https://github.com/jiji262/douyin-downloader.git
  echo.
  echo  或设置环境变量 DD_DL_SRC 指向其源码目录后再运行。
  pause
  exit /b 1
)
cd /d "%DL_DIR%"
echo ============================================================
echo  抖音 Cookie 抓取助手（扫码登录）
echo ============================================================
echo.
echo  [第一步] 本窗口会自动打开浏览器，进入抖音网页版登录页
echo           （若没自动打开，等 1 分钟初始化后手动打开：
echo             https://www.douyin.com/ ）
echo.
echo  [第二步] 在浏览器里点「扫码登录」
echo           - 打开手机上的抖音 App
echo           - 用右上角「扫一扫」对准网页上的二维码
echo           - 手机上点「确认登录」
echo           - 没有抖音账号就先注册一个
echo.
echo  [第三步] 登录成功、看到自己的主页后，回到本窗口按「回车」
echo           下方将开始自动抓取并保存 Cookie…
echo ============================================================
echo.
pause
echo.
echo  → 正在抓取 Cookie，请稍候（浏览器可能再次弹窗，保持登录状态）…
echo.
rem 优先用 DD_DL_PY（若设置了独立下载器解释器），否则用当前 python
set "PY=%DD_DL_PY%"
if "%PY%"=="" set "PY=python"
"%PY%" -m tools.cookie_fetcher --config config.yml
echo.
echo ============================================================
if errorlevel 1 (
  echo  [失败] Cookie 抓取出错。常见原因：
  echo     1. 浏览器还没登录成功就按了回车
  echo        → 重新运行，先在浏览器登录好，再回来按回车
  echo     2. 二维码已过期
  echo        → 重新运行本脚本，再扫一次
  echo     3. 当前 python 缺 douyin-downloader 的依赖
  echo        → 先 pip install -r requirements.txt
  echo.
  echo  请按上面提示处理后，重新双击本脚本再试。
) else (
  echo  [成功] 看到提示 "Saved ..." 就说明 Cookie 已保存到 config.yml！
  echo.
  echo  接下来可以运行：
  echo     python scripts\media_to_notes.py "<抖音链接>" --detect
)
echo ============================================================
echo.
pause
