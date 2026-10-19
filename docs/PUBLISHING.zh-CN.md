# GitHub 上传说明

## 仓库信息建议

仓库名称：

```text
urban-functional-suitability
```

About / Description：

```text
A GIS decision-support prototype for urban functional suitability analysis, map-based exploration, and knowledge-graph explanations.
```

Topics：

```text
python fastapi gis geopandas leaflet spatial-analysis urban-planning knowledge-graph decision-support
```

首页默认英文，并提供中文入口。两份说明的功能范围和已知问题一致。

## 整理内容

- 重写 `README.md`，增加 `README.zh-CN.md`。
- 增加 `.gitignore`、数据来源说明、已知问题和本上传说明。
- 源代码、配置、依赖清单和启动脚本逐字节保留。
- 保留输入样例、原技术方案与阶段文档。
- 从交付副本排除缓存、字节码、历史运行目录和生成结果；原始压缩包未改动。

排除的目录：

```text
__pycache__/
backend/cache/
backend/data/projects/
backend/sample_data/processed/
backend/sample_data/visualizations/
backend/test_output_osm/
```

原包两个网格中间文件分别约 **40.81 MiB** 和 **75.01 MiB**。GitHub 网页上传限制为单文件 25 MiB；这些生成结果没有必要随展示仓库上传。[GitHub 官方说明](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)

## 上传步骤

1. 解压 ZIP，进入 `urban-functional-suitability` 文件夹。
2. 在 GitHub 创建仓库，或使用准备好的空仓库。
3. 上传文件夹**里面的文件和子目录**，使 `README.md`、`backend/`、`frontend/` 位于仓库根目录。
4. 不要只上传 ZIP，这样别人才能直接浏览代码和首页。
5. 文件较多时优先使用 GitHub Desktop 或 Git；网页上传可分批完成。网页手动选文件时仍需检查选择内容，不要依赖 `.gitignore` 自动筛选。
6. 填写上面的 Description 和 Topics。

如果已有代码，只更新新文档和 `.gitignore` 即可。已被 Git 跟踪的缓存文件不会因新增 `.gitignore` 自动消失，需要另行取消跟踪。[GitHub 官方说明](https://docs.github.com/en/get-started/git-basics/ignoring-files)

首次上传的 commit message：

```text
Add urban suitability analysis prototype and documentation
```

已有代码、更新文档时的 commit message：

```text
Improve README, document limitations, and add ignore rules
```

## 建议继续补充的展示材料

最有价值的是两到三张**真实运行截图**：整体地图与输入图层、已生成的功能评分与网格详情、与结果对应的解释问答。建议放在 `docs/images/`，插入 README 的项目介绍之后。例如：

```markdown
![Study area and input layers](docs/images/overview.png)
```

整理版没有放入不存在的截图、演示链接或测试徽章。截图若来自另一版可运行代码，应说明对应版本，不要暗示当前快照已完成相同验证。

也可补充一段真实的个人贡献说明，但不能仅从目录推断独立开发、团队分工或用户测试经历。

## 发布说明

- 项目定位为可接收用户自有空间数据的通用分析工具，附带数据仅供演示。输入要求和界面/API 接入范围见 [KNOWN_ISSUES.md](KNOWN_ISSUES.md)。本次文档整理没有进行完整端到端运行测试，也不据此断言系统无法运行。
- 原 README 写了 MIT，但没有独立 `LICENSE`。确认权利归属和许可选择后再补文件；本次未新增软件授权，OSM 数据来源及 ODbL 链接已单独注明。
