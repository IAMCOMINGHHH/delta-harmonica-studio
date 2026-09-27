# 三角洲口琴工坊

一个零依赖、离线优先的《三角洲行动》口琴学习与制谱网页：提供键位说明、虚拟演奏、数字简谱解析、本地曲库、试听和 JSON 导入导出。

> **重要：** 本项目不会向游戏发送按键。三角洲行动官方明确禁止能模拟按键的自动脚本、硬件宏和鼠标宏；使用这类工具可能导致限制或封禁。本项目只在浏览器中播放合成音、显示手动操作提示。

## 功能

- 点击虚拟按键或使用 `Z X C V B N M ,` 在网页内吹奏
- 输入数字简谱，自动生成音名和游戏手动键位提示
- 浏览器 Web Audio 试听、速度调节和逐音高亮
- 内置公版/传统旋律示例；自建曲库存入浏览器 `localStorage`
- 曲库 JSON 导入与导出，不上传任何用户数据
- 响应式界面，可直接部署到 GitHub Pages

## 运行

直接双击 `index.html`，或在项目目录运行：

```powershell
npm run serve
```

然后打开终端显示的本地地址。自动测试：

```powershell
npm test
```

## 简谱格式

| 写法 | 含义 |
| --- | --- |
| `1`–`7` | 中音自然音 |
| `1,` / `1'` | 低八度 / 高八度 |
| `#4` | 升半音 |
| `0` | 休止一拍 |
| `-` | 前一个音延长一拍 |
| `3/2` | 半拍 |
| `3*2` | 两拍 |
| `|` | 小节线（仅排版） |

示例：`1 2 3 4 | 5 6 7 1' | 0 #5 4 3 | 2 - 1 -`

## 默认游戏映射（需自行校对）

| 功能 | 默认操作 |
| --- | --- |
| 自然音 `1 2 3 4 5 6 7 1'` | `Z X C V B N M ,` |
| 低八度 | 按住鼠标左键 |
| 升半音 | 按住鼠标中键 |
| 高八度 | 按住鼠标右键 |

该映射来自社区项目的实测说明，游戏版本或玩家设置可能变化，请以游戏内界面为准。

## 调研参考

- [LianZiZhou/HarmonicaScript](https://github.com/LianZiZhou/HarmonicaScript)：键位、音域与转调思路
- [ChickenD233/harmonica-auto-player](https://github.com/ChickenD233/harmonica-auto-player)：MIDI 编辑与试听交互参考
- [Garena 官方禁用软硬件列表](https://deltaforce.garena.com/en/news/all/RD6289)：自动脚本与硬件宏风险边界

本项目没有复制上述项目的代码；仅参考公开文档描述后独立实现。

## 发布到 GitHub Pages

仓库 Settings → Pages → **Deploy from a branch**，选择 `main` / `/ (root)` 即可。

## 许可

[MIT](LICENSE)
