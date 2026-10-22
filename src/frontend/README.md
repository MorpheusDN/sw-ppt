# React 和 ECharts 前端

本次新增实现使用 React 19.3.1、React DOM 19.3.1、Apache ECharts 6.1.0 和 esbuild 0.28.2，与仓库 M2 的前端技术方向一致。版本已锁定在 package-lock.json。

`src/web/` 已包含构建资源，运行基础演示只需 Python，不需要 CDN 或重新安装 npm 依赖。

修改 JSX 后，在当前目录执行：

```powershell
npm ci
npm run build
```

构建文件写入 `../web/`，后端以同源地址提供静态资源和 JSON API。前端包括查询与时间控制、记忆列表、原文详情、ECharts 关系图、关系表、导入导出和查询结果保存。SVG 渲染器由 ECharts 提供；关系表也可用于文字核查。

源码 `main.jsx` 可编辑，构建文件 `web/app.js` 由工具生成。依赖许可证见 licenses 目录和构建旁的 app.js.LEGAL.txt。node_modules 不进入交付包。

参考：[React 官方集成文档](https://react.dev/learn/add-react-to-an-existing-project)、[Apache ECharts 按需引入文档](https://echarts.apache.org/handbook/en/basics/import/)。本地单机课程应用不包含生产级鉴权和部署配置。
