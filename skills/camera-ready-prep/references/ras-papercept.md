# RAS / PaperCept 投稿要求（IROS, ICRA, RA-L, CASE 等）

适用于通过 **PaperCept**（`ras.papercept.net` 及各会议 `*.papercept.net`）提交、IEEE RAS 主办或协办的会议/期刊。
规则随年份与版本变化，**务必对照当年 Call for Papers 与 Author's Kit 复核**，本文件给出常见稳定项。

## 1. PDF / 字体合规（提交系统自动检查，不过则拒收）

- **禁止 Type 3 字体**：PaperCept 的 PDF 检查会因 Type 3 字体拒收，并指明页码（如 "This document has Type 3 fonts (on page 6)"）。
  - **最常见来源**：matplotlib 默认 PDF 导出（DejaVu 系字体以 Type 3 位图嵌入）。其次是部分老旧 EPS/PS 转换。
  - **源头修复**（有画图脚本时）：导出前设 `matplotlib.rcParams['pdf.fonttype'] = 42`（TrueType；`= 1` 为 Type 1 亦可），重新生成该图。
  - **无源码时的修复**：用 Ghostscript 把该图文字**轮廓化为矢量路径** —— `bash "$FONT_FLATTENER" <figure>.pdf`（共享助手 `tools/flatten_pdf_fonts.sh`，按 SKILL.md 的解析链取得）。消除字体对象，保持矢量清晰度与边界框，不损失质量；若轮廓化后仍残留 Type 3，脚本会拒绝覆盖原文件。
- **所有字体必须嵌入**（`pdffonts` 中 `emb=yes`）。
- **纸张 US Letter**；使用 IEEE 会议模板（`ieeeconf` / `IEEEtran`，10pt，conference）。
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
