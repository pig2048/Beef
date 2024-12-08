# Onefootball 自动任务签到

-  多账户并发处理
-  自动任务完成
-  定时签到（每12小时）

## 安装步骤

1. 确保已安装 Python 3.x
2. 克隆或下载此仓库
3. 安装依赖：
```bash
pip install -r requirements.txt
```

## 配置文件

### accounts.txt
(token获取方式，在浏览器中Ctrl+Shift+I或者F12,在Application>LocalStorage>AuthUserKey)
存放账户令牌，每行一个令牌。格式：
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxx...
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.yyy...
```

### proxy.txt
存放代理配置，每行一个代理。支持 SOCKS5 代理，格式：
```
127.0.0.1:7890
127.0.0.1:7891
```

## 使用方法

1. 运行脚本：

建议先创建虚拟环境
```bash
python -m venv venv
```
```bash
python onefootball_checkin.py
```

2. 选择操作：
   - 1️ 完成所有任务：立即执行所有账户的全部任务（先要在网页授权下x）
   - 2️ 启动定时签到：每12小时自动执行一次签到
   - 3️ 退出程序

## 日志说明

- 程序运行日志会显示在控制台
- ✓ 表示任务成功
- ✗ 表示任务失败
- 详细错误信息会记录在日志中

