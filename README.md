# agent-skills

中文写作、文章配图和录音整理用的 Agent Skills，在 Claude Code 和 Codex 上日常使用。

Agent Skills for Chinese writing, article illustration, and turning recordings into notes. Skill content is in Chinese.

每个 skill 里的规则都来自一次真实的失败：结果看着正常，其实是错的。skill 里写了当时怎么发现的、该怎么做，所以同一个坑不会再踩一次。

## 里面有什么

**写作**

- [`natural-chinese-writing`](skills/natural-chinese-writing/)：把中文回复、产品说明、周报改得直接、有判断，保留原文的事实和不确定性。
- [`longform-polish`](skills/longform-polish/)：把写完的中文长文改到能发出去。按事实、结构、语感、术语括注、标点、排版的顺序一层一层改，每层改完先汇报。
- [`native-english-review`](skills/native-english-review/)：找出英文稿里母语者不会那么说的句子，分成「语法不成立」和「能懂但不地道」两档列清单，不直接改稿。

**文章配图**

- [`article-visuals`](skills/article-visuals/)：需求方用。判断文章哪里值得配图、哪里配了有害，写出图简报，验收交回来的图，做公众号封面。
- [`article-figure-render`](skills/article-figure-render/)：出图方用。按简报用脚本把说明图画出来，渲染前先查字体缺不缺字，处理中文断行。

**录音和录像**

- [`recording-to-notes`](skills/recording-to-notes/)：把一段录音或录屏剪掉空白、压小体积、转写成字幕，再写成笔记并出 PDF。

## 安装

**Claude Code**：把要用的 skill 目录放进 `~/.claude/skills/`。

```bash
git clone https://github.com/Userneima/agent-skills.git
mkdir -p ~/.claude/skills
cp -R agent-skills/skills/longform-polish ~/.claude/skills/
```

想跟着仓库更新，就用软链代替复制：

```bash
ln -s "$PWD/agent-skills/skills/longform-polish" ~/.claude/skills/longform-polish
```

**Codex 和其他支持 Agent Skills 的工具**：同样把目录放进那个工具读取 skill 的位置。每个目录里的 `SKILL.md` 就是 skill 本身，不依赖 Claude Code 的专有功能。

## 依赖

写作类和 `article-visuals` 只有一份 `SKILL.md`，装上就能用。

`article-figure-render` 的缺字检查脚本要 Python 和 Pillow（`pip install Pillow`）。里面的字体例子针对 macOS 的苹方，其他系统要自己挑一款覆盖简体中文的字体。

`recording-to-notes` 依赖最多，目前只在 macOS 上用过：

- 剪辑和压缩要 FFmpeg。
- 主路径走 [FluentFlow Local](https://github.com/Userneima/fluentflow-local)，一个开源的本机转写应用。装好并把它的 MCP 注册到你的 agent，就能用上云转写和自动写笔记；不装也能用，只是退到本地脚本，转写换成本地模型，笔记要 agent 自己写。
- 出 PDF 要 Google Chrome 和 Python 的 `markdown` 包（`pip install markdown`）。
- 源文件用 Finder 送进回收站，这一步只在 macOS 上能跑。

## 飞书

有几个 skill 提到把结果写进飞书文档时要注意的操作细节。那些内容已经写在 skill 里，不装任何飞书相关的 skill 也不影响使用。

## 许可

[MIT](LICENSE)
