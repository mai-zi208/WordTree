# WordTree（词族树）

> 把单词按词根串成一族来记的本机背单词 Web 应用：便签墙挑族 → 读联想和例句 → 五种零键盘题型自评 → 到期自动回来复习。

| 文档 | 回答什么 |
|---|---|
| 本文件 | 这是什么、怎么跑起来 |
| [docs/设计说明.md](docs/设计说明.md) | 代码怎么组织的、为什么这么设计 |
| [docs/需求说明书.md](docs/需求说明书.md) | 要做什么、做到什么程度算验收通过 |

## 📝 项目简介

**解决什么问题**——零碎时间背单词的三个老毛病：

- 记完就忘：没有排期，背过的词再没出现过。
- 单词孤立：`inspect` 和 `perspective` 明明同一个词根，却是两行互不相干的字母。
- 枯燥：例句和释义都是词典腔，脑子里留不下画面。

**思路**：一族 = 一个词根（`spect` = 看）+ 五到八个派生词，每个词配一条中文"整活"联想（`往里看：卫生员探头检查厨房`）和一段真实英文内容，复习时按遗忘曲线排期；一族里整体走不通就整族降档，而不是单个词各走各的。词库不够可以让智能体现编，但**必须你逐族点"接受"才进词库**。

**适用场景**：一次打开 2–5 分钟，手机上、地铁里、课间。不做账号、不做云同步、不部署公网，只监听 `127.0.0.1`。

## ✨ 核心功能

- [x] **便签墙**：一族一张便签，一行一张挂在同一根竖线上（左上角打孔），没学过的排前面；卡上直接写清 `spect = 看`、五个成员词、7 点进度阵、`N/5 已学 · 下次 X月X日`
- [x] **词族内容页**：族谱图 + 逐词卡片（联想条 / 微故事·小说片段·例句三种排式 / 简笔画），页内上下滚动读完这一族
- [x] **滚轮翻族**：滚到底再往外推一下就换到墙上相邻的一族，手机上用页头 `← →` 按钮或左右横扫
- [x] **五种零键盘题型**：看词猜义 / 看梗反推词 / 例句填空 / 词块点按成句 / 看图解词；干扰项只取同族词，答完每个选项的中文意思一起亮出
- [x] **四档自评 + 间隔重复**：秒对 / 想起来了 / 想了很久 / 完全忘了 → `0,1,2,4,7,15,30` 天七档
- [x] **族级回退**：一次练习里同族忘掉 ≥3 词，整族降回短间隔，收工页明说降的是整族
- [x] **智能体生成词族**：粘一批词或给一个词根 → 分组预览 → 逐族生成到暂存 → 你接受的那几族才落库；散词凑不出词根时改凑主题族
- [x] **按联想配图**：点一个词出一张（按 `meme` 画面生图，字绝不进画面），整族补齐走后台任务
- [x] **深浅色跟随系统**、`prefers-reduced-motion`、`aria-live` 播报、44px 拇指区
- [ ] 进度导出 / 导入、发音朗读、词表级别切换（见"未来计划"）

## 🛠 技术栈

| 层 | 用什么 |
|---|---|
| 前端 | Vue 3（`<script setup>`，无组件库、无 Pinia，一个 `reactive` store）+ Vue Router 4（hash 模式）+ Vite 8 |
| 后端 | FastAPI + uvicorn + httpx，Python 3.11 |
| 数据 | SQLite 单文件（WAL、外键级联，不用 ORM），`backend/data/wordmemo.db` |
| 文本智能体 | 任意 OpenAI 兼容的 chat 接口（默认 DeepSeek，`response_format: json_object`） |
| 生图智能体 | DashScope 多模态生成接口（可选，默认关） |
| 无障碍 | 原生语义标签 + `aria-label` / `aria-live`，无第三方库 |

依赖清单见 [backend/requirements.txt](backend/requirements.txt)（3 个包）与 [web/package.json](web/package.json)。**本项目不使用 HelloAgents 框架**，README 结构参考其第 16.4.1 节写法。

## 🚀 快速开始

### 环境要求

- Python 3.11（本机实测版本；`pydantic` v2 + `from __future__ annotations`，3.10 未验证）
- Node 20.19+（Vite 8 的下限；本机 24.18）
- 一个 OpenAI 兼容的模型密钥。**不配也能跑**：背词、复习、题型、排期全正常，只有"生成词族""配图"会返回 503 并提示去设置里填。

### 安装依赖

```bash
# 后端
python -m venv .venv && source .venv/Scripts/activate     # Windows Git Bash
python -m pip install -r backend/requirements.txt

# 前端
cd web && npm install && cd ..
```

### 配置 API 密钥

```bash
cp backend/.env.example backend/.env
# 编辑 backend/.env，填 DEEPSEEK_API_KEY（以及中转站的话改 DEEPSEEK_BASE_URL / DEEPSEEK_MODEL）
```

或者先跑起来，在首页右上角设置面板里填——它写回同一个 `backend/.env`，回显只有 `****后四位`，密钥永不出前端。生图另开一个开关：`WORDMEMO_IMAGE_PROVIDER=dashscope`。

### 运行项目

```bash
# 用法 A（推荐）：构建一次，之后只开一个进程，页面和接口都归它
cd web && npm run build && cd ..
cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
#   打开 http://127.0.0.1:8000/

# 用法 B（改前端时）：两个进程，Vite 把 /api /assets /media 代理到 8000
cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
cd web && npm run dev          # http://127.0.0.1:5273
```

### 打成 exe（给不想装 Python 的人）

```bash
cd web && npm run build && cd ..
bash packaging/build.sh        # 产出 packaging/dist/WordTree.exe，约 52MB
```

双击 `WordTree.exe`：**不弹任何窗口**，浏览器自动打开页面（默认 8000，被占就自动往后找空端口）。几点约定：

- 打进包里的只有前端产物、手绘插画和一份起始词库，这些都是只读的。词库、生成的配图、`.env`（密钥）落在 **exe 旁边**的 `data/` 和 `.env`，首次启动才复制出来，之后只写不覆盖。
- 起始词库就是打包当时 `backend/data/wordmemo.db` 的内容，**含你当前的学习记录**；不想带就删掉 spec 里 `starter` 那两行重打。
- 密钥不进包：换到人手上是空配置，打开设置填 key 才有 AI 生成，所以发 exe 别捎上 `.env`。
- 退出：页面右下角「退出程序」。命令行方式跑的进程照旧 Ctrl+C，那个按钮只在 exe 里出现。
- 重复双击不会叠服务：`data/wordtree.port` 记着当前实例的端口，探活成功就只多开一个标签页。
- 出事先看 `data/wordtree.log`（每次启动覆盖），里面写着实际端口、数据目录和访问日志。

### 常见报错

| 现象 | 原因与处理 |
|---|---|
| 打开 `/` 空白 | 没执行 `npm run build`，`web/dist` 不存在，后端就只挂了接口没挂页面 |
| 生成词族提示 503 | 没配密钥。填 `backend/.env` 或首页右上角设置 |
| 改了后端代码不生效 | `uvicorn` 不带 `--reload` 时不会热更，手动重启进程 |
| `.venv` 起不来、报找不到解释器 | 虚拟环境里的 python 路径指向已不存在的解释器，删掉 `.venv` 重建 |
| 生成的一族被整族拒绝 | 校验拦的是形式：词根不是单词的子串、联想超 20 字、`blank` 不是该词的变形、例句里找不到 `blank`。预览卡片上写着具体原因 |
| 换设备图没了 | 生成的图在 `backend/data/images/`，跟数据库一起被 git 忽略，本来就不跨设备 |
| 双击 exe 浏览器没开 | exe 所在目录不可写（只读的 U 盘、`C:\Program Files`），`data/` 建不出来；换个能写的目录再双击，或看 `data/wordtree.log` |

## 📖 使用示例

**界面流程**：首页 → 便签墙点一张卡（或今天到期时点"开始复习"）→ 词族页读完这一族 → `开始：先学 N 个新词` → 逐题作答 + 四档自评 → 收工页告诉你"这一族 X 月 X 日回来" → 之后每天打开只看 `N个词今天到期` 那一行。

**接口长什么样**（都是本机实测返回，字段即前端用的名字）：

```bash
curl -s http://127.0.0.1:8000/api/families | python -m json.tool | head -20
```

```json
{
  "id": 1, "family": "spect", "root": "spect", "rootMeaning": "看",
  "intro": "同一个「看」，看的方向不同，词义就分岔了。",
  "kind": "root", "source": "seed",
  "learned": 5, "total": 5, "due": 5, "stageSum": 10, "nextDate": "2026-10-21",
  "words": [{
    "word": "inspect", "pos": "v.", "gloss": "检查；视察",
    "part": "in- 往里 + spect 看",
    "meme": "往里看：卫生员探头检查厨房",
    "content": { "type": "sentence",
                 "en": "The health officer inspected the kitchen.",
                 "zh": "卫生员检查了厨房。" },
    "example": "The health officer inspected the kitchen.",
    "blank": "inspected",
    "img": "/assets/inspect.png",
    "imgZh": "一只手拿放大镜对着厨房角落，照出一只老鼠"
  }]
}
```

取一组题（`pool` ∈ `fresh/due/weak/all`，`mode=review` 时取全库到期词）：

```bash
curl -s -X POST http://127.0.0.1:8000/api/study/queue \
  -H "Content-Type: application/json" \
  -d '{"mode":"practice","familyId":1,"pool":"all"}'
```

```json
{
  "kind": "meme", "word": "inspect", "familyId": 1,
  "stem": { "tag": "看梗反推词", "text": "往里看：卫生员探头检查厨房" },
  "options": ["perspective", "spectator", "respect", "inspect"],
  "optionNotes": ["视角；观点", "观众；旁观者", "尊重；敬意", "检查；视察"],
  "answer": "inspect",
  "hint": "The health officer inspected the kitchen.　（检查；视察）",
  "zh": "卫生员检查了厨房。"
}
```

提交自评由服务端算排期（`rating` ∈ `fast/back/long/gone`）：

```bash
curl -s -X POST http://127.0.0.1:8000/api/study/commit \
  -H "Content-Type: application/json" \
  -d '{"results":[{"word":"inspect","rating":"gone"}],"familyId":1}'
```

**生成一族词**：首页右上角"新增词族"→ 粘一批词（`postwar, upstairs, abroad, jar, stove`）或只给一个词根（`tract`）→ 先看分组预览、勾掉不要的 → 逐族生成 → 每族卡片上点"加入便签墙"才入库，退出即丢弃，24 小时后由启动清扫兜底。

## 🎯 项目亮点

- **AI 内容必须人判**：批量生成的词族先躺在 `generation_jobs.result_json` 里，不落库；接受才写 `families/words`，拒绝随行删除。这条是产品红线，不是"以后再说"。
- **约 20 条硬校验 + 错误回喂**：词根必须原样出现在单词和构词拆解里、联想必须 ≤20 字的中文画面、`blank` 必须原样出现在例句里还得是该词的变形。不合格时把错误清单原样发给模型重来一次，而不是让人去擦。
- **排期是 50 行纯函数**：`scheduling.py` 不碰数据库，`stage × 四档自评` 全组合可以手推。族级回退用一条 SQL 完成。
- **出题强制"看梗反推词"**：每个新词至少一道，用来验证联想真的挂上了词形，而不是只是好笑。
- **配图提示词只写画面**：正向提示词里一个"不要"都不写（禁令会勾着模型把气泡和汉字画出来），全部禁令交给 `negative_prompt`；文件类型按 magic bytes 认，不信 Content-Type。
- **滚轮翻族的手势状态机**：只有"已顶到边缘 + 同一手势继续往外推 200px"才换族，普通阅读滚动完全不受影响；三重闸门（一次性标记 + 250ms 手势间隔 + 600ms 冷却）挡住惯性尾巴，一次甩动只翻一族。
- **无鉴权是设计而非疏漏**：只监听 `127.0.0.1`，所以队列接口直接带答案、`.env` 明文写在本机。真要上公网，第一件事是把答案拆到提交之后才回。

## 📊 性能评估

本机 `127.0.0.1`、当前词库 10 族 / 50 词 / 25 张图的实测：

| 项 | 数值 |
|---|---|
| `GET /api/families` | 12–16ms，24.3KB |
| `GET /api/families/{id}` | 12–38ms，2.6KB |
| 首屏 HTML | 8ms，884B |
| 前端产物 | JS 136.6KB（gzip 51.0KB）、CSS 28.0KB（gzip 6.6KB） |
| 一次学习会话 | 目标 ≤5 分钟（验收标准第 1 条） |

模型侧不在这张表里，它取决于你接的是谁：文本生成一次调用出一族（`WORDMEMO_LLM_TIMEOUT` 默认 90 秒），出图按模型差别很大（`z-image-turbo` 秒级、`qwen-image` 系列代码注释记的是实测约一分钟，所以 `WORDMEMO_IMAGE_TIMEOUT` 单给一个 180 秒）。没有压测——单用户本机应用，压了也没意义。

验收看的是记忆效果不是响应时间，指标清单在 [docs/需求说明书.md §8](docs/需求说明书.md)。

## 📁 项目结构

```
WordTree/
├── README.md                     # 本文件
├── LICENSE                       # MIT
├── assets/                       # 10 张手绘简笔画 + 1 张页头图（只读，程序永不覆盖）
├── docs/
│   ├── 需求说明书.md              # 做什么、验收标准、修订记录
│   └── 设计说明.md                # 代码怎么组织、为什么这么设计
├── backend/
│   ├── requirements.txt          # fastapi / uvicorn / httpx
│   ├── .env.example              # 密钥与模型配置模板（.env 本身被 git 忽略）
│   ├── data/                     # SQLite + 生成的图片（整个目录被 git 忽略）
│   └── app/
│       ├── main.py               # FastAPI 入口：CORS、静态挂载、路由注册、启动清扫
│       ├── config.py             # 进程环境 + .env 分层、热重载、密钥打码、打包时资源/数据分家
│       ├── db.py                 # 建表、迁移兜底、连接（WAL）
│       ├── repositories.py       # 纯 SQL，不含业务规则
│       ├── scheduling.py         # 间隔重复：7 档间隔、四档自评、族级回退
│       ├── question_builder.py   # 五种题型的出题引擎
│       ├── serializer.py         # DB 行 → camelCase 出参
│       ├── schemas.py            # 入参校验（camelCase → snake_case）
│       ├── seed_data.json        # 种子词族（spect / dict）
│       ├── seed.py
│       ├── routers/              # families / study / generation / images / settings
│       └── agents/               # llm.py（底层客户端）/ family_agent.py / image_agent.py
├── packaging/
│   ├── launcher.py               # exe 入口：落词库、挑空端口、起 uvicorn、开浏览器
│   ├── wordtree.spec             # PyInstaller 配置：打进前端产物/插画/起始词库，数据不进包
│   └── build.sh                  # 建 .venv-pack → 装 pyinstaller → 产出 WordTree.exe
└── web/
    ├── vite.config.js            # 端口 5273/5274，代理 /api /assets /media
    ├── dist/                     # 构建产物（被 git 忽略）
    └── src/
        ├── main.js  router.js  api.js  store.js  say.js
        ├── styles/app.css        # 设计令牌 + 全部样式，一个文件
        ├── views/                # HomeView / FamilyView / QuizView / DoneView
        └── components/           # HeroMasthead / StickyNoteWall / WordCard /
                                  # QuestionCard / RatePanel / GeneratePanel / SettingsPanel
```

## 🔮 未来计划

- [ ] `assets/` 的 15MB PNG 压成 WebP（页面上只画到 ≤260px，能省九成；要动用户手工放进来的资产，等点头）
- [ ] `speechSynthesis` 朗读例句（零资源、离线可用，替代视频）
- [ ] 进度导出 / 导入 JSON（换设备用；后端一条 `GET/POST /api/study/progress` 的事）
- [ ] 生词手动加入某族、词表级别切换（考研 / 六级）
- [ ] 把一次性断言脚本收成 pytest，钉住排期与出题两个纯函数
- [ ] 配图支持换画风（现在是固定的手绘水彩简笔画）

## 🤝 贡献指南

欢迎提 Issue 和 Pull Request。这个仓库的约定：

- 分支直接走 `master`，提交信息用**中文**，标题一句讲清"改了什么 + 为什么"（不写"更新""修复"这类空词），正文补动机和取舍。
- 别提交：`backend/.env`、`backend/data/`、`web/dist/`、`.venv/`、`node_modules/`（`.gitignore` 已挡，`git status` 里冒出来就先查是不是密钥）。
- 改前端记得 `npm run build` 再在本机看效果，页面是从 `web/dist` 发的；改后端记得重启进程。
- 视觉与文案的改动以"能不能一眼看懂"为准，别为整齐牺牲灵动感；新增功能先对齐 [docs/需求说明书.md](docs/需求说明书.md)，动架构再补 [docs/设计说明.md](docs/设计说明.md)。

## 📄 许可证

MIT，见 [LICENSE](LICENSE)。

## 👤 作者

- GitHub: [@mai-zi208](https://github.com/mai-zi208)

## 🙏 致谢

- 感谢 Datawhale 社区和 [Hello-Agents](https://github.com/datawhalechina/hello-agents) 项目，本 README 的章节结构参考其第 16 章 16.4.1 节。
- 模型能力来自 DeepSeek 与阿里云 DashScope 的公开接口；简笔画由项目所有者手绘。
