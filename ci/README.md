# CI 实践指南 —— 在本项目里学习持续集成

> 目标:把"提交代码 → 自动编译/仿真/收覆盖率/出报告"这条流水线在本项目跑通,
> 并理解三大 CI 工具(Jenkins / GitLab CI / GitHub Actions)的取舍。
> 前置:先读懂 [pyverif/README.md](../pyverif/README.md),CI 只是"自动地"调它。

---

## 1. 什么是 CI?为什么验证工程师要会?

**持续集成(Continuous Integration)** = 每当有人改代码,就自动跑一遍构建和测试,
尽早发现"这次改动把别的东西搞坏了"。

在数字验证里,它解决一个真实痛点:testbench/RTL 几十人在改,
靠人工"记得跑回归"必然漏。CI 让机器**无人值守**地:

```
代码提交  →  编译       →  仿真        →  覆盖率收集   →  报告生成   →  通知
(commit)    (make com)    (make caseN)   (make cov)      (HTML/CSV)   (邮件)
```

本项目已经把这条链路拆成可被 CI 调用的命令(见下面的"映射表")。

---

## 2. 三大 CI 工具怎么选?

| 工具 | 跑在哪 | 能否驱动 VCS | 本项目对应文件 | 适合场景 |
|---|---|---|---|---|
| **Jenkins** | 公司**内网自建机** | ✅ 能(license/EDA 在内网) | [ci/Jenkinsfile](Jenkinsfile) | **IC 行业主流**,真回归 |
| **GitLab CI** | 内网自建 runner | ✅ 自建 runner 可装 VCS | [.gitlab-ci.yml](../.gitlab-ci.yml) | 内网用 GitLab 的团队 |
| **GitHub Actions** | GitHub **云端机** | ❌ 云端无 EDA/license | [.github/workflows/](../.github/workflows/) | 开源/纯软件层测试 |

**关键认知**:EDA 仿真器(VCS/Verdi)和 license 都在公司内网,GitHub/GitLab 的**云端**
机器跑不了真仿真。所以:

- **GitHub Actions** → 只跑 pyverif 的"离线模式"(纯 Python 模型,`-m "not sim"`),
  验证脚本/解析逻辑没坏。免费、零搭建,**最适合入门练手**。
- **Jenkins** → 跑在装了 VCS 的内网机上,`make com/caseN/cov` 驱动**真仿真**。
  **这是你将来在公司最可能用到的**。

> 建议学习顺序:先用 GitHub Actions 把概念跑通(不需要任何服务器),
> 再读 Jenkinsfile 理解企业真回归怎么搭。

---

## 3. 流水线设计(本项目如何映射)

| 流水线阶段 | 用到的命令 | 产物 |
|---|---|---|
| 代码提交 | git push / 定时触发 | 触发流水线 |
| 编译 | `make com`(真) / `pip install`(离线) | simv / 环境就绪 |
| 仿真 | `make case0 case1`(真) / `pytest`(离线) | sim.log / junit.xml |
| 覆盖率收集 | `make cov`(urg) / `pytest --cov` | urgReport/ |
| 报告生成 | `python scripts/run_regression.py` | regression.html / .csv |
| 趋势分析 | `python scripts/analyze_trend.py` | trend_*.png |
| 通知 | Jenkins emailext / Actions 邮件 step | 失败邮件 |

**门禁(gate)的原理**:CI 靠**退出码**判断成败。
[run_regression.py](../pyverif/scripts/run_regression.py) 全通过返回 `0`、有失败返回 `1`;
pytest 有用例失败也返回非 0。CI 一看到非 0 就把这次构建**标红**并通知 —— 这就是
"自动门禁"。这也是为什么脚本结尾要写 `raise SystemExit(main())`。

---

## 4. Nightly Regression(定时全量回归)

白天跑快测(冒烟),晚上跑慢的全量(压力/随机种子扫描),是行业惯例。三要素:

1. **定时触发**
   - Jenkins: `triggers { cron('H 2 * * *') }`
   - GitLab: 网页 *CI/CD → Schedules* + `$CI_PIPELINE_SOURCE == "schedule"`
   - Actions: `on: schedule: - cron: "0 18 * * *"`(注意是 **UTC** 时间!)
2. **多配置并行**:同时跑多 case / 多 Python 版本 / 多随机种子,缩短墙上时间。
   - Jenkins `parallel{}`、Actions `strategy.matrix`、GitLab 多 job。
3. **结果通知**:通常只在**失败**时发邮件(成功不打扰),见各文件的 notify/post 段。

> cron 时间换算坑:GitHub Actions 用 UTC。北京时间 = UTC+8,
> 想"北京 02:00 跑",cron 要写 `0 18 * * *`(前一天 UTC 18:00)。

---

## 5. 动手练(从易到难)

**第 0 步(前提)**:本项目当前还不是 git 仓库。先初始化并推到远端:
```bash
cd "入职前培训/UVM/apb_test"
git init && git add . && git commit -m "init APB project + pyverif + CI"
# 然后在 GitHub 建仓库,git remote add origin ...,git push
```

**练习 1 — GitHub Actions(不需要服务器,推荐先做)**
推上去后,进仓库 **Actions** 标签页,看 `APB 回归 (push/PR)` 自动跑。
跑完在页面底部下载 `apb-regression-reports` 看 HTML 报告。
故意把某个 `assert` 改错,再推一次 → 观察构建变红 + PR 出现叉。

**练习 2 — 本地模拟 CI 会跑的命令**(装好 Python 后,无需任何 CI):
```bash
cd pyverif
pip install -r requirements.txt
pytest -m "not sim" --junitxml=reports/junit.xml --html=reports/pytest_report.html --self-contained-html
python scripts/run_regression.py        # 看退出码: echo $?  (0=过,1=挂)
python scripts/analyze_trend.py
```
这就是 CI 在云端机里逐条敲的命令,本地先跑通,CI 基本就稳了。

**练习 3 — 读懂 Jenkinsfile**
对照 [ci/Jenkinsfile](Jenkinsfile) 的 5 个 stage,理解它如何 `make com → 并行 caseN
→ make cov → 跑 pyverif → 失败发邮件`。这是企业真回归的骨架。
有内网 Jenkins 时:新建 Pipeline 任务 → Pipeline script from SCM → 指向本仓库
`ci/Jenkinsfile` 即可。

**练习 4 — 给 nightly 加"多随机种子"**
在 [nightly.yml](../.github/workflows/nightly.yml) 的 matrix 里加一维 `seed: [1,2,3]`,
体会"多配置并行"如何提升回归覆盖。

---

## 6. 常见坑

- **云端跑仿真失败**:正常!GitHub/GitLab 云端没有 VCS。用 `-m "not sim"` 跳过,
  真仿真留给 Jenkins。
- **cron 不触发**:Actions 的 schedule 只在**默认分支**生效;且 UTC 时区;
  仓库 60 天无活动会自动暂停定时任务。
- **邮件密码泄露**:SMTP 账号密码必须放进 Secrets(Actions/GitLab)或凭据(Jenkins),
  **绝不**明文写进 yml/Jenkinsfile。
- **报告丢失**:记得 `if: always()` / `when: always` / `post{always{}}`,
  否则一失败就不归档报告,反而最该看的时候没报告。

---

## 7. 文件清单

```
apb_test/
├── .github/workflows/
│   ├── regression.yml      # push/PR 触发的快回归 (GitHub Actions)
│   └── nightly.yml         # 定时全量回归 + 多配置并行 + 邮件
├── .gitlab-ci.yml          # GitLab 流水线(等价实现)
└── ci/
    ├── Jenkinsfile         # 企业级:驱动真实 VCS 的回归骨架
    └── README.md           # 本文档
```
