# RAS / PaperCept 投稿要求（IROS, ICRA, RA-L, CASE 等）

适用于通过 **PaperCept**（`ras.papercept.net` 及各会议 `*.papercept.net`）提交、IEEE RAS 主办或协办的会议/期刊。
规则随年份与版本变化，**务必对照当年 Call for Papers 与 Author's Kit 复核**，本文件给出常见稳定项。

## 1. PDF / 字体合规（提交系统自动检查，不过则拒收）

- **禁止 Type 3 字体**：PaperCept 的 PDF 检查会因 Type 3 字体拒收，并指明页码（如 "This document has Type 3 fonts (on page 6)"）。
  - **最常见来源**：matplotlib 默认 PDF 导出（DejaVu 系字体以 Type 3 位图嵌入）。其次是部分老旧 EPS/PS 转换。
  - **源头修复**（有画图脚本时）：导出前设 `matplotlib.rcParams['pdf.fonttype'] = 42`（TrueType；`= 1` 为 Type 1 亦可），重新生成该图。
  - **无源码时的修复**：用 Ghostscript 把该图文字**轮廓化为矢量路径** —— `bash "$FONT_FLATTENER" <figure>.pdf`（共享助手 `tools/flatten_pdf_fonts.sh`，按 SKILL.md 的解析链取得）。消除字体对象，保持矢量清晰度与边界框，不损失质量；若轮廓化后仍残留 Type 3，脚本会拒绝覆盖原文件。
- **所有字体必须嵌入**（`pdffonts` 中 `emb=yes`）。
- **纸张 US Letter**；使用 IEEE 会议模板（10pt，conference）。**注意 `ieeeconf` 与 `IEEEtran` 并不等价**：官方 Author's Kit 发的是 `ieeeconf.cls`（配 `root.tex`），版面写死 `\textwidth 7.0in`，天然满足边距要求；若改用 `\documentclass[conference]{IEEEtran}`，它默认排 7.16in（侧边 0.68in）、首页标题从 0.75in 起排，**每一页都会超边距**，必须额外覆盖版面，见下条。
- **页边距（提交系统逐页画框检查）**：US Letter 下四边 **≥ 0.75in（54pt）**，且**首页顶部 ≥ 1in（72pt）**（其余页顶部 0.75in）。检查结果 PDF 把合法排版区涂成灰底，超出部分肉眼可见，但不告诉你超了多少。用 IEEEtran 时在 `\documentclass` **之前**加（CLASSINPUT 只在该位置生效），`\renewcommand` 放其后：
  ```latex
  \newcommand{\CLASSINPUTinnersidemargin}{56pt}
  \newcommand{\CLASSINPUToutersidemargin}{56pt}
  \newcommand{\CLASSINPUTtoptextmargin}{61pt}    % 页顶浮动体比正文高约 5pt
  \newcommand{\CLASSINPUTbottomtextmargin}{56pt}
  \documentclass[conference]{IEEEtran}
  \renewcommand{\IEEEtitletopspaceextra}{11pt}   % 首页标题下压，清过 1in 线
  ```
  自检：`gs -dQUIET -dBATCH -dNOPAUSE -sDEVICE=bbox main.pdf` 逐页给出 `%%HiResBoundingBox: x0 y0 x1 y1`，左 = `x0`、右 = `612-x1`、上 = `792-y1`、下 = `y0`，全部需 ≥54pt（首页顶 ≥72pt）。**overfull hbox 检查发现不了这类问题** —— 版面框本身摆错位置时，每一行都"合法地"排在错误的框里，日志干净、overfull 计数为 0。
- 自检：`bash "$FONT_FLATTENER" --check <main>.pdf`（再对 `Images/*.pdf` 逐张排查定位元凶；有 Type 3 时退出码非 0，只读不写）。

## 2. 页数上限（含参考文献）

- **ICRA / IROS**：正文通常 **6 页**，允许 **+2 页** 付费加页，**硬上限 8 页**（含参考文献与附录）。
- **RA-L**：通常 **8 页**（含参考文献）。
- 加入大段内容（如新段落 + 公式）易顶破页数；若超限，向用户报告并给出具体删减建议，或把新增内容用 `% ` 注释保留待定，不要静默截断。
- 具体数字按年份/版本可能调整，提交前核对当年 CFP。

## 3. 提交表单中的摘要（Abstract 框）

- **纯文本**；超出框的部分被**截断**。
- 仅识别 HTML 标签：`<b> <i> <sub> <sup>`。
  - 例：`<i>E = mc</i><sup>2</sup>` → 显示为 E = mc²；`F<sub>ext</sub>` → F_ext。
- **不要放 LaTeX**：`\url{...}` 写成裸 URL；公式用上述标签或文字改写；去掉 `\cite`、标签、注释。
- 若正文摘要无公式/强调，则纯 prose 即可，无需任何标签。

## 4. 评审模式与 camera-ready 去匿名

- 投稿初审通常**匿名**（作者、单位、致谢隐去；常以注释形式保留在源码中）。
- **Camera-ready 去匿名**：恢复真实作者/单位/邮箱；启用致谢与基金声明；按 eCF 加 IEEE 版权脚注。

## 5. 查重（CrossCheck / iThenticate）

- 提交后给出累计相似度（如 33%）与在线报告（需 PIN + 密码登录 `ras.papercept.net`）。
- 会议**不会**为修改稿再次出分；需自行依报告降重。报告在登录区，外部无法直接抓取——属于"需用户提供"的资源。

## 6. 其他 camera-ready 常见项

- IEEE 版权声明（按 eCopyright 流程产生的文字）。
- 视频附件（如有）：分辨率/时长/编码按当年要求。
- 最终 PDF 通过 PaperCept 的 PDF 检查/IEEE PDF eXpress（视会议）。
