# 华锐 SL1500 型双馈式风机齿轮箱智能健康管理系统

这是一个面向毕业设计演示的风机齿轮箱智能健康管理原型系统，采用 Flask 后端和静态前端实现，覆盖实时监测、故障诊断、AI 问答、故障数据管理、健康报告、参数设置和数字孪生展示。

## 功能模块

- 实时监测：模拟 SCADA、振动、油液和功率数据，使用 SSE 推送到前端。
- 故障诊断：提取 RMS、峭度、峰值、峰值因子等特征，输出故障类型、置信度、健康评分和 RUL。
- 数据闭环：诊断结果写入故障记录，支持列表查看、详情查看和 CSV 导出。
- 健康报告：生成设备健康评分、关键指标和维护建议。
- AI 问答：基于内置专家知识库和实时状态生成运维建议。
- 系统设置：支持阈值配置和用户管理。

## 技术栈

- 后端：Flask、Flask-CORS、Flask-SQLAlchemy、SQLite、NumPy、Pandas、scikit-learn
- 前端：HTML、CSS、JavaScript、ECharts、Three.js、Font Awesome
- 数据库：`instance/gearbox_system.db`

## 启动方式

```powershell
cd "D:\bishe\Huaren SL1500 Type Doubly-Fed Wind Turbine Gearbox Intelligent Health Management System1.1"
.\.venv\Scripts\python.exe backend\app.py
```

启动后访问：

```text
http://127.0.0.1:5000
```

默认账号：

```text
用户名：admin
密码：admin
```

健康检查：

```text
http://127.0.0.1:5000/health
```

## 毕设答辩说明建议

系统可按五层架构介绍：

1. 数据采集层：模拟风机齿轮箱温度、振动、油液、功率等多源数据。
2. 数据处理层：完成滤波、包络分析、特征提取和数据融合。
3. 智能诊断层：基于特征规则和模拟模型输出故障类别、置信度、健康评分与 RUL。
4. 知识服务层：基于专家知识库生成问答式运维建议。
5. 应用展示层：监控大屏、故障记录、健康报告、用户权限和数字孪生。

当前系统是工程原型，诊断模型和传感器数据以模拟为主，已预留真实数据接入和真实模型替换位置。

## 演示注意事项

- 前端使用 ECharts、Three.js、Font Awesome 等外部 CDN。离线答辩前建议将这些资源下载到本地并修改 `frontend/index.html`。
- `SECRET_KEY` 可通过环境变量配置。开发环境默认使用 `dev-secret-key`。
- 正式演示可设置 `FLASK_DEBUG=0` 关闭调试模式。
